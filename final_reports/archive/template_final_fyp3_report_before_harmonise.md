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

{{all_runs}}

![](figures/fig6_effects_forest.png)

{{paired}}

*`*`: CI excludes 0. A − B on the same tiles.*

- **Resolution:** confirmed for EfficientNetV2B0, not for MobileNetV3Small.
- **Batch size:** no effect on validation for either model.
- **GAN pretraining and mixed training:** no gain on BCI.
- **Tier winners** are not separable from their runners-up on validation; see `experiment_audit.md`.

## 3. Overfitting

On the 16 runs evaluated, train − test accuracy is 2.2–6.6 points against ≤ 0.7 on FYP2. Selection did not overfit validation: val is below test on every run.
Noise-aware verdict: 8 overfit, 7 mild, 1 none. **The 4 E1/E2/E4/E5 runs have no verdict yet.** The role of label noise is an interpretation.

## 4. External test

{{external}}

![](figures/fig3_stain_rule_vs_cnn.png)

- **No pipeline bug** (13 of 13 networks reproduced end to end).
- **Stain style explains the FYP2 vs BCI gap** (`cross_dataset_audit.md`).
- **Scale mismatch is about 4–5× and separate from that gap.**
- **Higher BCI performance does not transfer:** double resolution lowers external ranking.
- **Labels are ROI-level, the set is curated by a per-class colour filter, and it has 21 test slides.** It is not a representative clinical test.

## 5. Quantisation

{{deploy}}

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
