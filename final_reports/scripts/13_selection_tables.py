"""Tables for the selection document and report (no TensorFlow, no inference)."""
import json; from pathlib import Path
import numpy as np, pandas as pd
ROOT = Path(__file__).resolve().parents[2]; T = ROOT/"final_reports/tables"; H2 = ROOT/"next_experiment/harmonise2/outputs"; H1 = ROOT/"next_experiment/outputs"
def md(df): return "\n".join(["| " + " | ".join(map(str, df.columns)) + " |", "|" + "---|"*len(df.columns)] + ["| " + " | ".join(map(str, r)) + " |" for r in df.values])
o = json.load(open(T/"md_tables.json")); L = ["0","1+","2+","3+"]; m = pd.read_csv(ROOT/"splits/split_manifest_grouped.csv"); z = np.load(ROOT/"results/runs/EfficientNetV2B0__ce__hires/predictions.npz"); rows = []; ref = []
print(m.refined_label.dropna().unique()[:8])
for sp in ["val", "test"]:
    s = m[m.split == sp].reset_index(drop=True); y = s.label.values; a = z[sp].argmax(1); c = np.zeros((4,4), int); np.add.at(c, (y, a), 1); rec = np.diag(c)/c.sum(1); pre = np.diag(c)/c.sum(0); f1 = 2*pre*rec/(pre+rec)
    for i, k in enumerate(L): rows.append({"Split": f"BCI {sp}", "Score": k, "Tiles": int(c[i].sum()), "Recall": f"{rec[i]:.3f}", "Precision": f"{pre[i]:.3f}", "F1": f"{f1[i]:.3f}"})
    rl = pd.to_numeric(s.refined_label, errors="coerce") if s.refined_label.dropna().astype(str).str.fullmatch(r"\d+(\.0)?").all() else s.refined_label.astype(str).str.replace("+","",regex=False).pipe(pd.to_numeric, errors="coerce")
    k = rl.notna().values; r = rl.values
    for i in range(4):
        q = k & (y == i)
        if q.any(): ref.append({"Split": f"BCI {sp}", "Slide label": L[i], "Tiles with patch label": int(q.sum()), "Patch label agrees with slide label": f"{(r[q]==y[q]).mean():.3f}", "Model agrees with slide label": f"{(a[q]==y[q]).mean():.3f}", "Model agrees with patch label": f"{(a[q]==r[q]).mean():.3f}"})
o["primary_bci_classes"] = md(pd.DataFrame(rows)); o["primary_refined"] = md(pd.DataFrame(ref)); print(o["primary_refined"])
t = pd.read_csv(T/"h2_dev_vs_h1_test.csv"); names = {"EfficientNetV2B0__ce":"EfficientNetV2B0 224","MobileNetV3Small__ce":"MobileNetV3Small 224","MobileNetV3Large__corn":"MobileNetV3Large CORN 224","DenseNet121__ce":"DenseNet121 224","EfficientNetV2B0__ce__hires":"EfficientNetV2B0 448"}
rows = []
for run, n in names.items():
    for sp, lab in [("dev R (4,593)","dev"),("test (1,847)","test")]:
        for arm in ["none","frozen"]:
            r = t[(t.run==run)&(t.split==sp)&(t.arm==arm)].iloc[0]; rows.append({"Model": n, "Split": lab, "Arm": "raw" if arm=="none" else "stain_p99", "Acc": f"{r.accuracy:.3f}", "Bal. acc": f"{r.balanced_accuracy:.3f}", "Macro-F1": f"{r.macro_f1:.3f}", "QWK": f"{r.qwk:.3f}", "Recall 0/1+/2+/3+": f"{r.rec_0:.2f} / {r['rec_1+']:.2f} / {r['rec_2+']:.2f} / {r['rec_3+']:.2f}", "Precision 2+": f"{r['pre_2+']:.2f}", "F1 1+": f"{r['f1_1+']:.2f}", "F1 2+": f"{r['f1_2+']:.2f}"})
o["h1h2"] = md(pd.DataFrame(rows))
D = pd.read_csv(T/"h2_dose_all.csv"); rows = []
for dom, lab in [("external_dev","HER2-IHC-40x dev"),("bci_val","BCI val")]:
    for run, n in [("EfficientNetV2B0__ce","224"),("EfficientNetV2B0__ce__hires","448")]:
        for arm, an in [("none","raw"),("dab_only","DAB gain only"),("haem_only","Haematoxylin gain only"),("frozen","Both (stain_p99)")]:
            r = D[(D.domain==dom)&(D.run==run)&(D.arm==arm)].iloc[0]; rows.append({"Tiles": lab, "Input": n, "Arm": an, "Bal. acc": f"{r.balanced_accuracy:.3f}", "QWK": f"{r.qwk:.3f}", "Recall 3+": f"{r['recall_3+']:.3f}", "Recall 2+": f"{r['recall_2+']:.3f}", "Mean score": f"{r.mean_expected_score:.2f}"})
o["dose"] = md(pd.DataFrame(rows))
A = pd.read_csv(H2/"A_eval_EfficientNetV2B0__ce.csv"); c = A[A.family=="composition"]; o["composition"] = md(pd.DataFrame([{"3+ share in fit sample": f"{r.id.split('_')[1]}", "g_d": f"{r.g_d:.3f}", "Bal. acc": f"{r.balanced_accuracy:.3f}", "Recall 0": f"{r.recall_0:.2f}", "Recall 2+": f"{r._asdict().get('_x', 0) if False else A.loc[r.Index,'recall_2+']:.2f}", "Recall 3+": f"{A.loc[r.Index,'recall_3+']:.2f}"} for r in c.itertuples()]))
json.dump(o, open(T/"md_tables.json","w"), indent=1); print(o["composition"]); print(o["dose"][:600])
