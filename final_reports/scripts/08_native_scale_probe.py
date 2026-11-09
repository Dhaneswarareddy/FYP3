"""Audit 8 (no TensorFlow): nucleus-scale ratio at native 1024 px. External tiles come from the WSI-based TRAIN split
(read inside the zip, unlabelled use only), so the estimate never touches the external test split."""
import io, json, sys, zipfile; from pathlib import Path
import numpy as np, pandas as pd, cv2
from PIL import Image
ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT/"src"))
import analysis_data as AD
RAW = ROOT.parent/"FYP/data/raw/BCI_dataset/IHC"; Z = Path.home()/"Downloads/her2-ihc-40x-wsi.zip"
def diam(rgb, lo=40, hi=20000):
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV); bg = hsv[..., 1] < 8
    I0 = rgb[bg].mean(0) if bg.sum() > 500 else np.percentile(rgb.reshape(-1, 3), 99, axis=0)
    h = np.clip(AD.rgb2hed(rgb, np.maximum(I0, 1.0))[:, 0], 0, None).reshape(rgb.shape[:2])
    u = np.uint8(np.clip(h / max(np.percentile(h, 99.5), 1e-3), 0, 1) * 255)
    _, b = cv2.threshold(u, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU); b = cv2.morphologyEx(b, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    n, _, s, _ = cv2.connectedComponentsWithStats(b, connectivity=8); a = s[1:, cv2.CC_STAT_AREA]; a = a[(a >= lo) & (a <= hi)]
    return (float(np.sqrt(4*np.median(a)/np.pi)), len(a)) if len(a) >= 5 else (np.nan, len(a))
rng = np.random.default_rng(42); m = pd.read_csv(ROOT/"splits/split_manifest_grouped.csv"); tr = m[m.split=="train"]
rows = []
for p in rng.choice(tr.path.values, 300, replace=False):
    rows.append(("BCI", *diam(np.asarray(Image.open(RAW/p).convert("RGB")))))
z = zipfile.ZipFile(Z); iz = zipfile.ZipFile(z.open("WSI-based-dataset/train_data_wsi.zip")); names = [n for n in iz.namelist() if n.endswith(".png")]
for n in rng.choice(names, 300, replace=False):
    rows.append(("HER2-IHC-40x dev", *diam(np.asarray(Image.open(io.BytesIO(iz.read(n))).convert("RGB")))))
t = pd.DataFrame(rows, columns=["ds","d","n"]); s = t.groupby("ds").agg(tiles=("d","size"), valid=("d","count"), d_median=("d","median"), d_p25=("d",lambda x:x.quantile(.25)), d_p75=("d",lambda x:x.quantile(.75)), blobs=("n","median"))
print(s.round(2).to_string()); r = s.loc["HER2-IHC-40x dev","d_median"]/s.loc["BCI","d_median"]; print("ratio ext/BCI at native 1024:", round(r,2))
print("if BCI is 0.46 um/px, implied ext tile um/px:", round(0.46/r,3), "field um:", round(0.46/r*1024))
s.to_csv(ROOT/"final_reports/tables/native_scale_probe.csv")
