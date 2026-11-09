"""
Authoritative Physical Edge AI Benchmark Suite for Realme 6 (RMX2001).
Device: MediaTek Helio G90T (12nm, 2x Cortex-A76 @ 2.05GHz + 6x Cortex-A55 @ 2.0GHz)
OS: Android 11 (API 30, arm64-v8a)
Tool: Native AArch64 TensorFlow Lite Benchmark Binary (XNNPACK CPU Delegate)

Measures:
  - Latency: Mean, Median, Min, Max, P95, Std (us -> ms)
  - Throughput: Inferences / sec (FPS)
  - Memory: Peak RSS delta (MB)
  - Thermals: Battery temperature start/end (Celsius)
"""

import subprocess
import re
import time
import os
import csv
from pathlib import Path
import pandas as pd

ADB = "/Users/dhaneswarareddy/Library/Android/sdk/platform-tools/adb"
DEVICE_SERIAL = "BINVORW8TGFIRONV"
OUT_CSV = Path("/Users/dhaneswarareddy/Downloads/FYP3/deployment/benchmark_results/benchmark_realme_6.csv")
OUT_CSV.parent.mkdir(parents=True, exist_ok=True)

def run_adb_shell(cmd):
    full_cmd = [ADB, "-s", DEVICE_SERIAL, "shell", cmd]
    res = subprocess.run(full_cmd, capture_output=True, text=True)
    return res.stdout.strip()

def get_battery_temp():
    out = run_adb_shell("dumpsys battery | grep -i temperature | head -n 1")
    m = re.search(r"(\d+)", out)
    if m:
        return float(m.group(1)) / 10.0
    return 0.0

def parse_benchmark_output(raw_text):
    data = {}
    
    # Init time
    m_init = re.search(r"Init:\s*(\d+)", raw_text)
    data["init_us"] = int(m_init.group(1)) if m_init else None
    
    # Inference average
    m_avg = re.search(r"Inference \(avg\):\s*([\d\.]+)", raw_text)
    data["mean_us"] = float(m_avg.group(1)) if m_avg else None
    
    # Detailed count stats from measured runs
    count_matches = list(re.finditer(r"count=(\d+)\s+first=(\d+)\s+curr=(\d+)\s+min=(\d+)\s+max=(\d+)\s+avg=([\d\.]+)\s+std=([\d\.]+)\s+p5=(\d+)\s+median=(\d+)\s+p95=(\d+)", raw_text))
    if count_matches:
        last = count_matches[-1]
        data["num_runs"] = int(last.group(1))
        data["min_us"] = int(last.group(4))
        data["max_us"] = int(last.group(5))
        data["avg_us"] = float(last.group(6))
        data["std_us"] = float(last.group(7))
        data["median_us"] = int(last.group(9))
        data["p95_us"] = int(last.group(10))
    else:
        m_simple = re.search(r"curr=([\d\.]+)\s+min=([\d\.]+)\s+max=([\d\.]+)\s+avg=([\d\.]+)\s+p95=([\d\.]+)", raw_text)
        if m_simple:
            data["min_us"] = float(m_simple.group(2))
            data["max_us"] = float(m_simple.group(3))
            data["avg_us"] = float(m_simple.group(4))
            data["p95_us"] = float(m_simple.group(5))
            data["median_us"] = float(m_simple.group(4))
            data["std_us"] = 0.0

    # Memory delta overall
    m_mem = re.search(r"overall=([\d\.]+)", raw_text)
    data["peak_rss_mb"] = float(m_mem.group(1)) if m_mem else None

    # Model size in MB
    m_size = re.search(r"file size \(MB\):\s*([\d\.]+)", raw_text)
    data["file_size_mb"] = float(m_size.group(1)) if m_size else None
    
    return data

MODELS = [
    {
        "name": "primary_bci_hires_fp16",
        "file": "/data/local/tmp/primary_hires_fp16.tflite",
        "input_size": 448,
        "precision": "fp16"
    },
    {
        "name": "primary_bci_hires_int8",
        "file": "/data/local/tmp/primary_hires_int8.tflite",
        "input_size": 448,
        "precision": "int8"
    },
    {
        "name": "primary_bci_hires_fp32",
        "file": "/data/local/tmp/primary_hires_fp32.tflite",
        "input_size": 448,
        "precision": "fp32"
    },
    {
        "name": "experimental_stain224_fp16",
        "file": "/data/local/tmp/experimental_224_fp16.tflite",
        "input_size": 224,
        "precision": "fp16"
    }
]

THREADS = [1, 2, 4, 8]
NUM_RUNS = 50
WARMUP_RUNS = 10

results = []

print("=== Starting Realme 6 (Helio G90T) Automated Benchmark Suite ===")
print("Device: Realme 6 (RMX2001, MT6785, Android 11, arm64-v8a)")

for m in MODELS:
    print(f"\n--- Benchmarking Model: {m['name']} ({m['precision']}, {m['input_size']}px) ---")
    for t in THREADS:
        temp_start = get_battery_temp()
        cmd = f"/data/local/tmp/benchmark_model --graph={m['file']} --num_threads={t} --num_runs={NUM_RUNS} --warmup_runs={WARMUP_RUNS}"
        print(f"  Threads {t}: Starting at {temp_start}°C ...", end="", flush=True)
        
        raw_output = run_adb_shell(cmd)
        temp_end = get_battery_temp()
        parsed = parse_benchmark_output(raw_output)
        
        if not parsed.get("median_us"):
            print(f" ERROR: Failed to parse benchmark output!")
            print(raw_output[-500:])
            continue
            
        med_ms = (parsed.get("median_us") or 0) / 1000.0
        mean_ms = ((parsed.get("avg_us") or parsed.get("mean_us") or 0)) / 1000.0
        min_ms = (parsed.get("min_us") or 0) / 1000.0
        max_ms = (parsed.get("max_us") or 0) / 1000.0
        p95_ms = (parsed.get("p95_us") or 0) / 1000.0
        std_ms = (parsed.get("std_us") or 0) / 1000.0
        fps = 1000.0 / med_ms if med_ms > 0 else 0.0
        rss = parsed.get("peak_rss_mb") or 0.0
        file_size = parsed.get("file_size_mb") or 0.0
        
        row = {
            "device_model": "Realme 6 (RMX2001)",
            "platform": "mt6785",
            "soc": "MediaTek Helio G90T (12nm, 2x Cortex-A76 @ 2.05GHz + 6x Cortex-A55 @ 2.0GHz)",
            "os": "Android 11",
            "model_name": m["name"],
            "input_size": m["input_size"],
            "precision": m["precision"],
            "file_size_mb": round(file_size, 2),
            "threads": t,
            "num_runs": NUM_RUNS,
            "warmup_runs": WARMUP_RUNS,
            "mean_ms": round(mean_ms, 2),
            "median_ms": round(med_ms, 2),
            "min_ms": round(min_ms, 2),
            "max_ms": round(max_ms, 2),
            "p95_ms": round(p95_ms, 2),
            "std_ms": round(std_ms, 2),
            "throughput_fps": round(fps, 2),
            "peak_rss_mb": round(rss, 4),
            "temp_start_c": temp_start,
            "temp_end_c": temp_end
        }
        results.append(row)
        print(f" Median: {med_ms:.2f} ms | {fps:.2f} FPS | Peak RSS: {rss} MB | End Temp: {temp_end}°C")
        time.sleep(1.0) # Thermal settling

df = pd.DataFrame(results)
df.to_csv(OUT_CSV, index=False)
print(f"\n[SUCCESS] Authoritative benchmark saved to {OUT_CSV}")
print(df[["model_name", "precision", "threads", "median_ms", "throughput_fps", "peak_rss_mb", "temp_end_c"]].to_string())
