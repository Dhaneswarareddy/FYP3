"""Audit 2 (no TensorFlow): paired fragment-cluster bootstrap effects for E1, E2, E4, E5, recomputed with paired.py."""
import sys; from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT/"src"))
import pandas as pd, paired as P
C = [("E1 resolution","EfficientNetV2B0__ce__hires","EfficientNetV2B0__ce__lowbatch"),("E1 batch","EfficientNetV2B0__ce__lowbatch","EfficientNetV2B0__ce"),
     ("E1 combined","EfficientNetV2B0__ce__hires","EfficientNetV2B0__ce"),
     ("E2 resolution","MobileNetV3Small__ce__hires","MobileNetV3Small__ce__lowbatch"),("E2 batch","MobileNetV3Small__ce__lowbatch","MobileNetV3Small__ce"),
     ("E2 combined","MobileNetV3Small__ce__hires","MobileNetV3Small__ce"),
     ("E4 init_fyp2","EfficientNetV2B0__ce__init_fyp2","EfficientNetV2B0__ce"),("E5 mix_fyp2","EfficientNetV2B0__ce__mix_fyp2","EfficientNetV2B0__ce")]
rows = []
for lab, a, b in C:
    for sp in ["val", "test"]:
        d = P.compare(a, b, sp, ("accuracy","qwk","macro_f1","recall_0"))
        for k, v in d.items():
            rows.append(dict(effect=lab, run_a=a, run_b=b, split=sp, metric=k, delta=v["diff"], ci_lo=v["ci_lo"], ci_hi=v["ci_hi"], excludes_0=bool(v["ci_lo"]>0 or v["ci_hi"]<0)))
        print(lab, sp, {k: P.cell(v, 3) for k, v in d.items()}, flush=True)
pd.DataFrame(rows).to_csv(ROOT/"final_reports/tables/paired_effects.csv", index=False)
