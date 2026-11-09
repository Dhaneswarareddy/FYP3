"""Audit 6 (CPU, 24 images each, no training): load one checkpoint through the same path external_eval.py used, then
reproduce (a) saved own-test predictions and (b) the external CSV probabilities. Checks checkpoint loading,
preprocessing and class order end to end. Appends one JSON line to tables/checkpoint_verification.jsonl."""
import json, sys; from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT/"src"))
import numpy as np, pandas as pd, tensorflow as tf
tf.config.set_visible_devices([], "GPU")
from PIL import Image
import common as U, config as C
src, run = sys.argv[1], sys.argv[2]; N = 24
root = C.RUNS_DIR if src == "BCI" else C.FYP2_ROOT/"results/runs"
s = json.load(open(root/run/"summary.json")); size = s.get("image_size", 224); ss = (s.get("variant_spec") or {}).get("source_size", 256)
C.IMAGE_SIZE = size; model = U.load_trained(root/run)
z = np.load(root/run/"predictions.npz")
if src == "BCI":
    m = pd.read_csv(C.MANIFEST); m = m[m.split == "test"].reset_index(drop=True); paths = [C.ROOT/"data"/(f"ihc_{ss}_eval{size}" if size != 224 else "ihc_256")/p for p in m.path[:N]]
else:
    m = pd.read_csv(C.FYP2_ROOT/"splits/split_manifest.csv"); m = m[m.split == "test"].reset_index(drop=True); paths = [C.FYP2_ROOT/"HER2 SCORES DATA/Generated_HER2_images"/p for p in m.path[:N]]
x = np.stack([np.asarray(Image.open(p).convert("RGB").resize((size, size), Image.BILINEAR)) for p in paths]).astype(np.float32)
own = float(np.abs(model.predict(x, batch_size=8, verbose=0) - z["test"][:N]).max())
d = pd.read_csv(ROOT/f"results/external/her2_40x/{src}__{run}.csv"); idx = np.linspace(0, len(d)-1, N).astype(int)
cdir = C.ROOT/"data"/f"her2_40x_{ss}_eval{size}"
xe = np.stack([np.asarray(Image.open(cdir/p).convert("RGB")) for p in d.path.values[idx]]).astype(np.float32)
ext = float(np.abs(model.predict(xe, batch_size=8, verbose=0) - d[[f"p{k}" for k in range(4)]].values[idx]).max())
# cached tile equals a fresh resize of the raw file, and the folder gives the label
raw = ROOT.parent/"FYP/data/raw/HER2-IHC-40x/wsi_test"/d.path.values[idx[3]]
fresh = np.asarray(Image.open(raw).convert("RGB").resize((ss, ss), Image.LANCZOS).resize((size, size), Image.BILINEAR)).astype(np.int16)
cache = float(np.abs(fresh - xe[3]).max())
r = dict(source=src, run=run, input=size, own_test_max_abs_diff=own, external_max_abs_diff=ext, cache_vs_fresh_max_diff=cache)
open(ROOT/"final_reports/tables/checkpoint_verification.jsonl", "a").write(json.dumps(r)+"\n"); print(r, flush=True)
