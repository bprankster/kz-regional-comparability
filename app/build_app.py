"""Build the StatQUO web app: one self-contained HTML page (works offline, nothing leaves the computer).

    python app/build_app.py            # from the package root; writes app/StatQUO_app.html and docs/app/index.html

Inputs: rules/*.json (the rule files), console/data.json (Russian rule texts, SQL, regions, case files),
app/engine.js (the check engine, a port of engine/statquo.py) and app/app.html (the page)."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "app"

rules = {f: json.load(open(ROOT / "rules" / f"{f.lower()}_2023-2024.json", encoding="utf-8"))["rules"]
         for f in ("D002", "D006", "D008")}
d = json.load(open(ROOT / "console" / "data.json", encoding="utf-8"))
txt = {r["id"]: {"ru": r["ru"], "quote": r["quote"], "doc": r["doc"], "sql": r["sql"], "type": r["type"], "form": r["form"]}
       for r in d["rules"] if r["form"] in rules}
bundle = {
    "rules": rules,
    "txt": txt,
    "regions": d["regions"],
    "cases": d["cases"],
    "caseImpact": d.get("caseImpact", {}),
    "issues": d["issues"],
    "ruleCount": sum(d["ruleCounts"].values()),
    "sqlCount": sum(1 for r in d["rules"] if r["sql"]),
    "acc": d["acc"].get("ALL", {}),
}
data = json.dumps(bundle, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
engine = (APP / "engine.js").read_text(encoding="utf-8").replace("</", "<\\/")
page = (APP / "app.html").read_text(encoding="utf-8")
page = page.replace("/*ENGINE*/", engine).replace("/*DATA*/null", data)
out = APP / "StatQUO_app.html"
out.write_text(page, encoding="utf-8")
docs = ROOT / "docs" / "app"
docs.mkdir(parents=True, exist_ok=True)
(docs / "index.html").write_text(page, encoding="utf-8")
print("written", out, len(page), "bytes;", sum(len(v) for v in rules.values()), "rules in the page")
