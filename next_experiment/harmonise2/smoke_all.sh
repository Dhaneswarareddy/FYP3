#!/bin/bash
# Every HARMONISE-2 stage on a few tiles, into outputs_smoke/. No external test tile is read and nothing is trained.
cd "$(dirname "$0")"; PY=${PY:-/Users/dhaneswarareddy/Downloads/Final_Year_Project/Codes/Project/bin/python}; set -e
rm -rf outputs_smoke
R="$PY run_h2.py --smoke --stage"
$R preflight; $R regress; $R cache; $R a_params
for r in EfficientNetV2B0__ce MobileNetV3Small__ce; do $R a_eval --run $r; done
$R a_report; $R b_audit; $R b_surrogate
for r in EfficientNetV2B0__ce MobileNetV3Small__ce MobileNetV3Large__corn DenseNet121__ce EfficientNetV2B0__ce__hires; do $R c_predict --run $r; done
$R c_report; $R d_params
for r in EfficientNetV2B0__ce EfficientNetV2B0__ce__hires; do $R d_predict --run $r; $R d_bci --run $r; done
$R d_report; $R e_report; $R report; $R verify
echo SMOKE_OK
