# Antigravity handoff: HARMONISE-1

Prepared 30 Oct 2026 by Claude Code. **Nothing in this experiment has been run**, apart from a 40-tile smoke test.
It involves **no training**.

## 1. Paths

| What | Path |
|---|---|
| Project root | `/Users/dhaneswarareddy/Downloads/FYP3` |
| Experiment code | `next_experiment/run_harmonise.py`, `harmonise_lib.py`, `smoke_build_panel.py` |
| Configuration | `next_experiment/experiment_config.json` |
| Dependencies | `next_experiment/requirements.txt` (nothing new to install) |
| Python | `/Users/dhaneswarareddy/Downloads/Final_Year_Project/Codes/Project/bin/python` |
| Development tiles, read inside the zip | `/Users/dhaneswarareddy/Downloads/her2-ihc-40x-wsi.zip` |
| External test tiles | `/Users/dhaneswarareddy/Downloads/FYP/data/raw/HER2-IHC-40x/wsi_test` |
| Baseline external results (read-only) | `results/external/her2_40x/` |
| Reports | `final_reports/experiment_audit.md`, `cross_dataset_audit.md`, `quantization_deployment.md`, `final_fyp3_report.md` |
| Tables, figures, audit scripts | `final_reports/tables/`, `figures/`, `scripts/` |
| Your outputs | `next_experiment/outputs/` (created by the run) |
| Smoke output, not results | `next_experiment/outputs_smoke/` |

## 2. Audit findings that matter

- All 40 runs reproduce exactly; splits, class mapping and checkpoints are clean. **No bug explains the external results.**
- FYP2-trained networks beat BCI-trained ones on HER2-IHC-40x because of **stain style**. A stain-only rule fitted on FYP2 reaches accuracy 0.89 and QWK 0.96.
- BCI networks **rank tiles well but score them too high**: mean predicted score 2.71 vs a true 1.53 for the primary model.
- Scale mismatch is about 4–5× and uncertain.
- The external set has 21 test slides, ROI-level labels, no slide IDs and a per-class colour filter.
- External test labels were already seen in diagnostics. That is why **all parameters and the arm choice below come from development slides only**.

## 3. The experiment and why

**Primary experiment: unsupervised domain-level stain calibration, with scale as a controlled factor.**

- **Stain:** one fixed haematoxylin gain and one fixed DAB gain for the whole external domain, fitted by matching a percentile of tissue optical density between
  unlabelled development tiles and BCI training tiles.
- **Scale:** the external tile is downscaled by a factor from a fixed grid (2, 3, 4.8) and passed to the same weights at a smaller input size.

**Why this one:** the audit shows a systematic score shift while ranking is intact, so a global correction is the direct remedy.

| Alternative | Why not primary |
|---|---|
| Per-tile stain normalisation (Macenko, Reinhard) | DAB intensity is the label. Normalising each tile would erase it. The gains here are per domain and preserve the order of tiles |
| Test-time augmentation | Averages orientations; cannot correct a systematic score shift |
| Target-domain fine-tuning | Needs target labels and answers a different question. The 86/21 archive split is the only WSI-level separation, and without slide IDs no further independent split of the 86 is possible. Consider it only later |
| Retraining with stain or scale augmentation | Costly, and absolute DAB level differs between domains with the same labels, so augmentation alone cannot recover it |

**Data roles:**

| Tiles | Slides | Use |
|---|---|---|
| Development: WSI-based train split, 8,093 tiles | 86 | Fit sample (1,500, labels never read); dev-evaluation sample (2,000, disjoint, labels used for arm choice) |
| Test: WSI-based test split, 1,847 tiles | 21 | Evaluated **once**, on the selected arm |
| BCI train | | Stain reference only |
| Patch-based archive | | **Never use** |

**Arms (10, primary model only):** `none`; `scale2`, `scale3`, `scale4.8`; `stain_p90`, `stain_p95`, `stain_p99`; `stain_p95+scale2`, `+scale3`, `+scale4.8`.

**Selection on development tiles (automatic):** highest balanced accuracy of `EfficientNetV2B0__ce`. Arms within 0.01 of the best count as tied, and the simplest wins. It must beat `none` by ≥ 0.03, otherwise **stop: no test stage**.

**Primary endpoint on test:** Δ balanced accuracy of `EfficientNetV2B0__ce` (selected arm − none) **≥ +0.10 with a CI excluding 0**, bootstrapped over filename runs.

**Reported, not decisive:** ΔQWK, per-class recall, mean predicted score, and the other 4 panel runs.

## 4. Run commands

Run one at a time from the experiment folder. CPU is required on macOS: the GPU driver hangs on 448 px models.

```bash
cd /Users/dhaneswarareddy/Downloads/FYP3/next_experiment
PY=/Users/dhaneswarareddy/Downloads/Final_Year_Project/Codes/Project/bin/python

# 1. Protected-file hashes, archive and independence checks (about 10 min)
caffeinate -ims $PY run_harmonise.py --stage preflight
# 2. Fit and freeze the gains (about 3 min)
caffeinate -ims $PY run_harmonise.py --stage fit
# 3. Evaluate the grid on development tiles and select an arm (about 20 min)
caffeinate -ims $PY run_harmonise.py --stage dev --cpu
# 4. ONLY if outputs/dev_selection.json has a non-null "selected" (about 30 min)
for r in EfficientNetV2B0__ce EfficientNetV2B0__ce__hires DenseNet121__ce MobileNetV3Large__corn MobileNetV3Small__ce; do
  caffeinate -ims $PY run_harmonise.py --stage test --run $r --cpu
done
# 5. Final tables and the decision on the primary endpoint
$PY run_harmonise.py --stage summary
# 6. Confirm no protected file changed
$PY run_harmonise.py --stage verify
```

Times are estimates, not measurements. If a stage hangs (no output for 30 min, no CPU use), run `sample <pid> 3`, kill it, and rerun that stage. The test stage skips nothing and refuses to overwrite: delete a partial file only if the process crashed before it was fully written.

## 5. Expected outputs

| File in `next_experiment/outputs/` | Content |
|---|---|
| `preflight.json`, `protected_before.json`, `dev_exclude.txt` | Checks, hashes, excluded near-duplicates |
| `harmonisation_params.json`, `.sha256` | Frozen gains |
| `dev_eval_tiles.txt`, `dev_results.csv`, `dev_selection.json` | Grid results and selected arm |
| `test/<run>.csv`, `test_baseline_reproduction.json` | Test probabilities and the reproduction check |
| `final_summary.csv`, `final_decision.json` | All endpoints and the decision |

## 6. Expected values

These are checks, not forecasts of success.

| Quantity | Expected | If not |
|---|---|---|
| Preflight | `"go": true`, 8,093 dev, 1,847 test, 0 shared names | Stop |
| DAB gain (`g_d`) | Below 1. The smoke run gave about 0.2–0.5 | Inspect if above 1 |
| Haematoxylin gain (`g_h`) | Below 1. The smoke run gave about 0.3 | Inspect if above 1 |
| Dev `none` balanced accuracy | Near the test baseline, 0.30 | Large gaps need explaining before continuing |
| Test baseline reproduction | `max_abs_diff` < 1e-3 | Stop: the path differs from the baseline |
| Test baseline for the primary model | Acc 0.448, bal. acc 0.301, QWK 0.108, mean score 2.71 | Loaded from the stored CSV |

The smoke-test values come from 40 tiles and are **not results**.

## 7. Go / no-go

**Before starting:**
- [ ] No other TensorFlow job is running.
- [ ] `next_experiment/outputs/` does not exist yet.
- [ ] `CLAUDE_PREPARATION_COMPLETE.txt` exists in the project root.

**After preflight:** go only if `preflight.json` has `"go": true`.

**After dev:** go to test only if `selected` is not null. A null is a valid negative result: report it and stop.

**After test:** check `test_baseline_reproduction.json` has `"ok": true`.

**Hard rules:**
- Never tune, select or re-fit anything using test results.
- Never rerun the test stage with different settings. Any later change makes the test exploratory, and it must be labelled so.
- Never train in this experiment, and never write to `results/`, `splits/` or `FYP2/`.
- Do not change `experiment_config.json` after step 2.

## 8. Reporting

- Report `final_decision.json` as it stands, including a negative result.
- Success means calibration transfers to this one curated centre, **not** clinical validity.
- State the 21-slide limit and that the CIs are optimistic.
- Do not claim a Raspberry Pi benchmark.

## 9. Open items, none blocking

- The 4 new runs lack overfitting verdicts. To add them, first copy `results/metrics_all.csv` and `results/overfitting.csv`, then run `python src/evaluate_all.py`, which adds their per-run metrics and rewrites those two aggregates. Not needed for HARMONISE-1.
- `results/selection.json` and `results/REPORT.md` predate E1–E5. Leave them as they are; `final_reports/` holds the current conclusions.
- µm/px of HER2-IHC-40x is not published. The scale grid exists because of this.
- A Raspberry Pi benchmark needs the physical device and a FYP3 bundle, which does not exist.
