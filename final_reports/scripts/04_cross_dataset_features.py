"""Audit 4 (no TensorFlow): the same stain, colour and scale measurements on HER2-IHC-40x test, BCI and FYP2, plus
stain-only classifiers fitted on BCI train / FYP2 train and applied unchanged to the external tiles."""
import json, sys; from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
import numpy as np, pandas as pd, cv2
from PIL import Image
ROOT = Path(__file__).resolve().parents[2]; sys.path.insert(0, str(ROOT/"src"))
import analysis_data as AD
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, balanced_accuracy_score, cohen_kappa_score
OUT = ROOT/"final_reports/tables"; RAW = ROOT.parent/"FYP/data/raw/HER2-IHC-40x/wsi_test"; FYP2 = ROOT.parent/"FYP2"
GAN = FYP2/"HER2 SCORES DATA/Generated_HER2_images"

def scale_stats(path):
    """Blob size of haematoxylin-rich objects and texture scale, all at the same 224 px view the 224 networks get."""
    rgb = np.asarray(Image.open(path).convert("RGB").resize((224, 224), Image.BILINEAR))
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV); bg = hsv[..., 1] < 8
    I0 = rgb[bg].mean(0) if bg.sum() > 100 else np.percentile(rgb.reshape(-1, 3), 99, axis=0)
    h = np.clip(AD.rgb2hed(rgb, np.maximum(I0, 1.0))[:, 0], 0, None).reshape(224, 224)
    u = np.uint8(np.clip(h / max(np.percentile(h, 99.5), 1e-3), 0, 1) * 255)
    _, b = cv2.threshold(u, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    b = cv2.morphologyEx(b, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
    n, _, s, _ = cv2.connectedComponentsWithStats(b, connectivity=8); a = s[1:, cv2.CC_STAT_AREA]; a = a[(a >= 4) & (a <= 2000)]
    grey = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32); sp = np.abs(np.fft.fftshift(np.fft.fft2(grey - grey.mean()))) ** 2
    yy, xx = np.indices(sp.shape); r = np.hypot(yy - 112, xx - 112); rb = r.astype(int); prof = np.bincount(rb.ravel(), sp.ravel())[:112]; c = np.cumsum(prof) / prof.sum()
    return dict(blob_n=len(a), blob_diam_px=float(np.sqrt(4 * np.median(a) / np.pi)) if len(a) >= 5 else np.nan, spectrum_median_freq=float(np.searchsorted(c, 0.5)), spectrum_p90_freq=float(np.searchsorted(c, 0.9)))

def both(path):
    return dict(path=str(path), **AD.image_features(path), **scale_stats(path))

def main():
    g = pd.read_csv(ROOT/"splits/split_manifest_grouped.csv"); f = pd.read_csv(FYP2/"splits/split_manifest.csv")
    ext = sorted(RAW.glob("class_*/*.png"))
    bci_te = [ROOT/"data/ihc_256"/p for p in g[g.split=="test"].path]; gan_te = [GAN/p for p in f[f.split=="test"].path]
    with ProcessPoolExecutor(6) as ex:
        E = pd.DataFrame(list(ex.map(both, ext, chunksize=16))); B = pd.DataFrame(list(ex.map(both, bci_te, chunksize=16))); F = pd.DataFrame(list(ex.map(both, gan_te, chunksize=16)))
    lv = {"0":0,"1+":1,"2+":2,"3+":3}; E["label"] = [lv[Path(p).parent.name[6:]] for p in E.path]; E["dataset"] = "HER2-IHC-40x"
    B["label"] = g[g.split=="test"].label.values; B["dataset"] = "BCI"; F["label"] = f[f.split=="test"].label.values; F["dataset"] = "FYP2 GAN"
    A = pd.concat([E, B, F]); A.to_csv(OUT/"cross_dataset_features.csv", index=False)
    cols = ["dabc_mean","dabc_p90","dabc_frac030","hemc_mean","sat_mean","val_mean","bg_brightness","tissue_frac","sharpness","hf_share","blob_diam_px","blob_n","spectrum_median_freq","spectrum_p90_freq"]
    s = A.groupby(["dataset","label"])[cols].median().round(3); s.to_csv(OUT/"cross_dataset_features_by_class.csv"); pd.set_option("display.width",240); pd.set_option("display.max_columns",30); print(s.to_string())
    # stain-only rules, fitted on training tiles only
    df = pd.read_csv(ROOT/"results/analysis/data_features.csv"); b = df[df.dataset=="BCI (real)"].merge(g[["path","split"]].rename(columns={"split":"gsplit"}), on="path")
    trB = b[b.gsplit=="train"]; trF = df[(df.dataset=="FYP2 (GAN)")&(df.split=="train")]
    sets = {"DAB only": ["dabc_mean","dabc_median","dabc_p90","dabc_frac015","dabc_frac030"], "DAB + haematoxylin": ["dabc_mean","dabc_median","dabc_p90","dabc_frac015","dabc_frac030","hemc_mean"]}
    rows = []
    for fs, c in sets.items():
        for nm, tr in [("BCI train", trB), ("FYP2 train", trF)]:
            for mname, clf in [("logistic", make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000))), ("random forest", RandomForestClassifier(400, random_state=42, n_jobs=-1, min_samples_leaf=3))]:
                clf.fit(tr[c].values, tr.label.values.astype(int))
                for te, name in [(E, "HER2-IHC-40x test"), (B, "BCI test"), (F, "FYP2 test")]:
                    p = clf.predict(te[c].values); y = te.label.values
                    rows.append(dict(features=fs, fitted_on=nm, model=mname, applied_to=name, accuracy=accuracy_score(y,p), balanced_accuracy=balanced_accuracy_score(y,p), qwk=cohen_kappa_score(y,p,weights="quadratic"), share_pred_3plus=(p==3).mean(), mean_pred=p.mean()))
    r = pd.DataFrame(rows); r.to_csv(OUT/"stain_only_rules.csv", index=False); print(r.round(3).to_string(index=False))

if __name__ == "__main__":
    main()
