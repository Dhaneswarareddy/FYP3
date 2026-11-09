# HARMONISE-1 audit, before HARMONISE-2

Checked 30 Oct 2026 against `next_experiment/outputs/`, not against the execution report's wording. All figures below come from
stored outputs. No new test metric was computed: the class-wise table is arithmetic on stored confusion matrices.

## What holds

- The protocol ran as designed: parameters frozen before test, selection on development tiles, test evaluated once.
- The primary endpoint is met as defined: Δ balanced accuracy +0.202 for `EfficientNetV2B0__ce`.
- Development and test agree for the primary model (balanced accuracy 0.510 vs 0.503). This is the only genuine WSI-disjoint check available, and it covers one split.

## Claims in `ANTIGRAVITY_EXECUTION_REPORT.md` that need correcting

| Claim | Problem | Correct statement |
|---|---|---|
| "1,847 external test tiles across 21 slide clusters" | No slide clusters exist. The CI resamples filename runs, about 370 on the test split | CIs are over filename runs. They are not slide-level and are optimistic |
| "95% bootstrap CI" quoted as decisive | Same issue | The point estimates stand; the CI width does not reflect 21 slides |
| QWK 0.76–0.80 presented as strong results for DenseNet121 and MobileNetV3Small | QWK hides class collapse (table below) | See class-wise table |
| "Stain calibration alone … resolved the 3+ collapse" | Every stain arm changed H and DAB together, so their effects were never separated | The combined change had this effect |
| "Spatial resolution already acted as an inherent morphological regularizer" | No experiment tested this | Unsupported. Tested in experiment D |
| "OD gains calibrated at 256px do not linearly translate to 512px" | No experiment tested this | Unsupported. Tested in experiment D |
| "whole-slide scans" | The data are tiles | Tiles from 107 slides |

## Limitations the design must respect

1. **No genuine WSI identifiers.**
   - The archives hold PNG tiles only. Filenames are `her2-<score>-score_<split>_<number>.png`, numbered per score.
   - The Zenodo record has no per-patch metadata. The authors' repository does not define the numbering.
   - The `WSI/` and `ROI/` folders the record describes are not in the local archives.
   - BCI also has no slide IDs; its fragments are reconstructed, not verified.
2. **Development pools share slides.** HARMONISE-1's fit tiles, selection tiles and the unused tiles all come from the same 86 slides, in unknown proportions. Random tile resampling therefore measures tile-sampling variation, **not** variation between slides or sites.
3. **`stain_p99` is at the edge of the grid.** The DAB gain jumps from 0.211 at p95 to 0.504 at p99, so the optimum may lie beyond the grid, and the result may be fragile.
4. **Percentile matching depends on class mix.** p99 is set by the most strongly stained tiles. A site with few 3+ tiles would get a different gain, even if its stain were identical. This was not tested.
5. **Labels are ROI-level and propagated to tiles,** with no stated scoring standard. Reliability figures inherit that noise.
6. **Test split status.** It has been used once for HARMONISE-1, and the audit diagnostics saw its labels earlier. HARMONISE-2 never reads it. Any later test look at a changed method would be exploratory and must be labelled so.
7. **Single seed per network.**

## Class-wise view of the stored HARMONISE-1 test results

Recall and F1 for 0 / 1+ / 2+ / 3+.

| Model | Arm | QWK | Recall | F1 | Off by ≥ 2 |
|---|---|---|---|---|---|
| EfficientNetV2B0 | none | 0.108 | 0.01 / 0.18 / 0.01 / 1.00 | 0.02 / 0.27 / 0.01 / 0.64 | 0.441 |
| EfficientNetV2B0 | stain_p99 | 0.593 | 0.30 / 0.18 / 0.57 / 0.97 | 0.46 / 0.24 / 0.16 / 0.94 | 0.232 |
| MobileNetV3Small | none | 0.210 | 0.19 / 0.15 / 0.00 / 1.00 | 0.32 / 0.24 / 0.00 / 0.64 | 0.408 |
| MobileNetV3Small | stain_p99 | 0.802 | 0.89 / 0.14 / 0.09 / 0.99 | 0.86 / 0.22 / 0.14 / 0.85 | 0.122 |
| DenseNet121 | none | 0.032 | 0.01 / 0.04 / 0.00 / 0.99 | 0.02 / 0.08 / 0.00 / 0.61 | 0.465 |
| DenseNet121 | stain_p99 | 0.765 | 0.94 / **0.00** / **0.00** / 0.70 | 0.74 / 0.00 / 0.00 / 0.79 | 0.136 |
| MobileNetV3Large CORN | none | 0.100 | 0.02 / 0.03 / 0.00 / 1.00 | 0.03 / 0.05 / 0.00 / 0.64 | 0.507 |
| MobileNetV3Large CORN | stain_p99 | 0.405 | 0.39 / 0.35 / 0.01 / 0.97 | 0.52 / 0.43 / 0.01 / 0.74 | 0.296 |
| EfficientNetV2B0 448 px | none | 0.432 | 0.24 / 0.11 / 0.01 / 0.80 | 0.33 / 0.15 / 0.00 / 0.79 | 0.360 |
| EfficientNetV2B0 448 px | stain_p99 | −0.155 | 0.05 / 0.15 / 0.47 / **0.08** | 0.09 / 0.13 / 0.08 / 0.13 | 0.528 |

What this shows:
- **Real gains:** score 0 recall improves strongly in the four 224 px models, and their 3+ precision rises from 0.44–0.47 to 0.60–0.91.
- **High QWK does not mean every class works.** DenseNet121 never predicts 1+ or 2+ correctly, and MobileNetV3Small finds 9% of 2+.
- **3+ recall can fall sharply:** DenseNet121's dropped from 0.99 to 0.70.
- **Score 0 tiles are often called 2+ by the primary model** (354 of 658), which is a two-step error.
- **No model handles 1+ and 2+ together.** The best 2+ recall (0.57) comes with 2+ precision of 0.09, so most tiles it calls 2+ are not 2+.

## How HARMONISE-2 responds

| Limitation | Experiment |
|---|---|
| Edge of grid, tail sensitivity, class-mix dependence | A: resampling, grid-edge sweep, composition stress test |
| No slide IDs | B: documented as not possible, with an unverified surrogate only if a pre-set check passes |
| QWK hides class failure | C: class-wise metrics with automatic flags |
| 448 px failure unexplained | D: H/DAB decomposition, resolution-compatible gains, dose-response in both domains |
| No reliability information | E: ECE, temperature scaling, review flagging |

All five use the 4,593 development tiles that HARMONISE-1 never used, so its selection cannot inflate the results.
