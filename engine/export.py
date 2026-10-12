"""Export every rule as a row the Bureau can rerun: plain-language statement, source quote, and a SQL query
that counts violations by region on the Bureau's own tables.

    python engine/export.py rules/*.json --out out/rules_export.csv
"""
import argparse
import json
import warnings

import pandas as pd

warnings.filterwarnings("ignore")

TABLE_SQL = {"subject": "d002_subject", "ocenka": "d002_ocenka", "hh": "d002_subject JOIN d002_ocenka USING (NOMER)",
             "rio": "d006_rio", "kontr_k": "d008_kontr_k", "kv0": "d004_kv_vopr0", "kv1": "d004_kv_vopr1",
             "kv11": "d004_kv_vopr11", "kv12": "d004_kv_vopr12"}


def lit(v):
    return f"'{v}'" if isinstance(v, str) else str(int(v) if float(v).is_integer() else v)


def cond_sql(c):
    if c is None:
        return "TRUE"
    if "all" in c:
        return "(" + " AND ".join(cond_sql(x) for x in c["all"]) + ")"
    if "any" in c:
        return "(" + " OR ".join(cond_sql(x) for x in c["any"]) + ")"
    col = c["col"]
    if c.get("blank"):
        return f"{col} IS NULL"
    if c.get("filled"):
        return f"{col} IS NOT NULL"
    if "lt" in c:
        return f"CAST({col} AS INT) < {c['lt']}"
    if "ge" in c:
        return f"CAST({col} AS INT) >= {c['ge']}"
    return f"CAST({col} AS INT) IN ({', '.join(lit(v) for v in c['in'])})"


def cond_text(c):
    if c is None:
        return "always"
    if "all" in c:
        return " and ".join(cond_text(x) for x in c["all"])
    if "any" in c:
        return " or ".join(cond_text(x) for x in c["any"])
    if c.get("blank"):
        return f"{c['col']} is blank"
    if c.get("filled"):
        return f"{c['col']} is filled"
    if "lt" in c:
        return f"{c['col']} < {c['lt']}"
    if "ge" in c:
        return f"{c['col']} ≥ {c['ge']}"
    return f"{c['col']} in {c['in']}"


def violation_sql(r, col):
    """WHERE clause that selects violating records for one column of a rule."""
    t, a = r["type"], r.get("allowed")
    if t == "domain":
        if isinstance(a, dict) and "min" in a:
            return f"{col} IS NOT NULL AND (CAST({col} AS NUMERIC) < {a['min']} OR CAST({col} AS NUMERIC) > {a['max']})"
        if isinstance(a, dict) and a.get("no_leading_zero"):
            return f"{col} LIKE '0_%'"
        if isinstance(a, dict) and a.get("equals_column"):
            return f"{col} <> {a['equals_column']}"
        if isinstance(a, dict) and a.get("codebook"):
            return f"{col} NOT IN (SELECT kodnu FROM codebook_{col.lower()})"
        if isinstance(a, dict):
            return None
        if all(isinstance(v, (int, float)) for v in a):
            return f"{col} IS NOT NULL AND CAST({col} AS INT) NOT IN ({', '.join(lit(v) for v in a)})"
        return f"{col} IS NOT NULL AND {col} NOT IN ({', '.join(lit(str(v)) for v in a)})"
    if t == "skip":
        return f"{cond_sql(r['when'])} AND {col} IS NOT NULL"
    if t == "required":
        if r.get("mode") == "any":
            return f"{cond_sql(r.get('when'))} AND " + " AND ".join(f"{c} IS NULL" for c in r["targets"])
        return f"{cond_sql(r.get('when'))} AND {col} IS NULL"
    if t == "multi_select":
        return f"{col} IS NOT NULL AND {col} <> '1'"
    if t == "consistency" and r.get("check") == "implies":
        return f"{cond_sql(r['if'])} AND NOT {cond_sql(r['then'])}"
    if t == "consistency" and r.get("check") == "lte":
        return f"CAST({r['a']} AS NUMERIC) > CAST({r['b']} AS NUMERIC)"
    return None


def statement(r):
    t = r["type"]
    cols = ", ".join(r["targets"][:4]) + (f" … ({len(r['targets'])} columns)" if len(r["targets"]) > 4 else "")
    a = r.get("allowed")
    if t == "domain":
        if isinstance(a, list):
            return f"{cols} may only hold {a}"
        if isinstance(a, dict) and "min" in a:
            return f"{cols} between {a['min']} and {a['max']}"
        if a.get("codebook"):
            return f"{cols} must be a code from {a['codebook'].split('/')[-1]}"
        if a.get("equals_column"):
            return f"{cols} must equal the quarter of the folder"
        if a.get("equals_year"):
            return f"{cols} must equal the survey year"
        if a.get("no_leading_zero"):
            return f"{cols} written without a leading zero"
        return f"{cols}: {json.dumps(a, ensure_ascii=False)}"
    if t == "skip":
        return f"If {cond_text(r['when'])}, {cols} must be blank"
    if t == "required":
        what = "at least one of " if r.get("mode") == "any" else ""
        return f"If {cond_text(r.get('when'))}, {what}{cols} must be filled"
    if t == "multi_select":
        return f"{cols} are tick boxes (1 or blank)" + (f"; {r['exclusive']} cannot be ticked with others" if r.get("exclusive") else "")
    if t == "consistency" and r.get("check") == "implies" and r["if"].get("col") == "ROSTER_U18":
        has = r["if"]["in"] == [1]
        return (f"If the household {'has a' if has else 'has no'} member under 18 in the D-008 roster (same NOMER), "
                f"then {cond_text(r['then'])}")
    if t == "consistency" and r.get("check") == "implies":
        return f"If {cond_text(r['if'])}, then {cond_text(r['then'])}"
    return r.get("note", r["id"])


def main(paths, out):
    rows = []
    for p in paths:
        spec = json.load(open(p, encoding="utf-8"))
        for r in spec["rules"]:
            if r.get("superseded_by"):  # replaced after review; kept in the rule file only for the accuracy score
                continue
            tab = TABLE_SQL.get(r.get("table"), r.get("table"))
            sql = None
            if r["type"] not in ("doc_issue", "cross_form"):
                col = r["targets"][0]
                where = violation_sql(r, col)
                if where:
                    sql = f"SELECT TE, COUNT(*) AS violations FROM {tab} WHERE {where} GROUP BY TE ORDER BY violations DESC;"
            if r.get("sql"):   # rules that link to another form carry their own query (:year = survey year)
                sql = r["sql"]
            rows.append({"form": spec["form"], "rule_id": r["id"], "type": r["type"], "table": r.get("table"),
                         "columns": ", ".join(r["targets"]), "rule": statement(r),
                         "source": r["source"].get("doc"), "quote": r["source"].get("quote"),
                         "confidence": r.get("confidence"), "note": r.get("note", ""),
                         "added_after_review": bool(r.get("added_after_review")),
                         "sql_first_column": sql})
    df = pd.DataFrame(rows)
    df.to_csv(out, index=False)
    print(df.groupby(["form", "type"]).size().to_string())
    print("total", len(df), "with SQL", df["sql_first_column"].notna().sum())


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("rules", nargs="+")
    ap.add_argument("--out", default="out/rules_export.csv")
    a = ap.parse_args()
    main(a.rules, a.out)
