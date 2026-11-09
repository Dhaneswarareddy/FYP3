# FYP3: the FYP2 pipeline on real HER2 IHC (BCI dataset)

This is a separate experiment. **FYP2 is the main project and is not modified.** FYP3 reads FYP2's split, images,
weights and results, and writes only inside `FYP3/`. The BCI raw data (`FYP/data/raw/BCI_dataset`) is read only.

**Scope:** training, evaluation, comparison with FYP2, feature analysis and performance diagnosis. No quantisation or deployment.

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
  - IHC tiles are 1024 px and are downsampled once to 256 px.
  - Labels are slide-level, taken from BCI file names.
  - BCI's official split leaks: 63% of test tiles are edge-connected to training tiles. The main split therefore re-applies FYP2's
    grouped 70/15/15 recipe, with *slide fragments* as groups instead of pHash twins.
  - Training images stream from disk (memory).
- **Different by choice, to avoid unnecessary runs:**
  - CORN is trained only for the best CE model per tier.
  - The improvement variants (`variants.py`) run on a few models, chosen from the diagnosis.

See `DATASET.md` for the data and `results/REPORT.md` for results. Rebuilding on another machine: `FYP3_REPRODUCTION_GUIDE.md`.
Planned follow-up experiments (manual): `NEXT_EXPERIMENTS.md`; proposed report wording fixes: `REPORT_CORRECTIONS.md`.
