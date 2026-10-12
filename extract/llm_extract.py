"""Questionnaire → rules with the Claude API, for a form or year not yet covered.

The rule files in rules/ (v1) were written by Claude in a working session from the same prompt
(prompts/extract_rules_v1.md) and the same inputs this script sends. This script makes that step
repeatable by the Bureau: point it at a form's documentation and the data's column list, get a rule file
back, then score it against a reference set with gold/score.py before using it.

    pip install anthropic pypdf python-docx
    export ANTHROPIC_API_KEY=...
    python extract/llm_extract.py --form D002 --docs documentation/d002/2024 \
        --columns DATA_DIR/d002/2024/subject.csv DATA_DIR/d002/2024/ocenka.csv --out rules/d002_new.json

Without an API key (for example with a Claude Pro or Team chat):

    python extract/llm_extract.py ... --prompt-only prompt.txt      # paste prompt.txt into a new Claude chat
    python extract/llm_extract.py ... --from-reply reply.txt        # save the chat's answer as reply.txt

Nothing here sends survey records: only the blank forms, the instruction and the column names.
"""
import argparse
import json
import subprocess
from pathlib import Path

PROMPTS = Path(__file__).resolve().parents[1] / "prompts"
RULE_TYPES = {"domain", "required", "skip", "multi_select", "consistency", "cross_form", "doc_issue"}


def doc_text(path):
    p = Path(path)
    if p.suffix.lower() == ".pdf":
        return subprocess.run(["pdftotext", "-layout", str(p), "-"], capture_output=True, text=True).stdout
    if p.suffix.lower() == ".docx":
        import docx
        d = docx.Document(str(p))
        parts = [para.text for para in d.paragraphs]
        for t in d.tables:
            for row in t.rows:
                parts.append(" | ".join(dict.fromkeys(c.text.strip() for c in row.cells)))
        return "\n".join(parts)
    if p.suffix.lower() == ".doc":
        out = p.with_suffix(".txt")
        subprocess.run(["soffice", "--headless", "--convert-to", "txt:Text (encoded):UTF8", "--outdir",
                        str(p.parent), str(p)], capture_output=True)
        return out.read_text(encoding="utf-8", errors="replace")
    if p.suffix.lower() in (".xls", ".xlsx"):
        import pandas as pd
        return "\n".join(f"{a} | {b}" for a, b in pd.read_excel(p, header=None).dropna(how="all").fillna("").values[:, :2])
    return p.read_text(encoding="utf-8", errors="replace")


def columns_of(csvs):
    out = {}
    for c in csvs:
        with open(c, encoding="utf-8", errors="replace") as f:
            out[Path(c).stem] = f.readline().strip().split(",")
    return out


def validate(spec, cols):
    known = {c.upper() for cs in cols.values() for c in cs}
    problems = []
    for r in spec.get("rules", []):
        if r.get("type") not in RULE_TYPES:
            problems.append(f"{r.get('id')}: unknown type {r.get('type')}")
        if not r.get("source", {}).get("quote"):
            problems.append(f"{r.get('id')}: no source quote")
        for c in r.get("targets", []):
            if r.get("type") != "doc_issue" and c.upper() not in known:
                problems.append(f"{r.get('id')}: column {c} not in the data")
    return problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--form", required=True)
    ap.add_argument("--docs", required=True, help="folder with the form, instruction and structure files")
    ap.add_argument("--columns", nargs="+", required=True, help="data files whose header lists the columns")
    ap.add_argument("--out", required=True)
    ap.add_argument("--model", default="claude-opus-5-5")
    ap.add_argument("--prompt", default="v2", help="prompt version in prompts/ (v1 made the scored D-002 rules)")
    ap.add_argument("--prompt-only", help="write the full prompt to this file (to paste into a Claude chat) and stop")
    ap.add_argument("--from-reply", help="read the model's answer from this file instead of calling the API")
    a = ap.parse_args()

    docs = "\n\n".join(f"=== {p.name} ===\n{doc_text(p)}" for p in sorted(Path(a.docs).rglob("*")) if p.is_file()
                       and p.suffix.lower() in (".pdf", ".doc", ".docx", ".xls", ".xlsx", ".txt")
                       and not (p.suffix.lower() == ".txt" and p.with_suffix(".doc").exists()))
    cols = columns_of(a.columns)
    user = (f"Form: {a.form}\n\nData columns by table:\n{json.dumps(cols, ensure_ascii=False)}\n\n"
            f"Documentation:\n{docs}\n\nReturn only the JSON object.")
    system = (PROMPTS / f"extract_rules_{a.prompt}.md").read_text(encoding="utf-8")
    if a.prompt_only:
        Path(a.prompt_only).write_text(system + "\n\n---\n\n" + user, encoding="utf-8")
        print(f"prompt written to {a.prompt_only} ({len(system) + len(user):,} characters)")
        return
    if a.from_reply:
        text, how = Path(a.from_reply).read_text(encoding="utf-8"), "a Claude chat (reply pasted from file)"
    else:
        import anthropic
        msg = anthropic.Anthropic().messages.create(model=a.model, max_tokens=32000, system=system,
                                                    messages=[{"role": "user", "content": user}])
        text, how = "".join(b.text for b in msg.content if b.type == "text"), f"{a.model} via the API"
    spec = json.loads(text[text.find("{"): text.rfind("}") + 1])
    spec["extracted_by"] = f"{how}, extract/llm_extract.py, prompt {a.prompt}"
    problems = validate(spec, cols)
    Path(a.out).write_text(json.dumps(spec, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(spec.get('rules', []))} rules written to {a.out}")
    for p in problems:
        print("check:", p)


if __name__ == "__main__":
    main()
