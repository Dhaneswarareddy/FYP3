"""HARMONISE-2 driver: reliability of the frozen HARMONISE-1 calibration, on development tiles only.

Run stages in the order given in ANTIGRAVITY_RELIABILITY_HANDOFF.md. TensorFlow stages always run on CPU (the Mac GPU
driver hangs on 448 px networks) and take one --run each, so memory is released between models. No stage trains a
network, reads the external test split, or writes outside harmonise2/. --smoke runs on a few tiles into outputs_smoke/.
"""
import argparse, json, sys, time
import numpy as np, pandas as pd
from PIL import Image
import h2_lib as L
from h2_lib import CFG, H, H1, HERE, ROOT

ap = argparse.ArgumentParser()
ap.add_argument("--stage", required=True); ap.add_argument("--run"); ap.add_argument("--smoke", action="store_true")
args = ap.parse_args()
OUT = HERE / ("outputs_smoke" if args.smoke else "outputs"); (OUT / "preds").mkdir(parents=True, exist_ok=True); (OUT / "figures").mkdir(exist_ok=True)
SEED = CFG["seed"]; K_PX = CFG["pools"]["pixels_per_tile"]
SM = args.smoke; N_BOOT = 3 if SM else CFG["A"]["n_bootstrap"]; N_EVAL = 2 if SM else CFG["A"]["n_eval_param_sets"]


def tf_cpu():
    import tensorflow as tf
    tf.config.set_visible_devices([], "GPU")


def write_json(name, obj):
    json.dump(obj, open(OUT / name, "w"), indent=1, default=float)


def rindex():
    return pd.read_csv(OUT / "R_index.csv")


def arrays(info):
    """Memory-mapped development tiles at the network's baseline input size."""
    return np.load(OUT / "cache" / f"R_{info['input_size']}.npy", mmap_mode="r")


def predict_arr(model, arr, idx, g_h=1.0, g_d=1.0, chunk=32):
    out = []
    for k in range(0, len(idx), chunk):
        x = np.asarray(arr[np.sort(idx[k:k + chunk])], np.uint8)
        x = np.stack([H.apply_stain_gains(t, g_h, g_d) for t in x]) if (g_h, g_d) != (1.0, 1.0) else x.astype(np.float32)
        out.append(model.predict(x, batch_size=chunk, verbose=0))
    return np.concatenate(out)


def save_pred(sub, name, idx, prob):
    (OUT / "preds" / sub).mkdir(exist_ok=True); np.savez_compressed(OUT / "preds" / sub / f"{name}.npz", idx=idx, prob=prob.astype(np.float32))


def load_pred(sub, name):
    z = np.load(OUT / "preds" / sub / f"{name}.npz"); return z["idx"], z["prob"]


# ------------------------------------------------------------------ setup
def preflight():
    rep = {}; params, arm = L.frozen(); rep["frozen_arm"] = arm; rep["frozen_sha_ok"] = True
    p = OUT / "protected_before.json"
    if not p.exists():
        json.dump({str(f.relative_to(ROOT)): L.sha(f) for f in L.protected_files()}, open(p, "w"), indent=0)
    rep["n_protected"] = len(json.load(open(p)))
    d, fit, sel, rest = L.h1_pools(); rep.update(n_h1_fit=len(fit), n_h1_selection=len(sel), n_reliability=len(rest), pools_disjoint=len(set(fit) | set(sel) | set(rest)) == len(d.names))
    rep["test_guard_active"] = "external_test_dir" not in H.P
    rep["genuine_wsi_ids_available"] = False
    rep["go"] = bool(rep["pools_disjoint"] and rep["n_reliability"] == 4593 and arm["name"] == "stain_p99" and rep["test_guard_active"])
    write_json("preflight.json", rep); print(json.dumps(rep, indent=1, default=float)); sys.exit(0 if rep["go"] else 2)


def regress():
    """Gate: the frozen code path must reproduce HARMONISE-1's stored development metrics before anything else runs."""
    tf_cpu(); params, arm = L.frozen(); d, fit, sel, rest = L.h1_pools(); sel = sel[:64] if SM else sel
    pils = [d.read(n) for n in sel]; y = np.array([H.label_from_name(n) for n in sel]); info = H.run_info(H.CFG["primary_run"])
    stored = pd.read_csv(H1 / "dev_results.csv").set_index("arm"); rep = {}
    for a in [dict(name="none", scale=1.0, g_h=1.0, g_d=1.0), arm]:
        m = H.metrics(y, H.predict(H.build(info, 1.0), pils, info, a)); rep[a["name"]] = dict(balanced_accuracy=m["balanced_accuracy"], stored=float(stored.loc[a["name"], "balanced_accuracy"]))
    rep["ok"] = bool(SM or all(abs(rep[k]["balanced_accuracy"] - rep[k]["stored"]) < 1e-3 for k in ("none", arm["name"])))
    write_json("regression.json", rep); print(json.dumps(rep, indent=1, default=float)); sys.exit(0 if rep["ok"] else 2)


def cache():
    """Tile arrays for the reliability pool, and per-tile stain pixels for the fit pool and BCI train. Runs once."""
    (OUT / "cache").mkdir(exist_ok=True); d, fit, sel, rest = L.h1_pools(); rng = np.random.default_rng(SEED)
    blocks = L.index_blocks(d.names, CFG["pools"]["index_block_gap"])
    pool = (fit[:20] + sel[:20]) if SM else fit + sel
    rest = rest[:64] if SM else rest
    y = np.array([H.label_from_name(n) for n in rest]); df = pd.DataFrame(dict(name=rest, label=y, block=[blocks[n] for n in rest]))
    df["subset"] = L.split_blocks(df, CFG["pools"]["r_cal_fraction"], SEED); df.to_csv(OUT / "R_index.csv", index=False)
    a224 = np.lib.format.open_memmap(OUT / "cache/R_224.npy", "w+", np.uint8, (len(rest), 224, 224, 3)); a448 = np.lib.format.open_memmap(OUT / "cache/R_448.npy", "w+", np.uint8, (len(rest), 448, 448, 3))
    info = lambda s, z: dict(input_size=z, source_size=s); none = dict(name="none", scale=1.0, g_h=1.0, g_d=1.0); t0 = time.time()
    for i, n in enumerate(rest):
        im = d.read(n); a224[i] = H.prepare(im, info(256, 224), none); a448[i] = H.prepare(im, info(512, 448), none)
        if i % 500 == 0:
            print("reliability tiles", i, len(rest), f"{time.time()-t0:.0f}s", flush=True)
    a224.flush(); a448.flush()

    def px(rgb):
        h, a = H.stain_od(rgb); i = rng.integers(0, len(h), K_PX); return h[i].astype(np.float32), a[i].astype(np.float32)
    E = {k: [] for k in ("h256", "d256", "h448", "d448")}
    for i, n in enumerate(pool):
        im = d.read(n); r = np.asarray(im.resize((256, 256), Image.LANCZOS), np.uint8); h, a = px(r); E["h256"].append(h); E["d256"].append(a)
        h, a = px(H.prepare(im, info(512, 448), none).astype(np.uint8)); E["h448"].append(h); E["d448"].append(a)
        if i % 500 == 0:
            print("fit-pool tiles", i, len(pool), f"{time.time()-t0:.0f}s", flush=True)
    m = pd.read_csv(H.P["bci_manifest"]); tr = m[m.split == "train"].path.values; tr = tr[:40] if SM else tr; B = {k: [] for k in E}
    for p in tr:
        im = Image.open(H.P["bci_cache_256"] / p).convert("RGB"); h, a = px(np.asarray(im, np.uint8)); B["h256"].append(h); B["d256"].append(a)
        im = Image.open(ROOT / "data/ihc_512" / p).convert("RGB").resize((448, 448), Image.BILINEAR); h, a = px(np.asarray(im, np.uint8)); B["h448"].append(h); B["d448"].append(a)
    np.savez(OUT / "cache/stain_pixels.npz", **{f"ext_{k}": np.stack(v) for k, v in E.items()}, **{f"bci_{k}": np.stack(v) for k, v in B.items()}, pool_labels=np.array([H.label_from_name(n) for n in pool]),
             pool_blocks=np.array([blocks[n] for n in pool]), n_h1_fit=np.array(20 if SM else len(fit)))
    print("cache done", f"{time.time()-t0:.0f}s")


def pixels():
    return np.load(OUT / "cache/stain_pixels.npz")


def gains(eh, ed, bh, bd, p, p_h=95):
    """The HARMONISE-1 rule: BCI percentile / external percentile, H at p95, DAB at p, same clipping."""
    lo, hi = H.CFG["stain_fit"]["gain_limits"]
    return float(np.clip(np.percentile(bh, p_h) / np.percentile(eh, p_h), lo, hi)), float(np.clip(np.percentile(bd, p) / np.percentile(ed, p), lo, hi))


# ------------------------------------------------------------------ A: calibration stability
def a_params():
    """Parameter variation only (no CNN): tile resampling, sample size, grid edge and class composition."""
    z = pixels(); eh, ed, bh, bd = z["ext_h256"], z["ext_d256"], z["bci_h256"], z["bci_d256"]; rng = np.random.default_rng(SEED); rows = []
    sizes = [20, 40] if SM else CFG["A"]["sizes"]
    for n in sizes:
        for mode in ("external_only", "bci_only", "both"):
            for k in range(N_BOOT):
                ie = rng.integers(0, len(eh), n) if mode != "bci_only" else np.arange(len(eh)); ib = rng.integers(0, len(bh), n) if mode != "external_only" else np.arange(len(bh))
                ps = CFG["A"]["percentiles"]; lo, hi = H.CFG["stain_fit"]["gain_limits"]
                gh = float(np.clip(np.percentile(bh[ib].ravel(), 95) / np.percentile(eh[ie].ravel(), 95), lo, hi))
                gd = np.clip(np.percentile(bd[ib].ravel(), ps) / np.percentile(ed[ie].ravel(), ps), lo, hi)        # same rule as gains(), one sort per draw
                rows += [dict(n=n, mode=mode, k=k, percentile=p, g_h=gh, g_d=float(v)) for p, v in zip(ps, gd)]
    t = pd.DataFrame(rows); t.to_csv(OUT / "A_params_bootstrap.csv", index=False)
    s = t.groupby(["n", "mode", "percentile"]).agg(g_h_mean=("g_h", "mean"), g_h_sd=("g_h", "std"), g_d_mean=("g_d", "mean"), g_d_sd=("g_d", "std"), g_d_lo=("g_d", lambda v: v.quantile(.025)), g_d_hi=("g_d", lambda v: v.quantile(.975))).reset_index()
    s["g_h_cv"], s["g_d_cv"] = s.g_h_sd / s.g_h_mean, s.g_d_sd / s.g_d_mean; s.to_csv(OUT / "A_params_summary.csv", index=False)
    params, arm = L.frozen(); top = max(sizes); b = t[(t.n == top) & (t["mode"] == "both") & (t.percentile == 99)].sort_values("g_d").reset_index(drop=True)
    q = ((np.arange(N_EVAL) + .5) / N_EVAL * len(b)).astype(int); sets = [dict(id=f"boot{i}", g_h=float(b.g_h[j]), g_d=float(b.g_d[j])) for i, j in enumerate(q)]
    he, de, hb, db = eh.ravel(), ed.ravel(), bh.ravel(), bd.ravel()
    edge = [dict(id=f"edge_p{p:g}", percentile=p, **dict(zip(("g_h", "g_d"), gains(he, de, hb, db, p)))) for p in CFG["A"]["edge_percentiles"]]
    y, comp = z["pool_labels"], []; n = min(top, len(y))
    for share in CFG["A"]["composition_3plus_share"]:
        i3, io = np.where(y == 3)[0], np.where(y != 3)[0]; k3 = int(round(share * n)); j = np.r_[rng.choice(i3, k3, k3 > len(i3)), rng.choice(io, n - k3, n - k3 > len(io))]
        comp.append(dict(id=f"share3plus_{share:g}", share_3plus=share, **dict(zip(("g_h", "g_d"), gains(eh[j].ravel(), ed[j].ravel(), hb, db, 99)))))
    write_json("A_eval_params.json", dict(frozen=arm, bootstrap=sets, edge=edge, composition=comp)); print(s[(s.n == top) & (s["mode"] == "both")].round(3).to_string(index=False)); print(pd.DataFrame(comp).round(3).to_string(index=False))


def a_eval():
    """Performance across calibration samples. Evaluated on R_eval, which no calibration sample ever contains."""
    tf_cpu(); r = rindex(); idx = np.where(r.subset == "R_eval")[0]; y = r.label.values[idx]; ps = json.load(open(OUT / "A_eval_params.json")); info = H.run_info(args.run)
    model = H.build(info, 1.0); arr = arrays(info); rows = []
    for fam in ("bootstrap", "edge", "composition"):
        for s in ps[fam]:
            prob = predict_arr(model, arr, idx, s["g_h"], s["g_d"]); save_pred("A", f"{args.run}__{s['id']}", idx, prob)
            rows.append(dict(run=args.run, family=fam, id=s["id"], g_h=s["g_h"], g_d=s["g_d"], **L.scores(y, prob))); print(rows[-1]["id"], round(rows[-1]["balanced_accuracy"], 3), flush=True)
    pd.DataFrame(rows).to_csv(OUT / f"A_eval_{args.run}.csv", index=False)


def a_report():
    t = pd.concat(pd.read_csv(f) for f in OUT.glob("A_eval_*.csv")); s = pd.read_csv(OUT / "A_params_summary.csv"); top = s.n.max(); c = CFG["A"]; rows = []
    for run, g in t[t.family == "bootstrap"].groupby("run"):
        rows.append(dict(run=run, **{f"{m}_{f}": getattr(g[m], f)() for m in ("balanced_accuracy", "qwk") for f in ("mean", "min", "max")}, **{f"recall_{k}_range": g[f"recall_{k}"].max() - g[f"recall_{k}"].min() for k in ("0", "1+", "2+", "3+")}, balacc_range=g.balanced_accuracy.max() - g.balanced_accuracy.min()))
    v = pd.DataFrame(rows); p = s[(s.n == top) & (s["mode"] == "both") & (s.percentile == 99)].iloc[0]
    v["params_stable"] = bool(p.g_d_cv <= c["stable_cv_max"] and p.g_h_cv <= c["stable_cv_max"]); v["performance_stable"] = (v.balacc_range <= c["stable_balacc_range_max"]) & (v["recall_2+_range"] <= c["stable_recall_range_max"]) & (v["recall_3+_range"] <= c["stable_recall_range_max"])
    v.to_csv(OUT / "A_verdict.csv", index=False)
    mins = s[(s["mode"] == "both") & (s.percentile == 99) & (s.g_d_cv <= c["stable_cv_max"]) & (s.g_h_cv <= c["stable_cv_max"])]; write_json("A_verdict.json", dict(g_d_cv_at_top=p.g_d_cv, g_h_cv_at_top=p.g_h_cv, smallest_stable_n=int(mins.n.min()) if len(mins) else None)); print(v.round(3).T.to_string())


# ------------------------------------------------------------------ B: WSI-level generalisation
def b_audit():
    """Writes why slide-level analysis is impossible, then tests whether index blocks carry any source structure."""
    r = rindex(); arr = arrays(dict(input_size=224)); rows = []
    for i in range(len(r)):
        od = -np.log(np.maximum(np.asarray(arr[i], np.float32) / 255.0, 1e-3)); rows.append((od.mean(), od[..., 2].mean() - od[..., 0].mean(), np.percentile(od, 95)))
    f = pd.DataFrame(rows, columns=["od_mean", "blue_minus_red_od", "od_p95"]); f["block"], f["label"] = r.block.values, r.label.values
    icc = {}
    keep = f.groupby("block").block.transform("size") >= (3 if SM else CFG["B"]["min_tiles_per_block"])
    for c in ["od_mean", "blue_minus_red_od", "od_p95"]:
        g = f[keep].copy(); g[c] -= g.groupby("label")[c].transform("mean")                      # remove class differences
        n = g.groupby("block").size(); k = (len(g) - (n**2).sum() / len(g)) / max(len(n) - 1, 1); msb = (n * (g.groupby("block")[c].mean() - g[c].mean())**2).sum() / max(len(n) - 1, 1); msw = ((g[c] - g.groupby("block")[c].transform("mean"))**2).sum() / max(len(g) - len(n), 1)
        icc[c] = float((msb - msw) / (msb + (k - 1) * msw)) if msb + (k - 1) * msw else 0.0
    rep = dict(genuine_wsi_ids=False, evidence=["archives hold PNG tiles only, no CSV or metadata", "filenames are her2-<score>-score_<split>_<number>.png, numbered per score", "the Zenodo record and the authors' repository give no patch-to-slide mapping", "the WSI/ and ROI/ folders named in the record are not in the local archives"],
               only_genuine_wsi_boundary="86 development WSIs vs 21 test WSIs, already used once by HARMONISE-1", per_slide_analysis_possible=False, index_block_icc=icc, n_index_blocks=int(r.block.nunique()), surrogate_allowed=bool(np.median(list(icc.values())) >= CFG["B"]["min_icc"]))
    write_json("B_wsi_audit.json", rep); print(json.dumps(rep, indent=1, default=float))


def b_surrogate():
    """Optional sensitivity analysis on index blocks: NOT slide-level. Skipped unless b_audit found block structure."""
    rep = json.load(open(OUT / "B_wsi_audit.json"))
    if not (rep["surrogate_allowed"] or SM):
        print("Index blocks carry too little structure: surrogate skipped, as pre-set."); write_json("pseudogroup_status.json", dict(run=False, reason="median ICC below threshold")); return
    tf_cpu(); r = rindex(); z = pixels(); bl = z["pool_blocks"]; run = H.CFG["primary_run"]; info = H.run_info(run); model = H.build(info, 1.0); arr = arrays(info); rng = np.random.default_rng(SEED)
    ub = np.unique(r.block.values); folds = dict(zip(ub[rng.permutation(len(ub))], np.arange(len(ub)) % CFG["B"]["n_folds"])); F = r.block.map(folds).values; rows = []; P = np.zeros((len(r), 4), np.float32)
    for k in range(CFG["B"]["n_folds"]):
        hold = {b for b, v in folds.items() if v == k}; tr = ~np.isin(bl, list(hold)); gh, gd = gains(z["ext_h256"][tr].ravel(), z["ext_d256"][tr].ravel(), z["bci_h256"].ravel(), z["bci_d256"].ravel(), 99)
        idx = np.where(F == k)[0]
        if not len(idx):
            continue
        P[idx] = predict_arr(model, arr, idx, gh, gd); rows.append(dict(fold=k, n_fit_tiles=int(tr.sum()), n_eval_tiles=len(idx), g_h=gh, g_d=gd, **L.scores(r.label.values[idx], P[idx])))
    pd.DataFrame(rows).to_csv(OUT / "pseudogroup_folds.csv", index=False)
    d = pd.DataFrame(dict(block=r.block, label=r.label, ok=P.argmax(1) == r.label.values)); b = d.groupby("block").agg(n=("ok", "size"), label=("label", "first"), accuracy=("ok", "mean")).reset_index(); b[b.n >= (1 if SM else CFG["B"]["min_tiles_per_block"])].to_csv(OUT / "pseudogroup_blocks.csv", index=False)
    write_json("pseudogroup_status.json", dict(run=True, warning="Index blocks are unverified filename groupings. They are not slides, ROIs or patients. Do not report them as such."))


# ------------------------------------------------------------------ C: class-wise reliability
def c_predict():
    """none and frozen stain_p99 on all reliability tiles. These stored probabilities also feed D and E."""
    tf_cpu(); r = rindex(); idx = np.arange(len(r)); info = H.run_info(args.run); model = H.build(info, 1.0); arr = arrays(info); _, arm = L.frozen()
    for nm, gh, gd in [("none", 1.0, 1.0), ("frozen", arm["g_h"], arm["g_d"])]:
        t0 = time.time(); save_pred("C", f"{args.run}__{nm}", idx, predict_arr(model, arr, idx, gh, gd)); print(args.run, nm, f"{time.time()-t0:.0f}s", flush=True)


def c_report():
    r = rindex(); y = r.label.values; rng = np.random.default_rng(SEED); rows = []; flags = []; conf = {}; ub = r.block.unique(); byb = {b: np.where(r.block.values == b)[0] for b in ub}; B = 20 if SM else CFG["C"]["bootstrap"]; c = CFG["C"]
    for run in CFG["panel"]:
        got = {}
        for nm in ("none", "frozen"):
            _, p = load_pred("C", f"{run}__{nm}"); m = L.scores(y, p); got[nm] = m; a = p.argmax(1); conf[f"{run}__{nm}"] = L.class_table(y, a)[0].tolist(); boot = {k: [] for k in ("recall_2+", "recall_3+", "precision_2+", "precision_3+", "balanced_accuracy")}
            for _ in range(B):
                i = np.concatenate([byb[b] for b in rng.choice(ub, len(ub))])
                if len(np.unique(y[i])) == 4:
                    s = L.scores(y[i], p[i])
                    for k in boot:
                        boot[k].append(s[k])
            rows.append(dict(run=run, arm=nm, **m, **{f"{k}_lo": np.percentile(v, 2.5) for k, v in boot.items()}, **{f"{k}_hi": np.percentile(v, 97.5) for k, v in boot.items()}))
        for k in ("0", "1+", "2+", "3+"):
            n, f = got["none"], got["frozen"]; d = f[f"recall_{k}"] - n[f"recall_{k}"]
            flags.append(dict(run=run, cls=k, recall_none=n[f"recall_{k}"], recall_frozen=f[f"recall_{k}"], delta_recall=d, f1_frozen=f[f"f1_{k}"], deteriorated=d <= -c["recall_drop_flag"], class_failure=f[f"recall_{k}"] < c["failure_recall_below"] or f[f"f1_{k}"] < c["failure_f1_below"], qwk_gain=f["qwk"] - n["qwk"], hidden=(f["qwk"] > n["qwk"]) and (d <= -c["recall_drop_flag"] or f[f"recall_{k}"] < c["failure_recall_below"])))
    pd.DataFrame(rows).to_csv(OUT / "C_classwise.csv", index=False); pd.DataFrame(flags).to_csv(OUT / "C_flags.csv", index=False); write_json("C_confusions.json", conf); print(pd.DataFrame(flags).round(3).to_string(index=False))


# ------------------------------------------------------------------ D: resolution compatibility
def d_params():
    """Gains re-estimated at the 448 px network's own resolution, on the HARMONISE-1 fit tiles only."""
    z = pixels(); n = int(z["n_h1_fit"]); out = {}
    for res in ("256", "448"):
        out[res] = dict(zip(("g_h", "g_d"), gains(z[f"ext_h{res}"][:n].ravel(), z[f"ext_d{res}"][:n].ravel(), z[f"bci_h{res}"].ravel(), z[f"bci_d{res}"].ravel(), 99)))
    write_json("D_gains_by_resolution.json", out); print(out)


def d_subset():
    r = rindex(); e = np.where(r.subset == "R_eval")[0]; n = 32 if SM else CFG["D"]["n_tiles"]; return np.sort(np.random.default_rng(SEED).choice(e, min(n, len(e)), replace=False))


def d_arms(run):
    _, arm = L.frozen(); g = json.load(open(OUT / "D_gains_by_resolution.json")); gh, gd = arm["g_h"], arm["g_d"]; a = [("none", 1.0, 1.0, 1.0), ("frozen", 1.0, gh, gd), ("dab_only", 1.0, 1.0, gd), ("haem_only", 1.0, gh, 1.0)]
    a += [(f"dose_h{h:g}_d{d:g}", 1.0, h, d) for h, d in CFG["D"]["dose"] if (h, d) != (1.0, 1.0)]
    if "hires" in run:
        c = g["448"]; a += [("rescompat", 1.0, c["g_h"], c["g_d"]), ("rescompat_dab_only", 1.0, 1.0, c["g_d"]), ("frozen_scale2", 2.0, gh, gd), ("rescompat_scale2", 2.0, c["g_h"], c["g_d"])]
    return a


def d_predict():
    tf_cpu(); r = rindex(); idx = d_subset(); y = r.label.values[idx]; info = H.run_info(args.run); rows = []; nets = {}
    for nm, s, gh, gd in d_arms(args.run):
        nets.setdefault(s, H.build(info, s))
        if s == 1.0:
            p = predict_arr(nets[s], arrays(info), idx, gh, gd)
        else:
            assert H.target_size(info["input_size"], s) == 224, "scale arms reuse the 224 px cache"; p = predict_arr(nets[s], arrays(dict(input_size=224)), idx, gh, gd)
        rows.append(dict(domain="external_dev", run=args.run, arm=nm, scale=s, g_h=gh, g_d=gd, **L.scores(y, p))); print(nm, round(rows[-1]["balanced_accuracy"], 3), round(rows[-1]["recall_3+"], 3), flush=True)
    pd.DataFrame(rows).to_csv(OUT / f"D_external_{args.run}.csv", index=False)


def d_bci():
    """Same gains on BCI validation tiles: does the 448 px network react more strongly to stain in its own domain?"""
    tf_cpu(); info = H.run_info(args.run); m = pd.read_csv(H.P["bci_manifest"]); m = m[m.split == "val"].reset_index(drop=True); m = m.iloc[:32] if SM else m; d = ROOT / "data" / (f"ihc_{info['source_size']}_eval{info['input_size']}" if info["input_size"] != 224 else "ihc_256")
    z = info["input_size"]; x = np.stack([np.asarray(Image.open(d / p).convert("RGB").resize((z, z), Image.BILINEAR), np.uint8) for p in m.path]); y = m.label.values.astype(int); model = H.build(info, 1.0); rows = []
    for nm, s, gh, gd in d_arms(args.run):
        if s != 1.0 or nm.startswith("rescompat"):
            continue
        rows.append(dict(domain="bci_val", run=args.run, arm=nm, g_h=gh, g_d=gd, **L.scores(y, predict_arr(model, x, np.arange(len(x)), gh, gd)))); print(nm, round(rows[-1]["balanced_accuracy"], 3), flush=True)
    pd.DataFrame(rows).to_csv(OUT / f"D_bci_{args.run}.csv", index=False)


def d_report():
    t = pd.concat(pd.read_csv(f) for f in OUT.glob("D_external_*.csv")); h = t[t.run.str.contains("hires")].set_index("arm"); c = CFG["D"]; b = h.loc["none"]
    v = []
    for arm in ("frozen", "rescompat", "rescompat_dab_only", "frozen_scale2", "rescompat_scale2"):
        r = h.loc[arm]; v.append(dict(arm=arm, g_h=r.g_h, g_d=r.g_d, balanced_accuracy=r.balanced_accuracy, delta_vs_none=r.balanced_accuracy - b.balanced_accuracy, recall_3plus=r["recall_3+"], delta_recall_3plus=r["recall_3+"] - b["recall_3+"], meets_rule=bool(r.balanced_accuracy - b.balanced_accuracy >= c["success_min_gain_balacc"] and r["recall_3+"] - b["recall_3+"] >= -c["success_max_3plus_recall_drop"])))
    pd.DataFrame(v).to_csv(OUT / "D_verdict.csv", index=False); print(pd.DataFrame(v).round(3).to_string(index=False))


# ------------------------------------------------------------------ E: prediction confidence
def e_report():
    """ECE, reliability curves, temperature scaling and review flagging. Thresholds and T come from R_cal; R_eval reports."""
    from sklearn.metrics import roc_auc_score
    r = rindex(); cal, ev = np.where(r.subset == "R_cal")[0], np.where(r.subset == "R_eval")[0]; y = r.label.values; b = CFG["E"]["bins"]; rows, sel, curves = [], [], []

    def temp(p, T):
        q = np.exp(np.log(np.maximum(p, 1e-9)) / T); return q / q.sum(1, keepdims=True)

    def nll(p, t):
        return -np.log(np.maximum(p[np.arange(len(t)), t], 1e-9)).mean()
    for run in CFG["panel"]:
        z = np.load(ROOT / "results/runs" / run / "predictions.npz"); pv, yv = z["val"], z["y_val"].astype(int); e, _ = L.ece(yv, pv, b); rows.append(dict(run=run, arm="bci_val_reference", T=1.0, ece=e, nll=nll(pv, yv), accuracy=float((pv.argmax(1) == yv).mean()), mean_confidence=float(pv.max(1).mean())))
        for nm in ("none", "frozen"):
            _, p = load_pred("C", f"{run}__{nm}"); grid = np.geomspace(.2, 20, 60); T = float(grid[np.argmin([nll(temp(p[cal], t), y[cal]) for t in grid])])
            for lab, q, tt in [(nm, p, 1.0), (nm + "_temp_scaled", temp(p, T), T)]:
                e, c = L.ece(y[ev], q[ev], b); rows.append(dict(run=run, arm=lab, T=tt, ece=e, nll=nll(q[ev], y[ev]), accuracy=float((q[ev].argmax(1) == y[ev]).mean()), mean_confidence=float(q[ev].max(1).mean()))); curves.append(c.assign(run=run, arm=lab))
            s = np.sort(p, 1); u = dict(max_prob=p.max(1), margin=s[:, -1] - s[:, -2], neg_entropy=(p * np.log(np.maximum(p, 1e-9))).sum(1)); wrong = p.argmax(1)[ev] != y[ev]
            for sig, v in u.items():
                auc = roc_auc_score(wrong, -v[ev]) if 0 < wrong.mean() < 1 else np.nan
                for cov in CFG["E"]["coverages"]:
                    th = np.quantile(v[cal], 1 - cov); k = v[ev] >= th; kept = L.scores(y[ev][k], p[ev][k]) if k.sum() and len(np.unique(y[ev][k])) > 1 else {}
                    sel.append(dict(run=run, arm=nm, signal=sig, target_coverage=cov, threshold=float(th), coverage=float(k.mean()), accuracy_all=1 - float(wrong.mean()), accuracy_kept=kept.get("accuracy"), error_auroc=float(auc), share_2plus_referred=float((~k[y[ev] == 2]).mean()) if (y[ev] == 2).any() else np.nan, recall_2plus_kept=kept.get("recall_2+"), recall_3plus_kept=kept.get("recall_3+")))
    t = pd.DataFrame(rows); t.to_csv(OUT / "E_calibration.csv", index=False); s = pd.DataFrame(sel); s["accuracy_gain"] = s.accuracy_kept - s.accuracy_all; s["usable"] = (s.coverage >= CFG["E"]["usable_min_coverage"] - .02) & (s.accuracy_gain >= CFG["E"]["usable_min_accuracy_gain"]); s.to_csv(OUT / "E_flagging.csv", index=False); pd.concat(curves).to_csv(OUT / "E_reliability_curves.csv", index=False)
    fl = []                                                                                   # do tiles that flip across calibration samples fail more often?
    for run in CFG["A"]["eval_runs"]:
        fs = sorted((OUT / "preds/A").glob(f"{run}__boot*.npz"))
        if len(fs) > 1:
            P = np.stack([np.load(f)["prob"].argmax(1) for f in fs]); i = np.load(fs[0])["idx"]; flip = (P != P[0]).any(0); w = P[0] != y[i]; fl.append(dict(run=run, flip_rate=float(flip.mean()), error_if_flipped=float(w[flip].mean()) if flip.any() else np.nan, error_if_stable=float(w[~flip].mean()) if (~flip).any() else np.nan))
    pd.DataFrame(fl).to_csv(OUT / "E_calibration_flips.csv", index=False); print(t.round(3).to_string(index=False)); print(s[(s.arm == "frozen") & (s.signal == "max_prob")].round(3).to_string(index=False))


# ------------------------------------------------------------------ results and integrity
def figures():
    import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
    INK2, GRID, A, B = "#52514e", "#e4e3df", "#2a78d6", "#eb6834"; F = OUT / "figures"
    def st(ax, g="y"):
        [ax.spines[s].set_visible(False) for s in ("top", "right")]; ax.grid(axis=g, color=GRID, lw=.8); ax.set_axisbelow(True)
    s = pd.read_csv(OUT / "A_params_summary.csv"); d = s[(s["mode"] == "both") & (s.n == s.n.max())]; fig, ax = plt.subplots(figsize=(6.4, 3.2)); ax.errorbar(d.percentile.astype(str), d.g_d_mean, yerr=[d.g_d_mean - d.g_d_lo, d.g_d_hi - d.g_d_mean], fmt="o-", color=A, lw=1.8, ms=5); ax.set_xlabel("Percentile matched"); ax.set_ylabel("DAB gain"); ax.set_title("DAB gain depends strongly on the percentile", loc="left", fontweight="bold", fontsize=10); st(ax); fig.tight_layout(); fig.savefig(F / "A_gain_vs_percentile.png", dpi=150); plt.close(fig)
    c = pd.read_csv(OUT / "C_classwise.csv"); K = ["0", "1+", "2+", "3+"]; fig, axes = plt.subplots(1, len(CFG["panel"]), figsize=(13, 2.9), sharey=True, squeeze=False)
    for ax, run in zip(axes[0], CFG["panel"]):
        for o, arm, col in [(-.18, "none", B), (.18, "frozen", A)]:
            ax.bar(np.arange(4) + o, c[(c.run == run) & (c.arm == arm)].iloc[0][[f"recall_{k}" for k in K]].astype(float), .34, color=col, label=arm)
        ax.set_xticks(range(4), K); ax.set_title(run.replace("__", " "), loc="left", fontsize=8, fontweight="bold"); st(ax)
    axes[0][0].set_ylabel("Recall"); axes[0][0].legend(frameon=False, fontsize=8); fig.tight_layout(); fig.savefig(F / "C_recall_by_class.png", dpi=150); plt.close(fig)
    t = pd.concat(pd.read_csv(f) for f in OUT.glob("D_external_*.csv")); t = t[t.arm.str.startswith("dose_h1_") | (t.arm == "none")]; t = t.assign(g=t.g_d).sort_values("g"); fig, ax = plt.subplots(1, 2, figsize=(9, 3))
    for run, col in [(H.CFG["primary_run"], A), ("EfficientNetV2B0__ce__hires", B)]:
        q = t[t.run == run]
        ax[0].plot(q.g_d, q["recall_3+"], "o-", color=col, label=run.replace("__ce", "").replace("__", " ")); ax[1].plot(q.g_d, q.mean_expected_score, "o-", color=col)
    ax[0].set_xlabel("DAB gain"); ax[0].set_ylabel("Recall 3+"); ax[1].set_xlabel("DAB gain"); ax[1].set_ylabel("Mean predicted score"); ax[0].legend(frameon=False, fontsize=8); st(ax[0]); st(ax[1]); fig.tight_layout(); fig.savefig(F / "D_dose_response.png", dpi=150); plt.close(fig)
    r = pd.read_csv(OUT / "E_reliability_curves.csv"); fig, axes = plt.subplots(1, len(CFG["panel"]), figsize=(13, 2.9), sharey=True, squeeze=False)
    for ax, run in zip(axes[0], CFG["panel"]):
        q = r[(r.run == run) & (r.arm == "frozen") & (r.n > 0)]; ax.plot([0, 1], [0, 1], color=GRID); ax.plot(q.confidence, q.accuracy, "o-", color=A, ms=3); ax.set_title(run.replace("__", " "), loc="left", fontsize=8, fontweight="bold"); ax.set_xlabel("Confidence"); st(ax)
    axes[0][0].set_ylabel("Accuracy"); fig.tight_layout(); fig.savefig(F / "E_reliability_diagrams.png", dpi=150); plt.close(fig)


def report():
    figures(); s = pd.read_csv(OUT / "A_params_summary.csv"); top = s.n.max(); C = pd.read_csv(OUT / "C_classwise.csv"); Fl = pd.read_csv(OUT / "C_flags.csv"); V = pd.read_csv(OUT / "A_verdict.csv"); Dv = pd.read_csv(OUT / "D_verdict.csv"); E = pd.read_csv(OUT / "E_calibration.csv"); Es = pd.read_csv(OUT / "E_flagging.csv"); B = json.load(open(OUT / "B_wsi_audit.json")); Av = json.load(open(OUT / "A_verdict.json")); ae = pd.concat(pd.read_csv(f) for f in OUT.glob("A_eval_*.csv"))
    K = ["0", "1+", "2+", "3+"]; cc = C[["run", "arm", "accuracy", "balanced_accuracy", "macro_f1", "qwk", "off_by_2plus"] + [f"recall_{k}" for k in K] + [f"precision_{k}" for k in K]]
    L_ = ["# HARMONISE-2 reliability results", "", "Generated by `run_h2.py --stage report`. Development tiles only. The external test split was not read. Tiles share the 86 development slides with HARMONISE-1's fit and selection tiles, and index blocks are not slides.", "",
          "## A. Calibration stability", "", f"Gains at p99, n = {top}: CV g_d {Av['g_d_cv_at_top']:.3f}, CV g_h {Av['g_h_cv_at_top']:.3f}. Smallest sample meeting the CV limit: {Av['smallest_stable_n']}.", "", L.md(s[(s["mode"] == "both") & (s.percentile == 99)][["n", "g_h_mean", "g_h_cv", "g_d_mean", "g_d_cv", "g_d_lo", "g_d_hi"]]), "", L.md(V), "", "Grid edge and class composition:", "", L.md(ae[ae.family != "bootstrap"][["run", "id", "g_h", "g_d", "balanced_accuracy", "qwk", "recall_0", "recall_1+", "recall_2+", "recall_3+"]]), "", "![](figures/A_gain_vs_percentile.png)", "",
          "## B. WSI-level generalisation", "", "**Not possible as specified: no genuine slide identifiers exist.**", "", *[f"- {x}" for x in B["evidence"]], f"- Only genuine boundary: {B['only_genuine_wsi_boundary']}.", "", f"Index-block ICC (class removed): {B['index_block_icc']}. Surrogate allowed: {B['surrogate_allowed']}.", "",
          "## C. Class-wise reliability", "", L.md(cc), "", "Flags:", "", L.md(Fl), "", "![](figures/C_recall_by_class.png)", "", "## D. Resolution compatibility", "", L.md(Dv), "", "![](figures/D_dose_response.png)", "", "## E. Prediction confidence", "", L.md(E), "", L.md(Es[(Es.arm == "frozen") & (Es.signal == "max_prob")][["run", "target_coverage", "coverage", "accuracy_all", "accuracy_kept", "accuracy_gain", "error_auroc", "share_2plus_referred", "usable"]]), "", "![](figures/E_reliability_diagrams.png)", ""]
    (OUT / "RELIABILITY_RESULTS.md").write_text("\n".join(L_)); print("wrote", OUT / "RELIABILITY_RESULTS.md")


def verify():
    b = json.load(open(OUT / "protected_before.json")); bad = [k for k, v in b.items() if not (ROOT / k).exists() or L.sha(ROOT / k) != v]; print(f"{len(b)} protected files checked, {len(bad)} changed", bad[:10]); sys.exit(1 if bad else 0)


STAGES = dict(preflight=preflight, regress=regress, cache=cache, a_params=a_params, a_eval=a_eval, a_report=a_report, b_audit=b_audit, b_surrogate=b_surrogate, c_predict=c_predict, c_report=c_report, d_params=d_params, d_predict=d_predict, d_bci=d_bci, d_report=d_report, e_report=e_report, report=report, verify=verify)
STAGES[args.stage]()
