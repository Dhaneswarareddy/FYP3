# FYP3 final report: from GAN-trained HER2 scoring to real tissue

30 Oct 2026. This consolidates all FYP3 work including E1–E5, the external test and quantisation. It supersedes
the conclusions of `results/REPORT.md`, which is preserved unchanged for its detailed evidence. Results are marked
**confirmed** (measured) or **interpretation**.

## Summary

1. **Performance on real tissue.** The pipeline drops from about 100% test accuracy on FYP2's GAN images to 91–95% on BCI at 224 px (confirmed).
2. **Why.** BCI's classes are barely separable in generic features (frozen-probe accuracy 0.77 vs 0.98), real DAB separates 0/1+/2+ weakly,
   and 16–18% of tiles disagree with third-party patch labels. Most of the drop comes from the data (confirmed for the measures; causal weighting is interpretation).
3. **The one improvement that held up.** Higher resolution, confirmed as a resolution effect on EfficientNetV2B0 (test accuracy 0.905 → 0.975 at equal batch
   size), not confirmed on MobileNetV3Small. Class weights, label smoothing, CORN, GAN pretraining and mixed training gave no gain.
4. **External test.** On HER2-IHC-40x, BCI-trained networks score 0.42–0.59 accuracy and GAN-trained networks 0.69–0.76. This is a **stain-calibration effect**, not
   evidence that GAN training generalises. A stain-only rule reaches 0.89 and beats every CNN. BCI networks rank tiles well (7 of 10 with AUC ≥ 0.94) but score them too high.
5. **Deployment.** FP16 is safe; INT8 is degraded. **The Raspberry Pi benchmark has not been run.**

## 1. Data and method

| | FYP2 | BCI (FYP3) | HER2-IHC-40x |
|---|---|---|---|
| Nature | CGAN images, HER2SC-derived | Real IHC | Real IHC |
| Native size | 256 px | 1024 px, 0.46 µm/px | 1024 px, resized; µm/px unknown |
| Volume | 2,400 | 4,873 tiles, 51 WSI pairs (BCI paper) | 9,940 tiles, 107 WSIs |
| Labels | Generator class | Slide-level | ROI-level |
| Split | 70/15/15 by twin group | 70/15/15 by slide fragment | Report-only: test split of 21 WSIs |

All models used FYP2's schedule: two-stage training, frozen BatchNorm, seed 42, early stopping on val QWK. Decisions used
validation; paired CIs resample slide fragments. Details: `results/REPORT.md` sections 1–2.

## 2. Results on BCI

| Run | Input | Batch | Best / run epochs | Train min | Val acc | Val QWK | Test acc | Test bal. acc | Test QWK |
|---|---|---|---|---|---|---|---|---|---|
| EfficientNetV2B0 / ce / hires | 448 | 8 | 38 / 45 | 252 | 0.950 | 0.934 | 0.975 | 0.973 | 0.959 |
| EfficientNetV2B0 / ce | 224 | 32 | 31 / 41 | 49 | 0.895 | 0.869 | 0.926 | 0.917 | 0.915 |
| MobileNetV3Small / ce / hires | 448 | 8 | 15 / 25 | 45 | 0.898 | 0.865 | 0.908 | 0.898 | 0.874 |
| DenseNet121 / ce | 224 | 16 | 32 / 42 | 131 | 0.908 | 0.854 | 0.942 | 0.922 | 0.910 |
| EfficientNetV2B0 / ce / init_fyp2 | 224 | 32 | 29 / 39 | 55 | 0.902 | 0.854 | 0.920 | 0.919 | 0.894 |
| EfficientNetV2B0 / ce / mix_fyp2 | 224 | 32 | 18 / 28 | 56 | 0.884 | 0.847 | 0.917 | 0.915 | 0.910 |
| EfficientNetB0 / ce | 224 | 32 | 31 / 41 | 111 | 0.891 | 0.846 | 0.933 | 0.914 | 0.902 |
| ConvNeXtTiny / ce | 224 | 16 | 13 / 23 | 124 | 0.902 | 0.844 | 0.926 | 0.891 | 0.898 |
| DenseNet121 / corn | 224 | 16 | 30 / 40 | 143 | 0.880 | 0.841 | 0.914 | 0.893 | 0.874 |
| EfficientNetV2B0 / corn | 224 | 32 | 16 / 26 | 30 | 0.862 | 0.831 | 0.906 | 0.900 | 0.892 |
| EfficientNetV2B0 / ce / lowbatch | 224 | 8 | 16 / 26 | 42 | 0.868 | 0.829 | 0.905 | 0.901 | 0.896 |
| ResNet50 / ce | 224 | 16 | 43 / 45 | 108 | 0.902 | 0.829 | 0.949 | 0.934 | 0.932 |
| MobileNetV3Large / corn | 224 | 32 | 45 / 45 | 47 | 0.894 | 0.825 | 0.937 | 0.919 | 0.923 |
| NASNetMobile / ce | 224 | 32 | 28 / 38 | 100 | 0.884 | 0.805 | 0.921 | 0.895 | 0.904 |
| MobileNetV3Large / ce | 224 | 32 | 22 / 32 | 76 | 0.871 | 0.800 | 0.908 | 0.884 | 0.878 |
| MobileNetV3Small / ce / cw | 224 | 32 | 34 / 44 | 15 | 0.854 | 0.786 | 0.906 | 0.896 | 0.883 |
| MobileNetV2 / ce | 224 | 32 | 33 / 43 | 75 | 0.857 | 0.785 | 0.930 | 0.925 | 0.924 |
| MobileNetV3Small / ce / lowbatch | 224 | 8 | 30 / 40 | 28 | 0.857 | 0.775 | 0.905 | 0.875 | 0.857 |
| MobileNetV3Small / ce / ls | 224 | 32 | 31 / 41 | 16 | 0.864 | 0.767 | 0.905 | 0.868 | 0.873 |
| MobileNetV3Small / ce | 224 | 32 | 34 / 44 | 23 | 0.854 | 0.763 | 0.913 | 0.886 | 0.888 |

![](figures/fig6_effects_forest.png)

| Effect | A − B | Δ val QWK | Δ val acc | Δ test QWK | Δ test acc |
|---|---|---|---|---|---|
| E1 resolution | EfficientNetV2B0 / ce / hires − lowbatch | +0.105 [+0.056, +0.168] * | +0.083 [+0.051, +0.113] * | +0.063 [+0.026, +0.116] * | +0.070 [+0.042, +0.106] * |
| E1 batch | EfficientNetV2B0 / ce / lowbatch − ce | -0.040 [-0.109, +0.027] | -0.028 [-0.060, +0.007] | -0.019 [-0.064, +0.021] | -0.021 [-0.051, +0.006] |
| E1 combined | EfficientNetV2B0 / ce / hires − ce | +0.065 [+0.026, +0.108] * | +0.055 [+0.033, +0.076] * | +0.044 [+0.009, +0.089] * | +0.049 [+0.028, +0.079] * |
| E2 resolution | MobileNetV3Small / ce / hires − lowbatch | +0.090 [-0.007, +0.207] | +0.041 [+0.000, +0.086] | +0.017 [-0.034, +0.075] | +0.003 [-0.022, +0.031] |
| E2 batch | MobileNetV3Small / ce / lowbatch − ce | +0.012 [-0.061, +0.089] | +0.003 [-0.019, +0.026] | -0.030 [-0.067, -0.003] * | -0.008 [-0.028, +0.010] |
| E2 combined | MobileNetV3Small / ce / hires − ce | +0.102 [+0.031, +0.173] * | +0.044 [+0.012, +0.076] * | -0.014 [-0.063, +0.038] | -0.005 [-0.031, +0.024] |
| E4 init_fyp2 | EfficientNetV2B0 / ce / init_fyp2 − ce | -0.015 [-0.075, +0.042] | +0.007 [-0.018, +0.029] | -0.021 [-0.068, +0.017] | -0.007 [-0.031, +0.022] |
| E5 mix_fyp2 | EfficientNetV2B0 / ce / mix_fyp2 − ce | -0.023 [-0.073, +0.020] | -0.011 [-0.036, +0.014] | -0.005 [-0.035, +0.023] | -0.009 [-0.038, +0.023] |

*`*`: CI excludes 0. A − B on the same tiles.*

- **Resolution:** confirmed for EfficientNetV2B0, not for MobileNetV3Small.
- **Batch size:** no effect on validation for either model.
- **GAN pretraining and mixed training:** no gain on BCI.
- **Tier winners** are not separable from their runners-up on validation; see `experiment_audit.md`.

## 3. Overfitting

On the 16 runs evaluated, train − test accuracy is 2.2–6.6 points against ≤ 0.7 on FYP2. Selection did not overfit validation: val is below test on every run.
Noise-aware verdict: 8 overfit, 7 mild, 1 none. **The 4 E1/E2/E4/E5 runs have no verdict yet.** The role of label noise is an interpretation.

## 4. External test

| Trained on | Run | Input | Acc | Bal. acc | Macro-F1 | QWK | QWK CI (filename runs) | AUC 0/1+ vs 2+/3+ | AUC 3+ vs rest | Spearman | Mean pred. score | Recall 0/1+/2+/3+ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| FYP2 | ResNet50 / ce | 224 | 0.724 | 0.725 | 0.673 | 0.856 | [0.80, 0.90] | 0.982 | 0.999 | 0.83 | 1.81 | 0.32 / 0.96 / 0.63 / 0.99 |
| FYP2 | MobileNetV2 / ce | 224 | 0.685 | 0.618 | 0.573 | 0.868 | [0.83, 0.90] | 0.977 | 0.999 | 0.87 | 1.82 | 0.30 / 0.90 / 0.29 / 0.99 |
| FYP2 | EfficientNetV2B0 / ce | 224 | 0.761 | 0.608 | 0.573 | 0.792 | [0.72, 0.85] | 0.966 | 0.992 | 0.85 | 1.81 | 0.59 / 0.83 / 0.02 / 0.99 |
| BCI | EfficientNetV2B0 / ce / lowbatch | 224 | 0.507 | 0.381 | 0.345 | 0.584 | [0.51, 0.66] | 0.943 | 0.989 | 0.74 | 2.10 | 0.03 / 0.50 / 0.00 / 0.99 |
| BCI | MobileNetV3Small / ce / lowbatch | 224 | 0.586 | 0.381 | 0.357 | 0.403 | [0.34, 0.46] | 0.941 | 0.892 | 0.81 | 2.45 | 0.45 / 0.07 / 0.00 / 1.00 |
| BCI | MobileNetV3Small / ce | 224 | 0.508 | 0.337 | 0.301 | 0.210 | [0.15, 0.28] | 0.970 | 0.956 | 0.81 | 2.65 | 0.20 / 0.15 / 0.00 / 1.00 |
| BCI | EfficientNetV2B0 / ce | 224 | 0.448 | 0.301 | 0.235 | 0.108 | [0.07, 0.15] | 0.956 | 0.982 | 0.76 | 2.71 | 0.01 / 0.18 / 0.01 / 1.00 |
| BCI | MobileNetV3Small / ce / hires | 448 | 0.419 | 0.299 | 0.278 | 0.316 | [0.24, 0.40] | 0.848 | 0.798 | 0.60 | 2.29 | 0.12 / 0.28 / 0.00 / 0.79 |
| BCI | EfficientNetV2B0 / ce / hires | 448 | 0.435 | 0.290 | 0.318 | 0.432 | [0.36, 0.51] | 0.870 | 0.859 | 0.57 | 2.01 | 0.24 / 0.11 / 0.01 / 0.80 |
| BCI | EfficientNetV2B0 / ce / mix_fyp2 | 224 | 0.437 | 0.279 | 0.206 | 0.055 | [0.03, 0.09] | 0.956 | 0.984 | 0.76 | 2.81 | 0.03 / 0.07 / 0.02 / 1.00 |
| BCI | EfficientNetV2B0 / ce / init_fyp2 | 224 | 0.424 | 0.268 | 0.204 | 0.166 | [0.12, 0.21] | 0.974 | 0.978 | 0.81 | 2.72 | 0.00 / 0.06 / 0.01 / 1.00 |
| BCI | MobileNetV3Large / corn | 224 | 0.423 | 0.261 | 0.180 | 0.100 | [0.05, 0.15] | 0.964 | 0.945 | 0.80 | 2.83 | 0.02 / 0.03 / 0.00 / 1.00 |
| BCI | DenseNet121 / ce | 224 | 0.419 | 0.260 | 0.176 | 0.032 | [0.01, 0.07] | 0.764 | 0.755 | 0.31 | 2.88 | 0.01 / 0.04 / 0.00 / 0.99 |

![](figures/fig3_stain_rule_vs_cnn.png)

- **No pipeline bug** (13 of 13 networks reproduced end to end).
- **Stain style explains the FYP2 vs BCI gap** (`cross_dataset_audit.md`).
- **Scale mismatch is about 4–5× and separate from that gap.**
- **Higher BCI performance does not transfer:** double resolution lowers external ranking.
- **Labels are ROI-level, the set is curated by a per-class colour filter, and it has 21 test slides.** It is not a representative clinical test.

## 5. Quantisation

| Variant | Split | Status | Size MB | Mac CPU ms | Acc | Bal. acc | QWK | Recall 0/1+/2+/3+ |
|---|---|---|---|---|---|---|---|---|
| fp32 | val | ok | 22.36 | 71.3 | 0.950 | 0.945 | 0.935 | 0.94 / 0.94 / 0.97 / 0.92 |
| fp32 | test | ok | 22.36 | 71.3 | 0.975 | 0.973 | 0.959 | 0.97 / 0.96 / 0.98 / 0.98 |
| fp16 | val | ok | 11.27 | 75.5 | 0.950 | 0.945 | 0.935 | 0.94 / 0.94 / 0.97 / 0.92 |
| fp16 | test | ok | 11.27 | 75.5 | 0.975 | 0.973 | 0.959 | 0.97 / 0.96 / 0.98 / 0.98 |
| int8 | val | degraded | 6.82 | 133.5 | 0.919 | 0.910 | 0.870 | 0.92 / 0.88 / 0.97 / 0.87 |
| int8 | test | degraded | 6.82 | 133.5 | 0.933 | 0.932 | 0.907 | 0.97 / 0.85 / 0.97 / 0.93 |

FP16 is lossless here. INT8 falls below the agreement threshold. Latency is Mac CPU only. See `quantization_deployment.md`.

## 6. Limitations

- BCI has no slide IDs: fragments only partly recover slide structure, and residual leakage is possible.
- Single seed per configuration.
- BCI's grouped test split has unusually strong 3+ staining, which likely inflates test relative to val.
- External CIs are optimistic, and external labels have been seen in diagnostics.
- Patch labels used for diagnosis come from a third party with no documented protocol.
- Only 2 of 9 architectures were tested at 448 px; no heavy model was.
- No Raspberry Pi or Kria measurement exists for any FYP3 model.

## 7. Conclusions

1. A pipeline that looks perfect on GAN data loses 5–9 points on real tissue and more at another centre.
2. The most useful pipeline change for BCI was keeping more resolution, not changing the loss or adding synthetic data.
3. Absolute stain intensity differs between centres enough to shift every score. This is the main obstacle to generalisation found here.
4. A good external score can come from matching stain style. Ranking metrics and a stain-only baseline should accompany external results.

## 8. Next

`ANTIGRAVITY_HANDOFF.md` defines HARMONISE-1: unsupervised domain-level stain calibration with scale as a controlled factor, fitted on the 86 development slides,
with no retraining and one evaluation on the 21 test slides. It is prepared and **has not been run**.
