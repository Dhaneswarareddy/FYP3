"""Markdown tables for the reports, generated from the recomputed files (no hand-copied numbers)."""
import json; from pathlib import Path
import numpy as np, pandas as pd
ROOT = Path(__file__).resolve().parents[2]; T = ROOT/"final_reports/tables"
import sys; sys.path.insert(0, str(ROOT/"src")); import config as C; BATCH = {k: v["batch"] for k, v in C.MODELS.items()}
def md(df): return "\n".join(["| " + " | ".join(map(str, df.columns)) + " |", "|" + "---|"*len(df.columns)] + ["| " + " | ".join(map(str, r)) + " |" for r in df.values])
o = {}
m = pd.read_csv(T/"recomputed_metrics_all_runs.csv"); m = m[m.source=="grouped"]; p = m.pivot(index="run", columns="split", values=["accuracy","balanced_accuracy","macro_f1","qwk"])
sm = {d.name: json.load(open(d/"summary.json")) for d in (ROOT/"results/runs").iterdir() if (d/"summary.json").exists()}
exp = {"EfficientNetV2B0__ce__lowbatch":"E1","MobileNetV3Small__ce__lowbatch":"E2","EfficientNetV2B0__ce__init_fyp2":"E4","EfficientNetV2B0__ce__mix_fyp2":"E5"}
order = sorted(sm, key=lambda r: (-p.loc[r,("qwk","val")]))
o["all_runs"] = md(pd.DataFrame([{"Run": r.replace("__"," / "), "Input": sm[r].get("image_size",224), "Batch": sm[r].get("batch", BATCH[sm[r]["model"]]), "Best / run epochs": f"{sm[r]['best_epoch']} / {sm[r]['epochs_run']}", "Train min": round(sm[r]["train_time_s"]/60), "Val acc": f"{p.loc[r,('accuracy','val')]:.3f}", "Val QWK": f"{sm[r]['val']['qwk']:.3f}", "Test acc": f"{p.loc[r,('accuracy','test')]:.3f}", "Test bal. acc": f"{p.loc[r,('balanced_accuracy','test')]:.3f}", "Test QWK": f"{p.loc[r,('qwk','test')]:.3f}"} for r in order]))
q = pd.read_csv(T/"paired_effects.csv"); c = lambda d: f"{d.delta:+.3f} [{d.ci_lo:+.3f}, {d.ci_hi:+.3f}]" + (" *" if d.excludes_0 else "")
rows = []
for e in q.effect.unique():
    g = q[q.effect==e]; a = g.iloc[0]; rows.append({"Effect": e, "A − B": f"{a.run_a.replace('__',' / ')} − {a.run_b.split('__')[-1] if a.run_a.split('__')[0]==a.run_b.split('__')[0] else a.run_b}", "Δ val QWK": c(g[(g.split=='val')&(g.metric=='qwk')].iloc[0]), "Δ val acc": c(g[(g.split=='val')&(g.metric=='accuracy')].iloc[0]), "Δ test QWK": c(g[(g.split=='test')&(g.metric=='qwk')].iloc[0]), "Δ test acc": c(g[(g.split=='test')&(g.metric=='accuracy')].iloc[0])})
o["paired"] = md(pd.DataFrame(rows))
e = pd.read_csv(T/"external_recomputed.csv"); e = e.sort_values(["source","balanced_accuracy"], ascending=[False,False])
o["external"] = md(pd.DataFrame([{"Trained on": r.source, "Run": r.run.replace("__"," / "), "Input": r.input, "Acc": f"{r.accuracy:.3f}", "Bal. acc": f"{r.balanced_accuracy:.3f}", "Macro-F1": f"{r.macro_f1:.3f}", "QWK": f"{r.qwk:.3f}", "QWK CI (filename runs)": f"[{r.qwk_runcluster_lo:.2f}, {r.qwk_runcluster_hi:.2f}]", "AUC 0/1+ vs 2+/3+": f"{r.auc_low_vs_high:.3f}", "AUC 3+ vs rest": f"{r.auc_3plus_vs_rest:.3f}", "Spearman": f"{r.spearman_expected_vs_label:.2f}", "Mean pred. score": f"{r.mean_expected_score:.2f}", "Recall 0/1+/2+/3+": " / ".join(f"{x:.2f}" for x in json.loads(r.recall))} for r in e.itertuples()]))
o["oracle"] = md(pd.DataFrame([{"Trained on": r.source, "Run": r.run.replace("__"," / "), "Bal. acc": f"{r.balanced_accuracy:.3f}", "Bal. acc with true target prior": f"{r.oracle_prior_balacc:.3f}", "QWK": f"{r.qwk:.3f}", "QWK with true target prior": f"{r.oracle_prior_qwk:.3f}"} for r in e.itertuples()]))
s = pd.read_csv(T/"stain_only_rules.csv"); s = s[s.applied_to=="HER2-IHC-40x test"]
o["rules"] = md(pd.DataFrame([{"Features": r.features, "Fitted on": r.fitted_on, "Model": r.model, "Acc": f"{r.accuracy:.3f}", "Bal. acc": f"{r.balanced_accuracy:.3f}", "QWK": f"{r.qwk:.3f}", "Mean pred.": f"{r.mean_pred:.2f}"} for r in s.itertuples()]))
f = pd.read_csv(T/"cross_dataset_features_by_class.csv"); L=["0","1+","2+","3+"]
o["features"] = md(pd.DataFrame([{"Dataset": r.dataset, "Score": L[r.label], "DAB mean": f"{r.dabc_mean:.3f}", "DAB p90": f"{r.dabc_p90:.2f}", "Haem. mean": f"{r.hemc_mean:.3f}", "Saturation": f"{r.sat_mean:.0f}", "Background": f"{r.bg_brightness:.0f}", "Sharpness": f"{r.sharpness:.0f}", "High-freq. share": f"{r.hf_share:.3f}", "Spectrum p90 (cycles/224 px)": f"{r.spectrum_p90_freq:.0f}"} for r in f.itertuples()]))
d = pd.read_csv(T/"deploy_recomputed.csv")
o["deploy"] = md(pd.DataFrame([{"Variant": r.variant, "Split": r.split, "Status": r.status, "Size MB": r.size_mb, "Mac CPU ms": r.mac_latency_ms, "Acc": f"{r.accuracy:.3f}", "Bal. acc": f"{r.balanced_accuracy:.3f}", "QWK": f"{r.qwk:.3f}", "Recall 0/1+/2+/3+": " / ".join(f"{x:.2f}" for x in json.loads(r.recall.replace("'",'"')))} for r in d.itertuples()]))
v = pd.read_csv(T/"checkpoint_verification.csv")
o["verify"] = md(pd.DataFrame([{"Trained on": r.source, "Run": r.run.replace("__"," / "), "Input": r.input, "Max |Δp| own test": f"{r.own_test_max_abs_diff:.1e}", "Max |Δp| external": f"{r.external_max_abs_diff:.1e}", "Cache vs fresh resize": int(r.cache_vs_fresh_max_diff)} for r in v.itertuples()]))
sel = pd.read_csv(T/"selection_including_new_runs.csv")
o["selection"] = md(pd.DataFrame([{"Tier": r.tier, "Run": r.run.replace("__"," / "), "Params (M)": f"{r.params/1e6:.2f}", "Val QWK": f"{r.val_qwk:.3f}", "Val acc": f"{r.val_accuracy:.3f}", "Test QWK": f"{r.test_qwk:.3f}", "Test acc": f"{r.test_accuracy:.3f}"} for r in sel.sort_values(["tier","val_qwk"],ascending=[True,False]).itertuples()]))
json.dump(o, open(T/"md_tables.json","w"), indent=1); print({k: len(v) for k,v in o.items()})
print(o["paired"]); print(o["all_runs"][:900])
