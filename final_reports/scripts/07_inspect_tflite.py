"""Audit 7 (CPU, no conversion): inspect the deployed TFLite files, recompute metrics from the stored confusion
matrices and compare FP32-TFLite with the saved Keras predictions on 48 validation tiles."""
import json, sys, collections; from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT/"src"))
import numpy as np, pandas as pd, tensorflow as tf
tf.config.set_visible_devices([], "GPU")
from PIL import Image
from sklearn.metrics import cohen_kappa_score
D = ROOT/"results/deploy/EfficientNetV2B0__ce__hires"; run = ROOT/"results/runs/EfficientNetV2B0__ce__hires"
z = np.load(run/"predictions.npz"); m = pd.read_csv(ROOT/"splits/split_manifest_grouped.csv"); va = m[m.split=="val"].reset_index(drop=True)
x = np.stack([np.asarray(Image.open(ROOT/"data/ihc_512_eval448"/p).convert("RGB")) for p in va.path[:48]]).astype(np.float32)
out = {}
for v in ["fp32", "fp16", "int8"]:
    it = tf.lite.Interpreter(model_path=str(D/f"model_{v}.tflite")); it.allocate_tensors()
    i, o = it.get_input_details()[0], it.get_output_details()[0]
    ops = collections.Counter(d["op_name"] for d in it._get_ops_details())
    p = []
    for im in x:
        it.set_tensor(i["index"], im[None].astype(i["dtype"])); it.invoke(); p.append(it.get_tensor(o["index"])[0].astype(np.float32))
    p = np.stack(p); k = z["val"][:48]
    out[v] = dict(input_dtype=str(i["dtype"].__name__), output_dtype=str(o["dtype"].__name__), input_shape=i["shape"].tolist(), n_ops=sum(ops.values()), top_ops=ops.most_common(8), quantize_ops=ops.get("QUANTIZE",0), dequantize_ops=ops.get("DEQUANTIZE",0),
                  max_abs_diff_vs_keras_48=float(np.abs(p-k).max()), class_agreement_48=float((p.argmax(1)==k.argmax(1)).mean()))
print(json.dumps(out, indent=1)); s = pd.read_csv(D/"deploy_summary.csv"); rows = []
y = {sp: z[f"y_{sp}"] for sp in ["val","test"]}
def met(c):
    c = np.array(c); n = c.sum(1); y_t = np.repeat(range(4), n); pr = np.concatenate([np.repeat(range(4), c[i]) for i in range(4)])
    return dict(accuracy=np.trace(c)/c.sum(), balanced_accuracy=(np.diag(c)/n).mean(), qwk=cohen_kappa_score(y_t, pr, weights="quadratic"), recall=(np.diag(c)/n).round(3).tolist())
for r in s.itertuples():
    for sp in ["val","test"]:
        rec = met(json.loads(getattr(r, f"{sp}_confusion"))); rows.append(dict(variant=r.variant, split=sp, status=r.status, size_mb=round(r.size_mb,2), mac_latency_ms=round(r.mac_latency_ms,1), **rec, stored_accuracy=getattr(r, f"{sp}_accuracy"), stored_qwk=getattr(r, f"{sp}_qwk")))
t = pd.DataFrame(rows); t.to_csv(ROOT/"final_reports/tables/deploy_recomputed.csv", index=False); print(t.round(4).to_string(index=False))
json.dump(out, open(ROOT/"final_reports/tables/tflite_inspection.json","w"), indent=1, default=str)
kc = lambda sp: np.array(pd.crosstab(pd.Series(y[sp]), pd.Series(z[sp].argmax(1))).reindex(index=range(4),columns=range(4),fill_value=0)).tolist()
print("fp32 confusion equals Keras predictions: val", kc("val")==json.loads(s.val_confusion[0]), "test", kc("test")==json.loads(s.test_confusion[0]))
