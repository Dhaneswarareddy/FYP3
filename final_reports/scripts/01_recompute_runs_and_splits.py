"""Audit 1 (no TensorFlow): recompute every run's metrics from predictions.npz with labels taken from the
manifests, compare with summary.json and metrics_all.csv, and check splits, class mapping and leakage.
Writes only to final_reports/tables/."""
import json, sys
from pathlib import Path
import numpy as np, pandas as pd
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from sklearn.metrics import accuracy_score, balanced_accuracy_score, cohen_kappa_score, f1_score, confusion_matrix
OUT = ROOT / "final_reports" / "tables"; R = ROOT / "results"; FYP2 = ROOT.parent / "FYP2"

def m(y, p):
    a = p.argmax(1)
    return dict(accuracy=accuracy_score(y, a), balanced_accuracy=balanced_accuracy_score(y, a),
                macro_f1=f1_score(y, a, average="macro"), qwk=cohen_kappa_score(y, a, weights="quadratic"))

man = {"grouped": pd.read_csv(ROOT/"splits/split_manifest_grouped.csv"), "official": pd.read_csv(ROOT/"splits/split_manifest_official.csv"),
       "fyp2": pd.read_csv(FYP2/"splits/split_manifest.csv")}
metrics_all = pd.read_csv(R/"metrics_all.csv")
rows = []
for kind, root in [("grouped", R/"runs"), ("official", R/"runs_official"), ("fyp2", FYP2/"results/runs")]:
    M = man[kind]
    for d in sorted(root.iterdir()):
        if not (d/"summary.json").exists(): continue
        s = json.load(open(d/"summary.json")); z = np.load(d/"predictions.npz")
        for sp in ["val", "test"]:
            y = M[M.split == sp].label.values.astype(int)
            yz = z[f"y_{sp}"].astype(int) if f"y_{sp}" in z.files else None
            p = z[sp]; r = m(y, p)
            ms = s[sp]
            rec = dict(source=kind, run=d.name, split=sp, n=len(y), labels_match_manifest=None if yz is None else bool((yz == y).all()),
                       probs_sum_to_1=bool(np.allclose(p.sum(1), 1, atol=1e-3)), **{k: round(v, 5) for k, v in r.items()},
                       max_abs_diff_vs_summary=max(abs(r[k]-ms[k]) for k in ["accuracy","macro_f1","qwk"]),
                       in_metrics_all=bool(((metrics_all.run == d.name)).any()) if kind == "grouped" else None)
            rows.append(rec)
t = pd.DataFrame(rows); t.to_csv(OUT/"recomputed_metrics_all_runs.csv", index=False)
print("runs:", t.groupby("source").run.nunique().to_dict())
print("labels mismatch rows:", (t.labels_match_manifest == False).sum(), "| probs bad:", (~t.probs_sum_to_1).sum(), "| max diff vs summary:", t.max_abs_diff_vs_summary.max())
print("grouped runs missing from metrics_all.csv:", sorted(t[(t.source=="grouped")&(t.in_metrics_all==False)].run.unique()))

# splits
g = man["grouped"]; o = man["official"]; f = man["fyp2"]; chk = {}
chk["grouped_counts"] = g.split.value_counts().to_dict(); chk["official_counts"] = o.split.value_counts().to_dict(); chk["fyp2_counts"] = f.split.value_counts().to_dict()
chk["grouped_class_by_split"] = pd.crosstab(g.split, g.label).to_dict("index")
chk["grouped_fragments_crossing_splits"] = int((g.groupby("fragment").split.nunique() > 1).sum())
lv = {"0":0,"1+":1,"2+":2,"3+":3}
chk["bci_filename_label_mismatch"] = int((g.path.str.extract(r"_(0|1\+|2\+|3\+)\.png$")[0].map(lv) != g.label).sum())
chk["fyp2_folder_label_mismatch"] = int((f.path.str.extract(r"Score_(\d)")[0].astype(int) != f.label).sum())
chk["bci_paths_unique"] = bool(g.path.is_unique); chk["bci_same_set_grouped_official"] = bool(set(g.path) == set(o.path))
def cross(col, df):
    d = df.groupby(col).split.nunique(); return int((d > 1).sum())
chk["grouped_md5_groups_crossing_splits"] = cross("md5", g); chk["grouped_identical_phash_crossing_splits"] = cross("phash", g)
chk["fyp2_group_crossing_splits"] = cross("group", f); chk["fyp2_md5_crossing_splits"] = cross("md5", f)
ph = np.array([[int(c, 16) for c in s] for s in g.phash]);  # nibble form, only used for exact-near counts
def bits(s): return np.unpackbits(np.frombuffer(bytes.fromhex(s), dtype=np.uint8))
B = np.stack([bits(s) for s in g.phash]); sp = g.split.values
te = np.where(sp == "test")[0]; va = np.where(sp == "val")[0]; tr = np.where(sp == "train")[0]
def nn(a, b):
    d = np.concatenate([(B[a[k:k+200], None, :] != B[None, b, :]).sum(-1).min(1) for k in range(0, len(a), 200)]); return d
for nm, a in [("test", te), ("val", va)]:
    d = nn(a, tr); chk[f"grouped_{nm}_tiles_within_phash6_of_train"] = int((d <= 6).sum()); chk[f"grouped_{nm}_tiles_within_phash12_of_train"] = int((d <= 12).sum())
json.dump(chk, open(OUT/"split_checks.json", "w"), indent=1, default=str); print(json.dumps(chk, indent=1, default=str)[:1800])
