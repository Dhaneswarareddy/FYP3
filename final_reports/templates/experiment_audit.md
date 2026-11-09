# FYP3 experiment audit

Audit date: 30 Oct 2026. Every number here was recomputed from saved artifacts by the scripts in
`final_reports/scripts/`. Nothing was trained. `results/REPORT.md` (30 Oct, 09:04) was not changed and predates E1–E5.

## Verdict

- **The experiments are sound.** All 40 stored runs reproduce exactly, the splits are clean, class mapping is correct, and
  checkpoints and preprocessing reproduce saved outputs. No bug explains any result.
- **Some earlier conclusions were too strong.** They are corrected in the table at the end, including statements made by
  this project's previous analysis.
- **Open gaps:** the 4 new runs have no overfitting check, `selection.json` is stale, and two run settings were not logged.

## What was checked

| Check | Method | Result |
|---|---|---|
| Metrics | Accuracy, macro-F1 and QWK recomputed from `predictions.npz`, labels taken from the manifests, for 20 grouped + 2 official + 18 FYP2 runs | **Difference 0.0** against every `summary.json`. Labels match the manifests. Probabilities sum to 1 |
| Grouped split | Counts, fragments, md5, pHash | 3,388 / 727 / 758. **0** fragments and **0** exact duplicates cross splits. Near-duplicates to train (pHash ≤ 6): 1 test tile, 0 val tiles; (≤ 12): 15 test, 14 val |
| FYP2 split | Twin groups, md5 | **0** groups and **0** exact duplicates cross splits |
| Class mapping | Filename or folder vs label | BCI: 0 mismatches in 4,873. FYP2: 0 in 2,400. Same 0 / 1+ / 2+ / 3+ order in all networks |
| Checkpoints and preprocessing | 13 external-evaluated networks reloaded on CPU, 24 images each | All reproduce saved test predictions and external probabilities (table below). Cached external tiles equal a fresh resize of the raw file |
| External metrics | Recomputed from the per-tile CSVs | Difference 0.0 against the stored JSON |
| Mixed training leakage | Code review of `fyp2_train_paths()` | Uses FYP2's train split only. FYP2 val and test are never read. BCI val and test are unaffected |
| Deployment | Confusion matrices re-scored; FP32 confusion compared with Keras | Metrics match; FP32 equals Keras on val and test |

{{verify}}

## E1–E5

The plan's labels: E1 and E2 are the resolution and batch controls, E3 the external test, E4 GAN pretraining, E5 mixed
training. Δ is A − B on the same tiles, with a 95% fragment-cluster bootstrap CI. `*` means the CI excludes 0.

{{paired}}

![](figures/fig6_effects_forest.png)

**Reading the table:**
- **E1 (EfficientNetV2B0): resolution is the cause.** At equal batch size, 448 px beats 224 px on val and test. Batch size has
  no effect (val −0.040, CI includes 0). The caveat in the 30 Oct report is resolved for this model.
- **E2 (MobileNetV3Small): not confirmed.** The resolution effect on val has a CI that includes 0 (+0.090 [−0.007, +0.207]), and
  the test effect is near zero. By the pre-set rule, the resolution effect is confirmed on 1 of 2 models.
- **E4 and E5: no benefit.** Neither GAN pretraining nor mixed GAN + BCI training beats the baseline on BCI val or test.
- **E3:** see `cross_dataset_audit.md`.

## All grouped runs

{{all_runs}}

## Model selection

`selection.json` was written before E1–E5. The rule was re-applied read-only, top two per tier by val QWK, including all
new runs. **The baseline tier winners do not change.** The best run including improvements in each tier:

{{selection}}

- **Mid tier:** EfficientNetV2B0 at 448 px is the only clear winner.
- **Lite tier:** MobileNetV3Small at 448 px leads on val QWK, but it is within noise of MobileNetV3Large CORN (+0.040
  [−0.059, +0.157]) and has lower test QWK.
- **Heavy tier:** no 448 px run exists, so the tiers are not compared on equal terms.

## Findings to act on

| # | Severity | Finding | Action |
|---|---|---|---|
| 1 | Medium | The 4 new runs are missing from `metrics_all.csv`, `overfitting.csv`, `selection.json` and `REPORT.md`. They have **no train-accuracy or overfitting verdict** | Run `evaluate_all.py` after copying the aggregates, because it rewrites them (`ANTIGRAVITY_HANDOFF.md`, optional) |
| 2 | Medium | External CIs resample tiles, but the test split has only 21 slides and no slide IDs. Filename runs (370) are a partial proxy and still over-count slides | Treat external CIs as optimistic. Do not quote the tile CIs alone |
| 3 | Medium | The external test labels have now been seen in diagnostics, including this audit. It is no longer strictly unseen | Disclosed. Next-experiment parameters come only from the 86 development slides |
| 4 | Low | `mix_fyp2` used a non-default FT epoch ceiling that is not stored. The learning-rate curve implies 26 (26 × 158 = 4,108 steps vs 40 × 105 = 4,200 at baseline, a fair budget match). `run_variants.sh` cannot pass this option, so the command is unlogged | Record such options in `summary.json` in future |
| 5 | Low | `deploy.py` was edited at 17:57, after its outputs (15:44), and there is no deploy log | Metrics were re-verified, but the INT8 file cannot be tied to the current code |
| 6 | Low | The first E1 run deadlocked (log kept as `train_EfficientNetV2B0__ce__lowbatch_deadlocked_run1.log`). The reported run is the clean rerun | None |
| 7 | Low | Single seed per arm. Bootstrap CIs cover tile sampling, not training variance | State this wherever single-run differences are quoted |
| 8 | Low | Many comparisons were made without correction. The E2 batch test-QWK CI excludes 0 (−0.030), but val shows nothing | Treat as noise; decisions use val |
| 10 | Info | One FYP2 file changed after FYP3 began: `FYP2/pi/README.md` (30 Oct, 10:06) has four extra spaces before its title; a diff against the Pi bundle's copy shows nothing else. This audit did not make that change and left it as it is | Harmless. Remove the spaces if you wish |
| 9 | Info | BCI's grouped test split has **3+ tiles with about twice the DAB of train and val**: median 0.49 vs 0.25 and 0.23 | Likely contributes to test > val on every model (interpretation). Quote both splits |

## Corrected conclusions

| Earlier statement | Corrected |
|---|---|
| "Higher input resolution helps", confirmed on two models | Confirmed as a **resolution** effect on EfficientNetV2B0 only. On MobileNetV3Small the hires gain on val is real, but its resolution-only CI includes 0 and test shows no gain |
| The hires gain might be a batch-size effect | Not supported on either model: the batch-size CIs on val include 0 |
| "FYP2 models generalise better to real tissue" (a tempting reading of E3) | **Misleading.** They fail on BCI and succeed on HER2-IHC-40x because that set's stain resembles the GAN's. See `cross_dataset_audit.md` |
| Low batch improves external performance (QWK 0.58 vs 0.11) | **Misleading.** Ranking is the same (Spearman 0.74 vs 0.76). The gap is a calibration difference between two single training runs |
| Double resolution is the best model overall | Best on BCI only. It **lowers** external ranking (AUC 0.87 vs 0.96) |
| HER2-IHC-40x tiles are about 1.8× larger in scale than BCI | Measured ratio is about **4–5×** and uncertain: the paper says patches were resized to 1024 px |
| Whether HER2-IHC-40x labels are slide- or tile-level is unknown | Resolved from the paper: **ROI-level labels, propagated to patches** |
| `REPORT_CORRECTIONS.md` #2–3 (hires cause untested) | Superseded by E1/E2 as above |

All tables are in `final_reports/tables/`.
