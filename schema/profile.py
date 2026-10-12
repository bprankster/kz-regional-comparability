"""Data model of the survey files: tables, keys, columns, and how the tables link.

Reads the records and the organisers' structure files; writes three tables that the diagrams
(schema/draw.py) and DATA_MODEL.md are built from. Every number on the diagrams comes from here.

    python schema/profile.py --data DATA_DIR --out out/

out/schema_tables.csv   one row per table and year: grain, key, rows, columns, key unique, link to the roster
out/schema_columns.csv  one row per column: type, length and description from the structure file,
                        inferred kind, share filled, distinct values, the rules that use it
out/schema_links.csv    one row per link and year: how many records find their partner, and whether
                        region, sex, person number agree
"""
import argparse
import json
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
import statquo as S  # noqa: E402

YEARS = (2021, 2022, 2023, 2024)
D004_TABLES = ["kv_vopr0", "kv_vopr1", "kv_vopr2", "kv_vopr3", "kv_vopr4", "kv_vopr5", "kv_vopr6",
               "kv_vopr7", "kv_vopr9", "kv_vopr10", "kv_vopr11", "kv_vopr12"]

# form, table, grain, key (as documented / as used by the engine), role
TABLES = [
    ("D008", "kontr_k", "person", ["NOMER", "NOMP"], "household roster: every member of every sampled household"),
    ("D002", "subject", "household", ["NOMER"], "quality of life, part 1 (one respondent per household)"),
    ("D002", "ocenka", "household", ["NOMER"], "quality of life, parts 2-4 (same respondent)"),
    ("D006", "rio", "household", ["NOMER"], "main interview: dwelling, amenities, assets"),
    ("D004", "kv_vopr0", "household x quarter", ["NOMER", "KVARTAL"], "quarterly journal: visit result"),
] + [("D004", t, "household x quarter x item", ["NOMER", "KVARTAL", "KODNU"], "quarterly journal: spending lines")
     for t in D004_TABLES[1:]] + [
    ("T001", "baza", "person (respondent)", [], "labour force survey: no household or person number in the release"),
]


def path_of(form, table, year):
    if form == "D006":
        return S.D006_FILES[year]
    if form == "T001":
        return f"t001/{year}/2021.csv" if year == 2021 else f"t001/{year}/baza.csv"
    return f"{form.lower()}/{year}/{table}.csv"


_CACHE = {}


def read_table(D, form, table, year):
    """Read one table for one year (D-004: the four quarter folders stacked). Cached: links reuse the reads."""
    k = (form, table, year)
    if k not in _CACHE:
        _CACHE[k] = _read_table(D, form, table, year)
    return _CACHE[k]


def _read_table(D, form, table, year):
    if form == "T001":   # 470k rows: plain read, no whitespace strip (not needed for counting)
        p = Path(D, path_of(form, table, year))
        if not p.exists():
            return None
        d = pd.read_csv(p, dtype=str, encoding_errors="replace")
        d.columns = [c.strip().upper() for c in d.columns]
        return d
    if form == "D004":
        parts = []
        for q in (1, 2, 3, 4):
            p = Path(D, f"d004/{year}/{q}kv/{table}.csv")
            if p.exists():   # plain read: 1M+ rows, the whitespace strip is not needed for counting
                d = pd.read_csv(p, dtype=str, encoding_errors="replace")
                d.columns = [c.strip().upper() for c in d.columns]
                d["KVARTAL"] = d["KVARTAL"] if "KVARTAL" in d else str(q)
                parts.append(d)
        return pd.concat(parts, ignore_index=True) if parts else None
    p = Path(D, path_of(form, table, year))
    return S.read(D, path_of(form, table, year)) if p.exists() else None


# ---------- descriptions from the organisers' structure files ----------

def doc_to_text(p):
    with tempfile.TemporaryDirectory() as tmp:
        try:
            subprocess.run(["soffice", "--headless", "--convert-to", "txt:Text (encoded):UTF8", "--outdir", tmp, str(p)],
                           check=True, capture_output=True, timeout=120)
            return next(Path(tmp).glob("*.txt")).read_text(encoding="utf-8-sig", errors="replace")
        except Exception:
            return ""


def norm(c):
    return re.sub(r"[^A-Z0-9_]", "", c.upper().replace(".", "_"))


def descriptions(D):
    """{(form, table or None): {COLUMN: (type, length, description)}} — best effort, per file layout."""
    doc = Path(D, "documentation")
    out = {}
    # D-002: spreadsheet, two columns, table names as section headers
    import time; t0 = time.time()
    x = pd.read_excel(doc / "d002/2024/Структура файлов_D002_2024.xls", header=None, dtype=str)
    table = None
    for a, b in zip(x[0], x[1]):
        a = (a or "").strip() if isinstance(a, str) else ""
        b = b.strip() if isinstance(b, str) else ""
        if a.lower() in ("subject", "ocenka") and not b:
            table = a.lower()
        elif a and b and table:
            out.setdefault(("D002", table), {})[norm(a)] = ("", "", b)
    # D-004: one block per kv_vopr table: "n  NAME  Character  len  description"
    t = doc_to_text(next(doc.glob("d004/2024/*1kv*/*/Структура D004.doc")))
    table = None
    for line in t.splitlines():
        m = re.match(r"\s*(Kv_vopr\d+)", line, re.I)
        if m:
            table = m.group(1).lower()
            continue
        m = re.match(r"\s*\d+\s+(\w+)\s+(Character|Numeric)\s+(\d+)\s+(.*)", line)
        if m and table:
            out.setdefault(("D004", table), {})[norm(m.group(1))] = (m.group(2), m.group(3), m.group(4).strip())
    # D-008: "n. Name Type len description"
    t = doc_to_text(Path(doc, "d008/2024/D008_2024/Структура D008.doc"))
    for line in t.splitlines():
        m = re.match(r"\s*\d+\.\s+(\w+)\s+(Character|Numeric)\s+(\d+)\s+(.*)", line)
        if m:
            out.setdefault(("D008", "kontr_k"), {})[norm(m.group(1))] = (m.group(2), m.group(3), m.group(4).strip())
    # T-001: "NAME  текстовый (n)  вопрос ..."
    t = doc_to_text(Path(doc, "t001/2024/СТРУКТУРА_2022-2024гг.doc"))
    for line in t.splitlines():
        m = re.match(r"\s*(\w+)\s+тек.товый\s*\((\d+)\)\s*(.*)", line)
        if m:
            out.setdefault(("T001", "baza"), {})[norm(m.group(1))] = ("text", m.group(2), m.group(3).strip())
    # D-006: narrative; field names follow "поле"/"поля" next to the question, often as ranges (U1-U42)
    t = doc_to_text(Path(doc, "d006/2024/D006_deid/структураД006.doc"))
    d6 = out.setdefault(("D006", "rio"), {})
    for line in t.splitlines():
        mq = re.search(r"(?:В вопросе|Вопрос)\s+([\d.]+)", line)
        if not mq:
            continue
        label = re.sub(r"\s+", " ", line.strip())[:110]
        tail = re.split(r"пол[еяи]", line, maxsplit=1)
        if len(tail) < 2:
            continue
        tail = tail[1]
        for m in re.finditer(r"([A-Za-z_]+?)\s*(\d+)\s*-\s*(?:\1)?\s*(\d+)", tail, re.I):
            for i in range(int(m.group(2)), int(m.group(3)) + 1):
                d6.setdefault(norm(f"{m.group(1)}{i}"), ("", "", label))
        for name in re.findall(r"\b([A-Za-z][A-Za-z_]*\d*)\b", tail):
            d6.setdefault(norm(name), ("", "", label))
    print(f"structure files read in {time.time() - t0:.0f}s", flush=True)
    return out


# ---------- columns used by the rules ----------

def rule_columns(rules_dir):
    use = {}
    for f in sorted(Path(rules_dir).glob("*.json")):
        spec = json.load(open(f))
        form = spec["form"].replace("-", "").upper()
        for r in spec["rules"]:
            if r.get("superseded_by"):
                continue
            cols = set(r.get("targets", []))
            for k in ("when", "if", "then", "this", "lower", "upper_not"):
                cols |= set(re.findall(r'"col": "(\w+)"', json.dumps(r.get(k))))
            for k in ("a", "b", "key"):
                if isinstance(r.get(k), str):
                    cols.add(r[k])
            t = r.get("table", "both")
            t = re.sub(r"^kv(\d+)$", r"kv_vopr\1", t)
            for c in cols:
                use.setdefault((form, t if t not in ("both", "hh") else "*", c.upper()), []).append(r["id"])
    return use


def kind(s):
    f = s.dropna()
    f = f[f.astype(str).str.strip() != ""]
    if f.empty:
        return "empty"
    v = pd.to_numeric(f, errors="coerce")
    if v.notna().mean() < 0.95:
        return "text"
    whole = (v.dropna() % 1 == 0).all()
    nun = f.nunique()
    if whole and nun <= 40:
        return "code"
    if whole:
        return "integer"
    return "number"


# ---------- links ----------

def links(D):
    rows = []
    for y in YEARS:
        ros = read_table(D, "D008", "kontr_k", y)
        hh = ros.drop_duplicates("NOMER")[["NOMER", "TE", "K"]]
        sub, oc = read_table(D, "D002", "subject", y), read_table(D, "D002", "ocenka", y)
        rio, kv0 = read_table(D, "D006", "rio", y), read_table(D, "D004", "kv_vopr0", y)

        def to_roster(name, d):
            m = d[["NOMER", "TE", "K"]].drop_duplicates("NOMER").merge(hh, on="NOMER", how="left", suffixes=("", "_r"))
            found = m["TE_r"].notna()
            rows.append({"year": y, "link": f"{name} -> D008.kontr_k", "key": "NOMER", "level": "household",
                         "records": len(m), "found": int(found.sum()), "found_pct": round(100 * found.mean(), 1),
                         "region_agrees_pct": round(100 * (m.TE == m.TE_r)[found].mean(), 1),
                         "settlement_type_agrees_pct": round(100 * (m.K == m.K_r)[found].mean(), 1)})
        to_roster("D002.subject", sub)
        to_roster("D006.rio", rio)
        to_roster("D004.kv_vopr0", kv0)

        # D-002 respondent is a roster member
        m = sub[["NOMER", "NOMP", "POL"]].merge(ros[["NOMER", "NOMP", "POL"]], on=["NOMER", "NOMP"], how="left", suffixes=("", "_r"))
        found = m["POL_r"].notna()
        rows.append({"year": y, "link": "D002.subject respondent -> D008.kontr_k person", "key": "NOMER+NOMP",
                     "level": "person", "records": len(m), "found": int(found.sum()), "found_pct": round(100 * found.mean(), 1),
                     "sex_agrees_pct": round(100 * (m.POL == m.POL_r)[found].mean(), 1)})

        # subject and ocenka: two halves of one questionnaire, one respondent
        m = sub[["NOMER", "NOMP", "POL", "VOZ"]].merge(oc[["NOMER", "NOMP", "POL", "VOZ"]], on="NOMER", how="outer",
                                                      suffixes=("_s", "_o"), indicator=True)
        both = m["_merge"] == "both"
        cols = ["NOMP", "POL"] + (["VOZ"] if y != 2021 else [])   # 2021 age is not tied to the person (data guide)
        differ = np.zeros(len(m), bool)
        for c in cols:
            differ |= (m[c + "_s"] != m[c + "_o"]).values
        rows.append({"year": y, "link": "D002.subject <-> D002.ocenka", "key": "NOMER", "level": "household (1:1)",
                     "records": int(both.sum()), "found": int(both.sum()),
                     "found_pct": round(100 * both.sum() / len(m), 1),
                     "respondent_differs": int((differ & both.values).sum()),
                     "compared": "+".join(cols)})

        # D-004 line items -> the visit record of the same household and quarter
        for t in ("kv_vopr1", "kv_vopr12"):
            d = read_table(D, "D004", t, y)
            k = d[["NOMER", "KVARTAL"]].merge(kv0[["NOMER", "KVARTAL"]].drop_duplicates(), how="left", indicator=True)
            ok = k["_merge"] == "both"
            rows.append({"year": y, "link": f"D004.{t} -> D004.kv_vopr0", "key": "NOMER+KVARTAL",
                         "level": "household x quarter", "records": len(d), "found": int(ok.sum()),
                         "found_pct": round(100 * ok.mean(), 1)})

        # do answers that should agree across forms agree household by household? (synthetic: links broken)
        if "GOD_ROJD" in ros and "GR40" in oc:
            kids = (y - S.num(ros["GOD_ROJD"]) < 18).groupby(ros["NOMER"]).any().rename("roster_child")
            m = oc[["NOMER", "GR40"]].merge(kids, left_on="NOMER", right_index=True)
            yes = S.num(m.GR40) == 1
            rows.append({"year": y, "link": "D002.ocenka GR40 'has children' vs D008 member under 18", "key": "NOMER",
                         "level": "household, answer vs answer", "records": len(m),
                         "p_yes_if_child_pct": round(100 * yes[m.roster_child].mean(), 1),
                         "p_yes_if_no_child_pct": round(100 * yes[~m.roster_child].mean(), 1)})
        own = "VLAD1" if "VLAD1" in rio else "VLAD"
        if "GR31_1" not in oc:
            continue
        m = oc[["NOMER", "GR31_1"]].merge(rio[["NOMER", own]], on="NOMER")
        na = S.num(m.GR31_1) == 4
        owner = S.num(m[own]).isin([1, 2])
        rows.append({"year": y, "link": "D002.ocenka GR31_1 'rent: not relevant' vs D006 owner (VLAD1 1-2)", "key": "NOMER",
                     "level": "household, answer vs answer", "records": len(m),
                     "p_yes_if_child_pct": round(100 * na[owner].mean(), 1),
                     "p_yes_if_no_child_pct": round(100 * na[~owner].mean(), 1)})
    out = pd.DataFrame(rows)
    return out.rename(columns={"p_yes_if_child_pct": "share_if_condition_pct",
                               "p_yes_if_no_child_pct": "share_if_not_condition_pct"})


def household_children_check(D):
    """The D-002 child filter (GR40) against the D-008 roster, household by household, per region.

    The region-level check (D002-x-D008-children) compares two shares; joined on NOMER, the same
    question becomes: which households have a member under 18 in the roster but are coded 'no children'
    (missed), and which have none but are coded 'has children' (false yes)."""
    rows = []
    for y in YEARS:
        ros, oc = read_table(D, "D008", "kontr_k", y), read_table(D, "D002", "ocenka", y)
        if "GOD_ROJD" not in ros or "GR40" not in oc:
            continue
        kid = (y - S.num(ros["GOD_ROJD"]) < 18).groupby(ros["NOMER"]).any().rename("kid")
        m = oc[["NOMER", "TE", "GR40"]].merge(kid, left_on="NOMER", right_index=True)
        yes = S.num(m["GR40"]) == 1
        for te, g in m.groupby("TE"):
            k, y_ = g["kid"], yes[g.index]
            rows.append({"year": y, "te": te, "region": S.REGION.get(te, te), "households": len(g),
                         "with_child_in_roster": int(k.sum()), "coded_no_children": int((k & ~y_).sum()),
                         "missed_pct": round(100 * (k & ~y_).sum() / max(k.sum(), 1), 1),
                         "without_child_in_roster": int((~k).sum()), "coded_has_children": int((~k & y_).sum()),
                         "false_yes_pct": round(100 * (~k & y_).sum() / max((~k).sum(), 1), 1)})
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", default="out")
    ap.add_argument("--only", choices=("all", "tables", "links"), default="all",
                    help="run one half (tables + columns, or links), e.g. to keep each run short")
    ap.add_argument("--rules", default=str(Path(__file__).resolve().parents[1] / "rules"))
    a = ap.parse_args()
    D, out = a.data, Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    if a.only in ("all", "tables"):
        desc = descriptions(D)
        used = rule_columns(a.rules)
        roster_ids = {y: set(read_table(D, "D008", "kontr_k", y)["NOMER"]) for y in YEARS}
        t0 = time.time()

        man = pd.read_csv(Path(D, "MANIFEST.csv"))
        man["form"] = man["form"].str.upper()
        trows, crows = [], {}
        for form, table, grain, key, role in TABLES:
            for y in YEARS:
                mt = man[(man.form == form) & (man.year == y) &
                         (man.table.str.lower().str.startswith(table) | (form in ("D006", "T001")))]
                if form == "D004":
                    mt = mt[mt.table == table]
                if mt.empty:
                    continue
                detail = y == YEARS[-1] or form != "D004" and form != "T001"   # full read: latest year, small tables
                if detail:
                    d = read_table(D, form, table, y)
                else:   # headers only (big tables, earlier years)
                    first = Path(D, mt.path.iloc[0])
                    d = pd.read_csv(first, dtype=str, nrows=0)
                    d.columns = [c.strip().upper() for c in d.columns]
                k = [c for c in key if c in d]
                full = detail and k and len(k) == len(key)
                trows.append({"form": form, "table": table, "year": y, "grain": grain, "key": "+".join(key) or "none",
                              "files": len(mt), "rows": int(mt.rows_synthetic.sum()), "columns": d.shape[1],
                              "rows_real": int(mt.rows_real.sum()), "columns_real": int(mt.columns_real.max()),
                              "key_unique": (not d.duplicated(k).any()) if full else None,
                              "households": d["NOMER"].nunique() if detail and "NOMER" in d else None,
                              "households_in_roster_pct": round(100 * d["NOMER"].isin(roster_ids[y]).mean(), 1)
                              if detail and "NOMER" in d else None,
                              "regions": d["TE"].nunique() if detail and "TE" in d else None, "role": role})
                dd = desc.get((form, table), {})
                for c in d.columns:
                    r = crows.setdefault((form, table, c), {"form": form, "table": table, "column": c, "years": [],
                                                            "in_key": c in key})
                    r["years"].append(y)
                    if not detail:
                        continue
                    s = d[c]
                    filled = s.notna() & (s.astype(str).str.strip() != "")
                    r.update({"kind": kind(s), "filled_pct": round(100 * filled.mean(), 1), "distinct": int(s[filled].nunique()),
                              "top_values": "; ".join(f"{v}:{n}" for v, n in s[filled].value_counts().head(5).items()),
                              "profiled_year": y})
                    t, ln, de = dd.get(norm(c)) or dd.get(re.sub(r"\d+$", "", norm(c))) or ("", "", "")
                    r.update({"doc_type": t, "doc_length": ln, "description": de})
        cols = pd.DataFrame(crows.values())
        cols["years"] = cols["years"].map(lambda v: f"{min(v)}-{max(v)}" if len(v) == len(YEARS) else ",".join(map(str, v)))
        def ids(f, t, c):
            return sorted(set(used.get((f, t, c), []) + used.get((f, "*", c), [])))
        cols["rule_ids"] = ["; ".join(ids(f, t, c)) for f, t, c in zip(cols.form, cols.table, cols.column)]
        cols["rules"] = [len(ids(f, t, c)) for f, t, c in zip(cols.form, cols.table, cols.column)]
        cols["documented"] = cols["description"].ne("")

        print(f"tables profiled in {time.time() - t0:.0f}s", flush=True)
        pd.DataFrame(trows).to_csv(out / "schema_tables.csv", index=False)
        cols.to_csv(out / "schema_columns.csv", index=False)
        print(f"tables: {len(trows)} table-years, columns: {len(cols)}, documented: {cols.documented.mean():.0%}, "
              f"used by rules: {(cols.rules > 0).sum()}")
    if a.only in ("all", "links"):
        t0 = time.time()
        links(D).to_csv(out / "schema_links.csv", index=False)
        household_children_check(D).to_csv(out / "schema_household_children.csv", index=False)
        print(f"links in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
