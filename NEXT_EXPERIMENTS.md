# FYP3: next experiments (manual execution)

Written 30 Oct 2026. Nothing below has been run. The final report (`results/REPORT.md`, 30 Oct) stays as it is;
proposed wording changes are in `REPORT_CORRECTIONS.md`.

## 0. Audit answers (short)

| Question | Verified | Interpretation | Unknown |
|---|---|---|---|
| **Origin of the "patch-level" labels** | `BCI_metadata_pairs_refined.csv` is byte-identical (md5 `fc71ac99…`) to Zenodo record 10.5281/zenodo.17200604 (Macias Garcia & Garcia-Gutierrez, Univ. Seville, 2025). Column `her2_level_refined`; 3,513 of 4,873 pairs. It is not part of the BCI release (`FYP/docs/data_provenance.md`). | Third-party relabelling. Treat it as a second opinion, not ground truth. | Who labelled, how, and whether pathologists or a model were involved. The record does not document a protocol. |
| **Architectures run at double resolution** | Only **MobileNetV3Small** and **EfficientNetV2B0**. Config `hires`: 1024 → Lanczos 512 px source, random crop 70–100%, resized to 448; eval 512 → bilinear 448; batch 32 → 8; all else identical. Results (Δ vs 224 px, paired, val QWK): MNV3S +0.102 [+0.031, +0.173], test −0.014; EffV2B0 +0.065 [+0.026, +0.108], test acc 0.926 → 0.975. | The gain is real for "512 px + batch/4", but resolution and batch size changed together. One seed per arm. | Effect at 1024 px; effect on heavy models; seed-to-seed variance. |
| **Why 1024 → 256** | `config.py`: so the networks see FYP2's geometry (GAN images are natively 256 px), i.e. a like-for-like reproduction. BCI: 0.46 µm/px (BCI paper), so 256 px = 1.84 µm/px, 512 = 0.92, 1024 = 0.46. | 256 was right for "same pipeline", wrong for "best BCI model". 512 is worth a controlled test (E1–E3). 1024 only if 512 holds up after the batch control (E7). | Whether the GAN images have any physical scale. |
| **HER2-IHC-40x for external testing** | Local zips (not extracted): 1024×1024 PNG, 4 classes. WSI-based test split: 1,847 tiles (0 / 1+ / 2+ / 3+ = 658 / 316 / 111 / 762). 10 files have a folder class that differs from the filename score. Patch-based test split: 2,197 tiles, of which 1,748 are named `…score_train…` (from the WSI-based training pool) and 168 have folder ≠ filename score. Dataset record: 107 WSIs at 40×, Univ. Malaya, ROIs by expert pathologists; Zenodo 10.5281/zenodo.15179607; Data in Brief 2025, doi 10.1016/j.dib.2025.111922. | **Suitable as an external test set if only the WSI-based TEST split is used, report-only.** The patch-based split is not slide-independent. A different scanner and centre make it a real domain shift. | µm/px of the 40× scans (likely about 0.25; check the paper); whether labels are slide-level or ROI-level; train-split contents (not inspected); slide IDs (none in file names, so CIs are tile-level and optimistic). Only 111 tiles are 2+. |
| **Three most promising synthetic → real routes** | FYP2 networks do not transfer to BCI (balanced acc 0.30–0.46). The GAN exaggerates DAB 5–10× between 1+ and 2+/3+. Frozen-feature separability differs (0.98 vs 0.77). | 1) Mixed training or GAN pre-training with real fine-tuning (E5, E6). 2) DAB-calibrated stain augmentation or normalisation of the synthetic images, matching real per-class DAB distributions (targets the confirmed DAB gap). 3) Unsupervised target adaptation with unlabelled real tiles, e.g. re-estimating BatchNorm statistics on BCI (AdaBN): inference-only, cheap. | Which of these helps. All three are untested hypotheses. Routes 2 and 3 are not implemented. |

## 1. Before anything: protect existing results (2 min)

```bash
cd ~/Downloads/FYP3
tar czf ../FYP3_results_final_2026-10-30.tar.gz results splits      # ~1 GB snapshot
```

Rules:
- New runs go to new folders (`results/runs/<model>__ce__<variant>/`), and existing runs are never overwritten
  (the runner skips finished runs).
- **Do not run `select_models.py` or `report.py`** until you decide to publish a new report. They rewrite
  `selection.json` and `REPORT.md`. Decisions below need only `paired.py`, which reads saved predictions.
- BCI test and the HER2-IHC-40x tiles are report-only. Every decision uses BCI validation.

Set up once per shell (macOS):

```bash
cd ~/Downloads/FYP3/src
PY=/Users/dhaneswarareddy/Downloads/Final_Year_Project/Codes/Project/bin/python
```

Code support for these experiments was added on 30 Oct and syntax-checked, but **not executed**:
- `variants.py` gains `lowbatch`, `hires1024`, `init_fyp2` and `mix_fyp2`;
- `train_variant.py` implements them;
- new `external_eval.py`;
- `evaluate_all.py` now forces the CPU only on macOS.

**Run the smoke test of each new variant first.** A smoke test is 1+1 epochs, writes to `results/smoke/`, and takes about 2–5 min.

## 2. Plan, in priority order

| # | Experiment | New runs | Reference (exists) | Approx. time on the M1 | Question |
|---|---|---|---|---|---|
| **E1** | EfficientNetV2B0, 224 px at batch 8 | `EfficientNetV2B0__ce__lowbatch` | `__ce` (224/b32), `__ce__hires` (448/b8) | 1–1.5 h | Is the hires gain resolution or batch size? |
| E2 | MobileNetV3Small, 224 px at batch 8 | `MobileNetV3Small__ce__lowbatch` | `__ce`, `__ce__hires` | 0.5 h | Same, lite tier |
| E3 | External test on HER2-IHC-40x (inference only) | none | existing BCI and FYP2 runs | 0.5–1 h total | Do BCI-trained models generalise to another centre? Does hires help there? |
| E4 | GAN pre-training → BCI fine-tuning | `EfficientNetV2B0__ce__init_fyp2` | `EfficientNetV2B0__ce` | 1 h | Does synthetic pre-training help real training? |
| E5 | Mixed GAN + BCI training | `EfficientNetV2B0__ce__mix_fyp2` | `EfficientNetV2B0__ce` | 1–1.5 h | Does adding synthetic images help? |
| E6 | Heavy tier: DenseNet121 at 448/b4 and 224/b4 | `DenseNet121__ce__hires`, `DenseNet121__ce__lowbatch` | `DenseNet121__ce` | ~10–12 h + ~3–4 h (a CUDA GPU is far faster) | Only if E1 shows a resolution effect |
| E7 | Native resolution, lite only: 1024 → 896, batch 2 | `MobileNetV3Small__ce__hires1024` | `__ce__lowbatch`, `__ce__hires` | 3–5 h, ~7 GB extra disk | Only if E1/E2 show a resolution effect |

**Pre-registered decision rules** (also in `variants.py`): an effect counts only if the paired 95% fragment-cluster
CI of Δ val QWK excludes 0.

| Effect | Comparison |
|---|---|
| Resolution | `hires` − `lowbatch` |
| Batch size | `lowbatch` − baseline |
| GAN pre-training | `init_fyp2` − baseline |
| Mixed training | `mix_fyp2` − baseline |

E6 and E7 run only if E1 shows a resolution effect.

## 3. Exact commands

### E1 (run this first)

```bash
$PY train_variant.py --model EfficientNetV2B0 --loss ce --variant lowbatch --smoke 2>&1 | grep -E "^===|^DONE|Error"
#   expect: "=== EfficientNetV2B0__ce__lowbatch ... batch=8  input=224 ..." and a DONE line
./run_variants.sh EfficientNetV2B0:ce:lowbatch
#   output: results/runs/EfficientNetV2B0__ce__lowbatch/{summary.json,predictions.npz,history.csv,model.*}
#   log:    results/logs/train_EfficientNetV2B0__ce__lowbatch.log
$PY paired.py EfficientNetV2B0__ce__hires EfficientNetV2B0__ce__lowbatch --split val   # resolution effect
$PY paired.py EfficientNetV2B0__ce__lowbatch EfficientNetV2B0__ce --split val          # batch effect
```

Checks:
- `summary.json` shows `"batch": 8`, `"image_size": 224`.
- `best_epoch` < `epochs_run`.
- The DONE line's val QWK is plausible (0.75–0.95).

Read the `qwk` line of each paired.py output: an effect is real only if its CI excludes 0.

### E2

```bash
$PY train_variant.py --model MobileNetV3Small --loss ce --variant lowbatch --smoke 2>&1 | grep -E "^===|^DONE|Error"
./run_variants.sh MobileNetV3Small:ce:lowbatch
$PY paired.py MobileNetV3Small__ce__hires MobileNetV3Small__ce__lowbatch --split val
$PY paired.py MobileNetV3Small__ce__lowbatch MobileNetV3Small__ce --split val
```

### E3: external test (HER2-IHC-40x, WSI-based TEST split only)

Extract only the test split (about 280 MB), next to the BCI data, and make it read-only:

```bash
mkdir -p ~/Downloads/FYP/data/raw/HER2-IHC-40x && cd ~/Downloads/FYP/data/raw/HER2-IHC-40x
unzip -q ~/Downloads/her2-ihc-40x-wsi.zip "WSI-based-dataset/test_data_wsi.zip"
unzip -q WSI-based-dataset/test_data_wsi.zip -d wsi_test && rm -r WSI-based-dataset
chmod -R a-w wsi_test
ls wsi_test; find wsi_test -name "*.png" | wc -l        # class_0 class_1+ class_2+ class_3+ ; 1847
```

Evaluate one network per process (this avoids the Mac's memory build-up). The 448 px runs need `--cpu` on macOS:

```bash
cd ~/Downloads/FYP3/src; D=../../FYP/data/raw/HER2-IHC-40x/wsi_test
for r in DenseNet121__ce EfficientNetV2B0__ce MobileNetV3Large__corn MobileNetV3Small__ce; do
  $PY external_eval.py --data-dir $D --runs $r; done
for r in EfficientNetV2B0__ce__hires MobileNetV3Small__ce__hires; do
  $PY external_eval.py --data-dir $D --runs $r --cpu; done
for r in ResNet50__ce EfficientNetV2B0__ce MobileNetV2__ce; do            # FYP2 (GAN-trained) networks
  $PY external_eval.py --data-dir $D --fyp2-runs $r; done
```

Outputs, in `results/external/her2_40x/`:
- `<BCI|FYP2>__<run>.json`: all metrics, tile-bootstrap CIs, and a subset where the folder and filename labels agree;
- `.csv`: per-tile predictions;
- `summary.csv`.

Caches are written to `FYP3/data/her2_40x_*`.

Checks:
- The first printed line says `1847 tiles, per class [658, 316, 111, 762], folder/filename label mismatches 10`.
- Predicted shares are not all one class.

Paired hires-vs-224 difference on the same tiles:

```bash
$PY - <<'EOF'
import pandas as pd, numpy as np
d = "../results/external/her2_40x/"
a = pd.read_csv(d + "BCI__EfficientNetV2B0__ce__hires.csv"); b = pd.read_csv(d + "BCI__EfficientNetV2B0__ce.csv")
assert (a.path == b.path).all()
ok = (a.pred == a.label).values.astype(float) - (b.pred == b.label).values
r = np.random.default_rng(42); bs = [ok[r.integers(0, len(ok), len(ok))].mean() for _ in range(2000)]
print(f"delta acc {ok.mean():+.3f} [{np.percentile(bs, 2.5):+.3f}, {np.percentile(bs, 97.5):+.3f}] (tile bootstrap)")
EOF
```

Interpretation limits:
- The scale differs: the 40× tiles cover a smaller field than BCI's 0.46 µm/px tiles.
- There are no slide IDs, so the CIs are optimistic.
- 2+ has only 111 tiles.
- Nothing is selected on these images.

### E4 and E5: synthetic → real

```bash
$PY train_variant.py --model EfficientNetV2B0 --loss ce --variant init_fyp2 --smoke 2>&1 | grep -E "^===|^DONE|Error"
$PY train_variant.py --model EfficientNetV2B0 --loss ce --variant mix_fyp2  --smoke 2>&1 | grep -E "^===|^DONE|Error"
./run_variants.sh EfficientNetV2B0:ce:init_fyp2 EfficientNetV2B0:ce:mix_fyp2
$PY paired.py EfficientNetV2B0__ce__init_fyp2 EfficientNetV2B0__ce --split val
$PY paired.py EfficientNetV2B0__ce__mix_fyp2  EfficientNetV2B0__ce --split val
```

Inputs, read-only:
- `FYP2/results/runs/EfficientNetV2B0__ce/model.*` for `init_fyp2`;
- FYP2's train split only (1,680 JPEGs) for `mix_fyp2`. FYP2's val and test are never touched.

Checks:
- `mix_fyp2` must show 5,068 training images: steps per epoch = 5068 // 32 = 158, against 105 for the baseline. Inspect `history.csv` length or the log.
- The `init_fyp2` smoke run's first head epoch should differ clearly from the baseline log's first epoch.

Optionally run each new run through E3 as well.

### E6 (only if E1 shows a resolution effect)

```bash
./run_variants.sh DenseNet121:ce:lowbatch DenseNet121:ce:hires
$PY paired.py DenseNet121__ce__hires DenseNet121__ce__lowbatch --split val
```

### E7 (optional, only if E1 or E2 shows a resolution effect)

```bash
./run_variants.sh MobileNetV3Small:ce:hires1024        # first run builds data/ihc_1024 (~7 GB)
$PY paired.py MobileNetV3Small__ce__hires1024 MobileNetV3Small__ce__hires --split val
```

### After the experiments (optional)

```bash
$PY evaluate_all.py        # adds metrics/overfitting rows for the new runs only (finished runs are skipped)
# only when publishing an updated report (the snapshot from step 1 keeps the 30 Oct version):
cp ../results/REPORT.md ../results/REPORT_final_2026-10-30.md
$PY select_models.py && $PY report.py
```

## 4. Known risks

- **macOS GPU-driver faults** (tensorflow-metal):
  - ConvNeXtTiny's Grad-CAM deadlocks;
  - 448 px inference hangs (`evaluate_all.py` and `external_eval.py --cpu` avoid it);
  - occasional segfaults.

  If a log stops growing for 30 min, run `sample <pid> 3`. A sleeping main thread with an idle GPU means a deadlock: kill the process and rerun, because runners skip finished runs.
- **One seed per arm.** A borderline result (CI touching 0) needs a second seed before it is reported. Seeds are fixed in `config.SEED`. A seed option is not implemented.
- **The new variants are untested.** If a smoke test fails, fix it before launching the full run.
