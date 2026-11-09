"""CPU check: the driver's 'none' arm must reproduce the stored baseline probabilities through prepare(), and unit gains
must leave a tile unchanged. Reads no labels and computes no metric."""
import json, sys
import numpy as np, pandas as pd, tensorflow as tf
tf.config.set_visible_devices([], "GPU")
import harmonise_lib as H
names = H.test_tiles(); idx = np.linspace(0, len(names) - 1, 16).astype(int); sub = [names[i] for i in idx]; none = dict(name="none", scale=1.0, g_h=1.0, g_d=1.0)
for run in ["EfficientNetV2B0__ce", "MobileNetV3Small__ce__hires"]:
    info = H.run_info(run); base = pd.read_csv(H.P["external_baseline_dir"] / f"BCI__{run}.csv").set_index("path").loc[sub, [f"p{k}" for k in range(4)]].values
    p = H.predict(H.build(info, 1.0), [H.read_test(n) for n in sub], info, none); print(run, "max |dp| vs stored baseline", float(np.abs(p - base).max()), flush=True)
x = np.asarray(H.read_test(sub[0]).resize((224, 224)), np.uint8); y = H.apply_stain_gains(x, 1.0, 1.0)
print("unit gains: max pixel change", float(np.abs(y - x).max()))
y2 = H.apply_stain_gains(x, 0.3, 0.3); h0 = H.stain_od(x)[1].mean(); h1 = H.stain_od(np.uint8(np.round(y2)))[1].mean(); print("DAB mean before/after gain 0.3:", round(float(h0), 3), round(float(h1), 3))
