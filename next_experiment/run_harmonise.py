"""HARMONISE-1 driver. Stages, in order (see ANTIGRAVITY_HANDOFF.md):

  python run_harmonise.py --stage preflight        protected-file hashes, archive and independence checks
  python run_harmonise.py --stage fit              stain gains from unlabelled tiles, then freezes them
  python run_harmonise.py --stage dev --cpu        evaluates the grid on labelled development tiles, picks one arm
  python run_harmonise.py --stage test --run R --cpu   once per panel run; needs a selected arm
  python run_harmonise.py --stage summary          final tables; the only place test labels meet the decision rule
  python run_harmonise.py --stage verify           protected files unchanged

No stage trains anything or writes outside next_experiment/. The test stage refuses to run twice and refuses to
run without frozen parameters. --smoke runs fit and dev on a few tiles into outputs_smoke/ (test is never touched).
"""
import argparse, hashlib, json, sys, time
from pathlib import Path
import numpy as np, pandas as pd
from PIL import Image
import harmonise_lib as H
from harmonise_lib import CFG, NEXT, P, ROOT

ap = argparse.ArgumentParser()
ap.add_argument("--stage", required=True, choices=["preflight", "fit", "dev", "test", "summary", "verify"])
ap.add_argument("--run", default=None); ap.add_argument("--cpu", action="store_true"); ap.add_argument("--smoke", action="store_true")
args = ap.parse_args()
OUT = NEXT / ("outputs_smoke" if args.smoke else "outputs"); OUT.mkdir(exist_ok=True)
N = {k: (40 if args.smoke else v) for k, v in CFG["sampling"].items() if k != "pixels_per_tile"}
if args.cpu:
    import tensorflow as tf
    tf.config.set_visible_devices([], "GPU")


def sha(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def protected():
    pats = ["results/runs/*/summary.json", "results/runs/*/predictions.npz", "results/external/her2_40x/*", "results/deploy/*/*",
            "results/REPORT.md", "results/selection.json", "results/metrics_all.csv", "results/overfitting.csv", "splits/*"]
    return sorted(p for pat in pats for p in ROOT.glob(pat) if p.is_file())


def samples(d, exclude):
    """Disjoint, seeded, label-blind samples of the development tiles: fit and dev evaluation never share a tile."""
    names = [n for n in d.names if n not in exclude]
    perm = np.random.default_rng(CFG["seed"]).permutation(len(names))
    a, b = N["n_fit_tiles"], N["n_dev_eval_tiles"]
    return [names[i] for i in perm[:a]], [names[i] for i in perm[a:a + b]]


def preflight():
    import imagehash
    rep = {}; b = OUT / "protected_before.json"
    if not b.exists():
        json.dump({str(p.relative_to(ROOT)): sha(p) for p in protected()}, open(b, "w"), indent=0)
    d = H.DevZip(); te = H.test_tiles(); rep["n_dev"] = len(d.names); rep["n_test"] = len(te)
    dn, tn = {n.split("/")[-1] for n in d.names}, {n.split("/")[-1] for n in te}
    rep["shared_names"] = len(dn & tn)
    rep["dev_all_named_train"] = all("score_train_" in n for n in d.names); rep["test_all_named_test"] = all("score_test_" in n for n in te)
    bits = lambda im: np.array(imagehash.phash(im.resize((256, 256))).hash, bool).flatten()
    T = np.stack([bits(H.read_test(n)) for n in te])
    sub = d.names[:64] if args.smoke else d.names
    near = []
    for k, n in enumerate(sub):
        if ((T != bits(d.read(n))).sum(1)).min() <= 4:
            near.append(n)
        if k % 1000 == 0:
            print("  hashed", k, "of", len(sub), flush=True)
    rep["dev_tiles_within_phash4_of_test"] = len(near)
    (OUT / "dev_exclude.txt").write_text("\n".join(near))
    rep["go"] = rep["n_dev"] == 8093 and rep["n_test"] == 1847 and rep["shared_names"] == 0 and rep["dev_all_named_train"] and rep["test_all_named_test"] and len(near) < 0.02 * len(sub)
    json.dump(rep, open(OUT / "preflight.json", "w"), indent=1); print(json.dumps(rep, indent=1)); sys.exit(0 if rep["go"] else 2)


def fit():
    exc = set((OUT / "dev_exclude.txt").read_text().split("\n")) if (OUT / "dev_exclude.txt").exists() else set()
    d = H.DevZip(); fs, ev = samples(d, exc); rng = np.random.default_rng(CFG["seed"]); k = CFG["sampling"]["pixels_per_tile"]
    def collect(imgs):
        Hs, Ds = [], []
        for im in imgs:
            h, a = H.stain_od(np.asarray(im, np.uint8))
            i = rng.integers(0, len(h), min(k, len(h))); Hs.append(h[i]); Ds.append(a[i])
        return np.concatenate(Hs), np.concatenate(Ds)
    t0 = time.time()
    he, de = collect(d.read(n).resize((256, 256), Image.LANCZOS) for n in fs)
    m = pd.read_csv(P["bci_manifest"]); tr = m[m.split == "train"].path.values
    bi = np.random.default_rng(CFG["seed"]).permutation(len(tr))[:N["n_bci_tiles"]]
    hb, db = collect(Image.open(P["bci_cache_256"] / tr[i]).convert("RGB") for i in bi)
    lo, hi = CFG["stain_fit"]["gain_limits"]; g = {}
    for p in CFG["stain_fit"]["percentiles"]:
        g[str(p)] = dict(g_h=float(np.clip(np.percentile(hb, CFG["stain_fit"]["primary_percentile"]) / np.percentile(he, CFG["stain_fit"]["primary_percentile"]), lo, hi)),
                         g_d=float(np.clip(np.percentile(db, p) / np.percentile(de, p), lo, hi)),
                         q_bci_d=float(np.percentile(db, p)), q_ext_d=float(np.percentile(de, p)))
    params = dict(gains=g, n_fit=len(fs), n_bci=len(bi), seed=CFG["seed"], labels_used=False)
    json.dump(params, open(OUT / "harmonisation_params.json", "w"), indent=1)
    (OUT / "harmonisation_params.sha256").write_text(sha(OUT / "harmonisation_params.json"))
    (OUT / "dev_eval_tiles.txt").write_text("\n".join(ev))
    print(json.dumps(params, indent=1), f"\nfit took {time.time()-t0:.0f}s")


def load_params():
    p = OUT / "harmonisation_params.json"
    assert sha(p) == (OUT / "harmonisation_params.sha256").read_text(), "parameters changed after freezing"
    return json.load(open(p))


def dev():
    params = load_params(); d = H.DevZip(); names = (OUT / "dev_eval_tiles.txt").read_text().split("\n")
    pils = [d.read(n) for n in names]; y = np.array([H.label_from_name(n) for n in names]); info = H.run_info(CFG["primary_run"])
    rows = []; arms = H.make_arms(params)
    if args.smoke:
        arms = arms[:1] + [a for a in arms if a["name"] in ("stain_p95", "scale3", "stain_p95+scale3")]
    for arm in arms:
        t0 = time.time(); model = H.build(info, arm["scale"]); prob = H.predict(model, pils, info, arm)
        r = dict(arm=arm["name"], scale=arm["scale"], g_h=arm["g_h"], g_d=arm["g_d"], factors=H.n_factors(arm), seconds=round(time.time() - t0, 1), **H.metrics(y, prob))
        rows.append(r); print({k: (round(v, 3) if isinstance(v, float) else v) for k, v in r.items() if k in ("arm", "accuracy", "balanced_accuracy", "qwk", "mean_expected_score", "true_mean_score", "predicted_share")}, flush=True)
    t = pd.DataFrame(rows); t.to_csv(OUT / "dev_results.csv", index=False)
    s = CFG["selection"]; base = t[t.arm == "none"].iloc[0][s["metric"]]; best = t[s["metric"]].max()
    c = t[t[s["metric"]] >= best - s["tie_tolerance"]].sort_values(["factors", s["metric"]], ascending=[True, False]).iloc[0]
    sel = dict(baseline=float(base), best=float(best), selected=c.arm if best - base >= s["min_gain_over_none"] else None, metric=s["metric"], n_dev=len(y))
    if sel["selected"]:
        sel["arm"] = next(a for a in arms if a["name"] == c.arm)
    json.dump(sel, open(OUT / "dev_selection.json", "w"), indent=1); print(json.dumps(sel, indent=1))
    if not sel["selected"]:
        print("NO-GO: no arm beat 'none' by the pre-set margin on development tiles. Do not run the test stage.")


def test():
    assert not args.smoke, "smoke never touches the test split"
    assert args.run in CFG["test_panel"], "run not in the pre-registered panel"
    load_params(); sel = json.load(open(OUT / "dev_selection.json")); assert sel["selected"], "no arm selected on development tiles"
    (OUT / "test").mkdir(exist_ok=True); f = OUT / "test" / f"{args.run}.csv"
    assert not f.exists(), f"{f} exists: the test split is evaluated once"
    names = H.test_tiles(); pils = [H.read_test(n) for n in names]; info = H.run_info(args.run); arm = sel["arm"]
    prob = H.predict(H.build(info, arm["scale"]), pils, info, arm)
    base = pd.read_csv(P["external_baseline_dir"] / f"BCI__{args.run}.csv").set_index("path").loc[names]
    df = pd.DataFrame(prob, columns=[f"p{k}" for k in range(4)]); df.insert(0, "path", names); df.to_csv(f, index=False)
    print("written", f, "arm", arm["name"], "(metrics are computed only in the summary stage)")
    if args.run == CFG["primary_run"]:
        m = H.build(info, 1.0); none = dict(name="none", scale=1.0, g_h=1.0, g_d=1.0)
        d = np.abs(H.predict(m, pils[:64], info, none) - base[[f"p{k}" for k in range(4)]].values[:64]).max()
        json.dump(dict(max_abs_diff=float(d), ok=bool(d < 1e-3)), open(OUT / "test_baseline_reproduction.json", "w")); print("baseline reproduction max diff", d)


def summary():
    sel = json.load(open(OUT / "dev_selection.json")); names = H.test_tiles(); y = np.array([H.label_from_name(n) for n in names]); g = H.filename_groups(names)
    ids = np.unique(g); idx = [np.where(g == i)[0] for i in ids]; rows = []; N_B = CFG["bootstrap"]["n"]
    from sklearn.metrics import balanced_accuracy_score as bas, cohen_kappa_score as ck
    for run in CFG["test_panel"]:
        f = OUT / "test" / f"{run}.csv"
        if not f.exists():
            print("missing", run); continue
        cols = [f"p{k}" for k in range(4)]; a = pd.read_csv(f).set_index("path").loc[names, cols].values; b = pd.read_csv(P["external_baseline_dir"] / f"BCI__{run}.csv").set_index("path").loc[names, cols].values
        ma, mb = H.metrics(y, a), H.metrics(y, b); pa, pb = a.argmax(1), b.argmax(1); rng = np.random.default_rng(CFG["seed"]); db, dq = [], []
        for _ in range(N_B):
            i = np.concatenate([idx[j] for j in rng.integers(0, len(ids), len(ids))])
            if len(set(y[i])) == 4:
                db.append(bas(y[i], pa[i]) - bas(y[i], pb[i])); dq.append(ck(y[i], pa[i], weights="quadratic") - ck(y[i], pb[i], weights="quadratic"))
        rows.append(dict(run=run, arm=sel["selected"], **{f"none_{k}": mb[k] for k in ("accuracy", "balanced_accuracy", "qwk", "mean_expected_score")}, **{f"harmonised_{k}": ma[k] for k in ("accuracy", "balanced_accuracy", "qwk", "mean_expected_score", "recall", "predicted_share", "confusion")},
                         delta_balanced_accuracy=ma["balanced_accuracy"] - mb["balanced_accuracy"], delta_balacc_lo=float(np.percentile(db, 2.5)), delta_balacc_hi=float(np.percentile(db, 97.5)),
                         delta_qwk=ma["qwk"] - mb["qwk"], delta_qwk_lo=float(np.percentile(dq, 2.5)), delta_qwk_hi=float(np.percentile(dq, 97.5))))
    t = pd.DataFrame(rows); t.to_csv(OUT / "final_summary.csv", index=False); print(t.round(3).T.to_string())
    r = t[t.run == CFG["primary_run"]].iloc[0]; s = CFG["success"]
    ok = bool(r.delta_balanced_accuracy >= s["min_delta_balanced_accuracy"] and r.delta_balacc_lo > 0)
    json.dump(dict(primary_run=r.run, arm=r.arm, delta_balanced_accuracy=r.delta_balanced_accuracy, ci=[r.delta_balacc_lo, r.delta_balacc_hi], success=ok), open(OUT / "final_decision.json", "w"), indent=1)
    print("PRIMARY ENDPOINT", "MET" if ok else "NOT MET")


def verify():
    b = json.load(open(OUT / "protected_before.json")); bad = [k for k, v in b.items() if not (ROOT / k).exists() or sha(ROOT / k) != v]
    print(f"{len(b)} protected files checked, {len(bad)} changed", bad[:10]); sys.exit(1 if bad else 0)


{"preflight": preflight, "fit": fit, "dev": dev, "test": test, "summary": summary, "verify": verify}[args.stage]()
