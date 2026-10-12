"""Household finances (D-004): how much do recording and documentation problems change the indicators?

Second "so what" case, next to child poverty. Same question as the rest of StatQUO: before a figure is published,
which rules from the questionnaire and which regional differences change it, and by how much?

Unit: a household-quarter that took part (kv_vopr0 REZ = 1). Unweighted (the release has no weights).

Indicators
  income            sum of the 23 income columns of section 3 (kv_vopr11), all members of the household.
                    GR3 is printed on the form as "из него: доход от продажи сельскохозяйственной продукции"
                    under GR2 (self-employment), so it is part of GR2 and is NOT added (form-correct income).
  recorded spending sections 1.1-1.3 (kv_vopr1-7). D-004 has no section for food purchases.
  "savings rate"    1 - recorded spending / income: what a naive reading calls a savings rate.
  borrowed          new credit (KODNU 59) or money borrowed (61) > 0 in the quarter.
  debt service      repayments (2.1.1.4.1 credit, 2.1.1.4.2 debt) / income; burden = debt service > 30%.
  food loan         purpose of the loan (2.1, NOMVNEW 21) = 3 "Покупка продуктов питания".

Corrections measured, one at a time
  C-a  GR3 added to income (naive) vs left out (form)                     -> questionnaire rule
  C-b  repeated items in kv_vopr1 (same household, quarter, item code)    -> generator artefact named in the
       organisers' data guide ("15% of rows vs 2.4%"); sensitivity: spending with the extra copies removed
  C-c  no food section                                                    -> documentation; the 66% is not a savings rate
  C-d  Aktobe food loans                                                   -> regional recording (case already in the blind test)

    python analysis/finance_impact.py DATA_DIR out/
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
import statquo as S  # noqa: E402

D, OUT = sys.argv[1], Path(sys.argv[2])
YEARS = (2021, 2022, 2023, 2024)
SPEND = ["kv_vopr1", "kv_vopr2", "kv_vopr3", "kv_vopr4", "kv_vopr5", "kv_vopr6", "kv_vopr7"]
INC = [f"GR{i}" for i in range(1, 24)]
BURDEN = 0.30
AKTOBE = "15"
# Official benchmark (BNS, household budget survey, as reported by NUR.KZ for Q4 2024): food is 50.1% of total
# per-capita household spending. Used only to show the size of the gap, not to correct the data.
FOOD_SHARE = 0.501


def stack(y, name):
    parts = []
    for q in (1, 2, 3, 4):
        f = Path(D, f"d004/{y}/{q}kv/{name}.csv")
        if f.exists():
            d = S.read(D, f"d004/{y}/{q}kv/{name}.csv")
            d["Q"] = str(q)
            parts.append(d)
    return pd.concat(parts, ignore_index=True)


def hh_year(y):
    k0 = stack(y, "kv_vopr0")
    k0 = k0[k0.REZ == "1"][["NOMER", "Q", "TE", "K"]].drop_duplicates(["NOMER", "Q"])
    key = ["NOMER", "Q"]
    # income, person rows -> household-quarter
    k11 = stack(y, "kv_vopr11")
    v = k11[INC].apply(S.num).fillna(0)
    k11 = pd.concat([k11[key], v], axis=1)
    inc = k11.groupby(key)[INC].sum()
    inc_form = inc.drop(columns="GR3").sum(axis=1).rename("income")
    inc_naive = inc.sum(axis=1).rename("income_naive")
    gr3 = inc["GR3"].rename("gr3")
    pers = k11.assign(bad=(v.GR3 > v.GR2), has=(v.GR3 > 0))
    # spending
    sp, sp_dedup = [], []
    for name in SPEND:
        t = stack(y, name)
        t["v"] = S.num(t["STOIMK"]).fillna(0)
        sp.append(t.groupby(key)["v"].sum().rename(name))
        if name == "kv_vopr1":
            t1 = t
            extra = t.duplicated(["NOMER", "Q", "KODNU"])
            sp_dedup.append(t[~extra].groupby(key)["v"].sum().rename(name))
            rep = pd.DataFrame({"rep_rows": extra.groupby([t.NOMER, t.Q]).sum(), "kv1_rows": extra.groupby([t.NOMER, t.Q]).size(),
                                "rep_value": t.v.where(extra, 0).groupby([t.NOMER, t.Q]).sum()})
        else:
            sp_dedup.append(sp[-1])
    spend = pd.concat(sp, axis=1).fillna(0).sum(axis=1).rename("spend")
    spend_dd = pd.concat(sp_dedup, axis=1).fillna(0).sum(axis=1).rename("spend_dedup")
    # loans
    k12 = stack(y, "kv_vopr12")
    k12["v"] = S.num(k12["STOIMK"]).fillna(0)
    amt = k12.pivot_table(index=key, columns="KODNU", values="v", aggfunc="sum").fillna(0)
    for c in ("59", "61", "2.1.1.4.1", "2.1.1.4.2", "60"):
        if c not in amt:
            amt[c] = 0.0
    loans = pd.DataFrame({"borrowed": (amt["59"] + amt["61"]) > 0, "borrowed_amt": amt["59"] + amt["61"],
                          "repaid": amt["2.1.1.4.1"] + amt["2.1.1.4.2"], "savings_used": amt["60"]})
    purpose = k12[(k12.NOMVNEW == "21") & S.filled(k12.KOD)]
    food = (purpose.KOD == "3").groupby([purpose.NOMER, purpose.Q]).any().rename("food_loan")
    anyp = purpose.groupby(["NOMER", "Q"]).size().gt(0).rename("purpose_given")
    hh = (k0.set_index(key).join([inc_form, inc_naive, gr3, spend, spend_dd, loans, food, anyp, rep])
          .reset_index())
    for c in ("income", "income_naive", "gr3", "spend", "spend_dedup", "borrowed_amt", "repaid", "savings_used",
              "rep_rows", "kv1_rows", "rep_value"):
        hh[c] = hh[c].fillna(0)
    for c in ("borrowed", "food_loan", "purpose_given"):
        hh[c] = hh[c].fillna(False).astype(bool)
    hh["year"] = y
    hh["region"] = hh.TE.map(S.REGION)
    return hh, pers.merge(k0[key + ["TE"]], on=key)


SECTIONS = {"kv_vopr1": "1.1 non-food goods", "kv_vopr2": "1.2 utilities", "kv_vopr3": "1.2 communication",
            "kv_vopr4": "1.2 education", "kv_vopr5": "1.2 health", "kv_vopr6": "1.2-1.3 leisure, personal, financial",
            "kv_vopr7": "1.2 transport", "kv_vopr11": "3 income", "kv_vopr12": "2 loans and savings"}


def coverage(y):
    """Share of participating households with at least one record in each section, by region and quarter
    (then averaged over quarters). A section that a region leaves almost empty is the same kind of break as the
    child module in D-002: the indicator for that region rests on a few households."""
    k0 = stack(y, "kv_vopr0")
    k0 = k0[k0.REZ == "1"][["NOMER", "Q", "TE"]].drop_duplicates(["NOMER", "Q"])
    rows = []
    for name, label in SECTIONS.items():
        t = stack(y, name)[["NOMER", "Q"]].drop_duplicates().assign(has=True)
        m = k0.merge(t, on=["NOMER", "Q"], how="left")
        m["has"] = m["has"].fillna(False).astype(bool)
        for te, g in m.groupby("TE"):
            rows.append({"year": y, "te": te, "region": S.REGION.get(te, te), "section": name, "label": label,
                         "households_pct": round(100 * g.has.mean(), 1)})
    return rows


def summarise(g, p):
    pos = g[g.income > 0]
    dsr = pos.repaid / pos.income
    bor = g[g.borrowed]
    withp = g[g.purpose_given]
    return {
        "household_quarters": len(g),
        "zero_income_pct": round(100 * (g.income <= 0).mean(), 1),
        "income_mean": round(g.income.mean()),
        "gr3_added_pct": round(100 * g.gr3.sum() / g.income.sum(), 2),
        "gr3_gt_gr2_pct": round(100 * p.bad[p.has].mean(), 1) if p.has.any() else np.nan,
        "gr3_rows": int(p.has.sum()),
        "savings_rate_naive_pct": round(100 * (1 - g.spend.sum() / g.income_naive.sum()), 1),
        "savings_rate_form_pct": round(100 * (1 - g.spend.sum() / g.income.sum()), 1),
        "savings_rate_form_dedup_pct": round(100 * (1 - g.spend_dedup.sum() / g.income.sum()), 1),
        "kv1_repeat_rows_pct": round(100 * g.rep_rows.sum() / max(1, g.kv1_rows.sum()), 1),
        "kv1_repeat_value_pct_of_spend": round(100 * g.rep_value.sum() / g.spend.sum(), 1),
        "borrowed_pct": round(100 * g.borrowed.mean(), 1),
        "repaying_pct": round(100 * (g.repaid > 0).mean(), 1),
        "debt_service_median_pct": round(100 * dsr[pos.repaid > 0].median(), 1) if (pos.repaid > 0).any() else np.nan,
        "burden_gt30_pct": round(100 * (dsr > BURDEN).mean(), 1),
        "loans_with_purpose": int(len(withp)),
        "food_loan_pct_of_purpose": round(100 * withp.food_loan.mean(), 1) if len(withp) else np.nan,
        "food_loan_pct_of_households": round(100 * g.food_loan.mean(), 2),
        "borrowed_amt_to_income_pct": round(100 * bor.borrowed_amt.sum() / max(1, bor.income.sum()), 1) if len(bor) else np.nan,
    }


rows, nat, cov = [], [], []
for y in YEARS:
    cov += coverage(y)
    hh, pers = hh_year(y)
    pos = hh[(hh.income > 0) & (hh.spend > 0)]
    li, ls = np.log(pos.income), np.log(pos.spend)
    reg = pos.groupby("TE")[["income", "spend"]].mean()
    corr = {"corr_log_income_spend_household": round(float(np.corrcoef(li, ls)[0, 1]), 3),
            "corr_income_spend_region_means": round(float(np.corrcoef(reg.income, reg.spend)[0, 1]), 3)}
    for te, g in hh.groupby("TE"):
        rows.append({"year": y, "te": te, "region": S.REGION.get(te, te), **summarise(g, pers[pers.TE == te])})
    n = {"year": y, **summarise(hh, pers), **corr}
    r = 1 - n["savings_rate_form_pct"] / 100
    n["recorded_spend_to_income_pct"] = round(100 * r, 1)
    n["implied_spend_to_income_if_food_half_pct"] = round(100 * r / (1 - FOOD_SHARE), 1)
    rest = hh[hh.TE != AKTOBE]
    ak = hh[hh.TE == AKTOBE]
    wp = hh[hh.purpose_given]
    n["food_loan_pct_of_purpose_without_aktobe"] = round(100 * rest[rest.purpose_given].food_loan.mean(), 1)
    n["aktobe_share_of_food_loans_pct"] = round(100 * ak.food_loan.sum() / max(1, hh.food_loan.sum()), 1)
    n["aktobe_share_of_households_pct"] = round(100 * len(ak) / len(hh), 1)
    n["aktobe_food_loan_pct_of_purpose"] = round(100 * ak[ak.purpose_given].food_loan.mean(), 1)
    n["regions_food_loan_range_without_aktobe"] = None
    LOWCOV = ["47", "61", "79", "31"]  # filled in from finance_section_coverage.csv below; listed here to keep one pass
    keep = hh[~hh.TE.isin(LOWCOV)]
    n["repaying_pct_without_low_coverage"] = round(100 * (keep.repaid > 0).mean(), 1)
    n["borrowed_pct_without_low_coverage"] = round(100 * keep.borrowed.mean(), 1)
    n["burden_gt30_pct_without_low_coverage"] = round(100 * ((keep.repaid / keep.income.where(keep.income > 0)) > BURDEN).mean(), 1)
    nat.append(n)

t = pd.DataFrame(rows)
for n in nat:
    r = t[(t.year == n["year"]) & (t.te != AKTOBE)].food_loan_pct_of_purpose
    n["regions_food_loan_range_without_aktobe"] = [float(r.min()), float(r.median()), float(r.max())]
    kv = t[t.year == n["year"]].kv1_repeat_rows_pct
    n["kv1_repeat_rows_region_range"] = [float(kv.min()), float(kv.max())]
    g3 = t[t.year == n["year"]].gr3_added_pct
    n["gr3_added_region_max"] = {"region": t.loc[g3.idxmax(), "region"], "pct": float(g3.max())}
t.to_csv(OUT / "finance_impact.csv", index=False)
# section coverage flags: a region below half the median of the other regions, in at least 3 of the 4 years
c = pd.DataFrame(cov)
c["median_others"] = c.apply(lambda r: c[(c.year == r.year) & (c.section == r.section) & (c.te != r.te)].households_pct.median(), axis=1)
c["min_others"] = c.apply(lambda r: c[(c.year == r.year) & (c.section == r.section) & (c.te != r.te)].households_pct.min(), axis=1)
c["low"] = c.households_pct < 0.5 * c.median_others
yrs = c.groupby(["te", "section"]).agg(years_low=("low", "sum"), years=("year", "nunique")).reset_index()
c = c.merge(yrs, on=["te", "section"])
c["flag"] = c.low & (c.years_low >= 3)
c.to_csv(OUT / "finance_section_coverage.csv", index=False)
print(c[c.flag].to_string(index=False))
flagged = sorted(c[c.flag & (c.section == "kv_vopr12")].te.unique())
assert flagged == sorted(["47", "61", "79", "31"]), f"low-coverage regions changed: {flagged}; update LOWCOV"
json.dump(nat, open(OUT / "finance_impact_national.json", "w"), ensure_ascii=False, indent=1, default=float)
json.dump(nat, open(OUT / "finance_impact_national.json", "w"), ensure_ascii=False, indent=1, default=float)
pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 40)
print(t[t.year == 2024].sort_values("food_loan_pct_of_purpose").to_string(index=False))
print(json.dumps(nat, ensure_ascii=False, indent=1, default=float))
