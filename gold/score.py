"""Score an extracted rule file against the reference set.

Both files are broken into atomic rules: one per (rule type, data column). A rule counts as found when the
other file has the same type on the same column; it counts as exact when the details also match (allowed codes
for domain rules, the condition for skip/required rules).

    python gold/score.py rules/d002_2023-2024.json gold/d002_gold_reviewed.json
"""
import json
import sys
from collections import defaultdict

import pandas as pd

# reference atoms the team ruled equivalent to an extracted rule written another way: ref atom id -> extracted ids
EQUIV = {}

ROW_TYPES = ("domain", "required", "skip", "multi_select")


def cond_sig(c):
    if not c:
        return None
    if "in" in c:
        return (c["col"], tuple(sorted(c["in"])))
    return json.dumps(c, sort_keys=True)


def allowed_sig(a):
    if a is None:
        return None
    if isinstance(a, dict):
        return ("range", a.get("min"), a.get("max"))
    return tuple(sorted(a))


def atoms_extracted(spec):
    out = []
    for r in spec["rules"]:
        t = r["type"]
        if t == "required" and r.get("mode") == "any":
            out.append(("required_any", tuple(sorted(r["targets"])), cond_sig(r.get("when")), None, r["id"]))
        elif t in ROW_TYPES:
            tabs = ["subject", "ocenka"] if r.get("table") == "both" else [r.get("table")]
            for tab in tabs:
                for c in r["targets"]:
                    a = allowed_sig(r.get("allowed")) if t == "domain" else None
                    out.append((t, c, cond_sig(r.get("when")), a, f'{r["id"]}@{tab}'))
        else:
            cols = set(r["targets"])
            if t == "consistency" and r.get("check") == "implies":
                cols = {r["if"]["col"], r["then"]["col"]}
            out.append((t, tuple(sorted(cols)), None, None, r["id"]))
    return out


def atoms_reference(spec):
    out = []
    EQUIV.clear()
    for i, r in enumerate(spec["rules"]):
        t = r["type"]
        if r.get("equivalent_to"):
            EQUIV[f"ref{i}"] = set(r["equivalent_to"])
        if t in ROW_TYPES:
            a = r.get("allowed")
            if t == "domain" and a is None and "min" in r:
                a = {"min": r["min"], "max": r.get("max", 120)}
            a = allowed_sig(a) if t == "domain" else None
            out.append((t, r["column"], cond_sig(r.get("when")), a, f"ref{i}"))
        elif t == "required_any":
            out.append((t, tuple(sorted(r["columns"])), cond_sig(r.get("when")), None, f"ref{i}"))
        else:
            out.append((t, tuple(sorted(r["columns"])), None, None, f"ref{i}"))
    return out


def match(ext, ref):
    """Return per-atom status for both sides."""
    by_key = defaultdict(list)
    for a in ref:
        by_key[(a[0], a[1])].append(a)
    used, ext_status = set(), []
    pre = {}  # team-ruled equivalences are paired first
    for rid, ids in EQUIV.items():
        for e in ext:
            if e[4] in ids and e[4] not in pre and rid not in used:
                pre[e[4]] = rid
                used.add(rid)
    for e in ext:
        if e[4] in pre:
            ext_status.append((e, "exact"))
            continue
        status = "missing"
        if e[0] in ROW_TYPES or e[0] == "required_any":
            cands = by_key.get((e[0], e[1]), [])
            if e[0] == "required_any":
                cands = [a for a in ref if a[0] == "required_any" and set(a[1]) == set(e[1])]
        else:  # set-valued rules: match on overlapping columns
            cands = [a for a in ref if a[0] == e[0] and set(a[1]) & set(e[1])]
        exact = [a for a in cands if a[2] == e[2] and a[3] == e[3] and a[4] not in used]
        loose = [a for a in cands if a[4] not in used]
        if exact:
            status = "exact"
            used.add(exact[0][4])
        elif loose:
            status = "found, details differ"
            used.add(loose[0][4])
        ext_status.append((e, status))
    ref_status = [(a, "found" if a[4] in used else "missed") for a in ref]
    return ext_status, ref_status


def report(ext_status, ref_status):
    rows = []
    types = sorted({e[0] for e, _ in ext_status} | {a[0] for a, _ in ref_status})
    for t in types:
        e = [s for a, s in ext_status if a[0] == t]
        r = [s for a, s in ref_status if a[0] == t]
        found = sum(s != "missing" for s in e)
        exact = sum(s == "exact" for s in e)
        rec = sum(s == "found" for s in r)
        rows.append({"type": t, "extracted": len(e), "reference": len(r),
                     "precision": round(found / len(e), 3) if e else None,
                     "recall": round(rec / len(r), 3) if r else None,
                     "exact share of found": round(exact / found, 3) if found else None})
    df = pd.DataFrame(rows)
    tot_e = len(ext_status)
    tot_r = len(ref_status)
    df.loc[len(df)] = {"type": "ALL", "extracted": tot_e, "reference": tot_r,
                       "precision": round(sum(s != "missing" for _, s in ext_status) / tot_e, 3),
                       "recall": round(sum(s == "found" for _, s in ref_status) / tot_r, 3),
                       "exact share of found": round(sum(s == "exact" for _, s in ext_status)
                                                     / max(1, sum(s != "missing" for _, s in ext_status)), 3)}
    return df


if __name__ == "__main__":
    import argparse
    from pathlib import Path
    ap = argparse.ArgumentParser(description="Precision and recall of a rule file against the reference set.")
    ap.add_argument("rules")
    ap.add_argument("reference")
    ap.add_argument("matches", nargs="?", help="optional CSV with the status of every atom")
    ap.add_argument("--out", help="folder: writes accuracy_<form>_v1_vs_<reference>.csv and the atom statuses")
    ap.add_argument("--all", action="store_true",
                    help="also score rules added after the review (they came from the reference, so this is circular)")
    a = ap.parse_args()
    spec = json.load(open(a.rules, encoding="utf-8"))
    if not a.all:  # the accuracy figure is for the extraction as the model wrote it
        spec = dict(spec, rules=[r for r in spec["rules"] if not r.get("added_after_review")])
    ext = atoms_extracted(spec)
    ref = atoms_reference(json.load(open(a.reference, encoding="utf-8")))
    es, rs = match(ext, ref)
    rep = report(es, rs)
    pd.set_option("display.width", 200)
    print(rep.to_string(index=False))
    atoms = pd.DataFrame([{"side": "extracted", "type": x[0], "column": str(x[1]), "when": str(x[2]), "allowed": str(x[3]),
                           "id": x[4], "status": st} for x, st in es] +
                         [{"side": "reference", "type": x[0], "column": str(x[1]), "when": str(x[2]), "allowed": str(x[3]),
                           "id": x[4], "status": st} for x, st in rs])
    if a.matches:
        atoms.to_csv(a.matches, index=False)
    if a.out:
        form = spec.get("form", "d002").lower()
        tag = Path(a.reference).stem.split("_")[-1]          # d002_gold_reviewed -> reviewed
        v = "all" if a.all else "v1"
        rep.to_csv(Path(a.out, f"accuracy_{form}_{v}_vs_{tag}.csv"), index=False)
        atoms.to_csv(Path(a.out, f"{form}_match_{v}_vs_{tag}.csv"), index=False)
