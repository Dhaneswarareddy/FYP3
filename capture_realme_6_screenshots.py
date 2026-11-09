"""
Automated UI Driver & Screenshot Capture for HER2 Mobile Edge Android App on Realme 6 (RMX2001).
MediaTek Helio G90T (2× Cortex-A76 @ 2.05GHz + 6× Cortex-A55 @ 2.0GHz).
Captures pixel-perfect screenshots from physical device buffer to deployment/app_screenshots/realme_6/
"""

import os
import time
import subprocess
from pathlib import Path

ADB = "/Users/dhaneswarareddy/Library/Android/sdk/platform-tools/adb -s BINVORW8TGFIRONV"
OUT_DIR = Path("/Users/dhaneswarareddy/Downloads/FYP3/deployment/app_screenshots/realme_6")
OUT_DIR.mkdir(parents=True, exist_ok=True)

def adb_cmd(cmd):
    full_cmd = f"{ADB} {cmd}"
    res = subprocess.run(full_cmd, shell=True, capture_output=True, text=True)
    return res.stdout.strip()

def adb_tap(x, y):
    adb_cmd(f"shell input tap {x} {y}")
    time.sleep(1.2)

def adb_swipe(x1, y1, x2, y2, duration=300):
    adb_cmd(f"shell input swipe {x1} {y1} {x2} {y2} {duration}")
    time.sleep(1.2)

def capture_screen(filename):
    device_path = f"/sdcard/{filename}"
    local_path = OUT_DIR / filename
    adb_cmd(f"shell screencap -p {device_path}")
    adb_cmd(f"pull {device_path} {local_path}")
    print(f"[SAVED] {local_path} ({os.path.getsize(local_path)} bytes)")
    return local_path

print("=== Starting Realme 6 (RMX2001) App Automation ===")

# 1. Wake device and ensure app is foreground
adb_cmd("shell svc power stayon true")
adb_cmd("shell input keyevent 224") # Wakeup
adb_cmd("shell input keyevent 82")  # Unlock
adb_swipe(540, 1800, 540, 400, 200) # Dismiss keyguard
adb_cmd("shell am start -n com.fyp3.her2classifier/.MainActivity")
time.sleep(2.0)

# ==============================================================================
# Screen 1: Overview - Hardware Spec Card & Configuration Controls
# ==============================================================================
print("\n--- 1. Capturing App Overview & Hardware Controls ---")
# Scroll to top
adb_swipe(540, 600, 540, 2100, 300)
# Select FP16 (312, 759) and 4T (648, 983)
adb_tap(312, 759) # rbFp16
adb_tap(648, 983) # rb4Threads
time.sleep(1.0)
capture_screen("01_app_overview_hardware_and_controls.png")

# ==============================================================================
# Screen 2: Tile 0 (Negative, Score 0) - FP16, 4 Threads
# ==============================================================================
print("\n--- 2. Capturing Tile 0 (Score 0 Negative) ---")
# Tap btnSample0 at top coordinates (193, 1978)
adb_tap(193, 1978)
time.sleep(1.5)
# Scroll down to display full preview + diagnostic results card
adb_swipe(540, 1800, 540, 800, 300)
time.sleep(1.0)
capture_screen("02_app_inference_score_0_negative_fp16.png")

# ==============================================================================
# Screen 3: Tile 1 (Negative, Score 1+) - FP16, 4 Threads
# ==============================================================================
print("\n--- 3. Capturing Tile 1 (Score 1+ Negative) ---")
# When scrolled down, btnSample1 is at (424, 1063)
adb_tap(424, 1063)
time.sleep(1.5)
capture_screen("03_app_inference_score_1_negative_fp16.png")

# ==============================================================================
# Screen 4: Tile 2 (Equivocal, Score 2+) - FP16, 4 Threads (Reflex FISH Required)
# ==============================================================================
print("\n--- 4. Capturing Tile 2 (Score 2+ Equivocal / Borderline) ---")
# btnSample2 at (655, 1063)
adb_tap(655, 1063)
time.sleep(1.5)
capture_screen("04_app_inference_score_2_equivocal_fp16.png")

# ==============================================================================
# Screen 5: Tile 3 (Positive, Score 3+) - FP16, 4 Threads (Targeted Therapy)
# ==============================================================================
print("\n--- 5. Capturing Tile 3 (Score 3+ Overexpressed / Positive) ---")
# btnSample3 at (886, 1063)
adb_tap(886, 1063)
time.sleep(1.5)
capture_screen("05_app_inference_score_3_positive_fp16.png")

# ==============================================================================
# Screen 6: INT8 Quantized Fast Mode (Tile 3)
# ==============================================================================
print("\n--- 6. Capturing INT8 Quantized Fast Inference ---")
# Scroll to top
adb_swipe(540, 600, 540, 2100, 300)
# Tap rbInt8 at (768, 759)
adb_tap(768, 759)
time.sleep(1.0)
# Tap Tile 3 (886, 1978)
adb_tap(886, 1978)
time.sleep(1.5)
# Scroll down to display results
adb_swipe(540, 1800, 540, 800, 300)
time.sleep(1.0)
capture_screen("06_app_inference_score_3_int8_quantized.png")

# ==============================================================================
# Screen 7: Multi-Threading Benchmark Demonstration (1 Thread vs 4 Threads)
# ==============================================================================
print("\n--- 7. Capturing 1-Thread Baseline for Multi-Core Demonstration ---")
# Scroll to top
adb_swipe(540, 600, 540, 2100, 300)
# Tap rbFp16 (312, 759)
adb_tap(312, 759)
# Tap rb1Thread (192, 983)
adb_tap(192, 983)
time.sleep(1.0)
# Tap Tile 0 (193, 1978)
adb_tap(193, 1978)
time.sleep(1.5)
# Scroll down
adb_swipe(540, 1800, 540, 800, 300)
time.sleep(1.0)
capture_screen("07_app_inference_1thread_baseline.png")

print("\n[COMPLETE] All 7 Realme 6 physical device screenshots successfully captured!")
