"""Load a pinned model and run it. The mode decides everything: config, model file, preprocessing and whether stain
gains exist. Nothing can be overridden from the command line, so the two configurations cannot be mixed."""
import hashlib, json, os, time
from pathlib import Path
import numpy as np
from . import preprocess as P

BASE = Path(__file__).resolve().parent.parent
MODES = {"primary": "primary_bci_hires_fp16", "experimental": "experimental_stain224_fp16"}
# Copied from next_experiment/outputs/harmonisation_params.json (stain_p99). Pinned here so a config edit cannot change them.
FROZEN_G_H, FROZEN_G_D = 0.2545270680571192, 0.5044797263953001
LABELS = ["0", "1+", "2+", "3+"]


def sha256(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def load_config(mode, base=BASE):
    if mode not in MODES:
        raise ValueError(f"unknown mode {mode!r}; choose from {list(MODES)}")
    cfg = json.load(open(base / "configs" / f"{MODES[mode]}.json"))
    if cfg["mode"] != mode:
        raise ValueError("config does not belong to this mode")
    s = cfg["stain_calibration"]
    if mode == "primary" and (s is not None or cfg["input_size"] != 448):
        raise ValueError("primary mode must have no stain calibration and a 448 px input")
    if mode == "experimental":
        if cfg["input_size"] != 224 or s is None or (s["g_h"], s["g_d"]) != (FROZEN_G_H, FROZEN_G_D):
            raise ValueError("experimental mode must use a 224 px input and the frozen stain_p99 gains")
    return cfg


def interpreter_class():
    try:
        from ai_edge_litert.interpreter import Interpreter
        return Interpreter, "ai_edge_litert"
    except ImportError:
        pass
    try:
        from tflite_runtime.interpreter import Interpreter
        return Interpreter, "tflite_runtime"
    except ImportError:
        pass
    import tensorflow as tf
    return tf.lite.Interpreter, f"tensorflow {tf.__version__}"


class Her2Engine:
    def __init__(self, mode, threads=4, base=BASE, verify_hash=True):
        self.mode, self.cfg = mode, load_config(mode, base)
        path = base / "models" / MODES[mode] / "model.tflite"
        if verify_hash and sha256(path) != self.cfg["model_sha256"]:
            raise ValueError(f"{path} does not match the pinned hash")
        Interpreter, self.runtime = interpreter_class()
        t0 = time.perf_counter()
        self.interp = Interpreter(model_path=str(path), num_threads=threads); self.interp.allocate_tensors()
        self.load_s = time.perf_counter() - t0
        self.inp, self.out = self.interp.get_input_details()[0], self.interp.get_output_details()[0]
        self._pre = P.preprocess_primary if mode == "primary" else P.preprocess_experimental

    def preprocess(self, tile):
        return self._pre(tile, self.cfg)

    def from_resized(self, x):
        """x: uint8 tile already at the input size. Applies this mode's remaining step: none, or the frozen gains."""
        if self.mode == "primary":
            return x.astype(np.float32)
        return P.apply_stain_gains(x, self.cfg["stain_calibration"]["g_h"], self.cfg["stain_calibration"]["g_d"])

    def invoke(self, x):
        """x: H x W x 3 float32, 0-255. Returns 4 class probabilities."""
        self.interp.set_tensor(self.inp["index"], x[None].astype(np.float32)); self.interp.invoke()
        return self.interp.get_tensor(self.out["index"])[0].astype(np.float64)

    def predict(self, tile):
        p = self.invoke(self.preprocess(tile)); k = int(p.argmax())
        r = {"mode": self.mode, "prediction": LABELS[k], "confidence": float(p[k]), **{f"p_{l}": float(v) for l, v in zip(LABELS, p)}}
        T = (self.cfg.get("temperature") or {}).get("T")
        if T:
            q = np.exp(np.log(np.maximum(p, 1e-9)) / T); r["confidence_temperature_scaled"] = float((q / q.sum()).max())
        return r
