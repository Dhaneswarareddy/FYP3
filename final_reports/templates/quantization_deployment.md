# FYP3 quantisation and deployment status

Audit date: 30 Oct 2026. Source: `results/deploy/EfficientNetV2B0__ce__hires/`, produced by `src/deploy.py`.

## Status

| Item | Status |
|---|---|
| FP32, FP16 and INT8 TFLite conversion | **Done, for one model only**: EfficientNetV2B0, 448 px, the hires run |
| Accuracy on BCI val and test | Done, re-verified from stored confusion matrices |
| Latency | **Mac CPU only**, median of 50 single-image runs, default thread setting |
| **Raspberry Pi 4B benchmark** | **Not done.** No Pi latency, memory, thermal or power figure exists for any FYP3 model |
| FYP3 Pi bundle | **Does not exist.** `FYP2/pi/` is for FYP2's models |
| Kria KV260 | Not attempted |
| Quantised models on HER2-IHC-40x | Not evaluated |
| Other models and tiers | Not quantised |

## Results

{{deploy}}

![](figures/fig7_quantisation.png)

## Findings

- **FP32 matches Keras.** Its confusion matrices equal the Keras predictions on val and test. On 48 val tiles, probabilities differ by at most 2.3e-6.
- **FP16 is the safe choice.** Half the size, identical confusion matrices on val and test, about the same latency.
- **INT8 is flagged `degraded`.** It is 70% smaller, but agreement with FP32 is 0.928, below the 0.95 threshold.
  - Val accuracy falls 3.2 points and test 4.2 points. QWK falls 0.064 (val) and 0.051 (test).
  - The largest test recall loss is on 1+ (0.96 → 0.86).
  - FYP2 found the same weakness, where early layers encode subtle DAB intensity. Its mixed INT8 route was **not ported** to FYP3.
- **INT8 was slower on the Mac** (133 vs 71 ms). A likely cause is that the default interpreter path does not accelerate the
  integer graph as it does the float graph (interpretation, untested). Do not assume this ratio holds on ARM.
- **Inspection.** All three files use float32 input and output, shape 1 × 448 × 448 × 3. INT8 has one QUANTIZE and one DEQUANTIZE op, so it is a
  fully integer graph. The model has 71 LOGISTIC (sigmoid) ops from squeeze-excitation blocks, a plausible source of integer error (interpretation).
- **Calibration** uses 256 class-balanced training tiles only, so no val or test leakage.

## Provenance gap

`deploy.py` was edited at 17:57, after the outputs were written at 15:44, and no deploy log was kept. The stored metrics
were verified from the stored confusion matrices, but the files cannot be proven to come from the current script.

## Limitations

- 448 px input is 4× the pixels of 224 px. Pi feasibility is unknown and must not be inferred from Mac numbers.
- The deployed model is best on BCI but ranks external tiles worse than 224 px models. Its deployment value depends on the target domain.
- BCI-only accuracy says nothing about performance at a new site.

## Before any deployment claim

1. Build a FYP3 bundle and run the Pi benchmark (`FYP2/pi/benchmark_pi.py` is the template, with the input size and test set changed).
2. Port or test FYP2's mixed INT8 if integer inference is needed.
3. Report thermal state and throttling with every Pi latency, as FYP2's protocol does.
