# Antigravity handoff: HARMONISE-2 reliability experiments

> **Historical record; read with corrections (added 10 Nov 2026).** This file is kept unchanged as a log of the work at the time it was written. Some statements in it were later found to be wrong or unsupported (for example: phone "throttled=0x0" flags, a Pi INT8 latency that was never measured, energy/per-watt claims, the DAB mechanism for the 448 px collapse, and several Table 1/2 values). The authoritative versions are `FYP3_FINAL_REPORT.md` (revised 10 Nov 2026), `experiments_v2/README.md`, and the itemised list in `experiments_v2/REPORT_CORRECTIONS_v2.md`.


Prepared 30 Oct 2026 by Claude Code. Start only after `CLAUDE_RELIABILITY_READY.txt` exists in the FYP3 root.
Only smoke tests have been run. **No training. The external test split is never read.**

## 1. Paths

| What | Path |
|---|---|
| Project root | `/Users/dhaneswarareddy/Downloads/FYP3` |
| Work folder | `next_experiment/harmonise2/` |
| Driver and library | `run_h2.py`, `h2_lib.py` (reuses `next_experiment/harmonise_lib.py` unchanged) |
| Configuration | `next_experiment/harmonise2/config.json` |
| Method and hypotheses | `next_experiment/harmonise2/README.md` |
| Audit of HARMONISE-1 | `next_experiment/harmonise2/PREPARATION_AUDIT.md` |
| Dependencies | `next_experiment/harmonise2/requirements.txt` (nothing new to install) |
| Python | `/Users/dhaneswarareddy/Downloads/Final_Year_Project/Codes/Project/bin/python` |
| Development tiles, read inside the zip | `/Users/dhaneswarareddy/Downloads/her2-ihc-40x-wsi.zip` |
| Frozen parameters (read-only) | `next_experiment/outputs/harmonisation_params.json` |
| Your outputs | `next_experiment/harmonise2/outputs/` |
| Smoke output, not results | `next_experiment/harmonise2/outputs_smoke/` |

Free disk needed: about 5 GB, mostly `outputs/cache/`, which can be deleted after the run.

## 2. Key facts before you start

- **No genuine WSI identifiers exist.** Experiment B therefore documents why per-slide analysis is impossible. Do not create or report slide IDs.
- **Index blocks are not slides.** They are runs of nearby filename numbers. Never call them slides, ROIs, patients or clusters of slides.
- **`next_experiment/outputs/` is frozen.** Do not change anything from HARMONISE-1.
- Corrections to the HARMONISE-1 execution report are in `PREPARATION_AUDIT.md`. Do not repeat "21 slide clusters".

## 3. Execution sequence

Run one stage at a time. Estimated total is 2.5–3 hours on the Mac CPU; times are estimates, not measurements.

```bash
cd /Users/dhaneswarareddy/Downloads/FYP3/next_experiment/harmonise2
PY=/Users/dhaneswarareddy/Downloads/Final_Year_Project/Codes/Project/bin/python
R="caffeinate -ims $PY run_h2.py --stage"

# Setup (about 35 min)
$R preflight                     # G1
$R regress                       # G2: reproduces HARMONISE-1 dev metrics
$R cache                         # G3

# A. Calibration stability (about 35 min)
$R a_params                      # G4
for r in EfficientNetV2B0__ce MobileNetV3Small__ce; do $R a_eval --run $r; done
$R a_report

# B. WSI-level generalisation (about 5 min)
$R b_audit
$R b_surrogate                   # skips itself unless the blocks pass the pre-set check

# C. Class-wise reliability (about 45 min)
for r in EfficientNetV2B0__ce MobileNetV3Small__ce MobileNetV3Large__corn DenseNet121__ce EfficientNetV2B0__ce__hires; do $R c_predict --run $r; done
$R c_report                      # G5

# D. Resolution compatibility (about 40 min)
$R d_params
for r in EfficientNetV2B0__ce EfficientNetV2B0__ce__hires; do $R d_predict --run $r; $R d_bci --run $r; done
$R d_report

# E. Prediction confidence, and the results file (about 5 min)
$R e_report
$R report
$R verify                        # G6
```

If a stage hangs (no output for 30 min and no CPU use), run `sample <pid> 3`, kill it, and rerun that stage. Finished stages need not be repeated.

## 4. Go / no-go gates

| Gate | After | Pass condition | If it fails |
|---|---|---|---|
| G0 | Before starting | Signal file exists; no other TensorFlow job; `harmonise2/outputs/` does not exist | Do not start |
| G1 | `preflight` | `preflight.json`: `"go": true`, 4,593 reliability tiles, `frozen_arm` is `stain_p99` | Stop and report |
| G2 | `regress` | `regression.json`: `"ok": true`. Balanced accuracy within 0.001 of stored `none` 0.2956 and `stain_p99` 0.5104 | **Stop.** The code path differs from HARMONISE-1 |
| G3 | `cache` | `R_index.csv` has 4,593 rows, classes 1,765 / 1,038 / 301 / 1,489, subsets R_cal 2,191 and R_eval 2,402 | Stop and report |
| G4 | `a_params` | Frozen p99 gains (g_h 0.2545, g_d 0.5045) lie inside the bootstrap interval in `A_params_summary.csv` for n = 1,500, mode `both` | Continue, and report it as a finding |
| G5 | `c_report` | In `C_classwise.csv`, primary model balanced accuracy near HARMONISE-1 dev: `none` about 0.30, `frozen` about 0.51 (± 0.05) | Stop and investigate before D and E |
| G6 | `verify` | `0 changed` | Report immediately |

## 5. Expected outputs

Everything goes to `next_experiment/harmonise2/outputs/`. The main deliverable is **`RELIABILITY_RESULTS.md`**, with figures in `figures/`.

| Experiment | Files |
|---|---|
| A | `A_params_summary.csv`, `A_eval_params.json`, `A_eval_<run>.csv`, `A_verdict.csv`, `A_verdict.json` |
| B | `B_wsi_audit.json`; `pseudogroup_status.json` and, only if allowed, `pseudogroup_folds.csv`, `pseudogroup_blocks.csv` |
| C | `C_classwise.csv`, `C_flags.csv`, `C_confusions.json` |
| D | `D_gains_by_resolution.json`, `D_external_<run>.csv`, `D_bci_<run>.csv`, `D_verdict.csv` |
| E | `E_calibration.csv`, `E_flagging.csv`, `E_reliability_curves.csv`, `E_calibration_flips.csv` |

## 6. Expected results

Reference values, not targets. Do not adjust anything to reach them.

| Quantity | Reference |
|---|---|
| Primary model on development tiles, HARMONISE-1 | `none` 0.296, `stain_p99` 0.510 balanced accuracy |
| Same model on external test, HARMONISE-1 | 0.301 and 0.503 |
| Class failures seen on test, likely to recur | DenseNet121 1+ and 2+; MobileNetV3Small 2+; MobileNetV3Large 2+ |
| 448 px with frozen gains | Expected to fail: 3+ recall 0.08 on test |
| p99 DAB gain | Expected to be less stable than p90–p95, because it rests on the tail of the distribution |
| Gains at 256 and 448 px | Nearly equal in the 20-tile smoke test (0.54 vs 0.54). If this holds, the execution report's resolution explanation is wrong |
| Index-block ICC | Unknown. The smoke value is meaningless |

## 7. Safeguards

- Do not read `FYP/data/raw/HER2-IHC-40x/wsi_test`, `results/external/`, or `next_experiment/outputs/test/` for any purpose in this run. `h2_lib.py` disables the test functions.
- Do not train, fine-tune or update BatchNorm statistics.
- Do not adopt a new calibration. A, D and E measure; they do not select a replacement for `stain_p99`.
- **Do not run a new external test evaluation.** If D finds a working 448 px calibration, report it as a development-only result. A later test look would be exploratory and needs the user's decision.
- Do not edit `config.json` after `cache`. Any change must be reported.
- Write only inside `next_experiment/harmonise2/`. Never modify FYP2.

## 8. Reporting rules

Write `ANTIGRAVITY_RELIABILITY_REPORT.md` in the FYP3 root after the run.

- Report each experiment's pre-set verdict as it stands, including unfavourable ones.
- Lead with class-wise results, not QWK.
- State plainly that per-slide analysis (B) could not be done, and why.
- State that A measures tile sampling within one centre, not site-to-site stability.
- For D, say which hypothesis in `README.md` the evidence supports. If none clearly does, say so. Do not offer an explanation the data do not test.
- Mark any explanation that was not directly tested as an interpretation.
- Do not claim clinical validity or any Raspberry Pi result.

## 9. Blockers and open items

- **B as specified is blocked**: it needs a patch-to-slide mapping or the original `WSI/` and `ROI/` folders. This does not block the rest of the run. The dataset authors would need to supply them.
- `harmonise2/outputs_smoke/` and `outputs/cache/` can be removed after the run.
