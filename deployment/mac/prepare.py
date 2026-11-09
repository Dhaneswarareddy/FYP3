"""Mac-side deployment preparation. Stages, all short, none trains anything:

  python prepare.py --stage primary       copy the existing FP16 model and write its config
  python prepare.py --stage experimental  export the 224 px network to FP16 and write its config
  python prepare.py --stage reference     build the agreement sets (BCI val, development tiles; never the external test split)
  python prepare.py --stage validate [--limit N]  agreement of the engine with Keras on all of BCI val and test, and R_eval
  python prepare.py --stage bundle        build the Pi tarball
"""
import argparse, hashlib, json, shutil, sys, tarfile
from pathlib import Path
import numpy as np, pandas as pd
from PIL import Image
DEP = Path(__file__).resolve().parents[1]; ROOT = DEP.parent; sys.path[:0] = [str(DEP), str(ROOT / "src"), str(ROOT / "next_experiment"), str(ROOT / "next_experiment/harmonise2")]
ap = argparse.ArgumentParser(); ap.add_argument("--stage", required=True); ap.add_argument("--limit", type=int, default=0); a = ap.parse_args()
PRIMARY_RUN, EXP_RUN = "EfficientNetV2B0__ce__hires", "EfficientNetV2B0__ce"; H1 = ROOT / "next_experiment/outputs"; H2 = ROOT / "next_experiment/harmonise2/outputs"; N = 30
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest()
MAX_DP = 0.05            # FP16 vs Keras on any tile. Near-ties can still flip class, which is why probability change is the gate
COMMON = ["Research software. Not clinically validated. Do not use for diagnosis or treatment decisions.", "Scores individual tiles only. There is no slide-level or patient-level score."]


def write_cfg(name, d):
    json.dump(d, open(DEP / "configs" / f"{name}.json", "w"), indent=1); print("wrote", name, d["model_sha256"][:12])


def primary():
    src = ROOT / "results/deploy" / PRIMARY_RUN / "model_fp16.tflite"; dst = DEP / "models/primary_bci_hires_fp16/model.tflite"; shutil.copy2(src, dst); assert sha(src) == sha(dst)
    write_cfg("primary_bci_hires_fp16", dict(mode="primary", model_dir="primary_bci_hires_fp16", run=PRIMARY_RUN, precision="fp16", model_sha256=sha(dst), source_size=512, input_size=448, labels=["0", "1+", "2+", "3+"], stain_calibration=None, temperature=None,
        intended_input="BCI-like HER2 IHC tiles, 1024 px, about 0.46 um/px", warnings=COMMON + ["Performance applies to BCI-like tiles only. On HER2-IHC-40x this model scored 0.435 accuracy and very low 1+ and 2+ recall.", "Do not apply stain calibration to this model: it collapses."]))


def experimental():
    import tensorflow as tf
    tf.config.set_visible_devices([], "GPU")
    import common as U, deploy as D
    model = U.load_trained(ROOT / "results/runs" / EXP_RUN); dst = DEP / "models/experimental_stain224_fp16/model.tflite"; dst.write_bytes(D.convert_fp16(model))
    p = json.load(open(H1 / "harmonisation_params.json")); s = json.load(open(H1 / "dev_selection.json")); T = float(pd.read_csv(H2 / "E_calibration.csv").set_index(["run", "arm"]).loc[(EXP_RUN, "frozen_temp_scaled"), "T"])
    assert s["selected"] == "stain_p99"
    write_cfg("experimental_stain224_fp16", dict(mode="experimental", model_dir="experimental_stain224_fp16", run=EXP_RUN, precision="fp16", model_sha256=sha(dst), source_size=256, input_size=224, labels=["0", "1+", "2+", "3+"],
        stain_calibration=dict(arm="stain_p99", g_h=s["arm"]["g_h"], g_d=s["arm"]["g_d"], frozen=True, fitted_on="HER2-IHC-40x development tiles (unlabelled) against BCI train", source_file="next_experiment/outputs/harmonisation_params.json", source_sha256=sha(H1 / "harmonisation_params.json")),
        temperature=dict(T=T, affects="the reported confidence only, never the predicted class", fitted_on="HER2-IHC-40x development tiles (R_cal)"), intended_input="HER2-IHC-40x tiles only",
        warnings=COMMON + ["Experimental. Gains were fitted for one external dataset. Other sites need their own unlabelled calibration, which this package does not provide.", "Do not use on BCI tiles: the gains reduce BCI balanced accuracy from 0.875 to 0.407.", "Weak on borderline scores: test recall 1+ 0.18, 2+ 0.57 with 2+ precision 0.09."]))


def reference():
    import h2_lib as L
    from h2_lib import H
    import her2_infer.preprocess as PP
    from her2_infer import Her2Engine
    rng = np.random.default_rng(2026); m = pd.read_csv(ROOT / "splits/split_manifest_grouped.csv"); v = m[m.split == "val"].reset_index(drop=True); z = np.load(ROOT / "results/runs" / PRIMARY_RUN / "predictions.npz")
    idx = np.sort(np.concatenate([rng.choice(np.where(v.label == k)[0], N, replace=False) for k in range(4)])); X = np.stack([np.asarray(Image.open(ROOT / "data/ihc_512_eval448" / p).convert("RGB"), np.uint8) for p in v.path[idx]])
    e = Her2Engine("primary"); q = np.stack([e.invoke(x.astype(np.float32)) for x in X]); np.savez_compressed(DEP / "reference/primary.npz", tiles_preprocessed=X, keras=z["val"][idx], tflite_mac=q, labels=v.label.values[idx].astype(int), paths=v.path.values[idx])
    raw = DEP / "reference/raw_primary"; raw.mkdir(exist_ok=True)
    for i, j in enumerate(idx[::15]):
        Image.open(ROOT.parent / "FYP/data/raw/BCI_dataset/IHC" / v.path[j]).convert("RGB").save(raw / f"tile{i}.png")
    r = pd.read_csv(H2 / "R_index.csv"); ev = np.where(r.subset == "R_eval")[0]; pc = np.load(H2 / f"preds/C/{EXP_RUN}__frozen.npz")["prob"]; d = H.DevZip()
    idx = np.sort(np.concatenate([rng.choice(ev[r.label.values[ev] == k], N, replace=False) for k in range(4)])); X = np.stack([PP.resize_two_step(d.read(n), 256, 224) for n in r.name.values[idx]]); e = Her2Engine("experimental")
    q = np.stack([e.invoke(e.from_resized(x)) for x in X]); np.savez_compressed(DEP / "reference/experimental.npz", tiles_preprocessed=X, keras=pc[idx], tflite_mac=q, labels=r.label.values[idx], paths=r.name.values[idx])
    raw = DEP / "reference/raw_experimental"; raw.mkdir(exist_ok=True)
    for i, n in enumerate(r.name.values[idx[::15]]):
        d.read(n).save(raw / f"tile{i}.png")
    print("reference sets written", {f.name: round(f.stat().st_size / 2**20, 1) for f in (DEP / "reference").glob("*.npz")})


def validate():
    from harmonise_lib import DevZip
    from her2_infer import Her2Engine
    rep = {}; m = pd.read_csv(ROOT / "splits/split_manifest_grouped.csv"); z = np.load(ROOT / "results/runs" / PRIMARY_RUN / "predictions.npz"); e = Her2Engine("primary")
    for sp in ("val", "test"):
        s = m[m.split == sp].reset_index(drop=True); s = s.iloc[:a.limit] if a.limit else s; k = z[sp][:len(s)]
        q = np.stack([e.invoke(np.asarray(Image.open(ROOT / "data/ihc_512_eval448" / p).convert("RGB"), np.float32)) for p in s.path]); rep[f"primary_{sp}"] = dict(n=len(s), class_agreement=float((q.argmax(1) == k.argmax(1)).mean()), max_abs_dp=float(np.abs(q - k).max()), accuracy=float((q.argmax(1) == s.label.values).mean()))
    r = pd.read_csv(H2 / "R_index.csv"); ev = np.where(r.subset == "R_eval")[0]; ev = ev[:a.limit] if a.limit else ev; pc = np.load(H2 / f"preds/C/{EXP_RUN}__frozen.npz")["prob"]; e = Her2Engine("experimental"); d = DevZip()
    q = np.stack([e.invoke(e.preprocess(d.read(r.name.values[i]))) for i in ev]); rep["experimental_R_eval"] = dict(n=len(ev), class_agreement=float((q.argmax(1) == pc[ev].argmax(1)).mean()), max_abs_dp=float(np.abs(q - pc[ev]).max()), accuracy=float((q.argmax(1) == r.label.values[ev]).mean()))
    rep["worst_class_agreement"] = min(v["class_agreement"] for v in rep.values()); rep["worst_max_abs_dp"] = max(v["max_abs_dp"] for k, v in rep.items() if k.startswith(("primary", "experimental")))
    rep["go"] = bool(rep["worst_max_abs_dp"] < MAX_DP); rep["limit"] = a.limit; f = "validation_smoke.json" if a.limit else "validation_full.json"; json.dump(rep, open(DEP / "reference" / f, "w"), indent=1); print(json.dumps(rep, indent=1)); sys.exit(0 if rep["go"] else 2)


def bundle():
    out = ROOT / "deployment/her2_fyp3_pi_bundle.tar.gz"; items = ["her2_infer", "configs", "models", "reference", "predict.py", "benchmark.py", "verify_bundle.py", "requirements_pi.txt", "install_pi.sh"]
    shutil.copy2(ROOT / "DEPLOYMENT_README.md", DEP / "DEPLOYMENT_README.md"); items.append("DEPLOYMENT_README.md")
    with tarfile.open(out, "w:gz") as t:
        for i in items:
            t.add(DEP / i, arcname=f"her2_fyp3_pi_bundle/{i}", filter=lambda x: None if "__pycache__" in x.name else x)
    print("wrote", out, round(out.stat().st_size / 2**20, 1), "MB")


{"primary": primary, "experimental": experimental, "reference": reference, "validate": validate, "bundle": bundle}[a.stage]()
