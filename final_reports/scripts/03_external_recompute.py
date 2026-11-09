"""Audit 3 (no TensorFlow): recompute HER2-IHC-40x results from the per-tile CSVs; threshold-free ranking;
filename-run proxies for slides; oracle label-shift diagnostic. The external labels are used only for reporting."""
import json, re, sys; from pathlib import Path
import numpy as np, pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import roc_auc_score, cohen_kappa_score, f1_score, recall_score, confusion_matrix, balanced_accuracy_score
ROOT = Path(__file__).resolve().parents[2]; EXT = ROOT/"results/external/her2_40x"; OUT = ROOT/"final_reports/tables"
FYP2 = ROOT.parent/"FYP2"
g = pd.read_csv(ROOT/"splits/split_manifest_grouped.csv"); PRI = {"BCI": np.bincount(g[g.split=="train"].label, minlength=4)/ (g.split=="train").sum(), "FYP2": np.ones(4)/4}
files = sorted(p for p in EXT.glob("*__*.csv"))
base = pd.read_csv(files[0])[["path","label","filename_label"]]
base["num"] = base.path.str.extract(r"_(\d+)\.png$")[0].astype(int)
base["fscore"] = base.path.str.extract(r"her2-(.+?)-score")[0]
base = base.sort_values(["fscore","num"]); gap = base.groupby("fscore").num.diff().fillna(1)
base["run_id"] = ((gap > 1) | (base.fscore != base.fscore.shift())).cumsum()
base = base.sort_index()
runs = base.groupby("run_id").agg(n=("path","size"), score=("fscore","first"), first=("num","min"), last=("num","max"), labels=("label", lambda s: sorted(set(s))))
runs.to_csv(OUT/"external_filename_runs.csv"); print("filename runs:", len(runs), runs.groupby("score").n.agg(["size","sum","median","max"]).to_dict("index"))
tb = []; conf = {}
y_all = base.label.values
for f in files:
    d = pd.read_csv(f); src, run = f.stem.split("__", 1)
    assert (d.path == pd.read_csv(files[0]).path).all()
    y = d.label.values; P = d[[f"p{k}" for k in range(4)]].values; a = P.argmax(1); E = P @ np.arange(4)
    j = json.load(open(f.with_suffix(".json")))
    acc = (a == y).mean(); q = cohen_kappa_score(y, a, weights="quadratic"); bal = balanced_accuracy_score(y, a); mf = f1_score(y, a, average="macro")
    assert (a == d.pred.values).all()
    Q = P * (np.bincount(y, minlength=4)/len(y)) / PRI[src]; Q /= Q.sum(1, keepdims=True); b = Q.argmax(1)
    # cluster bootstrap over filename runs
    rid = base.set_index("path").run_id.reindex(d.path).values; ids = np.unique(rid); idx = {r: np.where(rid == r)[0] for r in ids}; rng = np.random.default_rng(42); ba, bq = [], []
    for _ in range(1000):
        i = np.concatenate([idx[r] for r in rng.choice(ids, len(ids))]); ba.append(balanced_accuracy_score(y[i], a[i]) if len(set(y[i]))==4 else np.nan); bq.append(cohen_kappa_score(y[i], a[i], weights="quadratic"))
    tb.append(dict(source=src, run=run, input=j["input_size"], accuracy=acc, json_accuracy=j["all"]["accuracy"], balanced_accuracy=bal, macro_f1=mf, qwk=q, json_qwk=j["all"]["qwk"],
        qwk_runcluster_lo=np.nanpercentile(bq,2.5), qwk_runcluster_hi=np.nanpercentile(bq,97.5), balacc_runcluster_lo=np.nanpercentile(ba,2.5), balacc_runcluster_hi=np.nanpercentile(ba,97.5),
        spearman_expected_vs_label=spearmanr(E, y)[0], auc_3plus_vs_rest=roc_auc_score(y==3, E), auc_low_vs_high=roc_auc_score(y>=2, E), auc_0_vs_1=roc_auc_score(y[y<=1]==1, E[y<=1]), auc_2_vs_3=roc_auc_score(y[y>=2]==3, E[y>=2]),
        macro_ovr_auc=np.mean([roc_auc_score(y==k, P[:,k]) for k in range(4)]),
        mean_expected_score=E.mean(), oracle_prior_accuracy=(b==y).mean(), oracle_prior_balacc=balanced_accuracy_score(y,b), oracle_prior_qwk=cohen_kappa_score(y,b,weights="quadratic"),
        recall=recall_score(y,a,average=None,labels=range(4)).round(3).tolist(), pred_share=(np.bincount(a,minlength=4)/len(a)).round(3).tolist()))
    conf[f.stem] = confusion_matrix(y, a, labels=range(4)).tolist()
t = pd.DataFrame(tb); t.to_csv(OUT/"external_recomputed.csv", index=False); json.dump(conf, open(OUT/"external_confusions.json","w"), indent=1)
pd.set_option("display.width",250); pd.set_option("display.max_columns",40)
print(t[["source","run","input","accuracy","balanced_accuracy","macro_f1","qwk","qwk_runcluster_lo","qwk_runcluster_hi","spearman_expected_vs_label","auc_3plus_vs_rest","auc_low_vs_high","auc_0_vs_1","auc_2_vs_3","macro_ovr_auc","mean_expected_score"]].round(3).to_string(index=False))
print(t[["source","run","oracle_prior_accuracy","oracle_prior_balacc","oracle_prior_qwk"]].round(3).to_string(index=False))
print("max diff vs stored json:", (t.accuracy-t.json_accuracy).abs().max(), (t.qwk-t.json_qwk).abs().max())
print("label mismatch rows:", base[base.label != base.filename_label][["path","label","filename_label"]].head(12).to_string())
