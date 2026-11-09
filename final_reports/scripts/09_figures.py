"""Report figures and read-only re-selection (no TensorFlow). Writes only to final_reports/."""
import json, sys; from pathlib import Path
import numpy as np, pandas as pd, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image
ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT/"src"))
import select_models as S
T = ROOT/"final_reports/tables"; F = ROOT/"final_reports/figures"
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3df"
COL = {"FYP2 GAN": "#2a78d6", "BCI": "#eb6834", "HER2-IHC-40x": "#2a9d6e"}; MK = {"FYP2 GAN": "o", "BCI": "s", "HER2-IHC-40x": "^"}
plt.rcParams.update({"font.size": 9, "axes.edgecolor": INK2, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2, "font.family": "DejaVu Sans"})
def style(ax, axis="y"):
    for s in ["top", "right"]: ax.spines[s].set_visible(False)
    ax.grid(axis=axis, color=GRID, lw=.8); ax.set_axisbelow(True)
L = ["0", "1+", "2+", "3+"]

# 1 stain by class, three datasets
A = pd.read_csv(T/"cross_dataset_features.csv")
fig, ax = plt.subplots(1, 2, figsize=(9.5, 3.5))
for a, c, t in zip(ax, ["dabc_mean", "hemc_mean"], ["DAB (brown HER2 stain)", "Haematoxylin (blue counterstain)"]):
    for d in COL:
        m = A[A.dataset == d].groupby("label")[c].median(); a.plot(range(4), m.values, color=COL[d], marker=MK[d], lw=2, ms=6, label=d)
        a.annotate(d, (3, m.values[-1]), xytext=(6, 0), textcoords="offset points", color=INK2, fontsize=8, va="center")
    a.set_xticks(range(4), L); a.set_xlabel("HER2 score"); a.set_title(t, loc="left", fontweight="bold", fontsize=10); style(a); a.set_xlim(-.2, 3.9)
ax[0].set_ylabel("Median optical density per tile\n(relative to the tile's background)")
ax[0].legend(frameon=False, fontsize=8, loc="upper left"); fig.tight_layout(); fig.savefig(F/"fig1_stain_by_class.png", dpi=160); plt.close(fig)

# 2 same-view montage
RAW = ROOT.parent/"FYP/data/raw/HER2-IHC-40x/wsi_test"; g = pd.read_csv(ROOT/"splits/split_manifest_grouped.csv"); f = pd.read_csv(ROOT.parent/"FYP2/splits/split_manifest.csv")
GAN = ROOT.parent/"FYP2/HER2 SCORES DATA/Generated_HER2_images"; ext = pd.read_csv(ROOT/"results/external/her2_40x/BCI__EfficientNetV2B0__ce.csv")
fig, axes = plt.subplots(3, 4, figsize=(8, 6.4))
for r, (nm, get) in enumerate([("FYP2 GAN", lambda k: GAN/f[(f.split=="test")&(f.label==k)].path.iloc[3]), ("BCI", lambda k: ROOT/"data/ihc_256"/g[(g.split=="test")&(g.label==k)].path.iloc[3]), ("HER2-IHC-40x", lambda k: RAW/ext[ext.label==k].path.iloc[20])]):
    for k in range(4):
        axes[r, k].imshow(Image.open(get(k)).convert("RGB").resize((224, 224), Image.BILINEAR)); axes[r, k].set_axis_off(); axes[r, k].set_title(f"{nm}, score {L[k]}", fontsize=8)
fig.suptitle("The same 224 px view each network receives", x=.01, ha="left", fontweight="bold", fontsize=10); fig.tight_layout(); fig.savefig(F/"fig2_same_view_examples.png", dpi=130); plt.close(fig)

# 3 stain-only rule vs CNN
r = pd.read_csv(T/"stain_only_rules.csv"); e = pd.read_csv(T/"external_recomputed.csv")
r = r[(r.applied_to == "HER2-IHC-40x test")]
fig, ax = plt.subplots(figsize=(7.6, 3.4)); y = 0; lab = []
groups = [("CNNs trained on FYP2", e[e.source=="FYP2"].balanced_accuracy.values, COL["FYP2 GAN"]), ("Stain-only rules fitted on FYP2", r[r.fitted_on=="FYP2 train"].balanced_accuracy.values, COL["FYP2 GAN"]),
          ("CNNs trained on BCI", e[e.source=="BCI"].balanced_accuracy.values, COL["BCI"]), ("Stain-only rules fitted on BCI", r[r.fitted_on=="BCI train"].balanced_accuracy.values, COL["BCI"])]
for i, (n, v, c) in enumerate(groups):
    ax.scatter(v, np.full(len(v), i), color=c, marker="o" if "CNN" in n else "D", s=42, edgecolor="white", lw=.8, zorder=3)
    ax.text(.86, i, f"{np.min(v):.2f}–{np.max(v):.2f}", va="center", color=INK2, fontsize=8)
ax.axvline(.25, color=INK2, lw=.8, ls=":"); ax.text(.25, 3.5, "chance", color=INK2, fontsize=8, ha="center")
ax.set_yticks(range(4), [g[0] for g in groups]); ax.invert_yaxis(); ax.set_xlim(.15, .95); ax.set_xlabel("Balanced accuracy on HER2-IHC-40x test"); style(ax, "x"); ax.set_title("A stain-only rule reproduces the FYP2 vs BCI gap without any CNN", loc="left", fontweight="bold", fontsize=10)
fig.tight_layout(); fig.savefig(F/"fig3_stain_rule_vs_cnn.png", dpi=160); plt.close(fig)

# 4 ranking vs calibration
e["lab"] = e.source + " " + e.run.str.replace("__ce", "").str.replace("__corn", " CORN").str.replace("__", " "); e = e.sort_values(["source", "auc_low_vs_high"])
fig, ax = plt.subplots(1, 2, figsize=(9.6, 4), sharey=True); ys = np.arange(len(e)); c = [COL["FYP2 GAN"] if s == "FYP2" else COL["BCI"] for s in e.source]; truth = 1.53
ax[0].barh(ys, e.auc_low_vs_high, color=c, height=.68); ax[0].set_xlim(.5, 1); ax[0].set_yticks(ys, e.lab, fontsize=8); ax[0].set_xlabel("AUC, score 0/1+ vs 2+/3+ (threshold-free)"); style(ax[0], "x")
ax[1].barh(ys, e.mean_expected_score, color=c, height=.68); ax[1].axvline(truth, color=INK, lw=1.2); ax[1].text(truth+.03, len(e)-.4, f"true mean {truth}", fontsize=8, color=INK); ax[1].set_xlim(0, 3); ax[1].set_xlabel("Mean predicted score"); style(ax[1], "x")
fig.suptitle("BCI-trained networks rank external tiles well but score them too high", x=.01, ha="left", fontweight="bold", fontsize=10); fig.tight_layout(); fig.savefig(F/"fig4_ranking_vs_calibration.png", dpi=160); plt.close(fig)

# 5 external confusions
C = json.load(open(T/"external_confusions.json")); keys = ["FYP2__ResNet50__ce", "FYP2__EfficientNetV2B0__ce", "BCI__EfficientNetV2B0__ce", "BCI__EfficientNetV2B0__ce__lowbatch", "BCI__EfficientNetV2B0__ce__hires", "BCI__DenseNet121__ce"]
from matplotlib.colors import LinearSegmentedColormap
cm = LinearSegmentedColormap.from_list("b", ["#f4f8fd", "#6da7ec", "#0d366b"])
fig, axes = plt.subplots(2, 3, figsize=(9, 6))
for a, k in zip(axes.flat, keys):
    c = np.array(C[k]); n = c / c.sum(1, keepdims=True); a.imshow(n, cmap=cm, vmin=0, vmax=1)
    for i in range(4):
        for j in range(4): a.text(j, i, f"{c[i,j]}", ha="center", va="center", fontsize=8, color="white" if n[i, j] > .55 else INK)
    a.set_xticks(range(4), L); a.set_yticks(range(4), L); a.set_title(k.replace("__", " ", 1).replace("__", " "), fontsize=8.5, loc="left", fontweight="bold"); a.set_xlabel("Predicted"); a.set_ylabel("True")
fig.tight_layout(); fig.savefig(F/"fig5_external_confusions.png", dpi=140); plt.close(fig)

# 6 effects forest
p = pd.read_csv(T/"paired_effects.csv"); q = p[(p.metric == "qwk")]
eff = ["E1 resolution", "E1 batch", "E2 resolution", "E2 batch", "E4 init_fyp2", "E5 mix_fyp2"]
name = {"E1 resolution": "EfficientNetV2B0: resolution (448 vs 224, batch 8)", "E1 batch": "EfficientNetV2B0: batch (8 vs 32, 224 px)", "E2 resolution": "MobileNetV3Small: resolution", "E2 batch": "MobileNetV3Small: batch", "E4 init_fyp2": "EfficientNetV2B0: GAN pretraining", "E5 mix_fyp2": "EfficientNetV2B0: mixed GAN + BCI"}
fig, ax = plt.subplots(figsize=(8.2, 3.5))
for off, sp, c, mk in [(-.15, "val", "#2a78d6", "o"), (.15, "test", "#eb6834", "s")]:
    d = q[q.split == sp].set_index("effect").loc[eff]
    ax.errorbar(d.delta, np.arange(len(eff))+off, xerr=[d.delta-d.ci_lo, d.ci_hi-d.delta], fmt=mk, color=c, ms=5, lw=1.6, capsize=0, label=f"{sp} (paired, 95% CI)")
ax.axvline(0, color=INK2, lw=.9); ax.set_yticks(range(len(eff)), [name[e] for e in eff], fontsize=8); ax.invert_yaxis(); ax.set_xlabel("Δ QWK on BCI"); style(ax, "x"); ax.legend(frameon=False, fontsize=8, loc="lower right")
fig.tight_layout(); fig.savefig(F/"fig6_effects_forest.png", dpi=160); plt.close(fig)

# 7 quantisation
t = pd.read_csv(T/"deploy_recomputed.csv"); v = ["fp32", "fp16", "int8"]; fig, ax = plt.subplots(1, 3, figsize=(9, 2.9))
for a, (c, lab) in zip(ax, [("size_mb", "Model size (MB)"), ("mac_latency_ms", "Median latency on Mac CPU (ms)")]):
    d = t[t.split == "test"].set_index("variant").loc[v][c]; a.bar(v, d, color="#2a78d6", width=.6); a.set_title(lab, loc="left", fontsize=9, fontweight="bold"); style(a)
    for i, x in enumerate(d): a.text(i, x, f"{x:.1f}", ha="center", va="bottom", fontsize=8, color=INK2)
for sp, c, o in [("val", "#2a78d6", -.17), ("test", "#eb6834", .17)]:
    d = t[t.split == sp].set_index("variant").loc[v].qwk; ax[2].bar(np.arange(3)+o, d, width=.32, color=c, label=sp)
    for i, x in enumerate(d): ax[2].text(i+o, x, f"{x:.3f}", ha="center", va="bottom", fontsize=7, color=INK2)
ax[2].set_xticks(range(3), v); ax[2].set_ylim(.7, 1.02); ax[2].set_title("QWK on BCI", loc="left", fontsize=9, fontweight="bold"); ax[2].legend(frameon=False, fontsize=8, ncol=2, loc="upper right"); style(ax[2])
fig.tight_layout(); fig.savefig(F/"fig7_quantisation.png", dpi=160); plt.close(fig)

# 8 read-only selection across all runs
runs = S.load_runs(); runs.to_csv(T/"all_runs_for_selection.csv", index=False)
cols = ["run", "tier", "params", "val_qwk", "val_accuracy", "test_qwk", "test_accuracy"]
best = runs[runs.variant == "baseline"].sort_values("val_qwk", ascending=False).groupby("tier").head(1)[cols]
all_ = runs.sort_values("val_qwk", ascending=False).groupby("tier").head(2)[cols]
print(best.round(4).to_string(index=False)); print(all_.round(4).to_string(index=False)); all_.to_csv(T/"selection_including_new_runs.csv", index=False)
