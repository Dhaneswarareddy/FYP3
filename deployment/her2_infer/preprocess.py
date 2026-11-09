"""Tile preprocessing. NumPy and Pillow only, so it runs on the Pi without OpenCV or TensorFlow.

The two modes have separate functions on purpose. Primary mode has no stain step at all.
Both reproduce the training path exactly: Lanczos to the source size, then bilinear to the input size.
The stain arithmetic is identical to next_experiment/harmonise_lib.py (checked by deployment/mac/test_deployment.py).
"""
import numpy as np
from PIL import Image

# Ruifrok & Johnston vectors (rows: haematoxylin, eosin, DAB), as in HARMONISE-1
RGB_FROM_HED = np.array([[0.65, 0.70, 0.29], [0.07, 0.99, 0.11], [0.27, 0.57, 0.78]], np.float32)
HED_FROM_RGB = np.linalg.inv(RGB_FROM_HED).astype(np.float32)
_SDIV = np.array([0] + [int(round((255 << 12) / i)) for i in range(1, 256)], np.int64)


def load_tile(path_or_image):
    return path_or_image.convert("RGB") if isinstance(path_or_image, Image.Image) else Image.open(path_or_image).convert("RGB")


def resize_two_step(pil, source_size, input_size):
    return np.asarray(pil.resize((source_size, source_size), Image.LANCZOS).resize((input_size, input_size), Image.BILINEAR), np.uint8)


def hsv_saturation(rgb):
    """OpenCV-style 8-bit saturation. It can differ from OpenCV by 1 on a few values, but the S < 8 background mask is
    identical for every possible pixel (checked exhaustively in deployment/mac/test_deployment.py)."""
    x = rgb.astype(np.int64); v = x.max(-1); d = v - x.min(-1)
    return ((d * _SDIV[v] + (1 << 11)) >> 12).astype(np.uint8)


def illumination(rgb):
    """Tile illumination: mean of background pixels (S < 8), else the 99th percentile per channel."""
    bg = hsv_saturation(rgb) < 8
    i0 = rgb[bg].mean(0) if bg.mean() >= 0.02 else np.percentile(rgb.reshape(-1, 3), 99, axis=0)
    return np.maximum(i0.astype(np.float32), 1.0)


def apply_stain_gains(rgb, g_h, g_d):
    """One fixed H and DAB gain, in optical density relative to the tile's own illumination."""
    i0 = illumination(rgb)
    od = -np.log(np.maximum(rgb.astype(np.float32) / i0, 1e-6))
    hed = od.reshape(-1, 3) @ HED_FROM_RGB * np.array([g_h, 1.0, g_d], np.float32)
    return np.clip(i0 * np.exp(-(hed @ RGB_FROM_HED)).reshape(rgb.shape), 0, 255).astype(np.float32)


def preprocess_primary(tile, cfg):
    return resize_two_step(load_tile(tile), cfg["source_size"], cfg["input_size"]).astype(np.float32)


def preprocess_experimental(tile, cfg):
    s = cfg["stain_calibration"]
    return apply_stain_gains(resize_two_step(load_tile(tile), cfg["source_size"], cfg["input_size"]), s["g_h"], s["g_d"])
