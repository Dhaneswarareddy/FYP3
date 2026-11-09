# HARMONISE-2 Reliability Execution Report

**Date**: October 30, 2026  
**Execution Agent**: Antigravity Autonomous Workflow  
**Environment**: MacBook Air M1 (Apple Silicon), Python 3.11.16, TensorFlow 2.15.0  
**Handoff Specification**: `ANTIGRAVITY_RELIABILITY_HANDOFF.md`  
**Primary Deliverable**: `next_experiment/harmonise2/outputs/RELIABILITY_RESULTS.md`  
**Integrity Status**: All 7 Gates Passed (G0–G6); 108 Protected Files Verified Unchanged (0 Changed)  
**External Test Set Guard**: Active (`external_test_dir` quarantined; zero test split reads)

---

## 1. Executive Summary

The HARMONISE-2 reliability suite was executed sequentially to rigorously evaluate the statistical stability, class-wise limits, resolution interaction, and confidence calibration of stain-calibrated HER2 classification models.

### Key Takeaways
1. **Calibration Parameter Stability (Exp A)**: The unsupervised stain calibration parameters ($g_h \approx 0.26, g_d \approx 0.50$) are statistically stable within the HER2-IHC-40x development cohort once sample size $n \ge 1,000$ (coefficient of variation $CV < 0.05$). The resulting balanced accuracy on evaluation tiles ($R_{\text{eval}}$) is exceptionally steady ($0.502$–$0.507$ across bootstrap draws). However, calibration is sensitive to severe class composition skew (e.g. if 3+ representation drops to 5%, $g_d$ inflates to 0.746 and balanced accuracy drops to 0.414).
2. **Structural Limit of Dataset Metadata (Exp B)**: An exhaustive audit proved that **genuine whole-slide identifiers (WSI IDs) do not exist** in the public HER2-IHC-40x tile release. Filenames represent sequential runs per class, not verified slides. Slide-level hierarchical generalisation cannot be claimed. Exploratory 5-fold cross-validation on filename index blocks yielded balanced accuracy across folds of $0.513 \pm 0.053$.
3. **Class-Wise Breakdown and QWK Deception (Exp C)**: While stain calibration lifts overall QWK dramatically (from $\sim 0.08$ to $0.525$ for EfficientNetV2B0 and $0.799$ for MobileNetV3Small), class-wise inspection exposes severe vulnerabilities:
   - Models struggle severely on the borderline classes (1+ and 2+).
   - In `MobileNetV3Small__ce` and `DenseNet121__ce`, the high QWK is driven almost entirely by polar separation (0 vs 3+), while 1+ and 2+ recall remain below $0.14$ and $0.04$, respectively.
   - In `EfficientNetV2B0__ce`, 2+ recall recovers to $0.668$, but at low precision ($0.107$) due to false-positive intrusion from 0 and 1+.
4. **Resolution Compatibility Mechanism (Exp D)**: Optical density gain estimation at 256px ($g_h=0.258, g_d=0.485$) and 448px ($g_h=0.255, g_d=0.492$) is virtually identical, confirming that stain shift is a true pixel-level optical density domain shift rather than a tiling artefact. However, 448px networks rely on membrane boundary contrast; suppressing DAB optical density dims faint membrane signals below the detection threshold, dropping 3+ recall ($0.849 \to 0.307$). Applying scale compensation (`scale2`) restores 3+ recall to $0.701$ and lifts balanced accuracy to $0.322$.
5. **Confidence & Selective Review (Exp E)**: Stain calibration cuts external Expected Calibration Error (ECE) from $>0.55$ to $0.19$–$0.26$, and temperature scaling ($T \approx 2.8$) further aligns confidence to an ECE of $0.100$. However, confidence-based review flagging is **not clinically usable** because low confidence heavily clusters on genuine 2+ cases, discarding up to $75.8\%$–$93.9\%$ of HER2 equivocal cases.

---

## 2. Gate Verification & Integrity Record

All 7 gates were verified sequentially without bypass:

| Gate | Stage | Requirement / Pass Criterion | Result | Status |
|---|---|---|---|---|
| **G0** | Initialization | `CLAUDE_RELIABILITY_READY.txt` present; no conflicting jobs; clean output dir | Verified present; no lingering TF processes | **PASSED** |
| **G1** | `preflight` | `go: true`, $n=4,593$ reliability tiles, `stain_p99`, test guard active | `pools_disjoint: true`, $n=4,593$, test guard active | **PASSED** |
| **G2** | `regress` | Exact reproduction of HARMONISE-1 dev results ($0.2956$ and $0.5104$) | `none: 0.295581`, `stain_p99: 0.510354` ($\Delta < 10^{-6}$) | **PASSED** |
| **G3** | `cache` | $4,593$ tiles (1,765 / 1,038 / 301 / 1,489), $R_{\text{cal}}=2,191$, $R_{\text{eval}}=2,402$ | Verified exact counts: $R_{\text{cal}}=2,191, R_{\text{eval}}=2,402$ | **PASSED** |
| **G4** | `a_params` | Frozen gains ($g_h=0.2545, g_d=0.5045$) lie inside 95% bootstrap interval | $g_h \in [0.247, 0.279], g_d \in [0.451, 0.523]$ | **PASSED** |
| **G5** | `c_report` | Primary model BalAcc on reliability set near dev ($\sim 0.30$ and $\sim 0.51 \pm 0.05$) | `none: 0.2954`, `frozen: 0.5168` | **PASSED** |
| **G6** | `verify` | 0 protected baseline/FYP2 files modified | 108 protected files checked, 0 changed | **PASSED** |

---

## 3. Experiment A: Calibration Stability

### 3.1 Sample Size Dependence
Resampling with replacement from the development fit pool across sample sizes ($n \in \{100, 300, 1000, 1500\}$) for mode `both`:

| $n$ | $g_h$ Mean | $g_h$ CV | $g_d$ Mean | $g_d$ CV | 95% CI $g_d$ |
|---|---|---|---|---|---|
| 100 | 0.257 | 0.123 | 0.478 | 0.142 | [0.352, 0.600] |
| 300 | 0.262 | 0.052 | 0.460 | 0.106 | [0.364, 0.516] |
| 1000 | 0.266 | 0.033 | 0.482 | 0.055 | [0.436, 0.529] |
| 1500 | 0.263 | 0.030 | 0.490 | 0.042 | [0.451, 0.523] |

- **Minimum Stable Sample Size**: $n = 1,000$ tiles achieves the target coefficient of variation ($CV \le 0.05$).
- **Caveat**: This measures sampling variance within the single development institution's staining protocol. It does **not** evaluate multi-center or cross-laboratory staining variation.

### 3.2 Performance Stability on Independent Evaluation Split ($R_{\text{eval}}$, $n=2,402$)
Evaluating 8 bootstrap parameter sets on $R_{\text{eval}}$:

| Model | BalAcc Mean | BalAcc Min | BalAcc Max | Range | QWK Mean | Range | Status |
|---|---|---|---|---|---|---|---|
| `EfficientNetV2B0__ce` | 0.504 | 0.502 | 0.507 | 0.005 | 0.490 | [0.480, 0.496] | **Stable** |
| `MobileNetV3Small__ce` | 0.517 | 0.509 | 0.528 | 0.018 | 0.739 | [0.726, 0.754] | **Stable** |

### 3.3 Class Composition Sensitivity
Evaluating parameter sensitivity when the fraction of 3+ tiles in the calibration pool varies:
- At 50% 3+: $g_d = 0.452 \implies$ BalAcc = 0.509
- At 30% 3+: $g_d = 0.492 \implies$ BalAcc = 0.504
- At 15% 3+: $g_d = 0.557 \implies$ BalAcc = 0.485
- At 5% 3+: $g_d = 0.746 \implies$ BalAcc = 0.414 (drop of $-0.090$)

**Verdict**: Calibration is robust to moderate class composition changes (15%–50% 3+), but degrades if high-intensity DAB tiles are severely depleted ($<10\%$).

---

## 4. Experiment B: WSI-Level Generalisation Audit

### 4.1 Audit Findings
- **Absence of Ground Truth Slide IDs**: The HER2-IHC-40x dataset archives provide only isolated PNG patches numbered sequentially per score (`her2-<score>-score_<split>_<number>.png`). No slide mapping or ROI metadata is included in the release or public repository.
- **Structural Consequence**: True patient-level or slide-level clustering (e.g., hierarchical mixed-effects models or leave-one-slide-out cross-validation) is **impossible**. Any previous claim of "21 slide clusters" was an interpretation based on filename runs rather than verified ground truth.

### 4.2 Exploratory Index-Block Analysis
Using filename block clusters as a surrogate (block gap threshold = 5, ICC $> 0.40$), a 5-fold cross-validation was conducted:
- Fold 0: BalAcc = 0.522, Accuracy = 0.513
- Fold 1: BalAcc = 0.488, Accuracy = 0.402
- Fold 2: BalAcc = 0.583, Accuracy = 0.542
- Fold 3: BalAcc = 0.440, Accuracy = 0.656
- Fold 4: BalAcc = 0.532, Accuracy = 0.405
- **Mean Across Folds**: BalAcc = $0.513 \pm 0.053$.
- **Constraint**: These results must remain marked strictly as exploratory surrogate groupings, not verified clinical WSIs.

---

## 5. Experiment C: Class-Wise Reliability & Failure Analysis

Evaluating all 5 panel models on the full $n=4,593$ reliability tiles with block-bootstrap confidence intervals:

### 5.1 Full Performance Comparison

| Model | Arm | Accuracy | BalAcc | Macro-F1 | QWK | Rec 0 | Rec 1+ | Rec 2+ | Rec 3+ |
|---|---|---|---|---|---|---|---|---|---|
| **EfficientNetV2B0** | `none` | 0.367 | 0.295 | 0.204 | 0.082 | 0.010 | 0.173 | 0.000 | **0.999** |
| (224px, primary) | `frozen` | **0.497** | **0.517** | **0.429** | **0.525** | 0.265 | 0.161 | **0.668** | 0.974 |
| **MobileNetV3Small** | `none` | 0.379 | 0.288 | 0.198 | 0.117 | 0.126 | 0.026 | 0.000 | **1.000** |
| (224px, lightweight) | `frozen` | **0.717** | **0.539** | **0.507** | **0.799** | **0.928** | 0.139 | 0.093 | **0.997** |
| **MobileNetV3Large** | `none` | 0.329 | 0.254 | 0.147 | 0.109 | 0.011 | 0.000 | 0.003 | **1.000** |
| (224px, CORN) | `frozen` | 0.543 | 0.429 | 0.404 | 0.409 | 0.436 | 0.217 | 0.070 | 0.993 |
| **DenseNet121** | `none` | 0.332 | 0.255 | 0.136 | 0.025 | 0.022 | 0.000 | 0.000 | **0.997** |
| (224px, baseline) | `frozen` | 0.627 | 0.447 | 0.404 | 0.758 | **0.964** | 0.010 | 0.037 | 0.777 |
| **EfficientNetV2B0** | `none` | 0.344 | 0.266 | 0.259 | 0.350 | 0.201 | 0.023 | 0.043 | 0.797 |
| (448px, hires) | `frozen` | 0.149 | 0.246 | 0.153 | -0.027 | 0.042 | 0.087 | 0.635 | 0.222 |

### 5.2 Critical Insights on Class Failures
1. **The QWK Fallacy**: High QWK values in `MobileNetV3Small` ($0.799$) and `DenseNet121` ($0.758$) are an artefact of quadratic penalty rewarding extreme class separation (Class 0 recall $>0.92$ and Class 3+ recall $>0.77$). Both models effectively **collapse on Class 1+ and 2+** (recalls $\le 0.139$ and $\le 0.093$).
2. **Equivocal 2+ Detection**: Only `EfficientNetV2B0__ce` with `frozen` calibration achieves meaningful 2+ sensitivity ($0.668$), whereas all other 224px architectures fail on 2+ ($0.037$–$0.093$).
3. **Low 2+ Precision**: The precision of 2+ in `EfficientNetV2B0__ce` remains low ($0.107$) because weakly stained 0 and 1+ tiles are erroneously predicted as 2+.

---

## 6. Experiment D: Resolution Compatibility

### 6.1 Gain Parameter Analysis Across Resolutions
Using the exact fit tiles from HARMONISE-1:
- **256px resolution**: $g_h = 0.2581, g_d = 0.4853$
- **448px resolution**: $g_h = 0.2546, g_d = 0.4915$

**Conclusion on Hypotheses**: The gains are identical across resolutions. Optical density distribution shift between BCI and external data is an intrinsic biochemical staining property, not a resolution artefact.

### 6.2 Why Hires 448px Fails Under Standard Calibration
The hires model was trained on unscaled $512 \to 448$ crops and learned high-frequency membrane continuity features.
- When $g_d = 0.50$ is applied, DAB optical density is halved across the board. In 448px tiles, faint membrane borders drop below the model's activation threshold, driving 3+ recall down from $0.849$ to $0.307$.
- When scale compensation (`scale2`) is applied, balanced accuracy increases to $0.322$ and 3+ recall is maintained at $0.701$.

| Model & Arm | Scale | $g_h$ | $g_d$ | BalAcc | $\Delta$ BalAcc vs None | Rec 3+ | Meets Rule? |
|---|---|---|---|---|---|---|---|
| `hires` (none) | 1.0 | 1.000 | 1.000 | 0.279 | baseline | 0.849 | — |
| `hires` (frozen) | 1.0 | 0.255 | 0.504 | 0.228 | -0.050 | 0.307 | **False** |
| `hires` (rescompat) | 1.0 | 0.255 | 0.492 | 0.227 | -0.052 | 0.304 | **False** |
| `hires` (frozen_scale2) | 2.0 | 0.255 | 0.504 | 0.322 | +0.043 | 0.701 | **False** (drop > 0.10) |
| `hires` (rescompat_scale2)| 2.0 | 0.255 | 0.492 | 0.320 | +0.042 | 0.701 | **False** |

### 6.3 Domain Invariance vs In-Domain Shift (BCI Val)
When calibration gains are applied directly to the in-domain BCI validation set:
- `EfficientNetV2B0__ce`: BalAcc drops from **0.875** (`none`) to **0.407** (`frozen`).
- `EfficientNetV2B0__ce__hires`: BalAcc drops from **0.945** (`none`) to **0.344** (`frozen`).

**Interpretation**: Stain calibration is strictly a directional transfer mapping from external stained slides into the BCI feature manifold. It does not act as a domain-invariant feature representation.

---

## 7. Experiment E: Prediction Confidence & Selective Referral

### 7.1 Expected Calibration Error (ECE) and Temperature Scaling

| Model | Domain / Arm | Temperature $T$ | ECE | Accuracy | Mean Confidence |
|---|---|---|---|---|---|
| **EfficientNetV2B0** | BCI Val (Reference) | 1.000 | **0.061** | 0.895 | 0.950 |
| (primary) | External `none` | 1.000 | 0.555 | 0.344 | 0.899 |
| | External `frozen` | 1.000 | **0.258** | 0.484 | 0.741 |
| | External `frozen` + Temp | 2.842 | **0.100** | 0.484 | 0.540 |
| **MobileNetV3Small** | BCI Val (Reference) | 1.000 | **0.054** | 0.854 | 0.900 |
| | External `none` | 1.000 | 0.613 | 0.341 | 0.953 |
| | External `frozen` | 1.000 | **0.196** | 0.677 | 0.874 |
| | External `frozen` + Temp | 2.080 | **0.079** | 0.677 | 0.756 |
| **DenseNet121** | BCI Val (Reference) | 1.000 | **0.033** | 0.908 | 0.924 |
| | External `frozen` + Temp | 5.306 | **0.061** | 0.602 | 0.598 |
| **Hires 448px** | BCI Val (Reference) | 1.000 | **0.029** | 0.950 | 0.975 |

- Stain calibration reduces ECE by more than half across all 224px models.
- Post-hoc temperature scaling ($T \approx 2.0$–$2.8$) achieves well-calibrated external probabilities ($\text{ECE} \le 0.10$).

### 7.2 Usability of Selective Review Flagging
Evaluating whether uncertain predictions can be deferred to human pathologists:
- In `EfficientNetV2B0__ce` at target coverage 0.50: accuracy on kept tiles rises from $0.484 \to 0.662$ ($+0.179$), but **$75.8\%$ of true 2+ tiles are referred away**.
- In `MobileNetV3Small__ce` at target coverage 0.50: accuracy on kept tiles reaches $0.930$, but **$93.9\%$ of true 2+ tiles are referred away**.
- **Verdict**: In automated review flagging, all configurations failed the usability rule (`usable: False`). Confidence-based thresholding prioritizes extreme classes (0 and 3+) while discarding clinically critical borderline cases (2+).

---

## 8. Final Model Selection & Edge Deployment Readiness

### 8.1 Dual-Track Recommendation

1. **In-Domain Clinical Workflow (BCI Native)**:
   - **Recommended Model**: `EfficientNetV2B0__ce__hires` (448px input).
   - **Performance**: Validation QWK = **0.9345**, Validation Accuracy = **0.9505**, BalAcc = **0.945**.
   - **Edge Deployment**: FP16 TFLite model verified at **11.27 MB** with 100.0% prediction agreement and zero metric drop compared to FP32. INT8 quantization is rejected due to 7.2% disagreement.
2. **Cross-Center / External Screening Workflow**:
   - **Recommended Architecture**: `EfficientNetV2B0__ce` (224px input) paired with `stain_p99` calibration.
   - **Performance**: External BalAcc = **0.503–0.517**, QWK = **0.525–0.593**, 2+ Recall = **0.668**.
   - **Limitation**: Must be deployed with explicit warnings regarding class 1+ sensitivity and 2+ false positives. Selective confidence filtering cannot replace human review for 2+ cases.

### 8.2 Deliverable Artifacts
- Full tabular results and markdown report: `next_experiment/harmonise2/outputs/RELIABILITY_RESULTS.md`
- Figures:
  - `figures/A_gain_vs_percentile.png`
  - `figures/C_recall_by_class.png`
  - `figures/D_dose_response.png`
  - `figures/E_reliability_diagrams.png`
- Gate verification records: `outputs/preflight.json`, `outputs/regression.json`, `outputs/verify.json`
- Deployment models: `results/deployment/EfficientNetV2B0__ce__hires_fp16.tflite` (11.27 MB)
