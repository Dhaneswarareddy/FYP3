# Cross-dataset audit: why FYP2 beats FYP3 on HER2-IHC-40x

Audit date: 30 Oct 2026. Sources: `results/external/her2_40x/` and `final_reports/tables/`. The external labels were used
only for reporting and diagnosis. Paper facts come from the HER2-IHC-40x dataset article (Data in Brief 2025).

## The question

Networks trained on synthetic GAN images score better on real external tissue than networks trained on real BCI tissue.
That is the opposite of what one would expect.

{{external}}

*QWK CIs resample filename runs, a partial proxy for the 21 unavailable slide IDs, so they are still optimistic.*

## Answer

**The difference is stain calibration, not better learning.** HER2-IHC-40x stains look like the GAN's and unlike BCI's, and
its classes are close to a stain threshold. A stain-only rule with no CNN reproduces the whole gap and beats every CNN.
**Good external scores here do not show that GAN-trained networks generalise to real tissue.** They fail on BCI
(balanced accuracy 0.30–0.46), and HER2-IHC-40x is not a representative test of real-world generalisation.

## Explanations tested

| Explanation | Test | Verdict |
|---|---|---|
| Pipeline bug (labels, class order, preprocessing, checkpoints) | End-to-end reproduction of 13 networks; cache vs raw; label mapping | **Ruled out** |
| Different image scale | Blob and spectrum measures. FYP2's images and BCI's are both far from the external scale, and FYP2 networks still succeed | **Does not explain the gap**, though the mismatch is large |
| Class-prior shift (BCI has 5% score 0, external 36%) | Oracle diagnostic with the true external prior | **Minor** for most networks (table below) |
| BCI networks lack useful features | Threshold-free ranking | **Mostly ruled out.** 7 of 10 reach AUC ≥ 0.94 for 0/1+ vs 2+/3+. The exceptions are DenseNet121 and the two 448 px runs |
| **Stain calibration** | Same measurements on all three sets; stain-only rules | **Confirmed as the main driver** |

## Evidence

### 1. BCI networks rank tiles well but score them too high

![](figures/fig4_ranking_vs_calibration.png)

EfficientNetV2B0 (BCI) separates 3+ from the rest with AUC 0.98, yet its QWK is 0.11. Its mean predicted score is 2.71,
against a true 1.53. The confusion matrices show the same thing: most tiles of every class are called 3+.

![](figures/fig5_external_confusions.png)

### 2. External stain resembles the GAN, not BCI

![](figures/fig1_stain_by_class.png)

{{features}}

External 1+ tiles carry more DAB (0.16) than BCI 2+ tiles (0.12), and external counterstain is 3–7× stronger than BCI's.
A network calibrated on BCI reads such tiles as high-scoring.

### 3. A stain-only rule reproduces the gap

Each rule was fitted on training tiles of one dataset and applied unchanged to the external test tiles.

{{rules}}

![](figures/fig3_stain_rule_vs_cnn.png)

- A logistic rule on six stain numbers, fitted on FYP2, reaches **accuracy 0.89 and QWK 0.96**, better than every CNN in the project.
- The same rule fitted on BCI reaches balanced accuracy 0.45.
- The CNN gap (0.61–0.72 vs 0.26–0.38) is reproduced by rules that know nothing about morphology.

**Interpretation.** The dataset paper describes per-class filtering: patches were kept only if their hue histogram matched 20
reference images of their class. That selects for class-typical colour, which plausibly makes this set unusually easy by
colour. The filter is documented; its causal role is an interpretation.

### 4. Class prior is a small part

{{oracle}}

This uses the true test prior, so it is a diagnostic only and **not a reportable performance**.

### 5. The scale mismatch is large but separate

![](figures/fig2_same_view_examples.png)

- At the same 224 px view, external tiles hold a few cells, BCI and GAN tiles hundreds.
- At native 1024 px, on unlabelled development tiles: median blob diameter 43.5 px (IQR 19–51) vs 9.1 px for BCI, a ratio of about **4.8**.
- Spectral content agrees: at 224 px the 90th-percentile frequency is 15–21 cycles against 54–69 for BCI.
- A ratio of 4.8 would imply about 0.10 µm/px, finer than a 40× scan normally gives. The paper says patches were resized to
  1024 px, so upsampling is likely (interpretation). The field size is not documented. The blob measure may merge touching
  cells, so 4.8 is an upper-range estimate. The next experiment tests 2, 3 and 4.8.
- Earlier statements of about 1.8× were based on assumed magnifications and are withdrawn.

## Dataset facts

| | HER2-IHC-40x, WSI-based split |
|---|---|
| Source | One centre (University of Malaya), scanner 3DHistech Pannoramic DESK, 40×; µm/px not reported |
| Slides | 107 WSIs: **86 train, 21 test**, split before patch extraction |
| Tiles | Train 8,093 (3,131 / 1,837 / 523 / 2,602); test 1,847 (658 / 316 / 111 / 762). Counts verified from the archives |
| Labels | **ROI-level**, propagated to patches. Scoring standard and number of raters not stated |
| Curation | Pathologist ROIs, per-class hue-histogram filter, intensity histogram normalisation, patches resized to 1024 px |
| Slide IDs | None. Filename runs are a partial proxy |
| Label oddities | Folder and filename score differ on 10 test and 2 train tiles |
| Patch-based split | Not independent: 1,594 of its test names are in the WSI-based training set. **Do not use it** |

## Limitations

- 21 test slides at most, with no IDs, so all CIs are optimistic.
- 2+ has only 111 tiles, possibly from few slides.
- The Ruifrok–Johnston stain vectors are generic, so stain channels are only approximately separated.
- Each network is one seed. External QWK varies widely across the five EfficientNetV2B0 runs (0.06–0.58).
- The stain comparison uses BCI's grouped test split, whose 3+ tiles stain unusually strongly (median 0.49; 0.25 across train).
  The gap to the external set is therefore, if anything, understated.
