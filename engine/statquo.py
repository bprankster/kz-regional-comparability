"""StatQUO check engine.

Runs the rule files written from the questionnaires (rules/*.json) against the survey records,
per region and year, and writes one long table of results. Every number in the case files and the
scorecard comes from here.

    python engine/statquo.py --data DATA_DIR --rules rules/d002_2023-2024.json --out out/
"""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

REGION = {"10": "Abai", "11": "Akmola", "15": "Aktobe", "19": "Almaty oblast", "23": "Atyrau",
          "27": "West Kazakhstan", "31": "Zhambyl", "33": "Zhetysu", "35": "Karaganda", "39": "Kostanay",
          "43": "Kyzylorda", "47": "Mangystau", "55": "Pavlodar", "59": "North Kazakhstan", "61": "Turkistan",
          "62": "Ulytau", "63": "East Kazakhstan", "71": "Astana", "75": "Almaty city", "79": "Shymkent"}

TABLES = {"D002": {"subject": "d002/{y}/subject.csv", "ocenka": "d002/{y}/ocenka.csv"},
          "D006": {"rio": None},
          "D008": {"kontr_k": "d008/{y}/kontr_k.csv"}}
D006_FILES = {2021: "d006/2021/rio.csv", 2022: "d006/2022/rio2022.csv",
              2023: "d006/2023/rio2023.csv", 2024: "d006/2024/rio_2024.csv"}


def read(data_dir, rel):
    df = pd.read_csv(Path(data_dir, rel), dtype=str, encoding_errors="replace")
    df.columns = [c.strip().upper() for c in df.columns]
    return df.apply(lambda s: s.str.strip() if s.dtype == object else s)


def load_d004(data_dir, year):
    """D-004 is a quarterly journal: one folder per quarter. Stack the quarters, keep the folder's quarter."""
    out = {}
    for t, name in (("kv0", "kv_vopr0"), ("kv1", "kv_vopr1"), ("kv11", "kv_vopr11"), ("kv12", "kv_vopr12")):
        parts = []
        for q in (1, 2, 3, 4):
            f = Path(data_dir, f"d004/{year}/{q}kv/{name}.csv")
            if f.exists():
                d = read(data_dir, f"d004/{year}/{q}kv/{name}.csv")
                d["Q_FOLDER"] = str(q)
                parts.append(d)
        out[t] = pd.concat(parts, ignore_index=True)
    rez = out["kv0"][["NOMER", "Q_FOLDER", "REZ"]]
    for t in ("kv1", "kv12"):
        out[t] = out[t].merge(rez, on=["NOMER", "Q_FOLDER"], how="left")
    k12 = out["kv12"]
    took = (k12["KODNU"].isin(["59", "61"]) & (num(k12["STOIMK"]) > 0)).groupby([k12["NOMER"], k12["Q_FOLDER"]]).any()
    took = took.rename("NEW_LOAN").reset_index()
    took["NEW_LOAN"] = took["NEW_LOAN"].map({True: "1", False: "2"})
    out["kv12"] = k12.merge(took, on=["NOMER", "Q_FOLDER"], how="left")
    return out


def load(data_dir, form, year):
    if form == "D004":
        return load_d004(data_dir, year)
    if form == "D006":
        return {"rio": read(data_dir, D006_FILES[year])}
    tables = {t: read(data_dir, p.format(y=year)) for t, p in TABLES[form].items()}
    if form == "D008":
        tables["kontr_k"]["AGE"] = (year - num(tables["kontr_k"]["GOD_ROJD"])).astype("Float64").astype(str).replace("<NA>", np.nan)
    if form == "D002":  # both halves of one questionnaire, joined on the household number
        sub, oc = tables["subject"], tables["ocenka"]
        tables["hh"] = sub.merge(oc[[c for c in oc.columns if c not in sub.columns or c == "NOMER"]],
                                 on="NOMER", how="inner")
    return tables


def num(s):
    return pd.to_numeric(s, errors="coerce")


def filled(s):
    return s.notna() & (s.astype(str).str.strip() != "")


def when_mask(df, cond):
    """Evaluate a rule condition on a table. Rows where the condition column is missing count as False."""
    if cond is None:
        return pd.Series(True, index=df.index)
    if "all" in cond:
        m = pd.Series(True, index=df.index)
        for c in cond["all"]:
            m &= when_mask(df, c)
        return m
    if "any" in cond:
        m = pd.Series(False, index=df.index)
        for c in cond["any"]:
            m |= when_mask(df, c)
        return m
    col = cond["col"]
    if col not in df:
        return pd.Series(False, index=df.index)
    if cond.get("blank"):
        return ~filled(df[col])
    if cond.get("filled"):
        return filled(df[col])
    if "lt" in cond:
        return num(df[col]) < cond["lt"]
    if "ge" in cond:
        return num(df[col]) >= cond["ge"]
    return num(df[col]).isin(cond["in"])


def tables_for(rule, tables):
    t = rule.get("table", "both")
    if t == "both":
        return [(n, d) for n, d in tables.items() if n != "hh"]
    return [(t, tables[t])] if t in tables else []


def evaluate(rule, tables):
    """Yield (table, column, applicable mask, violation mask) for one rule."""
    typ = rule["type"]
    skip = set(rule.get("skip_targets_by_year", {}).get(str(rule.get("_year")), []))
    for tname, df in tables_for(rule, tables):
        cols = [c for c in rule["targets"] if c in df and c not in skip]
        if typ == "domain":
            a = rule["allowed"]
            for c in cols:
                v, f = num(df[c]), filled(df[c])
                if isinstance(a, dict) and a.get("codebook"):
                    book = pd.read_excel(Path(rule["_data_dir"], a["codebook"]), dtype=str)
                    codes = set(book[a["column"]].dropna().str.strip().str.rstrip(","))
                    bad = f & ~df[c].astype(str).str.strip().isin(codes)
                elif isinstance(a, dict) and a.get("equals_column"):
                    bad = f & (df[c].astype(str).str.lstrip("0") != df[a["equals_column"]].astype(str).str.lstrip("0"))
                elif isinstance(a, dict) and a.get("equals_year"):
                    bad = f & (num(df[c]) != rule["_year"])
                elif isinstance(a, list) and any(isinstance(x, str) for x in a):
                    bad = f & ~df[c].astype(str).str.strip().isin([str(x) for x in a])
                elif isinstance(a, dict) and a.get("no_leading_zero"):
                    bad = f & df[c].astype(str).str.match(r"^0[0-9]")
                elif isinstance(a, dict) and ("min" in a or "max" in a):
                    bad = f & ~((v >= a.get("min", -np.inf)) & (v <= a.get("max", np.inf)))
                elif not a:
                    raise ValueError("domain rule without allowed codes")
                else:
                    bad = f & ~v.isin(a)
                yield tname, c, f, bad
        elif typ == "required":
            app = when_mask(df, rule.get("when"))
            if rule.get("mode") == "any":
                if cols:
                    state = ~df[cols].apply(filled).any(axis=1)
                    yield tname, "|".join(cols), app, app & state, state
            else:
                for c in cols:
                    yield tname, c, app, app & ~filled(df[c]), ~filled(df[c])
        elif typ == "skip":
            app = when_mask(df, rule["when"])
            for c in cols:
                yield tname, c, app, app & filled(df[c]), filled(df[c])
        elif typ == "multi_select":
            for c in cols:
                f = filled(df[c])
                yield tname, c, f, f & (num(df[c]) != 1)
            ex = [c for c in rule.get("exclusive", []) if c in df]
            others = [c for c in cols if c not in ex]
            for c in ex:
                app = filled(df[c])
                yield tname, c + "+other", app, app & df[others].apply(filled).any(axis=1)
        elif typ == "consistency":
            chk = rule.get("check")
            if chk is None:
                raise ValueError("consistency rule without a 'check' (see prompt v2: implies, lte, unique)")
            if chk == "manual":
                raise ValueError("marked 'manual' by the extraction: for a person to check")
            if chk == "implies":
                app = when_mask(df, rule["if"])
                ok = when_mask(df, rule["then"])
                yield tname, rule["then"].get("col", "+".join(rule["targets"])), app, app & ~ok, ~ok
            elif chk == "lte":
                x, y_ = num(df[rule["a"]]), num(df[rule["b"]])
                app = x.notna() & y_.notna()
                yield tname, f'{rule["a"]}<={rule["b"]}', app, app & (x > y_)
            elif chk == "hh_size":
                cnt = df.groupby("NOMER")["NOMER"].transform("size")
                yield tname, "KOL_CHL", pd.Series(True, index=df.index), num(df["KOL_CHL"]) != cnt
            elif chk == "one_head":
                heads = (num(df["RODSTVO"]) == 1).groupby(df["NOMER"]).transform("sum")
                yield tname, "RODSTVO", pd.Series(True, index=df.index), heads != 1
            elif chk == "head_is_member1":
                app = df["NOMP"].astype(str).str.lstrip("0") == "1"
                yield tname, "RODSTVO", app, app & (num(df["RODSTVO"]) != 1)
            elif chk == "unique":
                yield tname, "+".join(cols), pd.Series(True, index=df.index), df.duplicated(cols, keep=False)
            elif chk == "refusal_all_or_none":
                sub = df[cols].apply(num)
                anyr = (sub == rule["code"]).any(axis=1)
                allr = (sub == rule["code"]).all(axis=1)
                yield tname, "FIES block", pd.Series(True, index=df.index), anyr & ~allr
            elif chk == "tables_agree" and tname == list(tables)[0]:
                other = [d for n, d in tables.items() if n != tname][0]
                m = df[[rule["key"]] + cols].merge(other[[rule["key"]] + cols], on=rule["key"], how="left",
                                                   suffixes=("", "_o"))
                bad = pd.Series(False, index=df.index)
                for c in cols:
                    bad |= (m[c].values != m[c + "_o"].values)
                yield tname, "+".join(cols), pd.Series(True, index=df.index), pd.Series(bad.values, index=df.index)


def attach_roster(tables, data_dir, year):
    """Record link to the D-008 roster: ROSTER_U18 = 1 if the household has a member under 18, 2 if not.

    NOMER is the same household in D-002 and D-008 (schema/profile.py: every D-002 household is in the roster,
    region agrees). Only rules that name ROSTER_U18 use it; the column is added to a copy of ocenka."""
    roster = read(data_dir, f"d008/{year}/kontr_k.csv")
    if "GOD_ROJD" not in roster:
        return tables
    u18 = ((year - num(roster["GOD_ROJD"])) < 18).groupby(roster["NOMER"]).any()
    out = dict(tables)
    oc = tables["ocenka"].copy()
    oc["ROSTER_U18"] = oc["NOMER"].map(u18).map({True: "1", False: "2"})
    out["ocenka"] = oc
    return out


NOT_RUN = []   # rules that could not be executed, with the reason (written next to the results)


def run_rules(rules, data_dir, form, years, tables_by_year=None):
    """tables_by_year lets callers pass tables already in memory (used by the planted-error test)."""
    rows = []
    for y in years:
        tables = tables_by_year[y] if tables_by_year else load(data_dir, form, y)
        if form == "D002" and any("ROSTER_U18" in json.dumps(r) for r in rules):
            tables = attach_roster(tables, data_dir, y)
        for rule in rules:
            if rule["type"] in ("doc_issue", "cross_form") or rule.get("superseded_by"):
                continue
            rule = dict(rule, _data_dir=data_dir, _year=y)
            try:
                items = list(evaluate(rule, tables))
            except Exception as e:  # a rule the engine cannot execute is listed, never fatal
                NOT_RUN.append({"rule_id": rule.get("id"), "type": rule.get("type"), "year": y,
                                "reason": f"{type(e).__name__}: {e}"[:200]})
                continue
            if not items:
                NOT_RUN.append({"rule_id": rule.get("id"), "type": rule.get("type"), "year": y,
                                "reason": "no target column of this rule is in the data"})
            for item in items:
                tname, col, app, bad = item[:4]
                state = item[4] if len(item) > 4 else None
                te = tables[tname]["TE"]
                g = pd.DataFrame({"te": te, "rec": 1, "app": app.astype(int), "bad": bad.astype(int),
                                  "state": (state if state is not None else bad).astype(int)}).groupby("te").sum()
                for code, r in g.iterrows():
                    rows.append({"rule_id": rule["id"], "type": rule["type"], "table": tname, "column": col,
                                 "year": y, "te": code, "region": REGION.get(code, code), "records": int(r["rec"]),
                                 "applicable": int(r["app"]), "violations": int(r["bad"]),
                                 "conditional": state is not None, "bad_state": int(r["state"])})
    res = pd.DataFrame(rows)
    res["rate"] = np.where(res["applicable"] > 0, res["violations"] / res["applicable"].clip(lower=1), np.nan)
    return res


def synthesis_check(applicable, bad_state, records, violations):
    """Where a conditional rule's violations could come from in synthetic data.

    floor: the violation rate the two columns' own distributions force (what survives synthesis).
    independent: the rate if the condition and the answer were unrelated (what a generator that breaks
    links between columns produces). Returns floor, independent and a label."""
    pa, pb = applicable / max(records, 1), bad_state / max(records, 1)
    if applicable == 0:
        return np.nan, np.nan, "no cases"
    obs = violations / applicable
    floor = max(0.0, pa + pb - 1) / pa
    indep = pb
    if obs < 0.01:
        label = "holds"
    elif floor >= 0.5 * obs:
        label = "forced by the answer shares"
    elif indep > 0 and obs >= 0.7 * indep:
        label = "could be broken links in the synthetic data"
    else:
        label = "partly forced"
    return floor, indep, label


def household_children(data_dir, year):
    roster = read(data_dir, f"d008/{year}/kontr_k.csv")
    u18 = (year - num(roster["GOD_ROJD"])) < 18
    return u18.groupby([roster["TE"], roster["NOMER"]]).any().groupby(level=0).mean() * 100


def run_cross_form(rules, data_dir, years):
    rows = []
    for y in years:
        oc = read(data_dir, f"d002/{y}/ocenka.csv")
        for rule in rules:
            if rule["type"] != "cross_form":
                continue
            if "this" not in rule or rule.get("other_form") not in ("D008", "D006"):
                NOT_RUN.append({"rule_id": rule.get("id"), "type": "cross_form", "year": y,
                                "reason": "cross-form rule given in words; the automatic form-vs-form search (compare.py) covers it"})
                continue
            this = when_mask(oc, rule["this"]).groupby(oc["TE"]).mean() * 100
            upper = pd.Series(dtype=float)
            if rule["other_form"] == "D008":
                other = household_children(data_dir, y)
            else:
                d6 = read(data_dir, D006_FILES[y])
                own = "VLAD1" if "VLAD1" in d6 else "VLAD"
                low = rule.get("lower", {"in": [1, 2]})
                other = num(d6[own]).isin(low["in"]).groupby(d6["TE"]).mean() * 100
                if "upper_not" in rule:
                    upper = 100 - num(d6[own]).isin(rule["upper_not"]["in"]).groupby(d6["TE"]).mean() * 100
            for code in this.index:
                rows.append({"rule_id": rule["id"], "check": rule.get("check", "regional_share_match"), "year": y, "te": code,
                             "region": REGION.get(code, code), "this_share": round(this[code], 1),
                             "other_share": round(other.get(code, np.nan), 1),
                             "upper_share": round(upper.get(code, np.nan), 1) if len(upper) else np.nan,
                             "tolerance": rule.get("tolerance", np.nan)})
    return pd.DataFrame(rows)


def flag_regions(res, min_rate=0.05, ratio=3.0, min_n=30, min_excess=10):
    """Region vs rest of the country, per rule × column × year.

    A region is flagged when
    1. its violation rate among the records the rule applies to is at least `min_rate`, at least `ratio` times
       the rate in the other regions pooled, and beyond sampling noise (two-proportion z > 3); and
    2. the region has at least `min_excess` more violations than the rest-of-country rate would give.
    Test 2 keeps a handful of stray records in a small group from raising a flag."""
    out = []
    for (rid, col, y), g in res.groupby(["rule_id", "column", "year"]):
        tot_a, tot_b, tot_n = g["applicable"].sum(), g["violations"].sum(), g["records"].sum()
        for _, r in g.iterrows():
            ra, rb, rn = tot_a - r.applicable, tot_b - r.violations, tot_n - r.records
            if r.applicable < min_n or ra < min_n:
                continue
            p1, p0 = r.violations / r.applicable, rb / ra
            p = (r.violations + rb) / (r.applicable + ra)
            se = np.sqrt(p * (1 - p) * (1 / r.applicable + 1 / ra))
            z = (p1 - p0) / se if se > 0 else np.nan
            i1, i0 = r.violations / r.records, rb / max(rn, 1)
            excess = r.violations - r.applicable * p0
            test1 = p1 >= min_rate and p1 >= ratio * max(p0, 1e-9) and z > 3
            test2 = excess >= min_excess
            if test1:
                if r.get("conditional", False):
                    floor, indep, label = synthesis_check(r.applicable, r.bad_state, r.records, r.violations)
                else:
                    floor, indep, label = np.nan, np.nan, "not conditional"
                out.append({"synthesis": label, "floor": round(100 * floor, 1) if floor == floor else np.nan,
                            "independent": round(100 * indep, 1) if indep == indep else np.nan,"rule_id": rid, "type": r.type, "column": col, "year": y, "region": r.region,
                            "records": r.records, "applicable": r.applicable, "violations": r.violations,
                            "rate_region": round(100 * p1, 1), "rate_rest": round(100 * p0, 1), "z": round(z, 1),
                            "per_record_region": round(100 * i1, 1), "per_record_rest": round(100 * i0, 1),
                            "excess": round(excess, 1),
                            "flag": bool(test2)})
    return pd.DataFrame(out)


def flag_cross_form(xf, gap_points=15, min_regions=15):
    """Fit this-form share against other-form share across regions (1:1 expected); flag regions off the line."""
    out = []
    if xf.empty:
        return pd.DataFrame(out)
    for (rid, y), g in xf.groupby(["rule_id", "year"]):
        if "check" in g and g["check"].iloc[0] == "regional_share_bounds":
            # the share must lie between a lower and an upper bound from the other form, within a tolerance
            tol = float(g["tolerance"].iloc[0]) if g["tolerance"].notna().any() else 5.0
            for _, r in g.iterrows():
                below = r.this_share < r.other_share - tol
                above = r.upper_share == r.upper_share and r.this_share > r.upper_share + tol
                out.append({"rule_id": rid, "year": y, "region": r.region, "this_share": r.this_share,
                            "other_share": r.other_share, "upper_share": r.upper_share,
                            "gap": round(r.this_share - r.other_share, 1), "flag": bool(below or above),
                            "side": "below lower bound" if below else ("above upper bound" if above else "within bounds"),
                            "r2_other_regions": np.nan})
            continue
        g = g[["rule_id", "year", "region", "this_share", "other_share"]].dropna()
        gap = g["this_share"] - g["other_share"]
        off = gap.abs() >= gap_points
        on = g[~off]
        r2 = np.corrcoef(on["other_share"], on["this_share"])[0, 1] ** 2 if len(on) >= min_regions else np.nan
        for (_, r), gp, o in zip(g.iterrows(), gap, off):
            out.append({"rule_id": rid, "year": y, "region": r.region, "this_share": r.this_share,
                        "other_share": r.other_share, "gap": round(gp, 1), "flag": bool(o),
                        "r2_other_regions": round(r2, 2) if r2 == r2 else np.nan})
    return pd.DataFrame(out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--rules", required=True)
    ap.add_argument("--out", default="out")
    ap.add_argument("--years", default="2023,2024")
    a = ap.parse_args()
    spec = json.load(open(a.rules, encoding="utf-8"))
    years = [int(y) for y in a.years.split(",")]
    Path(a.out).mkdir(exist_ok=True, parents=True)
    res = run_rules(spec["rules"], a.data, spec["form"], years)
    res.to_csv(Path(a.out, f"{spec['form']}_results.csv"), index=False)
    flags = flag_regions(res)
    flags.to_csv(Path(a.out, f"{spec['form']}_region_flags.csv"), index=False)
    if NOT_RUN:
        pd.DataFrame(NOT_RUN).drop_duplicates(["rule_id", "reason"]).to_csv(Path(a.out, f"{spec['form']}_not_run.csv"), index=False)
        print(f"{len({r['rule_id'] for r in NOT_RUN})} rules not run (see {spec['form']}_not_run.csv)")
    xf = run_cross_form(spec["rules"], a.data, years)
    xf.to_csv(Path(a.out, f"{spec['form']}_cross_form.csv"), index=False)
    flag_cross_form(xf).to_csv(Path(a.out, f"{spec['form']}_cross_form_flags.csv"), index=False)
    print(f"{len(res)} result rows, {len(flags)} region flags, {len(xf)} cross-form rows")
