# FYP3: the FYP2 pipeline on real HER2 IHC (BCI dataset)

This is a separate experiment. **FYP2 is the main project and is not modified.** FYP3 reads FYP2's split, images,
weights and results, and writes only inside `FYP3/`. The BCI raw data (`FYP/data/raw/BCI_dataset`) is read only.

**Scope:** training, evaluation, comparison with FYP2, feature analysis and performance diagnosis (the pipeline below),
then external evaluation on HER2-IHC-40x with stain calibration (HARMONISE), the extended evaluation in `experiments_v2/`,
and deployment of the primary model to Android phones and a Raspberry Pi 4B (`deployment/`, `android_app/`).
The current write-up is `FYP3_FINAL_REPORT.md` (revised 10 Nov 2026); every correction to earlier versions is listed in
`experiments_v2/REPORT_CORRECTIONS_v2.md`.

**Start here:** `PROJECT_STATUS_AND_ROADMAP.md` lists every experiment in pipeline order (data → training → evaluation →
other laboratories → deployment), with results, evidence locations, a must-disclose list, and the split into this
semester's work (Steps 1–14) and next semester's (Steps 15 onward).

## Key findings (from `FYP3_FINAL_REPORT.md`)

- **In-domain (BCI, grouped split).** Validation accuracy of the baselines is 85.4%–90.8%. 448 px input is a confirmed
  improvement for EfficientNetV2B0 against a batch-matched 224 px control (Δ val QWK +0.105 [0.056, 0.168], Δ test QWK
  +0.063 [0.026, 0.116]); it was not confirmed for MobileNetV3Small. Primary model `EfficientNetV2B0__ce__hires`: val
  acc 0.950, QWK 0.935; test acc 0.975, QWK 0.959. FYP2 synthetic pretraining or mixing gave no measurable change.
- **External (HER2-IHC-40x, University of Malaya, Data in Brief 2025).** The test split (1,847 tiles) was examined in
  earlier diagnostics, so external results are exploratory. Zero-shot, the BCI networks collapse (accuracy 0.419–0.586,
  balanced accuracy 0.260–0.381; 43%–94% of tiles predicted 3+). HARMONISE (two optical-density gains fitted on
  unlabelled development tiles against BCI training tiles) raises 224 px EfficientNetV2B0 balanced accuracy from 0.301
  to 0.503, but sends 61% of negatives to 2+ and breaks the 448 px model (0.186; the development-tile dose-response points
  to the haematoxylin gain). FYP2's synthetic-trained networks score better here (0.61–0.73), explained by the external
  set's per-class colour selection.
- **Extended evaluation (`experiments_v2/`).** The 448 px model has the lowest clinical workflow cost on BCI test (0.12
  vs 0.31 for 224 px) and supports referral (93.7% coverage: accuracy 0.975 → 0.989), but is defocus-sensitive (blur
  σ = 0.9 µm costs 0.17 balanced accuracy vs 0.03 at 224 px). Grad-CAM suggests correct external 1+ calls attend to
  glass and pale areas. AdaBN reaches about 0.52 external balanced accuracy and rescues the 448 px model (0.516);
  fine-tuning on 5 labelled tiles per class reaches 0.782 ± 0.053. A frozen ImageNet backbone costs about 19 accuracy
  points.
- **Edge (measured 10 Nov 2026).** Android app v1.1 (preprocessing bit-exact with training) reproduces the validated
  predictions on 758/758 BCI test tiles on both a Samsung Galaxy M35 5G and a Realme 6 (accuracy 0.975). Median network
  latency per 448 px tile (FP16): 81.4 ms (Samsung, 4 threads), 139.1 ms (Realme, 8 threads), 336.5 ms (Raspberry Pi 4B,
  4 threads). INT8 is 3–4× faster but fails the accuracy gate (agreement 0.928) and is for speed tests only. Phone power
  (battery fuel gauge, measured afterwards; `experiments_v2/10_power/`): inference adds about 4 W at 4 threads, 0.39 J
  (Samsung) and 0.61 J (Realme) per tile above idle; Pi power not measured. Phone temperatures are battery temperatures.

## Pipeline

Run from `src/` with `PY=/Users/dhaneswarareddy/Downloads/Final_Year_Project/Codes/Project/bin/python`.
Every step uses the main **grouped** split. Prefix a command with `FYP3_SPLIT=official` to use the official BCI split (reference only).

| Step | Command | Output |
|---|---|---|
| 1. Data + official split | `$PY prepare_data.py` | `data/ihc_256/`, `splits/split_manifest_official.csv`, `results/features/` |
| 1a. Slide fragments (edge matching) | `$PY analysis_slides.py` | `results/analysis/slide_fragments.csv`, `edge_matches.csv` |
| 1b. Main grouped split | `$PY make_grouped_split.py` | `splits/split_manifest_grouped.csv` |
| 2. Train baseline (FYP2 pipeline) | `./run_queue.sh MobileNetV3Small:ce ...`; one run: `$PY train.py --model X --loss ce` | `results/runs/<model>__<loss>/` |
| 2b. Train improvement variants | `./run_variants.sh MobileNetV3Small:ce:cw ...`; one run: `$PY train_variant.py --model X --loss ce --variant cw` | `results/runs/<model>__<loss>__<variant>/` |
| 3. Full metrics + overfitting check | `$PY evaluate_all.py` (448 px runs are evaluated on the CPU automatically: GPU inference hangs) | `results/metrics/`, `metrics_all.csv`, `overfitting.csv` |
| 3b. Paired comparison of two runs | `$PY paired.py RUN_A RUN_B --split val` | printed Δ with fragment-cluster CIs |
| 4. Selection | `$PY select_models.py` | `results/selection.json` |
| 5a. Diagnosis, model-free | `$PY analysis_data.py` | `results/analysis/data_*.csv`, `stain_vs_background.csv`, figures D1–D2 |
| 5b. Diagnosis, labels/scan type/error drivers | `$PY analysis_labels.py` | `results/analysis/label_noise.csv`, `scan_type.csv`, `scan_by_class.csv`, `error_drivers.csv`, `prediction_drivers.csv`, figure D3 |
| 5c. Diagnosis, learned features | `./run_analysis_models.sh` (one process per architecture), except ConvNeXtTiny: `$PY analysis_models.py --archs ConvNeXtTiny --cpu` (its Grad-CAM deadlocks on the Mac GPU). Then `$PY analysis_models.py` redraws tables and figures from the cache | `results/analysis/model_summary.csv`, `cka.csv`, `stain_sensitivity.csv`, figures D4–D7, D10 |
| 5c2. Haematoxylin-cue test (FYP2-trained networks) | `$PY analysis_haem_cue.py --arch X` per architecture, then `$PY analysis_haem_cue.py` | `results/analysis/haem_cue.csv`, `haem_cue_decision.json`, figure D11 |
| 5d. Leakage effect and held-out variance | `$PY analysis_leakage.py` | `results/analysis/leakage_*.csv`, `heldout_*.csv`, figure D9 |
| 6. Report | `$PY report.py` | `results/REPORT.md` (+ `results/findings.md`, written by hand) |

**Uncertainty.** Tiles cut from one slide region are correlated, so every CI resamples whole slide fragments,
not tiles. One held-out split carries several points of noise (grouped test accuracy is 2.4–7.3 points above
validation accuracy for every one of the 9 baselines). Compare models with paired differences on the same tiles (`paired.py`), not with
their separate accuracies.

## What is the same as FYP2, and what differs

- **Same:**
  - the 9 backbones and 3 tiers
  - the 224 px input from a 256 px source
  - preprocessing, augmentation, two-stage schedule, early stopping, seed
  - CE and CORN losses, metrics, overfitting rules
- **Different, forced by the data:**
  - IHC tiles are 1024 px and are downsampled once to 256 px. (The 448 px `hires` variant instead uses 1024 → Lanczos
    512 → bilinear 448.)
  - Labels are slide-level, taken from BCI file names.
  - BCI's official split leaks: 63% of test tiles are edge-connected to training tiles. The main split therefore re-applies FYP2's
    grouped 70/15/15 recipe, with *slide fragments* as groups instead of pHash twins.
  - Training images stream from disk (memory).
- **Different by choice, to avoid unnecessary runs:**
  - CORN is trained only for the best CE model per tier.
  - The improvement variants (`variants.py`) run on a few models, chosen from the diagnosis.

See `DATASET.md` for the data and `FYP3_FINAL_REPORT.md` for results. `results/REPORT.md`, `results/selection.json`,
`results/metrics_all.csv` and `results/overfitting.csv` predate experiments E1–E5 and are stale. Rebuilding on another machine:
`FYP3_REPRODUCTION_GUIDE.md`. Planned follow-up experiments (manual): `NEXT_EXPERIMENTS.md`. E6 and E7 were run on 10–11 Nov 2026 in
`experiments_v2/09_resolution_e6_e7/` (next-semester work; neither met its pre-registered rule; see `PROJECT_STATUS_AND_ROADMAP.md` §4).
Report corrections: `experiments_v2/REPORT_CORRECTIONS_v2.md` (current; supersedes the earlier `REPORT_CORRECTIONS.md`).
