"""Shared code for HARMONISE-2. Reuses harmonise_lib.py unchanged, so calibration is the frozen HARMONISE-1 code.

Safeguards enforced here, not just documented:
  * the two external-test functions of harmonise_lib are replaced by a function that raises, and the test path is removed;
  * the frozen parameters are read only after their stored SHA-256 is checked;
  * every output goes to harmonise2/outputs (or outputs_smoke).
"""
import hashlib, json, re, sys
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import harmonise_lib as H                                    # noqa: E402

ROOT, H1 = H.ROOT, HERE.parent / "outputs"
CFG = json.load(open(HERE / "config.json"))


def _forbidden(*a, **k):
    raise RuntimeError("HARMONISE-2 must never read the external test split")


H.test_tiles = H.read_test = _forbidden
H.P.pop("external_test_dir")


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def frozen():
    p = H1 / "harmonisation_params.json"
    assert sha(p) == (H1 / "harmonisation_params.sha256").read_text().strip(), "HARMONISE-1 parameters changed"
    sel = json.load(open(H1 / "dev_selection.json"))
    return json.load(open(p)), sel["arm"]


def protected_files():
    pats = ["results/runs/*/summary.json", "results/runs/*/predictions.npz", "results/external/her2_40x/*", "results/deploy/*/*",
            "results/REPORT.md", "results/selection.json", "results/metrics_all.csv", "results/overfitting.csv", "splits/*",
            "next_experiment/outputs/*", "next_experiment/outputs/test/*", "next_experiment/*.py", "next_experiment/experiment_config.json",
            "final_reports/*.md", "ANTIGRAVITY_HANDOFF.md", "ANTIGRAVITY_EXECUTION_REPORT.md"]
    return sorted({p for pat in pats for p in ROOT.glob(pat) if p.is_file()})


def h1_pools():
    """Rebuild HARMONISE-1's sampling exactly, so its fit and selection tiles are known and the rest are unused."""
    d = H.DevZip(); exc = set((H1 / "dev_exclude.txt").read_text().split("\n"))
    names = [n for n in d.names if n not in exc]; perm = np.random.default_rng(H.CFG["seed"]).permutation(len(names))
    a, b = H.CFG["sampling"]["n_fit_tiles"], H.CFG["sampling"]["n_dev_eval_tiles"]
    fit = [names[i] for i in perm[:a]]; sel = [names[i] for i in perm[a:a + b]]; rest = [names[i] for i in perm[a + b:]]
    assert sel == (H1 / "dev_eval_tiles.txt").read_text().split("\n"), "cannot reproduce HARMONISE-1's dev sample"
    return d, fit, sel, rest


def index_blocks(names, gap):
    """Runs of nearby filename numbers within a score. These are NOT slides, ROIs or patients: the release has no such
    identifiers. They only keep neighbouring filenames together, and are always reported as 'index blocks'."""
    rows = sorted((re.search(r"her2-(.+?)-score", n).group(1), int(re.search(r"_(\d+)\.png$", n).group(1)), n) for n in names)
    out, c, prev = {}, 0, None
    for sc, num, n in rows:
        if prev is not None and (sc != prev[0] or num - prev[1] > gap):
            c += 1
        out[n] = f"idx{c:04d}"; prev = (sc, num)
    return out


def split_blocks(df, frac, seed):
    """Assign whole index blocks to R_cal until each score's share reaches frac; the rest is R_eval."""
    rng = np.random.default_rng(seed); cal = set()
    for _, g in df.groupby("label"):
        s = g.groupby("block").size(); bl = s.index.values[rng.permutation(len(s))]; tot = 0
        for b in bl:
            if tot >= frac * len(g):
                break
            if b not in cal:
                cal.add(b)
            tot += s[b]
    return df.block.isin(cal).map({True: "R_cal", False: "R_eval"})


def class_table(y, p):
    """Precision, recall, F1 and support per class, from hard predictions."""
    c = np.zeros((4, 4), int); np.add.at(c, (y, p), 1)
    rec = np.diag(c) / np.maximum(c.sum(1), 1); pre = np.diag(c) / np.maximum(c.sum(0), 1); f1 = 2 * pre * rec / np.maximum(pre + rec, 1e-12)
    return c, pre, rec, f1


def scores(y, prob):
    """Everything both A and C report for one set of probabilities."""
    from sklearn.metrics import cohen_kappa_score
    a = prob.argmax(1); c, pre, rec, f1 = class_table(y, a); e = prob @ np.arange(4)
    m = dict(n=len(y), accuracy=float((a == y).mean()), balanced_accuracy=float(rec[c.sum(1) > 0].mean()), macro_f1=float(f1.mean()),
             qwk=float(cohen_kappa_score(y, a, weights="quadratic", labels=range(4))), off_by_2plus=float((np.abs(a - y) >= 2).mean()), mean_expected_score=float(e.mean()), true_mean_score=float(y.mean()))
    for k, nm in enumerate(["0", "1+", "2+", "3+"]):
        m.update({f"precision_{nm}": float(pre[k]), f"recall_{nm}": float(rec[k]), f"f1_{nm}": float(f1[k]), f"predicted_share_{nm}": float((a == k).mean())})
    return m


def ece(y, prob, bins):
    conf, a = prob.max(1), prob.argmax(1); idx = np.minimum((conf * bins).astype(int), bins - 1); rows = []
    for b in range(bins):
        k = idx == b
        rows.append(dict(bin=b, n=int(k.sum()), confidence=float(conf[k].mean()) if k.any() else np.nan, accuracy=float((a[k] == y[k]).mean()) if k.any() else np.nan))
    t = pd.DataFrame(rows); v = t[t.n > 0]
    return float((v.n / v.n.sum() * (v.confidence - v.accuracy).abs()).sum()), t


def md(df, digits=3):
    f = lambda v: f"{v:.{digits}f}" if isinstance(v, (float, np.floating)) else str(v)
    return "\n".join(["| " + " | ".join(map(str, df.columns)) + " |", "|" + "---|" * len(df.columns)] + ["| " + " | ".join(f(v) for v in r) + " |" for r in df.values])
