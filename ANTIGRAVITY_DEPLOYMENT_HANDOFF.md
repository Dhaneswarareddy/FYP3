# Antigravity handoff: FYP3 deployment

> **Historical record; read with corrections (added 10 Nov 2026).** This file is kept unchanged as a log of the work at the time it was written. Some statements in it were later found to be wrong or unsupported (for example: phone "throttled=0x0" flags, a Pi INT8 latency that was never measured, energy/per-watt claims, the DAB mechanism for the 448 px collapse, and several Table 1/2 values). The authoritative versions are `FYP3_FINAL_REPORT.md` (revised 10 Nov 2026), `experiments_v2/README.md`, and the itemised list in `experiments_v2/REPORT_CORRECTIONS_v2.md`.


Prepared 30 Oct 2026 by Claude Code. Start only after `CLAUDE_DEPLOYMENT_READY.txt` exists in the FYP3 root.

**No new experiments.** Do not train, tune, or add architectures or domain adaptation. Do not read the external test split (`FYP/data/raw/HER2-IHC-40x/wsi_test`). Never modify FYP2. Do not change frozen parameters or any existing result.

## 1. Paths

| What | Path |
|---|---|
| Project root | `/Users/dhaneswarareddy/Downloads/FYP3` |
| Python on the Mac | `/Users/dhaneswarareddy/Downloads/Final_Year_Project/Codes/Project/bin/python` |
| Deployment package | `deployment/` |
| Inference code | `deployment/her2_infer/`, `predict.py` |
| Benchmark | `deployment/benchmark.py` |
| Mac preparation scripts | `deployment/mac/prepare.py`, `test_deployment.py`, `verify_artifacts.py` |
| Models | `deployment/models/primary_bci_hires_fp16/`, `experimental_stain224_fp16/` |
| Configs | `deployment/configs/` |
| Pi guide | `DEPLOYMENT_README.md` |
| Model selection | `FINAL_MODEL_SELECTION.md` |
| Technical report | `final_reports/final_fyp3_report.md` |
| Benchmark results go to | `deployment/benchmark_results/` |

## 2. State at handover

| Item | State |
|---|---|
| Both FP16 models | In place, hashes pinned in configs |
| Mode-separation tests | All pass |
| Full FP16 validation | Done: `deployment/reference/validation_full.json` |
| Bundle | **Not built.** Build it in step 3 |
| Pi benchmark | **Not run.** Needs a physical Pi 4B |

## 3. Mac steps (about 5 minutes)

Run in order. Stop at the first failure.

```bash
cd /Users/dhaneswarareddy/Downloads/FYP3/deployment/mac
PY=/Users/dhaneswarareddy/Downloads/Final_Year_Project/Codes/Project/bin/python

$PY verify_artifacts.py                 # D1
$PY test_deployment.py                  # D2
$PY prepare.py --stage bundle           # D3: writes deployment/her2_fyp3_pi_bundle.tar.gz

# D4: test the bundle away from the project, in a new folder
T=$(mktemp -d); tar xzf ../her2_fyp3_pi_bundle.tar.gz -C "$T"; cd "$T/her2_fyp3_pi_bundle"
$PY verify_bundle.py
$PY benchmark.py --mode primary --threads 2 --warmup 2 --runs 5 --e2e-repeats 1 --out-dir r
$PY benchmark.py --mode experimental --i-understand-experimental --threads 2 --warmup 2 --runs 5 --e2e-repeats 1 --out-dir r
```

The benchmark on the Mac writes `NOT_A_PI` files. They only prove the scripts run. **Never report them as Pi results.**

## 4. Raspberry Pi steps

Only if a physical Pi 4B is reachable. Otherwise stop here and report: **Pi benchmark pending, no Pi available.**

Follow `DEPLOYMENT_README.md`: copy the bundle, run `./install_pi.sh`, set the `performance` governor, run `benchmark.py` for both modes with threads 1, 2 and 4, then copy `results/benchmark_*_pi4.csv` to `deployment/benchmark_results/`.

## 5. Go / no-go

| Gate | Pass condition | If it fails |
|---|---|---|
| D0 | `CLAUDE_DEPLOYMENT_READY.txt` exists; no TensorFlow job running | Do not start |
| D1 | `unexpected changes: 0`; `FYP2 files changed ...: 0` | Stop and report |
| D2 | `ALL PASS` | Stop and report |
| D3 | Tarball about 94 MB | Stop and report |
| D4 | `BUNDLE OK`; both benchmarks write CSVs with `agreement_with_mac_tflite` 1.0 | Stop and report |
| P1, on the Pi | `verify_bundle.py` prints `BUNDLE OK` | Stop and report |
| P2, on the Pi | `is_raspberry_pi_4` True, `throttled` `0x0`, governor `performance`, `agreement_with_mac_tflite` ≥ 0.99 | Fix cooling or setup and repeat. Do not report an invalid run |

## 6. Expected values

| Quantity | Expected |
|---|---|
| Benchmark CSV | One row per thread count, with load, warm-up, mean, median, P95 and P99 latency, peak RAM, CPU and agreement columns |
| `agreement_with_keras`, experimental | May be just below 1.0. Near-ties flip under FP16 rounding |
| Mac latency, for scale only | Tens of milliseconds, and it varies with load. **Pi latency will differ and is unknown** |
| Mac peak RAM | About 700 MB, inflated by TensorFlow, which the Pi does not load. It says nothing about the Pi |

## 7. Known risks

- **XNNPACK warning.** The runtime warns that a delegate does not support dynamic-sized tensors in this graph. It was not investigated. Latency on the Pi may be higher than expected if acceleration does not apply. Report the warning if it appears, and do not attempt model surgery.
- **Memory at 448 px** on a low-memory Pi is unknown. An out-of-memory failure is a finding: report it.
- **The Pi runtime differs from the Mac's.** The Mac tests used TensorFlow's interpreter, while the Pi uses `ai-edge-litert` or `tflite-runtime`. P1 and P2 are the first real test of that path.

## 8. Reporting

Write `ANTIGRAVITY_DEPLOYMENT_REPORT.md` in the FYP3 root. It must state:

- each gate's outcome;
- whether a physical Pi was used. If not, say **"Raspberry Pi benchmark not performed"**;
- that genuine WSI identifiers are unavailable;
- that external test labels were previously exposed;
- that borderline HER2 performance remains weak;
- that nothing is clinically validated.

Do not use "clinical workflow" or similar wording. Do not change `FINAL_MODEL_SELECTION.md` or the final report. If valid Pi results exist, list them in your report and leave adding them to the final report to the user.
