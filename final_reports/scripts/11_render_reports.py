"""Insert the generated tables into the report templates."""
import json; from pathlib import Path
R = Path(__file__).resolve().parents[1]; T = json.load(open(R/"tables/md_tables.json"))
for t in (R/"templates").glob("*.md"):
    s = t.read_text()
    for k, v in T.items(): s = s.replace("{{%s}}" % k, v)
    assert "{{" not in s, t; (R/t.name).write_text(s); print("wrote", t.name, len(s))
