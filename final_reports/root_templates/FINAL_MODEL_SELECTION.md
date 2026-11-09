# FYP3 final model selection

30 Oct 2026. Evidence comes from stored run outputs, independently recomputed (`final_reports/`). Two configurations are selected for **different purposes** and must never be combined.

| | Primary | Experimental |
|---|---|---|
| Purpose | Scoring BCI-like tiles | Studying cross-domain calibration on HER2-IHC-40x |
| Model | EfficientNetV2B0, CE, 448 px (`EfficientNetV2B0__ce__hires`) | EfficientNetV2B0, CE, 224 px (`EfficientNetV2B0__ce`) |
| Format | FP16 TFLite, 11.27 MB | FP16 TFLite, 11.27 MB (new export) |
| Stain calibration | **None, and it must not be applied** | **Frozen `stain_p99`:** g_h 0.2545, g_d 0.5045 |
| Status | Selected model | Research configuration, not a product candidate |

Neither is clinically validated, and neither has been benchmarked on a Raspberry Pi.

## Disclosures

- **Genuine WSI identifiers are unavailable** in BCI and HER2-IHC-40x, so there are no per-slide or per-patient results.
- **External test labels were previously exposed** through diagnostics, and the split was evaluated once for HARMONISE-1. It is not a pristine test.
- **Borderline HER2 performance remains weak** across domains, and on BCI the 2+ result reflects slide-level labels.
- **All latency figures are Mac CPU.**

## Primary model

**Selection rule:** highest BCI validation QWK, decided on validation only, with paired CIs. The test split is reported, not used.

| Evidence | Value |
|---|---|
| BCI validation | Accuracy 0.950, QWK 0.935 |
| BCI test (report-only) | Accuracy 0.975, QWK 0.959, balanced accuracy 0.973 |
| vs 224 px baseline, val QWK | +0.065 [+0.026, +0.108] |
| vs 224 px at equal batch size, val QWK | +0.105 [+0.056, +0.168]; test +0.063 [+0.026, +0.116] |
| Overfitting verdict | Mild: train − test 2.4 points, log-loss gap 0.088 |
| FP16 vs Keras, through the deployment code | 100% class agreement on all 1,485 BCI val and test tiles; largest probability change 0.020 |

{{primary_bci_classes}}

**Why not the alternatives:**

{{selection}}

- **Other 224 px baselines:** lower validation QWK, and tier winners are not separable from their runners-up.
- **CORN, class weights, label smoothing, GAN pretraining, mixed training:** no gain on validation.
- **INT8:** rejected. Agreement 0.928 is below the 0.95 threshold, and test accuracy falls 4.2 points.
- **FP32:** no accuracy benefit over FP16, at twice the size.

**Limits of this selection:**
- It is best **on BCI only**. On HER2-IHC-40x it reaches 0.435 accuracy with 1+ recall 0.11 and 2+ recall 0.01 (test), and it ranks tiles worse than the 224 px model.
- Only 2 of 9 architectures were tested at 448 px, so it is the best *tested*, not the best possible.
- One seed. MobileNetV3Small did not confirm the resolution effect.
- BCI's test split has unusually strong 3+ staining, so validation is the more cautious estimate.
- Mac latency is 75.5 ms. Pi feasibility at 448 px is unknown.

**Borderline evidence on BCI.** Against third-party patch labels (protocol undocumented):

{{primary_refined}}

On slide-labelled 2+ tiles the model follows the slide label almost always, while the patch labels agree with the slide only 70–74% of the time. This does not show reliable tile-level reading of 2+.

## Experimental configuration

**Why this one:** `EfficientNetV2B0__ce` was HARMONISE-1's pre-registered primary model and is the only network that detects 2+ at all once calibrated. It was **not** chosen by test results.

{{h1h2}}

| Finding | Evidence |
|---|---|
| Endpoint met | Balanced accuracy 0.301 → 0.503 on test (Δ +0.202; CI optimistic) |
| FP16 vs Keras | 99.6% class agreement on 2,402 development tiles; disagreements examined were near-ties |
| Stable to tile sampling | CV 0.042 (g_d), 0.030 (g_h) at n = 1,500; balanced accuracy range 0.005 |
| Depends on class mix | At 5% 3+, g_d rises to 0.75 and balanced accuracy falls to 0.41 |
| 1+ remains poor | Recall 0.18 on test |
| 2+ is imprecise | Recall 0.57, precision 0.09 on test |
| Confidence cannot flag safely | At 50% target coverage, 76% of 2+ tiles would be referred |
| Unsafe on BCI | Balanced accuracy 0.875 → 0.407 |

**MobileNetV3Small** scores higher overall (test accuracy 0.755, QWK 0.80) but finds only 9% of 2+, so its headline is misleading.

**Do not generalise this configuration.** The gains belong to one dataset. Another site would need its own unlabelled calibration of about 1,000 tiles with a sensible class mix, and that has not been tested.

## Rejected combinations

| Combination | Why rejected |
|---|---|
| 448 px + stain calibration | Collapses: test balanced accuracy 0.186, 3+ recall 0.08. The haematoxylin gain is the cause |
| 448 px + refitted gains | Same collapse: gains are nearly identical across resolutions |
| 448 px + calibration + scale | 3+ recall falls to 0.70; fails the pre-set rule |
| Stain calibration on BCI tiles | Balanced accuracy 0.875 → 0.407 |
| DenseNet121 + calibration | QWK 0.76 with 1+ and 2+ recall near zero |

## What would change this selection

- Slide identifiers, or a multi-site external set.
- A 448 px run of a heavy architecture, or a second seed.
- A Pi benchmark showing 448 px is too slow. FP16 at 224 px would then be the fallback to test, with lower BCI accuracy.
