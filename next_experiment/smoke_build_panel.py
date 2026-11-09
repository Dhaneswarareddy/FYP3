"""CPU check of H.build for every panel run: at scale 1 it must reproduce the saved BCI test predictions on 8 tiles,
and at every grid scale it must build and return valid probabilities. Uses no external tiles and trains nothing."""
import json, sys
import numpy as np, pandas as pd, tensorflow as tf
tf.config.set_visible_devices([], "GPU")
from PIL import Image
import harmonise_lib as H
from harmonise_lib import CFG, ROOT
run = sys.argv[1]; info = H.run_info(run)
m = pd.read_csv(H.P["bci_manifest"]); m = m[m.split == "test"].reset_index(drop=True)
d = ROOT/"data"/(f"ihc_{info['source_size']}_eval{info['input_size']}" if info["input_size"] != 224 else "ihc_256")
x = np.stack([np.asarray(Image.open(d/p).convert("RGB").resize((info["input_size"],)*2, Image.BILINEAR)) for p in m.path[:8]]).astype(np.float32)
saved = np.load(ROOT/"results/runs"/run/"predictions.npz")["test"][:8]
diff = float(np.abs(H.build(info, 1.0).predict(x, verbose=0) - saved).max()); res = dict(run=run, input=info["input_size"], max_abs_diff_scale1=diff, ok=diff < 1e-3)
for s in CFG["scale_grid"]:
    t = H.target_size(info["input_size"], s); p = H.build(info, s).predict(np.random.default_rng(0).uniform(0, 255, (2, t, t, 3)).astype(np.float32), verbose=0)
    res[f"scale{s:g}_px"] = t; res["ok"] = res["ok"] and bool(np.allclose(p.sum(1), 1, atol=1e-3))
print(json.dumps(res), flush=True)
