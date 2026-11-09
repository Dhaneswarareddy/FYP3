"""Audit 12 (no TensorFlow, no inference): recompute HARMONISE-2 from its stored probabilities and reconcile it with
HARMONISE-1 and the BCI results. External test numbers come only from HARMONISE-1's stored confusion matrices."""
import hashlib, json, sys; from pathlib import Path
import numpy as np, pandas as pd
ROOT = Path(__file__).resolve().parents[2]; H2 = ROOT/"next_experiment/harmonise2/outputs"; H1 = ROOT/"next_experiment/outputs"; T = ROOT/"final_reports/tables"
sys.path.insert(0, str(ROOT/"next_experiment/harmonise2"))
from sklearn.metrics import cohen_kappa_score
pd.set_option("display.width", 240); pd.set_option("display.max_columns", 40); pd.set_option("display.max_rows", 200)
def cm(y, a):
    c = np.zeros((4, 4), int); np.add.at(c, (y, a), 1); return c
def stats(c):
    c = np.array(c); rec = np.diag(c)/np.maximum(c.sum(1), 1); pre = np.diag(c)/np.maximum(c.sum(0), 1); f1 = 2*pre*rec/np.maximum(pre+rec, 1e-12)
    yt = np.repeat(range(4), c.sum(1)); yp = np.concatenate([np.repeat(range(4), c[i]) for i in range(4)])
    return dict(accuracy=np.trace(c)/c.sum(), balanced_accuracy=rec.mean(), macro_f1=f1.mean(), qwk=cohen_kappa_score(yt, yp, weights="quadratic", labels=range(4)), rec=rec, pre=pre, f1=f1)
r = pd.read_csv(H2/"R_index.csv"); y = r.label.values; out = {}
out["R_has_test_names"] = int(r.name.str.contains("_test_").sum()); out["R_rows"] = len(r)
d = pd.read_csv(H2/"C_classwise.csv"); conf = json.load(open(H2/"C_confusions.json")); bad = 0; rows = []
for rec in d.itertuples():
    p = np.load(H2/f"preds/C/{rec.run}__{rec.arm}.npz"); a = p["prob"].argmax(1); s = stats(cm(y, a))
    bad += abs(s["balanced_accuracy"]-rec.balanced_accuracy) > 1e-6 or abs(s["qwk"]-rec.qwk) > 1e-6 or cm(y, a).tolist() != conf[f"{rec.run}__{rec.arm}"]
    rows.append(dict(run=rec.run, arm=rec.arm, split="dev R (4,593)", **{k: s[k] for k in ("accuracy","balanced_accuracy","macro_f1","qwk")}, **{f"rec_{k}": s["rec"][i] for i, k in enumerate(["0","1+","2+","3+"])}, **{f"pre_{k}": s["pre"][i] for i, k in enumerate(["0","1+","2+","3+"])}, **{f"f1_{k}": s["f1"][i] for i, k in enumerate(["0","1+","2+","3+"])}))
out["C_rows_not_reproduced"] = int(bad)
fs = pd.read_csv(H1/"final_summary.csv"); ext = json.load(open(T/"external_confusions.json"))
for q in fs.itertuples():
    for arm, c in [("none", ext["BCI__"+q.run]), ("frozen", json.loads(q.harmonised_confusion))]:
        s = stats(c); rows.append(dict(run=q.run, arm=arm, split="test (1,847)", **{k: s[k] for k in ("accuracy","balanced_accuracy","macro_f1","qwk")}, **{f"rec_{k}": s["rec"][i] for i, k in enumerate(["0","1+","2+","3+"])}, **{f"pre_{k}": s["pre"][i] for i, k in enumerate(["0","1+","2+","3+"])}, **{f"f1_{k}": s["f1"][i] for i, k in enumerate(["0","1+","2+","3+"])}))
t = pd.DataFrame(rows); t.to_csv(T/"h2_dev_vs_h1_test.csv", index=False); print(t[t.arm=="frozen"].sort_values(["run","split"]).round(3)[["run","split","accuracy","balanced_accuracy","macro_f1","qwk","rec_0","rec_1+","rec_2+","rec_3+","pre_2+","pre_3+","f1_1+","f1_2+"]].to_string(index=False))
ev = (r.subset == "R_eval").values; rows = []
from h2_lib import ece
for run in ["EfficientNetV2B0__ce", "MobileNetV3Small__ce"]:
    for arm in ["none", "frozen"]:
        p = np.load(H2/f"preds/C/{run}__{arm}.npz")["prob"]; e, _ = ece(y[ev], p[ev], 15); rows.append(dict(run=run, arm=arm, ece=e, stored=float(pd.read_csv(H2/"E_calibration.csv").query("run==@run and arm==@arm").ece.iloc[0])))
print(pd.DataFrame(rows).round(4).to_string(index=False))
S = pd.read_csv(H2/"A_params_summary.csv"); B = pd.read_csv(H2/"A_params_bootstrap.csv"); b = B[(B.n==1500)&(B["mode"]=="both")&(B.percentile==99)]; print("A recompute g_d cv", round(b.g_d.std()/b.g_d.mean(),4), "g_h cv", round(b.g_h.std()/b.g_h.mean(),4)); print(S[(S["mode"]=="both")&(S.percentile==99)][["n","g_h_cv","g_d_cv"]].round(3).to_string(index=False))
print(S[(S["mode"]=="both")&(S.n==1500)][["percentile","g_d_mean","g_d_lo","g_d_hi","g_d_cv"]].round(3).to_string(index=False))
D = pd.concat([pd.read_csv(f) for f in sorted(H2.glob("D_external_*.csv"))+sorted(H2.glob("D_bci_*.csv"))]); D.to_csv(T/"h2_dose_all.csv", index=False)
print(D[["domain","run","arm","scale","g_h","g_d","balanced_accuracy","qwk","mean_expected_score","recall_0","recall_1+","recall_2+","recall_3+","predicted_share_2+"]].round(3).to_string(index=False))
print(pd.read_csv(H2/"pseudogroup_folds.csv")[["fold","n_fit_tiles","n_eval_tiles","g_h","g_d","balanced_accuracy","accuracy","recall_2+","recall_3+"]].round(3).to_string(index=False)); print(pd.read_csv(H2/"E_calibration_flips.csv").round(3).to_string(index=False))
for f in ["outputs/verify.json"]: print(f, (H2.parent/f).exists())
print("results/deployment exists:", (ROOT/"results/deployment").exists())
for nm, fp in [("H1", H1/"protected_before.json"), ("H2", H2/"protected_before.json")]:
    b = json.load(open(fp)); ch = [k for k, v in b.items() if not (ROOT/k).exists() or hashlib.sha256(open(ROOT/k,"rb").read()).hexdigest() != v]; print(nm, len(b), "protected,", len(ch), "changed", ch[:6])
print(json.dumps(out)); json.dump(out, open(T/"h2_verification.json","w"), indent=1)
