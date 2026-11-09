# HARMONISE-2: reliability of the frozen stain calibration

HARMONISE-1 showed that one fixed stain calibration lifts balanced accuracy on HER2-IHC-40x. HARMONISE-2 asks whether that result can be
trusted: is it stable, does it hold class by class, why does it break the 448 px model, and do the networks know when they are wrong?

**It trains nothing, changes no frozen parameter, and never reads the external test split.** The rationale is in `PREPARATION_AUDIT.md`. The run
sequence is in `/Users/dhaneswarareddy/Downloads/FYP3/ANTIGRAVITY_RELIABILITY_HANDOFF.md`.

## Data

All tiles come from the 8,093 development tiles (86 slides) of the WSI-based archive.

| Pool | Tiles | Role here |
|---|---|---|
| HARMONISE-1 fit + selection | 3,500 | **Calibration sampling only**, unlabelled. Labels are used only to build the class-mix scenarios in A |
| Reliability, R (never used by HARMONISE-1) | 4,593 | **Evaluation only** |
| R_cal, 48% of R (target 40%; whole blocks are kept together) | 2,191 | Fits temperature and review thresholds in E |
| R_eval, 52% of R | 2,402 | Reports E and A |
| BCI train | 3,388 | Stain reference |
| BCI val | 727 | Dose-response in BCI's own domain (D) |

R_cal and R_eval are split by index block so that neighbouring filenames stay together.

## Experiments

| | Question | Method | Pre-set rule |
|---|---|---|---|
| **A** | Are the gains and the performance stable? | Bootstrap fit samples (n = 100–1,500), matching percentiles p90–p99.9, then 8 parameter sets through 2 networks. Grid-edge sweep (p97–p99.5). Class-mix stress test (3+ share 5–50%) | Stable if gain CV ≤ 0.10 at n = 1,500, balanced-accuracy range ≤ 0.05, and 2+ and 3+ recall range ≤ 0.10 |
| **B** | Does it generalise across slides? | **Not possible as specified**: no slide identifiers exist. Writes the evidence. An index-block surrogate runs only if the blocks show real structure (median ICC ≥ 0.2), and is never reported as slides | None: the surrogate cannot support a slide-level claim |
| **C** | Do gains hide class failures? | Precision, recall, F1, off-by-two and confusion matrices for all 5 networks, none vs frozen, with index-block bootstrap | Flag a class if recall falls ≥ 0.05, or if recall or F1 is below 0.20 |
| **D** | Why did 448 px break? | H-only vs DAB-only decomposition, dose-response on external and BCI tiles for 224 px and 448 px, gains re-fitted at 448 px, and a scale arm | Resolution-compatible calibration succeeds if balanced accuracy gains ≥ 0.03 and 3+ recall falls ≤ 0.05 |
| **E** | Do the networks know when they are wrong? | ECE, NLL, reliability curves, temperature scaling, and review flagging by max probability, margin and entropy; also whether tiles flip between calibration samples | Usable if coverage ≥ 70% with accuracy gain ≥ 0.10 on R_eval |

## Hypotheses for D, each with the result that would support it

| Hypothesis | Supported if |
|---|---|
| Gains fitted at 256 px do not suit 448 px | `rescompat` gains differ materially from frozen ones and rescue performance |
| Haematoxylin gain causes the failure | `haem_only` reproduces the collapse and `dab_only` does not |
| DAB gain causes the failure | The reverse |
| The 448 px network is inherently more stain-sensitive | It also collapses on **BCI** tiles under the same gains |
| Scale, not stain, is the issue | `frozen_scale2` rescues performance |

## Stages

| Stage | Needs TensorFlow | Output in `outputs/` |
|---|---|---|
| `preflight` | no | `preflight.json`, `protected_before.json` |
| `regress` | yes | `regression.json` |
| `cache` | no | `R_index.csv`, `cache/` |
| `a_params` | no | `A_params_bootstrap.csv`, `A_params_summary.csv`, `A_eval_params.json` |
| `a_eval --run R` | yes | `A_eval_<run>.csv`, `preds/A/` |
| `a_report` | no | `A_verdict.csv`, `A_verdict.json` |
| `b_audit` | no | `B_wsi_audit.json` |
| `b_surrogate` | yes, if allowed | `pseudogroup_*` |
| `c_predict --run R` | yes | `preds/C/` |
| `c_report` | no | `C_classwise.csv`, `C_flags.csv`, `C_confusions.json` |
| `d_params` | no | `D_gains_by_resolution.json` |
| `d_predict --run R`, `d_bci --run R` | yes | `D_external_<run>.csv`, `D_bci_<run>.csv` |
| `d_report` | no | `D_verdict.csv` |
| `e_report` | no | `E_calibration.csv`, `E_flagging.csv`, `E_reliability_curves.csv`, `E_calibration_flips.csv` |
| `report` | no | `RELIABILITY_RESULTS.md`, `figures/` |
| `verify` | no | prints the protected-file check |

`smoke_all.sh` runs every stage on a few tiles into `outputs_smoke/`. Those numbers are not results.

## Limits on interpretation

- **Bootstraps measure tile sampling, not sites.** All tiles share 86 slides from one centre, so stability here is a necessary condition, not proof of stability at another site.
- **Development results may flatter the method.** R shares slides with the tiles that fitted and selected the calibration. Slide-disjoint evidence is limited to HARMONISE-1's single test evaluation.
- **Labels are ROI-level,** so tile-level ECE and error rates include label noise.
- **The class-mix scenarios are simulations** built from one centre's tiles.
- **Stain vectors are generic,** so H and DAB are only approximately separated.
- **Nothing here is a clinical validation.**

## What would unblock experiment B

A patch-to-slide mapping from the dataset authors, or the `WSI/` and `ROI/` folders the Zenodo record describes (not in the local archives). The authors' preprocessing repository, https://github.com/seraju77/HER2-IHC-40x-data-preprocessing, does not define the numbering.
