#!/bin/bash
# Train a list of "model:loss" runs sequentially (one process each; skips finished runs).
#   ./run_queue.sh MobileNetV3Small:ce MobileNetV2:ce ...
cd "$(dirname "$0")"
PY=/Users/dhaneswarareddy/Downloads/Final_Year_Project/Codes/Project/bin/python
for spec in "$@"; do
  m=${spec%%:*}; rest=${spec#*:}; l=${rest%%:*}; extra=""
  [ "$rest" != "$l" ] && extra=${rest#*:}            # optional third field: --variant name
  name="${m}__${l}${extra:+__$extra}"
  if [ -f "../results/runs/$name/summary.json" ]; then echo "skip $name (done)"; continue; fi
  echo "$(date '+%H:%M:%S') start $name"
  "$PY" train.py --model "$m" --loss "$l" ${extra:+--variant "$extra"} > "../results/logs/train_${name}.log" 2>&1
  rc=$?
  grep -E "^DONE|Error" "../results/logs/train_${name}.log" | tail -2
  echo "$(date '+%H:%M:%S') end $name rc=$rc"
done
echo "QUEUE FINISHED $(date)"
