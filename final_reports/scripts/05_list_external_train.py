"""Read the name lists of the HER2-IHC-40x archives without extracting anything."""
import zipfile, re, collections, json
from pathlib import Path
D = Path.home()/"Downloads"; OUT = Path(__file__).resolve().parents[1]/"tables"
out = {}
def names(outer, inner):
    z = zipfile.ZipFile(D/outer); i = zipfile.ZipFile(z.open(inner)); return [n for n in i.namelist() if n.endswith(".png")], z.getinfo(inner).compress_type
for outer, kind in [("her2-ihc-40x-wsi.zip", "WSI-based-dataset/%s_data_wsi.zip"), ("her2-ihc-40x-patch.zip", "Patch-based-dataset/%s_data_patch.zip")]:
    for sp in ["train", "test"]:
        n, ct = names(outer, kind % sp); out[f"{outer}:{sp}"] = n
        c = collections.Counter(x.split("/")[-2] for x in n); t = collections.Counter(re.search(r"score_(train|test)_", x).group(1) for x in n)
        mis = sum(x.split("/")[-2].replace("class_", "") != re.search(r"her2-(.+?)-score", x).group(1) for x in n)
        print(outer, sp, len(n), dict(sorted(c.items())), dict(t), "folder!=filename", mis, "compress", ct, "e.g.", n[0])
tr = {x.split("/")[-1] for x in out["her2-ihc-40x-wsi.zip:train"]}; te = {x.split("/")[-1] for x in out["her2-ihc-40x-wsi.zip:test"]}
ptr = {x.split("/")[-1] for x in out["her2-ihc-40x-patch.zip:train"]}; pte = {x.split("/")[-1] for x in out["her2-ihc-40x-patch.zip:test"]}
print("WSI train/test shared names:", len(tr & te), "| patch test names in WSI train:", len(pte & tr), "| patch train in WSI test:", len(ptr & te))
json.dump({"wsi_train_test_shared_names": len(tr & te), "patch_test_in_wsi_train": len(pte & tr), "patch_train_in_wsi_test": len(ptr & te)}, open(OUT/"external_archive_name_checks.json", "w"), indent=1)
