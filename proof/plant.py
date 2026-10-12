"""Planted-error test.

1. Sensitivity: plant routing and coding errors into one region's records at a known rate and check whether
   the region-vs-rest flagger finds that region on that rule.
2. Specificity: replace one region's records with another region's records (answers shift a lot, routing
   stays intact). A real regional difference must produce no new flags.

    python proof/plant.py DATA_DIR rules/d002_2023-2024.json out/
"""
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
import statquo as S  # noqa: E402

YEAR = 2024
RNG = np.random.default_rng(20261010)


def hh_rebuild(t):
    sub, oc = t["subject"], t["ocenka"]
    t["hh"] = sub.merge(oc[[c for c in oc.columns if c not in sub.columns or c == "NOMER"]], on="NOMER")
    return t


def repair(tables, kind):
    """Remove the background violations of one rule in every region, so planting starts from a clean
    baseline. The synthetic release breaks some links between columns (7-15% background on two of the rules);
    real records should be close to clean. Running the test on both gives a lower and an upper bound."""
    t = {k: v.copy() for k, v in tables.items() if k != "hh"}
    sub, oc = t["subject"], t["ocenka"]
    n = S.num
    if kind == "skip: Q14 asked after 'no internet'":
        oc.loc[n(oc.GR313) == 2, "GR314"] = np.nan
    elif kind == "skip: Part 4 filled for 'no children'":
        cols = [c for c in oc.columns if c.startswith(("GR42_", "GR43_", "GR44_", "GR45_")) or c in ("GR41", "GR46")]
        oc.loc[n(oc.GR40) == 2, cols] = np.nan
    elif kind == "required: reason blank after 'no home internet'":
        g = [f"GR316_{i}" for i in range(1, 7)]
        blank = (n(oc.GR315) == 2) & ~oc[g].apply(S.filled).any(axis=1)
        oc.loc[blank, "GR316_6"] = "1"
    elif kind == "domain: out-of-range time code":
        sub.loc[S.filled(sub.ZT) & ~n(sub.ZT).isin([1, 2, 3, 4, 5, 6]), "ZT"] = "1"
    elif kind == "filter: 'no children' with a pre-school child":
        oc.loc[(n(oc.GR317) == 1) & (n(oc.GR40) == 2), "GR40"] = "1"
    return hh_rebuild(t)


def plant(tables, region_code, kind, rate):
    """Return a copy of the tables with errors of `kind` planted in `rate` of the eligible records."""
    t = {k: v.copy() for k, v in tables.items() if k != "hh"}
    sub, oc = t["subject"], t["ocenka"]
    n = S.num
    if kind == "skip: Q14 asked after 'no internet'":
        elig = oc.index[(oc.TE == region_code) & (n(oc.GR313) == 2)]
        pick = RNG.choice(elig, int(round(rate * len(elig))), replace=False)
        oc.loc[pick, "GR314"] = "1"
        rule, col = "D002-P3Q14-skip", "GR314"
    elif kind == "skip: Part 4 filled for 'no children'":
        elig = oc.index[(oc.TE == region_code) & (n(oc.GR40) == 2)]
        pick = RNG.choice(elig, int(round(rate * len(elig))), replace=False)
        donors = oc.index[(n(oc.GR40) == 1) & S.filled(oc.GR44_1)]
        cols = [c for c in oc.columns if c.startswith(("GR44_", "GR45_")) or c in ("GR41", "GR46")]
        oc.loc[pick, cols] = oc.loc[RNG.choice(donors, len(pick)), cols].values
        rule, col = "D002-P4-skip", "GR44_1"
    elif kind == "required: reason blank after 'no home internet'":
        elig = oc.index[(oc.TE == region_code) & (n(oc.GR315) == 2)]
        pick = RNG.choice(elig, int(round(rate * len(elig))), replace=False)
        oc.loc[pick, [f"GR316_{i}" for i in range(1, 7)]] = np.nan
        rule, col = "D002-P3Q16-required", "|".join(f"GR316_{i}" for i in range(1, 7))
    elif kind == "domain: out-of-range time code":
        elig = sub.index[sub.TE == region_code]
        pick = RNG.choice(elig, int(round(rate * len(elig))), replace=False)
        sub.loc[pick, "ZT"] = "7"
        rule, col = "D002-ZT-domain", "ZT"
    elif kind == "filter: 'no children' with a pre-school child":
        elig = oc.index[(oc.TE == region_code) & (n(oc.GR317) == 1) & (n(oc.GR40) == 1)]
        pick = RNG.choice(elig, int(round(rate * len(elig))), replace=False)
        oc.loc[pick, "GR40"] = "2"
        rule, col = "D002-preschool-implies-children", "GR40"
    else:
        raise ValueError(kind)
    return hh_rebuild(t), rule, col, len(pick), len(elig)


def flagged(rules, tables):
    res = S.run_rules(rules, None, "D002", [YEAR], {YEAR: tables})
    f = S.flag_regions(res)
    return f[f["flag"]] if len(f) else f


def main(data_dir, rules_path, out):
    rules = json.load(open(rules_path, encoding="utf-8"))["rules"]
    base = S.load(data_dir, "D002", YEAR)
    base_flags = flagged(rules, base)
    base_keys = set(zip(base_flags.rule_id, base_flags.column, base_flags.region))
    # regions near or over the threshold for a rule before planting are left out for that rule
    allf = S.flag_regions(S.run_rules(rules, None, "D002", [YEAR], {YEAR: base}))
    near = {rid: set(g["region"]) for rid, g in allf.groupby("rule_id")}
    res0 = S.run_rules(rules, None, "D002", [YEAR], {YEAR: base})

    rows = []
    kinds = ["skip: Q14 asked after 'no internet'", "skip: Part 4 filled for 'no children'",
             "required: reason blank after 'no home internet'", "domain: out-of-range time code",
             "filter: 'no children' with a pre-school child"]
    rule_of = {kinds[0]: "D002-P3Q14-skip", kinds[1]: "D002-P4-skip", kinds[2]: "D002-P3Q16-required",
               kinds[3]: "D002-ZT-domain", kinds[4]: "D002-preschool-implies-children"}
    clean = bool(os.environ.get("CLEAN"))
    for kind in kinds:
        start, start_keys, start_near, start_res = base, base_keys, near, res0
        if clean:  # repaired baseline: this rule has no background violations anywhere
            start = repair(base, kind)
            start_res = S.run_rules(rules, None, "D002", [YEAR], {YEAR: start})
            ff = S.flag_regions(start_res)
            start_near = {rid: set(g["region"]) for rid, g in ff.groupby("rule_id")}
            ff = ff[ff["flag"]] if len(ff) else ff
            start_keys = set(zip(ff.rule_id, ff.column, ff.region))
        regions = [c for c in S.REGION if S.REGION[c] not in start_near.get(rule_of[kind], set())]
        g0 = start_res[start_res.rule_id == rule_of[kind]]
        background = 100 * g0.violations.sum() / max(1, g0.applicable.sum())
        for rate in (0.05, 0.10, 0.20, 0.30, 0.50):
            for trial in range(int(os.environ.get('TRIALS', 10))):
                reg = RNG.choice(regions)
                t, rule, col, k, elig = plant(start, reg, kind, rate)
                f = flagged(rules, t)
                keys = set(zip(f.rule_id, f.column, f.region))
                hit = (rule, col, S.REGION[reg]) in keys
                new = keys - start_keys - {(rule, col, S.REGION[reg])}
                elsewhere = [k_ for k_ in new if k_[2] != S.REGION[reg]]
                same_region = [k_ for k_ in new if k_[2] == S.REGION[reg]]
                rows.append({"baseline": "repaired" if clean else "synthetic as shipped", "kind": kind, "rule": rule_of[kind], "background_rate": round(background, 2),
                             "rate": rate, "trial": trial, "region": S.REGION[reg],
                             "planted": k, "eligible": elig, "detected": hit,
                             "new_flags_other_regions": len(elsewhere),
                             "new_flags_same_region": len(same_region),
                             "same_region_rules": "; ".join(sorted({k_[0] for k_ in same_region}))})
                print(kind, rate, S.REGION[reg], k, hit, len(elsewhere), len(same_region), flush=True)
    sens = pd.DataFrame(rows)
    sens.to_csv(Path(out, "proof_sensitivity_clean.csv" if clean else "proof_sensitivity.csv"), index=False)
    if os.environ.get('SKIP_TRANSPLANT') or clean:
        return

    # Specificity: give a region another region's households (answers shift, routing stays intact)
    clean = [c for c in S.REGION if S.REGION[c] not in set(base_flags.region)]
    spec = []
    for trial in range(20):
        a = RNG.choice(list(S.REGION))
        b = RNG.choice([c for c in clean if c != a])
        sub, oc = base["subject"], base["ocenka"]
        n_a = int((sub.TE == a).sum())
        donors = RNG.choice(sub.loc[sub.TE == b, "NOMER"].values, n_a, replace=True)
        new_ids = [f"X{trial}_{i}" for i in range(n_a)]
        t = {}
        for name, df in (("subject", sub), ("ocenka", oc)):
            d = df.set_index("NOMER").loc[donors].reset_index()
            d["NOMER"], d["TE"] = new_ids, a
            t[name] = pd.concat([df[df.TE != a], d], ignore_index=True)
        t = hh_rebuild(t)
        f = flagged(rules, t)
        keys = set(zip(f.rule_id, f.column, f.region))
        new = {k for k in keys - base_keys if k[2] == S.REGION[a]}
        spec.append({"trial": trial, "region_replaced": S.REGION[a], "donor": S.REGION[b],
                     "new_flags_in_region": len(new),
                     "examples": "; ".join(sorted(f"{k[0]}:{k[1]}" for k in new))[:200]})
        print("transplant", S.REGION[a], "<-", S.REGION[b], len(new), flush=True)
    pd.DataFrame(spec).to_csv(Path(out, "proof_specificity.csv"), index=False)
    answer_shift(base, spec).to_csv(Path(out, "proof_specificity_shift.csv"), index=False)


def answer_shift(base, spec):
    """How far each transplant moved the region's answers: Jensen-Shannon divergence between the replaced and the
    donor region on every categorical column of the 2024 D-002 tables (missing counted as an answer)."""
    from compare import categorical_columns, js
    code = {v: k for k, v in S.REGION.items()}
    rows = []
    for s_ in spec:
        a, b = code[s_["region_replaced"]], code[s_["donor"]]
        vals = []
        for name in ("subject", "ocenka"):
            df = base[name]
            for c in categorical_columns(df, 30):
                ct = pd.crosstab(df["TE"], df[c].fillna("∅"))
                vals.append(js(ct.loc[a].values, ct.loc[b].values))
        v = np.array(vals)
        rows.append({"pair": f'{s_["region_replaced"]} <- {s_["donor"]}', "median_js": float(np.median(v)),
                     "vars_js_gt_0.05": int((v > 0.05).sum()), "n_vars": len(v)})
    return pd.DataFrame(rows)


if __name__ == "__main__":
    main(*sys.argv[1:4])
