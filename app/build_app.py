"""Build the StatQUO web app: one self-contained HTML page (works offline, nothing leaves the computer).

    python app/build_app.py            # from the package root; writes app/StatQUO_app.html and docs/app/index.html

Inputs: rules/*.json (the rule files), console/data.json (Russian rule texts, SQL, regions, case files and every
section of the former console), app/engine.js (the check engine, a port of engine/statquo.py),
app/analysis_extra.js (the console's analysis sections: child poverty, finances, rules, new form, decoder,
trust, data) and app/app.html (the page).

The console itself (console/StatQUO_console.html) is kept as an archive copy at docs/console/; the site root
(docs/index.html) now sends visitors to the app."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "app"

rules = {f: json.load(open(ROOT / "rules" / f"{f.lower()}_2023-2024.json", encoding="utf-8"))["rules"]
         for f in ("D002", "D006", "D008")}
d = json.load(open(ROOT / "console" / "data.json", encoding="utf-8"))

# Case C1: lead with Ulytau 2024 (the case shown in the talk); the other impact lines keep their order.
ci = d.get("caseImpact", {})
if "C1" in ci:
    ci["C1"] = sorted(ci["C1"], key=lambda x: 0 if "Улытау" in x[1] else 1)

txt = {r["id"]: {"ru": r["ru"], "quote": r["quote"], "doc": r["doc"], "sql": r["sql"], "type": r["type"], "form": r["form"]}
       for r in d["rules"] if r["form"] in rules}
bundle = {
    "rules": rules,
    "txt": txt,
    "regions": d["regions"],
    "cases": d["cases"],
    "caseImpact": ci,
    "issues": d["issues"],
    "ruleCount": sum(d["ruleCounts"].values()),
    "sqlCount": sum(1 for r in d["rules"] if r["sql"]),
    "acc": d["acc"].get("ALL", {}),
    # field labels for the form built from the rules: the Bureau's file-structure description and column order
    "cols": {f: {c["c"]: [c["d"] or "", i] for i, c in enumerate(d["schema"]["columns"]) if c["f"] == f}
             for f in rules},
}
js = lambda o: json.dumps(o, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
engine = (APP / "engine.js").read_text(encoding="utf-8").replace("</", "<\\/")
extra = (APP / "analysis_extra.js").read_text(encoding="utf-8").replace("/*CONSOLE*/null", js(d))
page = (APP / "app.html").read_text(encoding="utf-8")
# the model step: the extraction prompt (same as extract/llm_extract.py) and the saved run of 10 Oct 2026 (D-002 2022)
prompt_txt = (ROOT / "demo" / "prompt_d002_2022_v2.txt").read_text(encoding="utf-8")
cols_line = prompt_txt.split("Data columns by table:\n", 1)[1].split("\n", 1)[0]
aicfg = {
    "prompt": (ROOT / "prompts" / "extract_rules_v2.md").read_text(encoding="utf-8"),
    "saved": {"form": "D002", "year": 2022, "when": "10.10.2026", "seconds": 105,
              "columns": json.loads(cols_line),
              "docs": [l[4:-4] for l in prompt_txt.splitlines() if l.startswith("=== ") and l.endswith(" ===")],
              "reply": (ROOT / "demo" / "reply_d002_2022_v2.txt").read_text(encoding="utf-8")},
}
ai = (APP / "ai_stage.js").read_text(encoding="utf-8").replace("/*AICFG*/null", js(aicfg)).replace("</", "<\\/")
page = page.replace("/*ENGINE*/", engine).replace("/*EXTRA*/", extra).replace("/*DATA*/null", js(bundle)).replace("/*AI*/", ai)
out = APP / "StatQUO_app.html"
out.write_text(page, encoding="utf-8")

docs = ROOT / "docs"
(docs / "app").mkdir(parents=True, exist_ok=True)
(docs / "app" / "index.html").write_text(page, encoding="utf-8")
console = ROOT / "console" / "StatQUO_console.html"
if console.exists():
    (docs / "console").mkdir(parents=True, exist_ok=True)
    (docs / "console" / "index.html").write_text(console.read_text(encoding="utf-8"), encoding="utf-8")
(docs / "index.html").write_text("""<!doctype html>
<html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>StatQUO</title><meta http-equiv="refresh" content="0; url=app/">
<style>body{font:16px/1.5 'IBM Plex Sans','Segoe UI',Arial,sans-serif;background:#f6f7f9;color:#18202b;margin:0;padding:40px 16px}
@media (prefers-color-scheme: dark){body{background:#12161c;color:#e8ecf1}a{color:#9cc0f5}}</style>
<p>Приложение StatQUO: <a href="app/">открыть</a>.</p></html>
""", encoding="utf-8")
print("written", out, len(page), "bytes;", sum(len(v) for v in rules.values()), "rules in the page")
