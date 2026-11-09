"""Confirm nothing original changed. Compares the HARMONISE-1 and HARMONISE-2 hash lists; only the reports listed below may differ,
because the final report was updated on request (the old version is in final_reports/archive/) and its siblings were re-rendered."""
import hashlib, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
ALLOWED = {"final_reports/final_fyp3_report.md", "final_reports/experiment_audit.md", "final_reports/cross_dataset_audit.md", "final_reports/quantization_deployment.md"}
sha = lambda p: hashlib.sha256(open(p, "rb").read()).hexdigest(); bad = []; seen = 0; noted = set()
for f in ["next_experiment/outputs/protected_before.json", "next_experiment/harmonise2/outputs/protected_before.json"]:
    b = json.load(open(ROOT / f))
    for k, v in b.items():
        seen += 1
        if not (ROOT / k).exists() or sha(ROOT / k) != v:
            noted.add(k) if k in ALLOWED else bad.append(k)
print(f"{seen} hash entries checked; unexpected changes: {len(bad)} {bad[:8]}; expected report updates: {sorted(noted)}")
newer = [p for p in (ROOT.parent / "FYP2").rglob("*") if p.is_file() and p.name != ".DS_Store" and p.stat().st_mtime > (ROOT / "CLAUDE_PREPARATION_COMPLETE.txt").stat().st_mtime]
print("FYP2 files changed since preparation began:", len(newer)); sys.exit(1 if bad or newer else 0)
