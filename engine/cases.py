"""Case files. The wording was written by the LLM (Claude); every number is computed here from the engine's
outputs and the records, and filled into the text. Re-running on the real records refreshes every number.

    python engine/cases.py DATA_DIR out/
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

import statquo as S


def pct(x):
    return f"{x:.1f}%"


def facts(D, out):
    out = Path(out)
    F = {}
    xf = pd.read_csv(out / "D002_cross_form_flags.csv")
    c = xf[xf.rule_id == "D002-x-D008-children"].set_index(["region", "year"])
    for reg, y in [("Ulytau", 2024), ("Almaty city", 2024), ("Aktobe", 2023), ("Zhetysu", 2023), ("Ulytau", 2023),
                   ("Almaty city", 2023), ("Aktobe", 2024), ("Zhetysu", 2024)]:
        F[f"gr40_{reg}_{y}"] = pct(c.loc[(reg, y), "this_share"])
        F[f"roster_{reg}_{y}"] = pct(c.loc[(reg, y), "other_share"])
    F["r2_2024"] = f"{c.xs(2024, level='year')['r2_other_regions'].iloc[0]:.2f}"
    F["r2_2023"] = f"{c.xs(2023, level='year')['r2_other_regions'].iloc[0]:.2f}"
    fl = pd.read_csv(out / "D002_region_flags.csv")
    p = fl[fl.rule_id == "D002-preschool-implies-children"].set_index(["region", "year"])
    for reg, y in [("Ulytau", 2024), ("Almaty city", 2024), ("Zhetysu", 2023), ("Zhetysu", 2024)]:
        F[f"pre_{reg}_{y}"] = pct(p.loc[(reg, y), "rate_region"])
    res = pd.read_csv(out / "D002_results.csv")
    x = res[(res.rule_id == "D002-preschool-implies-children") & (res.year == 2024)]
    rest = x[~x.region.isin(p.xs(2024, level="year").index)]
    F["pre_rest_2024"] = pct(100 * rest.violations.sum() / rest.applicable.sum())
    # the same filter, household by household: D-002 joined to the D-008 roster on NOMER
    hh = res[res.rule_id.isin(["D002-x-D008-child-household", "D002-x-D008-nochild-household"])]
    for rid, key in (("D002-x-D008-child-household", "hh"), ("D002-x-D008-nochild-household", "hhno")):
        g = hh[hh.rule_id == rid].set_index(["region", "year"])
        for (reg, y), r in g.iterrows():
            F[f"{key}_{reg}_{y}"] = f"{int(r.violations)} of {int(r.applicable)}"
            F[f"{key}pct_{reg}_{y}"] = pct(100 * r.violations / max(r.applicable, 1))
        for y in (2023, 2024):
            gy = hh[(hh.rule_id == rid) & (hh.year == y)]
            F[f"{key}_agree_{y}"] = pct(100 - 100 * gy.violations.sum() / gy.applicable.sum())

    # Rent: 'not relevant' vs owners
    rent = pd.read_csv(out / "D002_cross_form.csv")
    r24 = rent[(rent.rule_id == "D002-x-D006-owners-rent") & (rent.year == 2024)].set_index("region")
    F["rent_nr_min"] = pct(r24.this_share.min())
    F["rent_nr_min_region"] = r24.this_share.idxmin()
    F["rent_nr_max"] = pct(r24.this_share.max())
    F["rent_nr_max_region"] = r24.this_share.idxmax()
    F["owners_min"], F["owners_max"] = pct(r24.other_share.min()), pct(r24.other_share.max())
    # lower bound: non-renters include all owners, so 'not relevant' should be at least the owners' share
    rf = pd.read_csv(out / "D002_cross_form_flags.csv")
    rf = rf[rf.rule_id == "D002-x-D006-owners-rent"]
    for y in (2023, 2024):
        g = rf[rf.year == y]
        F[f"rent_below_{y}"] = int((g.side == "below lower bound").sum())
        F[f"rent_within_{y}"] = ", ".join(g[g.side == "within bounds"].region)
        F[f"rent_above_{y}"] = int((g.side == "above upper bound").sum())
        F[f"rent_regions_{y}"] = int(len(g))
    r23 = rent[(rent.rule_id == "D002-x-D006-owners-rent") & (rent.year == 2023)].set_index("region")
    F["rent_kyz_2023"], F["rent_kyz_2024"] = pct(r23.this_share["Kyzylorda"]), pct(r24.this_share["Kyzylorda"])
    F["upper_min_2024"] = pct(r24.upper_share.min())

    # decoder: regional code shifts and the two cases it explains
    dpath = out / "decoder_cases.json"
    if dpath.exists():
        dc = json.load(open(dpath))
        kz, al = dc["kyzylorda"], dc["almaty"]
        for y in ("2023", "2024"):
            F[f"kz7_{y}"] = pct(kz[y]["kyzylorda_pct_code7"])
            F[f"kz7_rest_max_{y}"] = pct(kz[y]["other_regions_max"])
            F[f"al_s2c2_{y}"], F[f"al_s2c5_{y}"] = al[y]["status2_code2"], al[y]["status2_code5"]
            F[f"al_oral5_out_{y}"] = pct(al[y]["oral_among_code5_outside_almaty_pct"])
        F["al_nocontract_2024"] = pct(al["2024"]["no_contract_status2_almaty_pct"])
        F["al_nocontract_rest_2024"] = pct(al["2024"]["no_contract_status2_rest_pct"])

    # Kazakh/Russian wording, Part 2 Q5
    rows = {}
    for y in (2023, 2024):
        sub = S.load(D, "D002", y)["subject"]
        t = pd.crosstab(sub.TE.map(S.REGION), sub.GR25, normalize="index") * 100
        rows[f"code2 {y}"], rows[f"code3 {y}"] = t["2"], t["3"]
    g = pd.DataFrame(rows)
    g.to_csv(out / "case_GR25_shares.csv")
    F["gr25_min"], F["gr25_min_region"] = pct(g["code2 2024"].drop("Mangystau").min()), g["code2 2024"].drop("Mangystau").idxmin()
    F["gr25_max"], F["gr25_max_region"] = pct(g["code2 2024"].max()), g["code2 2024"].idxmax()
    F["gr25_r_2023"] = f"{np.corrcoef(g['code2 2023'], g['code3 2023'])[0, 1]:.2f}"

    # Mangystau 2024 defaults
    sw = pd.read_csv(out / "compare_region_sweep.csv")
    m = sw[(sw.form == "D002") & (sw.table == "subject") & (sw.region == "Mangystau")].drop_duplicates(["variable", "year"]).set_index(["variable", "year"])
    F["mang_zt_2024"] = pct(m.loc[("ZT", 2024), "share_region"])
    F["mang_zt_rest"] = pct(m.loc[("ZT", 2024), "share_rest_same"])
    F["mang_gr1_2024"] = pct(m.loc[("GR1", 2024), "share_region"])
    F["mang_gr1_rest"] = pct(m.loc[("GR1", 2024), "share_rest_same"])
    def zt(form, region, year):
        r = sw[(sw.form == form) & (sw.variable == "ZT") & (sw.region == region) & (sw.year == year)].iloc[0]
        return pct(r.share_region), pct(r.share_rest_same)
    F["ast_zt_d002_2023"], F["zt_rest_d002_2023"] = zt("D002", "Astana", 2023)
    F["ast_zt_d006_2023"], F["zt_rest_d006_2023"] = zt("D006", "Astana", 2023)
    F["tur_zt_d002_2023"], _ = zt("D002", "Turkistan", 2023)

    # Pavlodar leading zeros
    f6 = pd.read_csv(out / "D006_region_flags.csv")
    k = f6[(f6.rule_id == "D006-KOL_K-format") & (f6.region == "Pavlodar")].set_index("year")
    F["pav_2023"], F["pav_2024"] = pct(k.loc[2023, "rate_region"]), pct(k.loc[2024, "rate_region"])
    F["pav_rest_2023"], F["pav_rest_2024"] = pct(k.loc[2023, "rate_rest"]), pct(k.loc[2024, "rate_rest"])

    # Astana birth month default (T-001)
    t = sw[(sw.form == "T001") & (sw.variable == "DH_DATROZH_2") & (sw.region == "Astana")].set_index("year")
    F["ast_jan_2023"], F["ast_jan_2024"] = pct(t.loc[2023, "share_region"]), pct(t.loc[2024, "share_region"])
    F["ast_jan_rest"] = pct(t.loc[2024, "share_rest_same"])

    # Kostanay cars
    cars = {}
    for y in (2023, 2024):
        d6 = S.load(D, "D006", y)["rio"]
        cars[y] = S.num(d6.TDP35).groupby(d6.TE.map(S.REGION)).mean()
    F["kos_cars_2023"], F["kos_cars_2024"] = f"{cars[2023]['Kostanay']:.1f}", f"{cars[2024]['Kostanay']:.1f}"
    F["cars_median_2024"] = f"{cars[2024].drop('Kostanay').median():.1f}"

    # National rule breaks
    r2 = pd.read_csv(out / "D002_results.csv")
    def nat(df, rid, y):
        x = df[(df.rule_id == rid) & (df.year == y)]
        return pct(100 * x.violations.sum() / max(1, x.applicable.sum()))
    F["p2q2_2023"], F["p2q2_2024"] = nat(r2, "D002-P2Q2-required", 2023), nat(r2, "D002-P2Q2-required", 2024)
    F["minor89_2024"] = nat(r2, "D002-child-economic-89", 2024)
    F["mobile_2024"] = nat(r2, "D002-mobile-implies-internet", 2024)
    F["voz15_2024"] = nat(r2, "D002-VOZ-respondent15", 2024)
    r8 = pd.read_csv(out / "D008_results.csv")
    F["d008_code_2024"] = nat(r8, "D008-PR_IZ-domain", 2024)
    F["d008_zt_2024"] = nat(r8, "D008-ZT-required", 2024)
    r4 = pd.read_csv(out / "D004_results.csv")
    F["d004_purpose_2023"], F["d004_purpose_2024"] = nat(r4, "D004-2.1-needs-new-loan", 2023), nat(r4, "D004-2.1-needs-new-loan", 2024)
    r6 = pd.read_csv(out / "D006_results.csv")
    F["d006_age0_2024"] = nat(r6, "D006-Q8-adult", 2024)
    finance(out, F)
    return F


def finance(out, F):
    """Numbers for case C11 (household finances), from analysis/finance_impact.py. Skipped if not run."""
    nj = out / "finance_impact_national.json"
    if not nj.exists():
        return
    N = {n["year"]: n for n in json.load(open(nj, encoding="utf-8"))}
    t = pd.read_csv(out / "finance_impact.csv")
    cv = pd.read_csv(out / "finance_section_coverage.csv", dtype={"te": str})
    n = N[2024]
    F["fin_saving_naive"] = pct(n["savings_rate_naive_pct"])
    F["fin_spend_income"] = pct(n["recorded_spend_to_income_pct"])
    F["fin_spend_income_food"] = pct(n["implied_spend_to_income_if_food_half_pct"])
    F["fin_gr3_nat"] = f'{n["gr3_added_pct"]:.1f}%'
    g = t[t.year == 2024].set_index("region")
    F["fin_gr3_max"], F["fin_gr3_max_region"] = f'{g.gr3_added_pct.max():.1f}%', g.gr3_added_pct.idxmax()
    F["fin_gr3_rule"] = pct(n["gr3_gt_gr2_pct"])
    F["fin_food_nat"], F["fin_food_wo_aktobe"] = pct(n["food_loan_pct_of_purpose"]), pct(n["food_loan_pct_of_purpose_without_aktobe"])
    F["fin_aktobe_share_food"], F["fin_aktobe_share_hh"] = pct(n["aktobe_share_of_food_loans_pct"]), pct(n["aktobe_share_of_households_pct"])
    F["fin_aktobe_food"] = pct(n["aktobe_food_loan_pct_of_purpose"])
    c = cv[(cv.year == 2024) & (cv.section == "kv_vopr12")].set_index("region")
    F["fin_cov_mang"], F["fin_cov_median"] = pct(c.loc["Mangystau", "households_pct"]), pct(c.loc["Mangystau", "median_others"])
    low = c[c.flag].households_pct
    F["fin_cov_low_regions"] = ", ".join(sorted(low.index))
    F["fin_cov_low_range"] = f"{low.min():.1f}–{low.max():.1f}%"
    allmang = cv[(cv.section == "kv_vopr12") & (cv.region == "Mangystau")].households_pct
    F["fin_cov_mang_range"] = f"{allmang.min():.1f}–{allmang.max():.1f}%"
    F["fin_repay_nat"], F["fin_repay_wo_low"] = pct(n["repaying_pct"]), pct(n["repaying_pct_without_low_coverage"])
    F["fin_burden_nat"], F["fin_burden_wo_low"] = pct(n["burden_gt30_pct"]), pct(n["burden_gt30_pct_without_low_coverage"])
    F["fin_rep_rows"], F["fin_rep_value"] = pct(n["kv1_repeat_rows_pct"]), pct(n["kv1_repeat_value_pct_of_spend"])
    F["fin_rep_range"] = "{:.1f}–{:.1f}%".format(*n["kv1_repeat_rows_region_range"])
    F["fin_corr_hh"] = f'{n["corr_log_income_spend_household"]:.2f}'


CASES = [
    {"id": "C1", "title": "Child module: the filter question is filled differently by region",
     "forms": "D-002 Part 4, D-008 roster", "type": "Routing filter applied inconsistently",
     "status": "holds in synthetic data",
     "finding": "In 2024, {gr40_Ulytau_2024} of Ulytau households are marked 'has children under 18' (GR40), against {roster_Ulytau_2024} with a member under 18 in the D-008 roster; Almaty city {gr40_Almaty city_2024} against {roster_Almaty city_2024}. The other regions follow the roster closely (R² {r2_2024}). Aktobe shows the same break in 2023 ({gr40_Aktobe_2023} against {roster_Aktobe_2023}) and recovers in 2024 ({gr40_Aktobe_2024}). Inside D-002 alone, {pre_Ulytau_2024} of Ulytau and {pre_Almaty city_2024} of Almaty city households that report a pre-school child not attending kindergarten are coded 'no children' (other regions together {pre_rest_2024}). Joined household by household on NOMER (D-002 to the D-008 roster), the same break names the households: {hh_Almaty city_2024} households with a child in the roster are coded 'no children' in Almaty city ({hhpct_Almaty city_2024}), {hh_Ulytau_2024} in Ulytau ({hhpct_Ulytau_2024}), {hh_Aktobe_2023} in Aktobe in 2023 ({hhpct_Aktobe_2023}) and {hh_Zhetysu_2023} in Zhetysu in 2023 ({hhpct_Zhetysu_2023}); in the country as a whole GR40 agrees with the roster for {hh_agree_2024} of households with children. The reverse also appears: households with no one under 18 in the roster coded 'has children' in Turkistan ({hhnopct_Turkistan_2024}, 2024) and Kyzylorda ({hhnopct_Kyzylorda_2023}, 2023), which may also come from birth years in the roster.",
     "indicator": "Child multidimensional poverty (D-002 Part 4) for these regions and years rests on a small, self-selected share of households with children.",
     "cause": "GR40 is not printed on the questionnaire: the file structure says it was added ('В форме нет такого вопроса (добавили)'). Without a printed question, each region fills it by local practice.",
     "fix": "Derive GR40 from the D-008 roster in processing, or print it on the form; add the rule 'Part 3 Q17 = 1 ⇒ GR40 = 1' to data entry. On the real records, list the households from the record-link query (rules export) for the regional offices to recheck.",
     "rules": ["D002-preschool-implies-children", "D002-x-D008-children", "D002-x-D008-child-household",
               "D002-x-D008-nochild-household", "D002-P4-skip", "D002-P4-required"]},
    {"id": "C2", "title": "Rent: one situation, two codes",
     "forms": "D-002 Part 3 Q1.1, D-006 ownership", "type": "Answer meaning coded differently",
     "status": "holds in synthetic data",
     "finding": "A household that does not rent cannot be in rent arrears, so 'not relevant' should be at least the share of owners (D-006: {owners_min}–{owners_max} in every region, 2024) and at most 100 minus those paying for their dwelling (at least {upper_min_2024}). No region is above the upper bound. Only {rent_within_2024} reach the lower bound in 2024 ({rent_within_2023} in 2023); the other {rent_below_2024} of {rent_regions_2024} regions code most owners 3 'no', down to {rent_nr_min} in {rent_nr_min_region}. Kyzylorda switched between years: {rent_kyz_2023} in 2023, {rent_kyz_2024} in 2024.",
     "indicator": "Any arrears indicator computed 'among households for whom rent is relevant' changes with the region's coding habit, not with arrears.",
     "cause": "Option 4 reads 'маңызды емес' (not important) in Kazakh and 'не актуально' (not relevant) in Russian; the instruction does not say how to code owners.",
     "fix": "One sentence in the instruction: households that do not rent are coded 4 (most regions do the opposite, so this is a national rule, not a regional error). Align the Kazakh wording with 'қолданылмайды'. Check on the real records: 'not relevant' among owners by region.",
     "rules": ["D002-x-D006-owners-rent", "D002-doc-kk-ru-P3Q1opt4"]},
    {"id": "C3", "title": "Kazakh and Russian versions give code 2 opposite meanings",
     "forms": "D-002 Part 2 Q5", "type": "Questionnaire wording", "status": "documentation; pattern holds in synthetic data",
     "finding": "Code 2 is 'кем дегенде айына бір рет' (at least once a month) in Kazakh and 'реже чем раз в месяц' (less than once a month) in Russian. Its share runs from {gr25_min} ({gr25_min_region}) to {gr25_max} ({gr25_max_region}) in 2024, and in 2023 it trades off against code 3 across regions (r = {gr25_r_2023}), as the Kazakh overlap predicts.",
     "indicator": "Social contact frequency, an input to social isolation measures.",
     "cause": "Translation error in the form. Seven more Kazakh/Russian mismatches in the same form, checked against its text: rent arrears option 4, internet-use codes 1 and 2, air quality (garbage vs emissions), the debt reason (or vs related to), furniture (and vs or), and 'outside the home' missing in Kazakh.",
     "fix": "Correct the Kazakh option text; recode by interview language for past years if the language is recorded.",
     "rules": ["D002-doc-kk-ru-P2Q5opt2"]},
    {"id": "C4", "title": "The same default time in several regions and forms",
     "forms": "D-002, D-006", "type": "Default or interviewer-entered values", "status": "holds in synthetic data",
     "finding": "{mang_zt_2024} of Mangystau's D-002 forms in 2024 record '1–2 hours' to complete (rest of country {mang_zt_rest}), and {mang_gr1_2024} score life satisfaction 10 of 10 (rest {mang_gr1_rest}). The same time code dominates Astana in 2023 in two forms (D-002 {ast_zt_d002_2023}, D-006 {ast_zt_d006_2023}, against {zt_rest_d002_2023} and {zt_rest_d006_2023} elsewhere) and Turkistan's D-002 in 2023 ({tur_zt_d002_2023}).",
     "indicator": "Life satisfaction and every Part 1 score for Mangystau 2024.",
     "cause": "A pre-filled default in the entry software, or values entered by interviewers.",
     "fix": "Break down by interviewer on the real records; block default values in entry software.",
     "rules": []},
    {"id": "C5", "title": "Pavlodar enters counts with a leading zero",
     "forms": "D-006 Q4 (rooms)", "type": "Data-entry signature", "status": "holds in synthetic data",
     "finding": "Room counts are written '03' instead of '3' in {pav_2023} (2023) and {pav_2024} (2024) of Pavlodar records, against {pav_rest_2023} and {pav_rest_2024} elsewhere.",
     "indicator": "None by itself: the value is the same. It marks a different entry program in one region, which is where other recording differences are likely to start.",
     "cause": "A different data-entry tool or export in Pavlodar.",
     "fix": "Standardise the export format; check Pavlodar's other D-006 fields first.",
     "rules": ["D006-KOL_K-format"]},
    {"id": "C6", "title": "Astana: half of all birth months are January",
     "forms": "T-001 (labour force survey)", "type": "Default value", "status": "holds in synthetic data",
     "finding": "Birth month is '01' for {ast_jan_2023} (2023) and {ast_jan_2024} (2024) of Astana's records, against {ast_jan_rest} elsewhere.",
     "indicator": "Exact age, so age groups at the boundaries (15, 16–72, 73+) and any age-based weighting.",
     "cause": "Month defaulted to January when unknown.",
     "fix": "Record 'unknown' explicitly; impute from D-008 where the household is in both surveys.",
     "rules": []},
    {"id": "C7", "title": "Kostanay: nine cars per household",
     "forms": "D-006 Q9 (durable goods)", "type": "Implausible counts", "status": "holds in synthetic data",
     "finding": "Among households with a value, the car count (TDP35) averages {kos_cars_2023} (2023) and {kos_cars_2024} (2024) in Kostanay, against a median of {cars_median_2024} in the other regions.",
     "indicator": "Car ownership and household asset indices.",
     "cause": "Another quantity stored in the car column (column shift or code entered as count).",
     "fix": "Add plausibility limits per item; check Kostanay's D-006 export layout.",
     "rules": []},
    {"id": "C9", "title": "Kyzylorda codes the education of children aged 7–10 its own way (code shift)",
     "forms": "D-008 roster, UROV", "type": "Answer meaning coded differently",
     "status": "holds in synthetic data",
     "finding": "The D-008 instruction codes children aged 7–10 in grades 1–4 as 1 'preschool' when they had preschool education. Kyzylorda codes {kz7_2023} (2023) and {kz7_2024} (2024) of these children 7 'no level attained'; no other region exceeds {kz7_rest_max_2023} and {kz7_rest_max_2024}. The code-shift detector finds it on its own: in Kyzylorda code 7 behaves like code 1 elsewhere.",
     "indicator": "Children's education level and any preschool-coverage figure derived from D-008.",
     "cause": "Kyzylorda appears to code current attendance (kindergarten 1, school without completed primary 7) rather than the level attained, as the instruction asks.",
     "fix": "One sentence in the interviewer instruction; check on the real records and recompute 2023–2024.",
     "rules": []},
    {"id": "C10", "title": "Almaty oblast: employer type and contract changed code together (T-001)",
     "forms": "T-001 labour force survey", "type": "Code redefined between years",
     "status": "holds in synthetic data",
     "finding": "Employees of individuals (status 2) in Almaty oblast: {al_s2c2_2023} records with employer type 2 and {al_s2c5_2023} with code 5 in 2023; {al_s2c2_2024} and {al_s2c5_2024} in 2024. In the same year their oral-agreement share is {al_nocontract_2024} against {al_nocontract_rest_2024} elsewhere. Outside the oblast code 5 changed too: oral agreements among code 5 rose from {al_oral5_out_2023} (2023) to {al_oral5_out_2024} (2024). Found first by the year-vs-year model; the decoder reads what the codes mean.",
     "indicator": "Share of workers without a written contract (informal employment), Almaty oblast and national, 2024.",
     "cause": "Code 5 seems to have been redefined in 2024, and Almaty oblast moved all employees of individuals onto it. The jobs are the same: codes 2 and 5 have near-identical profiles.",
     "fix": "Confirm the 2024 meaning of employer-type code 5 and the contract rule in the T-001 instruction; recompute informal employment.",
     "rules": []},
    {"id": "C11", "title": "Household finances (D-004): four corrections before a vulnerability indicator",
     "forms": "D-004 quarterly journal, sections 1-3", "type": "Indicator impact (second 'so what' case)",
     "status": "mixed; listed for checking",
     "finding": "Read naively, D-004 gives a household savings rate of {fin_saving_naive} (2024). (1) The journal has no food section: recorded spending is {fin_spend_income} of income; with food at half of household spending (official figure) it would be about {fin_spend_income_food}, so the 'savings rate' cannot be computed from D-004 alone. (2) Income: on the form GR3 is 'of which' under GR2, so summing all 23 columns counts agricultural sales twice: +{fin_gr3_nat} nationally, up to +{fin_gr3_max} in {fin_gr3_max_region}. (3) Loans for food: Aktobe is {fin_aktobe_share_hh} of households but {fin_aktobe_share_food} of households that borrowed for food ({fin_aktobe_food} of its loans with a stated purpose); the national share of loans taken for food is {fin_food_nat}, {fin_food_wo_aktobe} without Aktobe. (4) The loan section is filled for {fin_cov_mang} of households in Mangystau against a median of {fin_cov_median} (between {fin_cov_mang_range} in each year 2021–2024); {fin_cov_low_regions} are all low ({fin_cov_low_range}). The national share of households repaying loans is {fin_repay_nat}, {fin_repay_wo_low} without these four regions; the share with repayments above 30% of income is {fin_burden_nat} and {fin_burden_wo_low}. In the synthetic release, {fin_rep_rows} of non-food rows repeat an item (the organisers' guide names this; {fin_rep_range} by region, {fin_rep_value} of recorded spending), so regional comparisons are not affected; household-level links are weak (log income vs log spending r = {fin_corr_hh}), so only regional figures are reported.",
     "indicator": "Financial vulnerability: savings rate, spending and debt burden, borrowing for food, by region.",
     "cause": "A missing section read as zero spending; an 'of which' line summed as a separate income; one region's coding of informal loans; a section that four regions leave almost empty.",
     "fix": "Do not publish a savings rate from D-004 without the food diary; never sum GR3 with GR2 (rule D004-3-agri-within-self-employment, and a note in the file structure); Aktobe loan purpose and lender by interviewer; on the real records, loan-section coverage in Mangystau, Shymkent, Turkistan and Zhambyl against the National Bank's regional credit data.",
     "rules": ["D004-doc-no-food", "D004-3-agri-within-self-employment", "D004-doc-income-of-which",
               "D004-doc-repeated-items-synthetic", "D004-2.1-required"]},
    {"id": "C8", "title": "Rules broken everywhere: process questions for the Bureau",
     "forms": "D-002, D-004, D-006, D-008", "type": "National rule breaks", "status": "mixed; listed for checking",
     "finding": "Part 2 Q2 (reasons for low income) is blank for {p2q2_2023} (2023) and {p2q2_2024} (2024) of the respondents it applies to. {minor89_2024} of respondents under 18 rate the family's economic situation instead of coding 89, which the instruction suggests for children (a soft check: the instruction names no age). {mobile_2024} of 'no home internet, I use mobile internet' answers come from households reporting no internet use. {voz15_2024} of D-002 respondents are under 15, though the form is for 15+. In D-008, {d008_code_2024} of composition-change codes are outside the instruction's list (mostly 29), and the time-to-complete field is blank for every household ({d008_zt_2024}). In D-004, {d004_purpose_2023} (2023) and {d004_purpose_2024} (2024) of loan purpose/source rows belong to households with no credit or debt that quarter. In D-006, {d006_age0_2024} of land-plot age fields hold 0 rather than blank.",
     "indicator": "Reasons for low income; FIES-adjacent items; household composition changes; loan purposes.",
     "cause": "Questions dropped in practice, instructions not followed, or code lists in the instruction incomplete.",
     "fix": "Confirm on the real records which are real; add the rules to data entry.",
     "rules": ["D002-P2Q2-required", "D002-child-economic-89", "D002-mobile-implies-internet", "D002-VOZ-respondent15",
               "D008-PR_IZ-domain", "D008-ZT-required", "D004-2.1-needs-new-loan", "D006-Q8-adult"]},
]


def render(F):
    out = []
    for c in sorted(CASES, key=lambda c: int(c["id"][1:])):
        d = dict(c)
        try:
            d["finding"] = c["finding"].format(**F)
        except KeyError:  # numbers from a step that was not run (e.g. the decoder); the case is skipped
            continue
        out.append(d)
    return out


if __name__ == "__main__":
    D, out = sys.argv[1], Path(sys.argv[2])
    F = facts(D, out)
    json.dump(F, open(out / "case_numbers.json", "w"), ensure_ascii=False, indent=1)
    cases = render(F)
    json.dump(cases, open(out / "cases.json", "w"), ensure_ascii=False, indent=1)
    for c in cases:
        print(c["id"], c["title"]); print("  ", c["finding"]); print()
