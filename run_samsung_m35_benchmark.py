"""
Automated Android Benchmark Suite for FYP3 Edge Deployment
Target Device: Samsung Galaxy M35 5G (SM-M356B, Exynos 1380, 8 Cores, Android 16)
Collects actual physical execution metrics over ADB:
  - Latency: mean, median, min, max, std, p5, p95
  - Throughput: FPS
  - Memory: Peak RAM footprint delta (MB)
  - Thermals: Battery temperature start & end (°C)
  - Thread scaling: 1, 2, 4, 8 threads
  - Model variants: Primary FP16 (448px), Primary INT8 (448px), Primary FP32 (448px), Experimental FP16 (224px)
"""

import subprocess
import re
import time
import pandas as pd
from pathlib import Path

ADB = "/Users/dhaneswarareddy/Library/Android/sdk/platform-tools/adb"
OUT_DIR = Path("/Users/dhaneswarareddy/Downloads/FYP3/deployment/benchmark_results")
OUT_DIR.mkdir(parents=True, exist_ok=True)

def run_adb_shell(cmd):
    full_cmd = [ADB, "shell", cmd]
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
    
    # Detailed run stats from INFO: count=...
    # Look for the last count= line (the measured runs, not warmup)
    count_matches = list(re.finditer(r"count=(\d+)\s+first=(\d+)\s+curr=(\d+)\s+min=(\d+)\s+max=(\d+)\s+avg=([\d\.]+)\s+std=([\d\.]+)\s+p5=(\d+)\s+median=(\d+)\s+p95=(\d+)", raw_text))
    if count_matches:
        last = count_matches[-1]
        data["count"] = int(last.group(1))
        data["min_us"] = int(last.group(4))
        data["max_us"] = int(last.group(5))
        data["std_us"] = float(last.group(7))
        data["p5_us"] = int(last.group(8))
        data["median_us"] = int(last.group(9))
        data["p95_us"] = int(last.group(10))
    else:
        data["count"] = None
        data["min_us"] = None
        data["max_us"] = None
        data["std_us"] = None
        data["p5_us"] = None
        data["median_us"] = None
        data["p95_us"] = None

    # Memory footprint delta
    m_mem = re.search(r"Memory footprint delta.*init=([\d\.]+)\s+overall=([\d\.]+)", raw_text)
    if m_mem:
        data["mem_init_mb"] = float(m_mem.group(1))
        data["mem_overall_mb"] = float(m_mem.group(2))
    else:
        data["mem_init_mb"] = None
        data["mem_overall_mb"] = None

    return data

def main():
    print("=== Starting Samsung Galaxy M35 5G Automated Benchmark Suite ===")
    
    # Device details
    device_model = run_adb_shell("getprop ro.product.model")
    device_board = run_adb_shell("getprop ro.board.platform")
    android_ver = run_adb_shell("getprop ro.build.version.release")
    abi = run_adb_shell("getprop ro.product.cpu.abi")
    
    print(f"Device: {device_model} ({device_board}, Android {android_ver}, {abi})")
    
    models = [
        {
            "name": "primary_bci_hires_fp16",
            "file": "/data/local/tmp/primary_hires_fp16.tflite",
            "input_size": 448,
            "precision": "fp16",
            "file_size_mb": 11.27
        },
        {
            "name": "primary_bci_hires_int8",
            "file": "/data/local/tmp/primary_hires_int8.tflite",
            "input_size": 448,
            "precision": "int8",
            "file_size_mb": 6.82
        },
        {
            "name": "primary_bci_hires_fp32",
            "file": "/data/local/tmp/primary_hires_fp32.tflite",
            "input_size": 448,
            "precision": "fp32",
            "file_size_mb": 22.36
        },
        {
            "name": "experimental_stain224_fp16",
            "file": "/data/local/tmp/experimental_224_fp16.tflite",
            "input_size": 224,
            "precision": "fp16",
            "file_size_mb": 11.27
        }
    ]
    
    threads_list = [1, 2, 4, 8]
    num_runs = 50
    warmup_runs = 10
    
    records = []
    
    for m in models:
        print(f"\n--- Benchmarking Model: {m['name']} ({m['precision']}, {m['input_size']}px) ---")
        for t in threads_list:
            temp_start = get_battery_temp()
            print(f"  Threads {t}: Starting at {temp_start:.1f}°C ... ", end="", flush=True)
            
            cmd = f"/data/local/tmp/benchmark_model --graph={m['file']} --num_threads={t} --warmup_runs={warmup_runs} --num_runs={num_runs}"
            raw_out = run_adb_shell(cmd)
            temp_end = get_battery_temp()
            
            parsed = parse_benchmark_output(raw_out)
            
            mean_ms = parsed["mean_us"] / 1000.0 if parsed["mean_us"] else 0.0
            median_ms = parsed["median_us"] / 1000.0 if parsed["median_us"] else 0.0
            min_ms = parsed["min_us"] / 1000.0 if parsed["min_us"] else 0.0
            max_ms = parsed["max_us"] / 1000.0 if parsed["max_us"] else 0.0
            p95_ms = parsed["p95_us"] / 1000.0 if parsed["p95_us"] else 0.0
            std_ms = parsed["std_us"] / 1000.0 if parsed["std_us"] else 0.0
            fps = 1000.0 / median_ms if median_ms > 0 else 0.0
            
            rec = {
                "device_model": device_model,
                "platform": device_board,
                "soc": "Samsung Exynos 1380 (5nm, 4x Cortex-A78 @ 2.4GHz + 4x Cortex-A55 @ 2.0GHz)",
                "os": f"Android {android_ver}",
                "model_name": m["name"],
                "input_size": m["input_size"],
                "precision": m["precision"],
                "file_size_mb": m["file_size_mb"],
                "threads": t,
                "num_runs": parsed["count"],
                "warmup_runs": warmup_runs,
                "mean_ms": round(mean_ms, 2),
                "median_ms": round(median_ms, 2),
                "min_ms": round(min_ms, 2),
                "max_ms": round(max_ms, 2),
                "p95_ms": round(p95_ms, 2),
                "std_ms": round(std_ms, 2),
                "throughput_fps": round(fps, 2),
                "peak_rss_mb": parsed["mem_overall_mb"],
                "temp_start_c": temp_start,
                "temp_end_c": temp_end
            }
            records.append(rec)
            print(f"Median: {median_ms:.2f} ms | {fps:.2f} FPS | Peak RSS: {parsed['mem_overall_mb']} MB | End Temp: {temp_end:.1f}°C")
            
            # Short cooldown between thread configs to prevent thermal accumulation
            time.sleep(2)
            
    df = pd.DataFrame(records)
    csv_path = OUT_DIR / "benchmark_samsung_m35.csv"
    df.to_csv(csv_path, index=False)
    print(f"\n[SUCCESS] Authoritative benchmark saved to {csv_path}")
    print(df[["model_name", "precision", "threads", "median_ms", "throughput_fps", "peak_rss_mb", "temp_end_c"]].to_string())

if __name__ == "__main__":
    main()
