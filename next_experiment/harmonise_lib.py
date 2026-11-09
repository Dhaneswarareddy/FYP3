"""Shared functions for HARMONISE-1. No function here reads a class label unless its name says so."""
import io, json, re, sys, zipfile
from pathlib import Path
import cv2
import numpy as np
from PIL import Image

NEXT = Path(__file__).resolve().parent
ROOT = NEXT.parent
sys.path.insert(0, str(ROOT / "src"))
CFG = json.load(open(NEXT / "experiment_config.json"))
P = {k: (ROOT / v).resolve() if k != "external_dev_inner" else v for k, v in CFG["paths"].items()}

# Ruifrok & Johnston vectors, same as FYP3/src/analysis_data.py (rows: haematoxylin, eosin, DAB)
RGB_FROM_HED = np.array([[0.65, 0.70, 0.29], [0.07, 0.99, 0.11], [0.27, 0.57, 0.78]], np.float32)
HED_FROM_RGB = np.linalg.inv(RGB_FROM_HED).astype(np.float32)
LEVELS = {"0": 0, "1+": 1, "2+": 2, "3+": 3}


class DevZip:
    """The WSI-based training split, read inside the archive (stored uncompressed, nothing is extracted)."""
    def __init__(self):
        self.z = zipfile.ZipFile(P["external_dev_zip"])
        self.i = zipfile.ZipFile(self.z.open(P["external_dev_inner"]))
        self.names = sorted(n for n in self.i.namelist() if n.endswith(".png"))

    def read(self, name):
        return Image.open(io.BytesIO(self.i.read(name))).convert("RGB")


def test_tiles():
    return sorted(str(p.relative_to(P["external_test_dir"])) for p in P["external_test_dir"].glob("class_*/*.png"))


def read_test(name):
    return Image.open(P["external_test_dir"] / name).convert("RGB")


def label_from_name(name):
    """Class folder of a tile; used only by the dev evaluation and the final test report."""
    return LEVELS[name.split("/")[0][len("class_"):]]


def illumination(rgb):
    """Tile illumination I0: mean of background pixels (HSV S < 8), else the 99th percentile per channel."""
    bg = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)[..., 1] < 8
    I0 = rgb[bg].mean(0) if bg.mean() >= 0.02 else np.percentile(rgb.reshape(-1, 3), 99, axis=0)
    return np.maximum(I0.astype(np.float32), 1.0), bg


def stain_od(rgb):
    """(tissue-pixel H OD, tissue-pixel DAB OD), relative to the tile's own illumination."""
    I0, bg = illumination(rgb)
    od = -np.log(np.maximum(rgb.astype(np.float32) / I0, 1e-6))
    hed = od.reshape(-1, 3) @ HED_FROM_RGB
    keep = ~bg.reshape(-1) if (~bg).sum() > 100 else np.ones(bg.size, bool)
    return np.clip(hed[keep, 0], 0, None), np.clip(hed[keep, 2], 0, None)


def apply_stain_gains(rgb, g_h, g_d):
    """One fixed H and DAB gain per domain. Tiles keep their relative order: no per-tile normalisation."""
    I0, _ = illumination(rgb)
    od = -np.log(np.maximum(rgb.astype(np.float32) / I0, 1e-6))
    hed = od.reshape(-1, 3) @ HED_FROM_RGB * np.array([g_h, 1.0, g_d], np.float32)
    return np.clip(I0 * np.exp(-(hed @ RGB_FROM_HED)).reshape(rgb.shape), 0, 255).astype(np.float32)


def prepare(pil, run_info, arm):
    """1024 px tile -> network input. s = 1 is the exact baseline path (Lanczos to source, bilinear to input)."""
    size, source = run_info["input_size"], run_info["source_size"]
    if arm["scale"] == 1.0:
        im = pil.resize((source, source), Image.LANCZOS).resize((size, size), Image.BILINEAR)
    else:
        t = target_size(size, arm["scale"])
        im = pil.resize((t, t), Image.LANCZOS)
    x = np.asarray(im, np.uint8)
    return apply_stain_gains(x, arm["g_h"], arm["g_d"]) if arm["g_d"] != 1.0 or arm["g_h"] != 1.0 else x.astype(np.float32)


def target_size(input_size, scale):
    return max(int(round(input_size / scale)), 32)


def run_info(run):
    s = json.load(open(ROOT / "results" / "runs" / run / "summary.json"))
    return dict(run=run, model=s["model"], loss=s["loss"], input_size=s.get("image_size", 224),
                source_size=(s.get("variant_spec") or {}).get("source_size", 256))


def build(info, scale):
    """The trained weights in a network of the arm's input size. Convolutions and global pooling make the
    weights independent of input size; at scale 1 this is the original network."""
    import common as U
    import config as C
    C.IMAGE_SIZE = target_size(info["input_size"], scale) if scale != 1.0 else info["input_size"]
    _, infer, _ = U.build_model(info["model"], info["loss"])
    infer.load_weights(ROOT / "results" / "runs" / info["run"] / "model.weights.h5")
    return infer


def predict(model, pils, info, arm, chunk=32):
    out = []
    for k in range(0, len(pils), chunk):
        x = np.stack([prepare(p, info, arm) for p in pils[k:k + chunk]])
        out.append(model.predict(x, batch_size=chunk, verbose=0))
    return np.concatenate(out)


def make_arms(params):
    """Pre-registered grid: none, scale only, stain only, stain at the primary percentile + scale."""
    p0 = CFG["stain_fit"]["primary_percentile"]
    gain = lambda p: params["gains"][str(p)]
    arms = [dict(name="none", scale=1.0, g_h=1.0, g_d=1.0)]
    arms += [dict(name=f"scale{s:g}", scale=s, g_h=1.0, g_d=1.0) for s in CFG["scale_grid"]]
    arms += [dict(name=f"stain_p{p}", scale=1.0, g_h=gain(p)["g_h"], g_d=gain(p)["g_d"]) for p in CFG["stain_fit"]["percentiles"]]
    arms += [dict(name=f"stain_p{p0}+scale{s:g}", scale=s, g_h=gain(p0)["g_h"], g_d=gain(p0)["g_d"]) for s in CFG["scale_grid"]]
    return arms


def n_factors(arm):
    return int(arm["scale"] != 1.0) + int(arm["g_d"] != 1.0 or arm["g_h"] != 1.0)


def metrics(y, prob):
    from sklearn.metrics import balanced_accuracy_score, cohen_kappa_score, confusion_matrix, f1_score, recall_score, roc_auc_score
    a = prob.argmax(1); e = prob @ np.arange(4)
    m = dict(n=int(len(y)), accuracy=float((a == y).mean()), balanced_accuracy=float(balanced_accuracy_score(y, a)),
             macro_f1=float(f1_score(y, a, average="macro", labels=range(4), zero_division=0)),
             qwk=float(cohen_kappa_score(y, a, weights="quadratic")), mean_expected_score=float(e.mean()),
             true_mean_score=float(y.mean()), recall=recall_score(y, a, average=None, labels=range(4), zero_division=0).round(4).tolist(),
             predicted_share=(np.bincount(a, minlength=4) / len(a)).round(4).tolist(),
             confusion=confusion_matrix(y, a, labels=range(4)).tolist())
    if len(set(y)) == 4:
        m["auc_3plus_vs_rest"] = float(roc_auc_score(y == 3, e)); m["auc_low_vs_high"] = float(roc_auc_score(y >= 2, e))
    return m


def filename_groups(names):
    """Consecutive filename numbers within a score: the only grouping visible in the release. It over-counts
    the 21 test slides, so CIs built on it are still optimistic."""
    rows = [(re.search(r"her2-(.+?)-score", n).group(1), int(re.search(r"_(\d+)\.png$", n).group(1)), i) for i, n in enumerate(names)]
    rows.sort(); g = np.zeros(len(names), int); c = 0
    for j, (sc, num, i) in enumerate(rows):
        if j and (sc != rows[j - 1][0] or num != rows[j - 1][1] + 1):
            c += 1
        g[i] = c
    return g
