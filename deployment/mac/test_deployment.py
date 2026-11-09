"""Deployment checks, seconds to run. Compares preprocessing with the frozen HARMONISE-1 code and tries to break mode separation."""
import json, shutil, subprocess, sys, tempfile
from pathlib import Path
import cv2, numpy as np, pandas as pd
from PIL import Image
DEP = Path(__file__).resolve().parents[1]; ROOT = DEP.parent; sys.path[:0] = [str(DEP), str(ROOT / "next_experiment"), str(ROOT / "next_experiment/harmonise2")]
import harmonise_lib as H
import her2_infer.preprocess as P
from her2_infer import Her2Engine, load_config
fails = []
def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name, detail); fails.extend([] if ok else [name])
r = pd.read_csv(ROOT / "next_experiment/harmonise2/outputs/R_index.csv"); d0 = H.DevZip(); A = [P.resize_two_step(d0.read(n), 256, 224) for n in r.name.values[np.linspace(0, len(r) - 1, 200).astype(int)]]; idx = range(len(A))
v, m = np.meshgrid(np.arange(256), np.arange(256), indexing="ij"); k = m <= v; every = np.stack([v[k], m[k], m[k]], -1).astype(np.uint8)[None]          # S depends only on max and min
sa, sb = P.hsv_saturation(every), cv2.cvtColor(every, cv2.COLOR_RGB2HSV)[..., 1]; check("background mask (S < 8) equals OpenCV for every possible pixel", ((sa < 8) == (sb < 8)).all(), f"{sa.size} max/min pairs; S itself differs by 1 on {(sa != sb).sum()}")
for g in [(0.2545270680571192, 0.5044797263953001)]:
    d = max(float(np.abs(P.apply_stain_gains(A[i], *g) - H.apply_stain_gains(A[i], *g)).max()) for i in idx); check("stain gains equal HARMONISE-1 on 200 tiles", d == 0.0, f"max diff {d}")
n = d0.names[10]; pil = d0.read(n); cp, ce = load_config("primary"), load_config("experimental")
ip = dict(input_size=448, source_size=512); ie = dict(input_size=224, source_size=256); none = dict(name="none", scale=1.0, g_h=1.0, g_d=1.0); arm = dict(name="stain_p99", scale=1.0, g_h=ce["stain_calibration"]["g_h"], g_d=ce["stain_calibration"]["g_d"])
check("primary preprocessing equals HARMONISE-1 path", np.array_equal(P.preprocess_primary(pil, cp), H.prepare(pil, ip, none))); check("experimental preprocessing equals HARMONISE-1 path", np.array_equal(P.preprocess_experimental(pil, ce), H.prepare(pil, ie, arm)))
check("primary preprocessing has no stain step", cp["stain_calibration"] is None and not np.array_equal(P.preprocess_primary(pil, cp), P.apply_stain_gains(P.preprocess_primary(pil, cp).astype(np.uint8), 0.25, 0.5)))
check("frozen gains match HARMONISE-1 file", json.load(open(ROOT / "next_experiment/outputs/dev_selection.json"))["arm"]["g_d"] == ce["stain_calibration"]["g_d"])
check("modes use different models", cp["model_sha256"] != ce["model_sha256"])
def bad(mut, mode):
    with tempfile.TemporaryDirectory() as t:
        b = Path(t); shutil.copytree(DEP / "configs", b / "configs"); shutil.copytree(DEP / "models", b / "models"); f = b / "configs" / f"{ {'primary': 'primary_bci_hires_fp16', 'experimental': 'experimental_stain224_fp16'}[mode]}.json"; c = json.load(open(f)); mut(c, b); json.dump(c, open(f, "w"))
        try:
            Her2Engine(mode, 1, base=b); return False
        except ValueError:
            return True
check("rejects stain gains added to primary", bad(lambda c, b: c.update(stain_calibration=dict(g_h=.25, g_d=.5)), "primary"))
check("rejects changed gains in experimental", bad(lambda c, b: c["stain_calibration"].update(g_d=0.4), "experimental"))
check("rejects 224 px primary", bad(lambda c, b: c.update(input_size=224), "primary"))
check("rejects a swapped model file", bad(lambda c, b: shutil.copy2(DEP / "models/experimental_stain224_fp16/model.tflite", b / "models/primary_bci_hires_fp16/model.tflite"), "primary"))
PY = sys.executable
s = subprocess.run([PY, "predict.py", "--mode", "experimental", "--input", "reference", "--out", "/tmp/x.csv"], cwd=DEP, capture_output=True, text=True); check("experimental needs explicit flag", s.returncode != 0 and "i-understand" in s.stderr + s.stdout)
print("ALL PASS" if not fails else f"{len(fails)} FAILED: {fails}"); sys.exit(1 if fails else 0)
