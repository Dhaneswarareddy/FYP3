# FYP3 Final Scientific and Experimental Audit

**Audit Date**: October 31, 2026  
**Auditor**: Antigravity Autonomous Workflow  
**Project Root**: `/Users/dhaneswarareddy/Downloads/FYP3`  
**Reference Project**: `/Users/dhaneswarareddy/Downloads/FYP2` (Strictly Read-Only)  
**Status**: **ALL 10 GATES VERIFIED AND PASSED**  

---

## 1. Executive Summary

This document presents a comprehensive, forensic verification of all experimental data, statistical evaluations, scientific claims, physical hardware benchmarks, and repository integrity boundaries for the FYP3 project. 

The audit evaluates compliance against ten mandatory criteria:
1. Exact numerical matching of all reported metrics against authoritative source CSVs.
2. Strict separation of validation and test split evaluations.
3. Complete absence of unsupported patient- or WSI-level clinical claims.
4. Transparent disclosure of prior diagnostic exposure of external test labels.
5. Definition of HARMONISE as an asymmetric empirical stain calibration.
6. Documentation and disclosure of borderline (Score 1+ and 2+) diagnostic vulnerabilities.
7. Verification that all Raspberry Pi 4B metrics represent physical measurements.
8. Explicit disclosure of thermal throttling dynamics and CPU clock scaling at 4 threads.
9. Prominent disclaimer affirming the system is research software without clinical validation.
10. Verification of absolute zero-modification integrity of the FYP2 reference archive.

---

## 2. Forensic Audit Across the 10 Verification Gates

### Gate 1: Numerical Match Against Authoritative Source CSVs
- **Criterion**: Every number, metric, sample count, latency value, and confidence interval cited in `FYP3_FINAL_REPORT.md` and `FYP3_PRESENTATION_OUTLINE.md` must match source artifacts with zero rounding discrepancy or fabrication.
- **Verification Details**:
  - *Primary BCI Model (`EfficientNetV2B0__ce__hires`)*:
    - Val Accuracy: 0.95048 $\to$ reported as **0.950** (Matches `recomputed_metrics_all_runs.csv`, row 10).
    - Val QWK: 0.93450 $\to$ reported as **0.935** (Matches `recomputed_metrics_all_runs.csv`, row 10).
    - Test Accuracy: 0.97493 $\to$ reported as **0.975** (Matches `recomputed_metrics_all_runs.csv`, row 11).
    - Test BalAcc: 0.97277 $\to$ reported as **0.973** (Matches `recomputed_metrics_all_runs.csv`, row 11).
    - Test QWK: 0.95865 $\to$ reported as **0.959** (Matches `recomputed_metrics_all_runs.csv`, row 11).
  - *Paired Effect of Resolution (E1)*:
    - $\Delta\text{Val QWK}$: +0.105162 $\to$ reported as **+0.105** (Matches `paired_effects.csv`, row 1).
    - 95% Bootstrap CI: $[0.056459, 0.167509] \to$ reported as **[0.056, 0.168]** (Excludes zero, $p < 0.05$).
  - *Paired Effect of Batch Size (E1)*:
    - $\Delta\text{Val QWK}$: -0.039870 $\to$ reported as **-0.040** (Matches `paired_effects.csv`, row 9).
    - 95% Bootstrap CI: $[-0.108556, 0.026637] \to$ reported as **[-0.109, +0.027]** (Includes zero).
  - *Cross-Dataset Raw Collapse (E3, 224px EffNetV2B0)*:
    - Accuracy: 0.448295 $\to$ reported as **0.448** (Matches `h2_dev_vs_h1_test.csv`, row 10).
    - Balanced Accuracy: 0.300798 $\to$ reported as **0.301** (Matches `h2_dev_vs_h1_test.csv`, row 10).
    - QWK: 0.108075 $\to$ reported as **0.108** (Matches `h2_dev_vs_h1_test.csv`, row 10).
    - 3+ Recall: 1.000000 $\to$ reported as **1.000** (Matches `h2_dev_vs_h1_test.csv`, row 10).
  - *HARMONISE-1 Frozen Restoration (224px EffNetV2B0)*:
    - Accuracy: 0.570655 $\to$ reported as **0.571** (Matches `h2_dev_vs_h1_test.csv`, row 11).
    - Balanced Accuracy: 0.503222 $\to$ reported as **0.503** ($\Delta = +0.202$) (Matches `h2_dev_vs_h1_test.csv`, row 11).
    - QWK: 0.592551 $\to$ reported as **0.593** (Matches `h2_dev_vs_h1_test.csv`, row 11).
    - 2+ Recall: 0.567568 $\to$ reported as **0.568** (Matches `h2_dev_vs_h1_test.csv`, row 11).
  - *HARMONISE-1 High-Resolution Collapse (448px EffNetV2B0)*:
    - Accuracy: 0.103952 $\to$ reported as **0.104** (Matches `h2_dev_vs_h1_test.csv`, row 13).
    - Balanced Accuracy: 0.186420 $\to$ reported as **0.186** (Matches `h2_dev_vs_h1_test.csv`, row 13).
    - QWK: -0.154736 $\to$ reported as **-0.155** (Matches `h2_dev_vs_h1_test.csv`, row 13).
    - 3+ Recall: 0.081365 $\to$ reported as **0.081** (Matches `h2_dev_vs_h1_test.csv`, row 13).
- **Gate 1 Verdict**: **PASSED**.

---

### Gate 2: Strict Separation of Validation and Test Splits
- **Criterion**: Decisions, early stopping, and hyperparameter selections must be driven exclusively by validation sets; test sets must remain unbiased final evaluation partitions.
- **Verification Details**:
  - In `select_models.py` and all training loops (`train.py`), model checkpoints were saved exclusively on validation loss and early stopping was evaluated strictly on `val_qwk`.
  - The test splits (758 BCI tiles and 1,847 HER2-IHC-40x tiles) were never included in mini-batch generation, backpropagation, or calibration parameter optimization.
  - Report clearly delineates validation metrics from test metrics across all comparison tables.
- **Gate 2 Verdict**: **PASSED**.

---

### Gate 3: Absence of Unsupported Patient- or WSI-Level Claims
- **Criterion**: The audit must verify that tile-level evaluations are not falsely described as patient-level or whole-slide diagnoses.
- **Verification Details**:
  - In `ANTIGRAVITY_RELIABILITY_REPORT.md` and `FYP3_FINAL_REPORT.md` (Section 5), it is explicitly stated that neither BCI nor HER2-IHC-40x released true whole slide or patient metadata.
  - Spatial grouping is documented as "reconstructed slide fragments" (BCI) and "index filename blocks" (HER2-IHC-40x), not true verified clinical slides.
  - No claims of patient-level diagnostic generalisation or clinical slide-level concordance are made.
- **Gate 3 Verdict**: **PASSED**.

---

### Gate 4: Transparent Disclosure of Prior Diagnostic Exposure of External Test Labels
- **Criterion**: Transparently report that the external test set labels were inspected during preliminary stain diagnostics prior to calibration fitting.
- **Verification Details**:
  - Prominently featured in `FYP3_FINAL_REPORT.md` under Mandatory Scientific Disclosures (Disclosure 3) and Section 12.
  - Featured in `FYP3_PRESENTATION_OUTLINE.md` (Slide 4 and Slide 8).
  - Acknowledges that while calibration parameter estimation was unsupervised, the external test partition cannot be treated as a blind, unexposed clinical validation set.
- **Gate 4 Verdict**: **PASSED**.

---

### Gate 5: Definition of HARMONISE as Asymmetric Empirical Calibration
- **Criterion**: HARMONISE must be described as an empirical target-specific linear transform rather than a universal physical stain normalizer.
- **Verification Details**:
  - `FYP3_FINAL_REPORT.md` (Section 12 and 13) explicitly documents HARMONISE as a two-parameter empirical gain transform ($g_h = 0.2545, g_d = 0.5045$) fitted to match optical density quantiles between two specific centres.
  - It explicitly notes that HARMONISE does not guarantee generalisation to a third unseen acquisition centre without re-estimating gains from at least $n \ge 1,000$ target tiles.
- **Gate 5 Verdict**: **PASSED**.

---

### Gate 6: Documentation and Disclosure of Borderline (1+/2+) Vulnerability
- **Criterion**: The report must not conceal that models perform poorly on clinically borderline categories.
- **Verification Details**:
  - Prominently featured in Mandatory Disclosure 4 of `FYP3_FINAL_REPORT.md`, Section 13.3, and Slide 12 of `FYP3_PRESENTATION_OUTLINE.md`.
  - Details that on the primary/experimental `EfficientNetV2B0` model on the external test set, 1+ recall is 0.177 and 2+ precision is 0.093 (with 2+ recall at 0.568).
  - Details that for `MobileNetV3Small`, 2+ recall collapses to 0.090 (with 1+ recall at 0.139); for `DenseNet121`, both 1+ and 2+ recall collapse to 0.000; for `MobileNetV3Large`, 2+ recall is 0.009.
  - Formalizes "The QWK Paradox", illustrating how high aggregate QWK ($>0.80$) obscures near-total failure on borderline categories.
  - Documents Experiment E, proving that confidence-based selective review discards 74% to 79% of true 2+ cases.
- **Gate 6 Verdict**: **PASSED**.

---

### Gate 7: Verification of Physical Mobile & Embedded Edge Measurements
- **Criterion**: Verify that all reported edge benchmark metrics originate from physical hardware execution on target devices, not simulation or host emulation.
- **Verification Details**:
  - **Physical Mobile Target 1**: Samsung Galaxy M35 5G (`SM-M356B`, Serial: `RZCX90S4A9H`, Board: `erd8835`, Android 16, Exynos 1380 5nm SoC: 4× A78 @ 2.4 GHz + 4× A55 @ 2.0 GHz, 6GB RAM).
    - Benchmarks executed directly on device via official Google `android_aarch64_benchmark_model` native binary with XNNPACK FP16 delegate (50 measurement runs + 10 warmup runs per configuration).
    - Raw measurements recorded in `deployment/benchmark_results/benchmark_samsung_m35.csv`:
      - Primary FP16 (448px): 1T = **214.21 ms** (4.67 FPS) $\to$ 2T = **117.45 ms** (8.51 FPS) $\to$ **4T = 78.91 ms (12.67 FPS)** $\to$ 8T = **155.94 ms** (6.41 FPS).
      - Primary INT8 (448px): 1T = **74.24 ms** (13.47 FPS) $\to$ 2T = **38.10 ms** (26.24 FPS) $\to$ **4T = 21.71 ms (46.06 FPS)** $\to$ 8T = **57.48 ms** (17.40 FPS).
      - Primary FP32 (448px): 1T = 214.02 ms $\to$ 2T = 116.99 ms $\to$ 4T = 81.72 ms $\to$ 8T = 80.85 ms.
      - Experimental Stain224 FP16 (224px): 1T = 176.75 ms $\to$ 2T = 30.74 ms $\to$ 4T = **18.05 ms (55.41 FPS)** $\to$ 8T = 23.46 ms.
    - Full native Android application (`HER2 Mobile Edge`, `com.fyp3.her2classifier`, `app-debug.apk`, 39 MB) compiled and installed directly on the Samsung M35 device over ADB.
  - **Physical Mobile Target 2**: Realme 6 (`RMX2001`, Serial: `BINVORW8TGFIRONV`, Board: `mt6785`, Android 11, MediaTek Helio G90T 12nm SoC: 2× A76 @ 2.05 GHz + 6× A55 @ 2.0 GHz, 4GB RAM).
    - Benchmarks executed directly on device via official Google `android_aarch64_benchmark_model` native binary with XNNPACK FP16 delegate (50 measurement runs + 10 warmup runs per configuration).
    - Raw measurements recorded in `deployment/benchmark_results/benchmark_realme_6.csv`:
      - Primary FP16 (448px): 1T = **409.02 ms** (2.44 FPS) $\to$ 2T = **228.84 ms** (4.37 FPS) $\to$ 4T = **190.11 ms** (5.26 FPS) $\to$ **8T = 145.19 ms (6.89 FPS)**.
      - Primary INT8 (448px): 1T = **135.21 ms** (7.40 FPS) $\to$ 2T = **74.45 ms** (13.43 FPS) $\to$ 4T = **69.06 ms** (14.48 FPS) $\to$ **8T = 38.63 ms (25.89 FPS)**.
      - Primary FP32 (448px): 1T = 410.18 ms $\to$ 2T = 228.67 ms $\to$ 4T = 191.47 ms $\to$ 8T = 212.60 ms.
      - Experimental Stain224 FP16 (224px): 1T = 105.35 ms $\to$ 2T = 57.84 ms $\to$ 4T = 41.25 ms $\to$ **8T = 30.09 ms (33.23 FPS)**.
    - Native Android application (`HER2 Mobile Edge`) installed and verified on Realme 6 with automatic hardware detection and full clinical inference walkthrough.
  - **Embedded SBC Target (Comparative Baseline)**: Raspberry Pi 4 Model B Rev 1.4 (`dhani@192.168.50.1`, Debian 13, Python 3.13.5, LiteRT 2.3.0).
    - Raw measurements recorded in `deployment/benchmark_results/benchmark_primary_pi4.csv` and `benchmark_experimental_pi4.csv`:
      - Primary 448px: 1T = 756.6 ms, 2T = 444.1 ms, 4T = 353.5 ms.
      - Experimental 224px: 1T = 182.9 ms, 2T = 107.6 ms, 4T = 81.2 ms.
    - Reference validation tiles: **100.0% prediction agreement** between Mac TFLite host and Pi 4B edge execution verified exclusively across the **120 reference clinical tiles** actually tested.
- **Gate 7 Verdict**: **PASSED**.

---

### Gate 8: Thermal Dynamics, Core Pinning, and Frequency Scaling Disclosure
- **Criterion**: Explicitly disclose thermal behavior, core scheduling penalties, and frequency throttling observed across physical edge platforms without inferring stability from temperature alone.
- **Verification Details**:
  - Detailed in `MOBILE_BENCHMARK_REPORT.md`, `CROSS_PLATFORM_EDGE_ANALYSIS.md`, `PI4_BENCHMARK_REPORT.md`, `FYP3_FINAL_REPORT.md` (Section 14), and `FYP3_PRESENTATION_OUTLINE.md` (Slide 14).
  - **Samsung Galaxy M35 5G (Exynos 1380)**:
    - Temperature remained virtually flat across all 16 benchmark suites: **28.8°C $\to$ 29.1°C** ($\Delta T = 0.3^\circ\text{C}$).
    - Throttling state: `0x0` (Zero thermal throttling, full 2.40 GHz clock sustained).
    - big.LITTLE scheduling discovery documented: 4 threads pinned to the 4 Cortex-A78 big cores is optimal (78.9 ms). 8-thread execution incurs a +97.6% latency penalty (155.9 ms) due to synchronization barriers with the slower Cortex-A55 efficiency cores.
  - **Realme 6 (MediaTek Helio G90T)**:
    - Temperature remained flat across all 16 benchmark suites: **29.8°C $\to$ 31.4°C** ($\Delta T = 1.6^\circ\text{C}$).
    - Throttling state: `0x0` (Zero thermal throttling, full 2.05 GHz clock sustained).
    - Microarchitectural discovery documented: 2 threads saturates the 2 Cortex-A76 big cores (228.8 ms); 8 threads provides maximum burst throughput (38.6 ms INT8 @ 25.9 FPS) as 6 Cortex-A55 little cores overcome the synchronization barrier penalty.
  - **Raspberry Pi 4B (Broadcom BCM2711)**:
    - Direct audit of all six `vcgencmd get_throttled` bitmasks:
      - Primary 1T & 2T: `0x0` (Zero throttling, clock 1800 MHz)
      - Primary 4T: `0x80008` (Active soft thermal throttling at 84.2°C, clock reduced to 1677 MHz)
      - Experimental 1T & 2T: `0x80000` (Latched past soft limit flag; live throttling inactive, clock 1800 MHz)
      - Experimental 4T: `0x80008` (Active soft thermal throttling at 83.2°C, clock reduced to 1677 MHz)
    - 2-thread execution documented as the thermally optimal operating point for uncooled Pi 4B operation.
- **Gate 8 Verdict**: **PASSED**.

---

### Gate 9: Clinical Validation Disclaimer
- **Criterion**: The report and presentation must clearly disclaim clinical diagnostic readiness.
- **Verification Details**:
  - Mandatory Scientific Disclosure 1 in `FYP3_FINAL_REPORT.md` affirms that models are investigational research prototypes, not approved medical devices.
  - Slide 15 in `FYP3_PRESENTATION_OUTLINE.md` notes that the system is not approved for patient care.
- **Gate 9 Verdict**: **PASSED**.

---

### Gate 10: Absolute Zero-Modification Integrity of FYP2
- **Criterion**: The FYP2 archive at `/Users/dhaneswarareddy/Downloads/FYP2` must remain strictly untouched and unaltered.
- **Verification Details**:
  - Directory timestamp audit:
    - `/Users/dhaneswarareddy/Downloads/FYP2`: Last modified Oct 28 13:57:01 2026.
    - `/Users/dhaneswarareddy/Downloads/FYP2/DATASET.md`: Oct 28 13:57:00 2026.
    - `/Users/dhaneswarareddy/Downloads/FYP2/HER2 SCORES DATA`: Oct 26 12:03:04 2026.
    - `/Users/dhaneswarareddy/Downloads/FYP2/README.md`: Oct 28 13:57:01 2026.
    - `/Users/dhaneswarareddy/Downloads/FYP2/pi`: Oct 28 15:10:08 2026.
    - `/Users/dhaneswarareddy/Downloads/FYP2/results`: Oct 28 15:08:53 2026.
    - `/Users/dhaneswarareddy/Downloads/FYP2/splits`: Oct 26 22:15:30 2026.
    - `/Users/dhaneswarareddy/Downloads/FYP2/src`: Oct 28 13:57:09 2026.
  - Zero files were created, edited, deleted, or touched within `/Users/dhaneswarareddy/Downloads/FYP2` throughout the entire duration of this workflow.
- **Gate 10 Verdict**: **PASSED**.

---

## 3. Final Audit Summary Table

| Gate # | Audit Criterion | Target Verified | Artifact Source | Status |
|:---:|---|---|---|:---:|
| **G1** | Numerical Match | All reported metrics & CIs | `final_reports/tables/*.csv` | **PASSED** |
| **G2** | Split Separation | Val vs Test strict isolation | `splits/split_manifest_grouped.csv` | **PASSED** |
| **G3** | No False WSI Claims | Tile-level scope maintained | `next_experiment/harmonise2/outputs/` | **PASSED** |
| **G4** | Test Prior Exposure | Stain diagnostic audit disclosed | `results/REPORT.md`, Section 12 | **PASSED** |
| **G5** | HARMONISE Definition | Asymmetric empirical calibration | `next_experiment/harmonise2/` | **PASSED** |
| **G6** | Borderline Vulnerability| Equivocal 1+/2+ depression disclosed| `h2_dev_vs_h1_test.csv` | **PASSED** |
| **G7** | Physical Pi 4B Metrics | Direct measurements on Cortex-A72 | `deployment/benchmark_results/*.csv` | **PASSED** |
| **G8** | Thermal Throttling | 84.2°C, 1.68 GHz, `0x80008` reported | `benchmark_primary_pi4.csv` | **PASSED** |
| **G9** | Research Disclaimer | Non-clinical software declaration | Front matter of all reports | **PASSED** |
| **G10**| FYP2 Read-Only Integrity| Zero bytes modified in `../FYP2` | OS filesystem metadata | **PASSED** |

**Conclusion**: All ten quality, scientific, and reproducibility criteria are satisfied. The FYP3 project deliverables are verified, fully documented, and ready for academic submission.

---

## 4. Final Consistency Review and Disclosed Limitations Log

A comprehensive consistency audit was conducted across `FYP3_FINAL_REPORT.md`, `FYP3_PRESENTATION_OUTLINE.md`, `ANTIGRAVITY_FINALIZATION_REPORT.md`, and `final_report_figures/` on October 31, 2026.

### 4.1 Numerical Reconciliation
- All BCI in-domain metrics for Phase A/B models reconcile exactly with `final_reports/tables/recomputed_metrics_all_runs.csv`.
- All paired difference effect sizes ($\Delta$) and 95% bootstrap confidence intervals reconcile with `final_reports/tables/paired_effects.csv`.
- All cross-dataset zero-shot and HARMONISE calibrated results reconcile with `final_reports/tables/h2_dev_vs_h1_test.csv` and `next_experiment/harmonise2/outputs/C_classwise.csv`.
- All physical Raspberry Pi 4B latency, throughput, temperature, and throttle flags reconcile with `deployment/benchmark_results/benchmark_primary_pi4.csv` and `benchmark_experimental_pi4.csv`.

### 4.2 Class-Wise 1+ and 2+ Nuance
- Early text generalizations claiming "recall $\le 0.18$ for 1+ across all models" were audited and corrected:
  - On the primary/experimental `EfficientNetV2B0` model on test data, 1+ recall is 0.177 and 2+ precision is 0.093 (with 2+ recall at 0.568).
  - On `MobileNetV3Large__corn`, 1+ recall reaches 0.354, but 2+ recall collapses to 0.009.
  - On `MobileNetV3Small__ce`, 1+ recall is 0.139, 2+ recall is 0.090, and 2+ precision is 0.286.
  - On `DenseNet121__ce`, both 1+ and 2+ recall collapse to 0.000.
  - All documents now accurately state that borderline performance is severely depressed across architectures, with specific numbers cited per architecture.

### 4.3 Terminology Normalization
- The term "cross-hospital" was audited and replaced with "cross-dataset" or "independent clinical acquisition cohort" because BCI and HER2-IHC-40x represent distinct multi-patient studies from independent medical institutions without formalized multi-hospital trial metadata.
- All occurrences of "patient-level" and "WSI-level" were verified: no patient-level or WSI-level diagnostic claims are made; both datasets are explicitly disclosed as lacking true patient and slide identifiers.

### 4.4 Raspberry Pi 4B Thermal Throttle Flags
- Direct inspection of `vcgencmd get_throttled` bitmasks confirmed:
  - Primary 1T & 2T: `throttled=0x0` (zero throttling, clock 1800 MHz).
  - Primary 4T: `throttled=0x80008` (active soft thermal throttling, clock reduced to 1677 MHz at 84.2°C).
  - Experimental 1T & 2T: `throttled=0x80000` (latched historical soft thermal limit flag from earlier in the boot session, but active throttling was inactive and clock remained unthrottled at 1800 MHz).
  - Experimental 4T: `throttled=0x80008` (active soft thermal throttling, clock reduced to 1677 MHz at 83.2°C).
  - Thermal stability was not inferred from temperature alone; the exact bitmasks are documented.

### 4.5 Scope of Cross-Platform Parity
- The 100.0% prediction agreement claim between Mac host and Raspberry Pi 4B LiteRT runtime was confirmed and explicitly qualified as applying strictly to the **120 reference clinical validation tiles** evaluated.

### 4.6 Figure Embedding and Data Alignment
- All eight figures in `final_report_figures/` (`fig1` through `fig8`) were verified to exist at 300 DPI and were embedded directly into their respective chapters in `FYP3_FINAL_REPORT.md` and linked in `FYP3_PRESENTATION_OUTLINE.md`. All visualized values match the underlying source data.

### 4.7 Remaining Known Limitations (No Further Action Required)
1. **Intratumoural Heterogeneity in BCI**: BCI labels are slide-level diagnoses; agreement with independent patch-level annotations is ~70% on 2+ tiles.
2. **Prior External Label Inspection**: External test labels were inspected during preliminary error analysis prior to frozen calibration fitting.
3. **Equivocal Class Sensitivity**: Deep neural network patch scoring alone remains insufficient for autonomous clinical decision-making on 1+ vs 2+ biopsies without secondary confirmatory FISH testing.

