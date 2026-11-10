# Proposed corrections to `results/REPORT.md` (30 Oct 2026 version)

> **Superseded (note added 10 Nov 2026)** by `experiments_v2/REPORT_CORRECTIONS_v2.md`, which re-checks every claim against the stored artifacts, and by the revised `FYP3_FINAL_REPORT.md`.


The report is unchanged. These are proposals from the 30 Oct audit. To apply them, edit `results/findings.md` (§0)
and the limitation strings in `src/report.py`, then regenerate (see `NEXT_EXPERIMENTS.md`, "After the experiments").

| # | Where | Current wording | Proposed | Reason |
|---|---|---|---|---|
| 1 | §0 finding 3; §6b; §8 "Labels are slide-level" | "patch-level reference labels"; "undocumented origin" | "third-party patch-level labels (`BCI_metadata_pairs_refined.csv`, Zenodo 10.5281/zenodo.17200604, Macias Garcia & Garcia-Gutierrez, Univ. Seville, 2025; labelling protocol undocumented)" | The **origin is documented** (byte-identical to the Zenodo record, `FYP/docs/data_provenance.md`). Only the **method** is undocumented. "Reference" suggests ground truth. |
| 2 | §0 finding 4 heading | "Confirmed: the FYP2 pipeline throws away resolution that BCI needs" | "Confirmed: the 512 px configuration (with a quarter of the batch size) beats the 224 px baseline on two architectures. Whether resolution or batch size causes it is not yet tested (planned experiment E1)." | Resolution and batch size changed together. The heading overstates the cause; the caveat appears only further down. |
| 3 | §0 finding 9 | "Confirmed: higher input resolution helps." | "Confirmed: the hires configuration helps (resolution and batch size confounded; one seed per arm)." | Same as #2, plus training-seed variance is outside the bootstrap CI. |
| 4 | §0 finding 13 | "With 16–18% of tiles carrying a slide label their own appearance contradicts, a network that fits its training tiles well cannot transfer that fit." (inside a "Confirmed" item) | Move this to a separate "**Interpretation:**" line | The overfitting gap is measured; its cause is not tested. |
| 5 | §0 finding 3, second bullet | "On tiles where the two agree, the CE baselines reach 0.94–0.98 … 0.97–1.00" | Add "(computed on the 67% of val and 77% of test tiles that have a refined label)" | 489 of 727 val tiles and 584 of 758 test tiles have a refined label. |
| 6 | §8 Limitations (new bullet) | none | "**Few slides.** The BCI paper reports 51 WSI pairs (0.46 µm/px, Hamamatsu NanoZoomer S60). Val and test therefore contain few independent slides, which is consistent with the 2.4–7.3-point val/test gap." | A source fact that explains the imprecision; it is not stated anywhere in the report. |
| 7 | §8 "Unknown relative magnification" | "compared at the same pixel size (256 px)" | Add "BCI: 1024 px = 0.46 µm/px, so the 256 px cache is 1.84 µm/px and the 512 px cache 0.92 µm/px." | Puts the resolution findings in physical units. |
| 8 | §0 finding 13 | "8 of 16 runs 'overfit', 7 'mild', 1 'none'" | Unchanged, but add that FYP2's thresholds (0.02 accuracy gap) were set for a 360-image test set without label noise | Gives the reader the context needed to apply the rule fairly. |
