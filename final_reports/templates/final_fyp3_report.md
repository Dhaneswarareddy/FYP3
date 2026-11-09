# FYP3 final technical report

Updated 30 Oct 2026. Covers E1–E5, the external test, HARMONISE-1, HARMONISE-2, quantisation and model selection. The earlier version is kept in
`archive/final_fyp3_report_before_harmonise.md`, and `results/REPORT.md` is preserved for its detailed evidence. Findings are marked **confirmed** (measured) or **interpretation**.

## Required disclosures

1. **No clinical validation.** Nothing here has been tested in a clinical setting or against an independent reference standard. The models are research software.
2. **Genuine WSI identifiers are unavailable.** Neither BCI nor HER2-IHC-40x provides slide or patient IDs for tiles. No per-slide or per-patient result exists. Slide fragments (BCI) and index blocks (HER2-IHC-40x) are reconstructions, not verified slides.
3. **The external test set has been exposed.** Its labels were used for diagnostics, including the stain analysis that motivated HARMONISE-1, before calibration was fitted. It was then evaluated once for HARMONISE-1. It is not a pristine test set, and its CIs are optimistic.
4. **Borderline HER2 performance remains weak.** Across domains, 1+ and 2+ are poorly detected (section 6). On BCI, high 2+ scores reflect slide-level labels (section 8).
5. **No Raspberry Pi benchmark exists.** All latency figures are Mac CPU. A benchmark protocol and scripts are prepared, not run on a Pi.

## Summary

1. **BCI.** The FYP2 pipeline drops from about 100% test accuracy on GAN images to 91–95% on BCI at 224 px. EfficientNetV2B0 at 448 px reaches 0.975 test accuracy and val QWK 0.935, the best BCI result.
2. **What worked.** Higher resolution, as a confirmed resolution effect on EfficientNetV2B0 only. Class weights, label smoothing, CORN, GAN pretraining and mixed training gave no gain.
3. **External generalisation failed without calibration.** On HER2-IHC-40x, BCI-trained models reach 0.42–0.59 accuracy. The primary model reaches 0.435.
4. **HARMONISE-1.** One fixed stain calibration raised balanced accuracy of the 224 px EfficientNetV2B0 by +0.202, to 0.503. It failed for the 448 px model.
5. **HARMONISE-2.** The gains are stable to tile sampling, but borderline classes remain weak and confidence cannot safely flag them. Slide-level analysis was not possible.
6. **Selection.** Primary: EfficientNetV2B0 448 px FP16, for BCI-like tiles. Experimental only: EfficientNetV2B0 224 px with frozen stain calibration, for HER2-IHC-40x. They are kept separate.

## 1. Data and method

| | FYP2 | BCI (FYP3) | HER2-IHC-40x |
|---|---|---|---|
| Nature | CGAN images, HER2SC-derived | Real IHC | Real IHC |
| Native size | 256 px | 1024 px, 0.46 µm/px | 1024 px; µm/px unknown |
| Volume | 2,400 | 4,873 tiles, 51 WSI pairs (BCI paper) | 9,940 tiles, 107 WSIs |
| Labels | Generator class | Slide-level | ROI-level, propagated to patches |
| Split | 70/15/15 by twin group | 70/15/15 by reconstructed slide fragment | 86 development / 21 test WSIs, by the publishers |

All models used FYP2's schedule: two-stage training, frozen BatchNorm, seed 42, early stopping on val QWK. Decisions used validation. Paired CIs resample slide fragments on BCI.

## 2. Results on BCI, including E1, E2, E4, E5

{{all_runs}}

![](figures/fig6_effects_forest.png)

{{paired}}

*`*`: CI excludes 0. A − B on the same tiles.*

- **E1 (EfficientNetV2B0):** the resolution effect is confirmed on val and test. Batch size has no effect.
- **E2 (MobileNetV3Small):** resolution is not confirmed (val CI includes 0, test near zero).
- **E4 and E5:** GAN pretraining and mixed training gave no gain.
- **Heavy models** were never tested at 448 px.

## 3. Overfitting

On the 16 runs evaluated, train − test accuracy is 2.2–6.6 points against ≤ 0.7 on FYP2. Selection did not overfit validation: val is below test on every run. Noise-aware verdict: 8 overfit, 7 mild, 1 none. The primary model is "mild" (gap 2.4 points, log-loss gap 0.088). **The four E1, E2, E4 and E5 runs have no verdict.** The role of label noise is an interpretation.

## 4. External test without calibration (E3)

{{external}}

![](figures/fig3_stain_rule_vs_cnn.png)

- **No pipeline bug:** 13 of 13 networks reproduced end to end.
- **Stain style explains why GAN-trained networks beat BCI-trained ones.** A stain-only rule fitted on FYP2 reaches accuracy 0.89 and QWK 0.96, better than any CNN. This is not evidence that GAN training generalises: the same networks fail on BCI. See `cross_dataset_audit.md`.
- **BCI networks mostly rank tiles well but score them too high.**

## 5. HARMONISE-1: frozen stain calibration

One haematoxylin gain and one DAB gain for the whole external domain, fitted on unlabelled development tiles against BCI training tiles. `stain_p99` was selected on 2,000 labelled development tiles and evaluated once on test: g_h 0.2545, g_d 0.5045.

- **Endpoint met:** Δ balanced accuracy +0.202 for EfficientNetV2B0 224 px (CI [+0.147, +0.258]), from 0.301 to 0.503. The CI resamples filename runs, not slides, and is optimistic.
- **Scale correction alone did not help.**
- **The 448 px model collapsed** (balanced accuracy 0.290 → 0.186).

## 6. HARMONISE-2: reliability

All on 4,593 development tiles unused by HARMONISE-1, from the same 86 slides. The test split was not read. Every stored result was independently recomputed from saved probabilities and reproduces exactly.

{{h1h2}}

### A. Calibration stability: stable to tile sampling

- At n = 1,500: CV 0.042 (g_d) and 0.030 (g_h). The smallest sample meeting the pre-set limit of 0.10 is 1,000 tiles.
- Across 8 parameter sets, balanced accuracy varies by 0.005 (EfficientNetV2B0) and 0.018 (MobileNetV3Small).
- **p99 is not a fragile edge:** balanced accuracy is flat from p97 to p99.5 (0.494–0.506). But 3+ recall changes from 0.73 to 0.97 across that range, so the flat summary hides a trade-off.
- **Class mix matters:**

{{composition}}

A site with few 3+ tiles gets a higher gain and loses about 0.09 balanced accuracy, with no change in staining.

**Limit:** this measures tile sampling within one centre, not site-to-site stability.

### B. WSI-level generalisation: not possible

No slide identifiers exist, so no per-slide result can be produced. The only genuine slide boundary is 86 development vs 21 test WSIs: primary-model balanced accuracy is 0.51 on development selection tiles and 0.50 on test.

An exploratory 5-fold check on filename index blocks gave balanced accuracy 0.44–0.58, and 2+ recall 0.19–0.79. Index blocks are **not** slides. This spread is far wider than the 0.005 from tile resampling, which suggests (interpretation) that heterogeneity between tissue regions is much larger than the stability figures imply.

### C. Class-wise reliability: borderline classes are weak

- **QWK hides class failure.** DenseNet121 has QWK 0.76 with 1+ recall 0.01 and 2+ recall 0.04. MobileNetV3Small has 0.80 with 2+ recall 0.09.
- **Only EfficientNetV2B0 finds 2+** (recall 0.57 test, 0.67 dev), with precision 0.09–0.11. About 9 in 10 tiles it calls 2+ are not 2+.
- **1+ recall is at most 0.35 on any model** on test, and 0.16–0.18 for EfficientNetV2B0.
- **Calibration can harm a class:** DenseNet121's 3+ recall fell from 1.00 to 0.78 on development tiles.

### D. Why the 448 px model fails

{{dose}}

- **Haematoxylin gain is the cause (confirmed on development tiles).** DAB gain alone leaves 3+ recall at 0.85. Haematoxylin gain alone cuts it to 0.27.
- **Not a resolution-of-fit problem:** gains fitted at 256 and 448 px are nearly identical (g_d 0.485 vs 0.492), and refitted gains do not help.
- **Not simply greater stain sensitivity:** on BCI validation tiles both networks collapse under these gains, and the 448 px one is less sensitive to DAB alone.
- **Scale compensation helps partly:** balanced accuracy rises to 0.322, but 3+ recall falls to 0.70, which fails the pre-set rule.
- **On the 224 px network the two gains work only together:** balanced accuracy is 0.32 with DAB alone, 0.33 with haematoxylin alone, 0.50 with both.
- **The gains are not safe on BCI itself:** balanced accuracy falls from 0.875 to 0.407.

Why the 448 px network depends on the external counterstain in this way was not tested.

### E. Confidence: better calibrated, not usable for review

- ECE falls from 0.56 to 0.26 with calibration, and to 0.10 with temperature scaling (T = 2.84, EfficientNetV2B0). Temperatures differ widely between networks (2.1–5.3) and need target labels to fit.
- Reference ECE on BCI validation is 0.03–0.06.
- **No configuration met the rule for review flagging.** Keeping confident tiles raises accuracy, but it removes the very cases that matter: at 50% target coverage, 76% of true 2+ tiles (EfficientNetV2B0) and 94% (MobileNetV3Small) are referred.
- Tiles whose class flips between calibration samples are wrong more often (0.69 vs 0.49).

## 7. Quantisation

{{deploy}}

FP16 gives confusion matrices identical to FP32. INT8 falls below the agreement threshold (0.928 vs 0.95) and is rejected. Latency is Mac CPU only. See `quantization_deployment.md`.

**FP16 re-validated through the deployment code (Mac):**
- Primary: 100% class agreement with Keras on all 1,485 BCI validation and test tiles; largest probability change 0.020; accuracy reproduced (0.950, 0.975).
- Experimental (a new FP16 export): 99.6% agreement on 2,402 development tiles; largest probability change 0.014. The disagreements examined were near-ties.

## 8. Model selection

**Primary, for BCI-like tiles:** EfficientNetV2B0 448 px FP16. **Experimental, for HER2-IHC-40x only:** EfficientNetV2B0 224 px with frozen `stain_p99`. Full reasoning is in `FINAL_MODEL_SELECTION.md`.

{{primary_bci_classes}}

These figures use slide-level labels. Against third-party patch labels:

{{primary_refined}}

Slide-labelled 2+ tiles agree with the patch labels only about 70–74% of the time, and the model follows the slide label. **Its 2+ performance does not show reliable tile-level reading of borderline staining.**

## 9. Corrections to earlier reports

| Earlier statement | Correction |
|---|---|
| HARMONISE-1 report: "21 slide clusters" | CIs resample filename runs. No slide clusters exist |
| HARMONISE-1 report: resolution "regularizer", gains "do not translate" to 512 px | Unsupported. Gains are nearly identical across resolutions |
| HARMONISE-2 report: DAB suppression dims membranes and causes the 448 px failure | **Contradicted by its own data.** DAB alone leaves 3+ recall unchanged; haematoxylin gain causes the collapse |
| HARMONISE-2 report: target CV ≤ 0.05 met at n = 1,000 | The pre-set limit was 0.10. At n = 1,000 g_d CV is 0.055 |
| HARMONISE-2 report: "external" 2+ recall 0.668 | That is a development figure. Test is 0.568 |
| HARMONISE-2 report: "clinical workflow", "external screening workflow" | No clinical use is supported |
| HARMONISE-2 report: `results/deployment/...` and `outputs/verify.json` | These files do not exist. Use `results/deploy/...`; `verify` printed its result only |
| HARMONISE-2 report: ECE halved on all 224 px models, T 2.0–2.8 | MobileNetV3Large is just under half; T ranges 2.1–5.3 |
| Earlier statement in this report: the 448 px model is confirmed on two models | Confirmed on one |
| Earlier statement: patches "resized" to 1024 px | The paper's table says so; the authors' repository says "adaptive" extraction. Treat the scale as unknown |

## 10. Limitations

- **Single centre for each external and internal dataset,** one seed per configuration, and no multi-site test.
- **The external set is curated** by a per-class colour filter, with ROI-level labels and only 111 test tiles at 2+.
- **BCI's grouped test split** has unusually strong 3+ staining, which likely inflates test relative to val.
- **Residual leakage is possible** on BCI, because fragments only partly recover slide structure.
- **Stain vectors are generic,** so H and DAB are only approximately separated.
- **Calibration depends on class mix** and needs about 1,000 unlabelled target tiles.
- **Only 2 of 9 architectures were tested at 448 px.**
- **Third-party patch labels** have no documented protocol.

## 11. Conclusions

1. A pipeline that looks perfect on GAN data loses 5–9 points on real tissue and fails at another centre without calibration.
2. Higher resolution gave the best BCI model but did not improve generalisation.
3. A simple stain calibration can correct much of a systematic score shift, without retraining. It does not fix borderline scores.
4. Overall metrics, QWK especially, can hide complete failure on the categories that matter most. Class-wise reporting is essential.
5. These models are suitable for research and edge-inference study, not for clinical use.

## 12. Deployment status

Reusable inference, both modes and the Pi benchmark are prepared in `deployment/`. See `DEPLOYMENT_README.md`. **Pi figures do not exist until the benchmark is run on a physical Pi 4B.**
