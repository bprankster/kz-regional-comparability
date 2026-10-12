"""One table for the 'problem -> impact -> fix' view, built only from outputs that already exist.
Nothing is recomputed: rows = out/scorecard_issues.csv (same order, same numbers as the console's data.json),
texts = console/data.json (Russian, as in the console), impact numbers = files written by code.
Usage: python viz/viz_export.py out/ console/data.json DEST/"""
import json, sys
from pathlib import Path
import pandas as pd

OUT, DATA, DEST = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
DEST.mkdir(parents=True, exist_ok=True)
d = json.load(open(DATA, encoding="utf-8"))
iss = pd.read_csv(OUT / "scorecard_issues.csv")
assert len(iss) == len(d["issues"]), "scorecard and console data out of step: rebuild the console first"
REG = {r["key"]: r["ru"] for r in d["regions"]}
RULE = {r["id"]: r for r in d["rules"]}
CASE = {c["id"]: c for c in d["cases"]}

# case link: rule lists of the case files first; for ML rows the column named in the case
# (priority order, so Mangystau 2024 'GR25, ZT, GR33' goes to C4, Turkistan 2024 'GR25, GR40, GR41' to C1)
case_of_rule = {r: c["id"] for c in d["cases"] for r in c["rules"]}
ML_CASE = [("ZT", "C4"), ("DH_DATROZH_2", "C6"), ("GR40", "C1"), ("GR41", "C1"), ("KOL_K", "C5"), ("GR25", "C3")]
def case_for(x):
    if x.rule_id in case_of_rule:
        return case_of_rule[x.rule_id]
    cols = [v.strip() for v in str(x.example_column).split(",")]
    if x.evidence == "region vs rest (ML)":
        if x.form == "T001" and x.region == "Almaty oblast":
            return "C10"
        return next((c for k, c in ML_CASE if k in cols), None)
    if x.evidence == "code shift (decoder)":
        return "C9" if (x.region == "Kyzylorda" and "UROV" in cols) else None
    if x.evidence == "regional shares, two forms":
        return "C1"
    return None

# impact numbers: only where a script computed them
ch = pd.read_csv(OUT / "child_impact.csv").set_index(["region", "year"])
num = json.load(open(OUT / "case_numbers.json", encoding="utf-8"))
dc = json.load(open(OUT / "decoder_cases.json", encoding="utf-8"))
# coverage of the child indicator is the impact of MISSED children only (the reverse error, 'children' where the
# roster has none, does not shrink coverage), so it is attached to those rules and to the four cross-form flags
MISSED = {"D002-x-D008-child-household", "D002-x-D008-children", "D002-preschool-implies-children"}
XF = {(r.region, int(r.year)) for r in iss[iss.rule_id == "D002-x-D008-children"].itertuples()}
def missed_children(x):
    return x.rule_id in MISSED or (x.evidence == "region vs rest (ML)" and (x.region, int(x.year)) in XF)
def impact(case, x):
    if case == "C1" and missed_children(x) and (x.region, x.year) in ch.index:
        r = ch.loc[(x.region, x.year)]
        return (float(r.coverage_pct), "% домохозяйств с детьми (по Д-008), ответивших на часть 4",
                f"охват {r.coverage_pct:.1f}%, погрешность индикатора ±{r.moe_pp:.1f} п.п.", "out/child_impact.csv")
    if case == "C4" and x.region == "Mangystau" and x.year == 2024 and x.form == "D002":
        return (float(num["mang_gr1_2024"].rstrip("%")), "% ставят удовлетворённости жизнью 10 из 10",
                f"{num['mang_gr1_2024']} против {num['mang_gr1_rest']} в остальных", "out/case_numbers.json")
    if case == "C9" and str(x.year) in dc["kyzylorda"]:
        k = dc["kyzylorda"][str(x.year)]
        return (float(k["kyzylorda_pct_code7"]), "% детей 7–10 лет с кодом 7 вместо 1",
                f"{k['kyzylorda_pct_code7']}% против не больше {k['other_regions_max']}% в других регионах", "out/decoder_cases.json")
    if case == "C10" and x.year == 2024:
        a = dc["almaty"]["2024"]
        return (float(a["no_contract_status2_almaty_pct"]), "% работников у физлиц без письменного договора",
                f"{a['no_contract_status2_almaty_pct']}% против {a['no_contract_status2_rest_pct']}% в остальных", "out/decoder_cases.json")
    return (None, "", "", "")

EVID = {"rule check": "правило из анкеты", "region vs rest (ML)": "ML: регион против остальных",
        "code shift (decoder)": "декодер: сдвиг кода", "regional shares, two forms": "две формы: доли по регионам",
        "section coverage (finance case)": "охват раздела займов (дело C11)"}
TRUST = {"holds in synthetic data": "A — держится на синтетике", "check on real records": "B — проверить на реальных записях"}
for _k in set(iss.status) - set(TRUST): TRUST[_k] = "B — проверить на реальных записях"
rows = []
for k, ((_, x), i) in enumerate(zip(iss.iterrows(), d["issues"]), 1):
    assert (i["region"], i["year"], i["rule"]) == (x.region, int(x.year), x.rule_id)
    case = i["case"]   # same link as the console (build_console.py)
    c = CASE.get(case, {})
    val, unit, text, src = impact(case, x)
    rr, rest = x.rate_region, x.rate_rest
    ml = x.evidence != "rule check"
    rows.append({
        "issue_id": f"I{k:03d}", "region": x.region, "region_ru": REG.get(x.region, x.region), "year": int(x.year),
        "form": x.form, "form_ru": i["formRu"],
        "case_id": case or "", "case_name": c.get("title", ""),
        "rule_name": x.rule_id, "rule_text_ru": i["ru"], "check_type_ru": i["type"], "evidence_ru": EVID.get(x.evidence, x.evidence),
        "column": i["col"],
        "affected_records": None if pd.isna(x.records) else int(x.records),
        "affected_share": None if (pd.isna(rr) or x.evidence == "code shift (decoder)") else float(rr),
        "rest_share": None if (pd.isna(rest) or x.evidence == "code shift (decoder)") else float(rest),
        "share_meaning": ("% записей региона, нарушающих правило (из тех, к кому оно относится)" if not ml else
                          "% записей региона с отличающимся ответом" if x.evidence == "region vs rest (ML)" else
                          "% домохозяйств с «есть дети» (GR40); rest_share — % с ребёнком в Д-008" if x.evidence == "regional shares, two forms" else "сдвиг кода: доли нет, см. кейс C9"),
        "trust_level": TRUST[x.status], "trust_reason_ru": i["trust"],
        "rule_confidence": RULE.get(x.rule_id, {}).get("conf", ""),
        "indicator_ru": c.get("indicator", ""), "fix_ru": c.get("fix", ""),
        "impact_value": val, "impact_unit": unit, "impact_text": text, "impact_source": src,
    })
df = pd.DataFrame(rows)
df.to_csv(DEST / "statquo_issues_for_viz.csv", index=False, encoding="utf-8-sig")

nat = json.load(open(OUT / "child_impact_national.json"))
CASE_IMPACT_OLD = {
 "C1": "охват индикатора по стране: " + ", ".join(f"{r['coverage_national']}% ({r['year']})" for r in nat) + "; минимум по регионам — в строках issues",
 "C4": f"Мангистау 2024: 10 из 10 — {num['mang_gr1_2024']} против {num['mang_gr1_rest']}",
 "C9": f"Кызылорда: код 7 у {dc['kyzylorda']['2023']['kyzylorda_pct_code7']}% (2023) и {dc['kyzylorda']['2024']['kyzylorda_pct_code7']}% (2024) детей 7–10 лет",
 "C10": f"Алматинская обл. 2024: без письменного договора {dc['almaty']['2024']['no_contract_status2_almaty_pct']}% против {dc['almaty']['2024']['no_contract_status2_rest_pct']}%",
}
cases = pd.DataFrame([{
    "case_id": c["id"], "case_name": c["title"], "status": c["status"], "finding_ru": c["finding"],
    "indicator_ru": c["indicator"], "cause_ru": c["cause"], "fix_ru": c["fix"],
    "issues": int((df.case_id == c["id"]).sum()),
    "regions": ", ".join(sorted(df.loc[df.case_id == c["id"], "region_ru"].unique())),
    "impact_text": "; ".join(f"{a} — {b}" for a, b in d.get("caseImpact", {}).get(c["id"], [])),
    "scope": "по регионам" if (df.case_id == c["id"]).any() else "нет строк в скоркарте (общий кейс или найден отдельным расчётом) — см. finding_ru",
} for c in d["cases"]])
cases.to_csv(DEST / "statquo_cases_for_viz.csv", index=False, encoding="utf-8-sig")

DICT = [
 ("issue_id", "номер проблемы (строка скоркарта)"), ("region / region_ru", "регион (ключ / по-русски, как в консоли)"),
 ("year", "год"), ("form / form_ru", "форма обследования"),
 ("case_id / case_name", "кейс C1–C10, к которому относится проблема; пусто — отдельный кейс не написан"),
 ("rule_name", "id правила (rules/*.json) или метод (ML, декодер)"), ("rule_text_ru", "что проверяет правило, по-русски"),
 ("check_type_ru", "тип проверки"), ("evidence_ru", "чем найдено"), ("column", "столбец-пример"),
 ("affected_records", "сколько записей региона нарушают правило; пусто для ML (там нет одного правила)"),
 ("affected_share / rest_share", "доля в регионе / в остальной стране, %; смысл — в share_meaning"),
 ("trust_level", "A — держится на синтетике; B — проверить на реальных записях (тот же статус, что в консоли)"),
 ("trust_reason_ru", "почему такой уровень доверия"), ("rule_confidence", "уверенность в самом правиле (high / medium) из файла правил"),
 ("indicator_ru", "какой показатель затронут (из кейса)"), ("fix_ru", "рекомендация (из кейса)"),
 ("impact_value / impact_unit / impact_text", "число влияния — только где его посчитал код; иначе пусто"),
 ("impact_source", "файл, из которого взято число"),
]
dic = pd.DataFrame(DICT, columns=["поле", "что значит"])
with pd.ExcelWriter(DEST / "statquo_issues_for_viz.xlsx", engine="openpyxl") as w:
    df.to_excel(w, sheet_name="issues", index=False); cases.to_excel(w, sheet_name="cases", index=False); dic.to_excel(w, sheet_name="поля", index=False)
    for ws in w.book.worksheets:
        ws.freeze_panes = "A2"
        for col in ws.columns:
            ws.column_dimensions[col[0].column_letter].width = min(60, max(10, max(len(str(c.value or "")) for c in col[:50]) + 2))
print("issues", len(df), "linked to a case", int((df.case_id != "").sum()), "with impact number", int(df.impact_value.notna().sum()))
print(df.case_id.replace("", "—").value_counts().to_dict()); print(df.trust_level.value_counts().to_dict())
