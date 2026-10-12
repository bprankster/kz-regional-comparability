"""Collect everything the tool produced into one data file for the StatQUO Console page.

    python console/build_console.py out/ console/
Writes console/data.json; console/make_page.py embeds it into the page.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

OUT, DEST = Path(sys.argv[1]), Path(sys.argv[2])
ROOT = OUT.parent

REG = {"Abai": "Абай", "Akmola": "Акмола", "Aktobe": "Актобе", "Almaty city": "г. Алматы", "Almaty oblast": "Алматинская обл.",
       "Astana": "г. Астана", "Atyrau": "Атырау", "East Kazakhstan": "ВКО", "Karaganda": "Караганда", "Kostanay": "Костанай",
       "Kyzylorda": "Кызылорда", "Mangystau": "Мангистау", "North Kazakhstan": "СКО", "Pavlodar": "Павлодар",
       "Shymkent": "г. Шымкент", "Turkistan": "Туркестан", "Ulytau": "Улытау", "West Kazakhstan": "ЗКО",
       "Zhambyl": "Жамбыл", "Zhetysu": "Жетысу"}
# schematic tile map: (column, row), west to east, north to south
TILE = {"Kostanay": (2, 0), "North Kazakhstan": (3, 0), "Pavlodar": (5, 0),
        "West Kazakhstan": (0, 1), "Akmola": (3, 1), "Astana": (4, 1), "Abai": (6, 1), "East Kazakhstan": (7, 1),
        "Atyrau": (0, 2), "Aktobe": (1, 2), "Ulytau": (2, 2), "Karaganda": (3, 2), "Zhetysu": (6, 2),
        "Mangystau": (0, 3), "Kyzylorda": (2, 3), "Zhambyl": (4, 3), "Almaty oblast": (5, 3),
        "Turkistan": (2, 4), "Shymkent": (3, 4), "Almaty city": (5, 4)}
FORM = {"D002": "Д-002", "D004": "Д-004", "D006": "Д-006", "D008": "Д-008", "T001": "Т-001", "D002×D008": "Д-002 × Д-008"}
TYPE_RU = {"domain": "Допустимые коды", "required": "Обязательный ответ", "skip": "Переход (пропуск)", "multi_select": "Множественный выбор",
           "consistency": "Связь ответов", "cross_form": "Связь с другой формой", "doc_issue": "Противоречие в документации",
           "answer shares": "Доли ответов (ML)"}
STATUS = {"holds in synthetic data": "держится", "check on real records": "проверить"}
SYN = {"forced by the answer shares": "вытекает из долей ответов", "partly forced": "частично вытекает из долей",
       "could be broken links in the synthetic data": "может быть разрывом связей в синтетике",
       "not conditional": "доли ответов", "links between the two halves of the form": "связь двух частей формы"}
DOC = {"form": "анкета", "instruction": "инструкция", "structure": "структура файла", "codebook": "справочник"}


def nfmt(x):
    return str(x).rstrip("0").rstrip(".") if isinstance(x, float) else str(x)


def cond(c):
    if not c:
        return ""
    if "all" in c:
        return " и ".join(cond(x) for x in c["all"])
    if "any" in c:
        return " или ".join(cond(x) for x in c["any"])
    col = c.get("col", "?")
    if c.get("blank"):
        return f"{col} пусто"
    if c.get("filled"):
        return f"{col} заполнено"
    if "lt" in c:
        return f"{col} < {nfmt(c['lt'])}"
    if "ge" in c:
        return f"{col} ≥ {nfmt(c['ge'])}"
    v = c.get("in", [])
    return f"{col} = {v[0]}" if len(v) == 1 else f"{col} ∈ {{{', '.join(map(str, v))}}}"


def cols(r, n=4):
    t = r.get("targets", [])
    return ", ".join(t) if len(t) <= n else f"{', '.join(t[:n - 1])} … {t[-1]} ({len(t)})"


def ru_rule(r):
    t, a = r["type"], r.get("allowed")
    if t == "domain":
        if isinstance(a, list):
            return f"{cols(r)}: только коды {', '.join(map(str, a))}"
        if isinstance(a, dict) and ("min" in a or "max" in a):
            lo, hi = a.get("min"), a.get("max")
            rng = f"от {nfmt(lo)} до {nfmt(hi)}" if lo is not None and hi is not None else (f"не меньше {nfmt(lo)}" if lo is not None else f"не больше {nfmt(hi)}")
            return f"{cols(r)}: значение {rng}"
        if isinstance(a, dict) and a.get("codebook"):
            return f"{cols(r)}: только коды из справочника"
        if isinstance(a, dict) and a.get("no_leading_zero"):
            return f"{cols(r)}: число без ведущего нуля"
        if isinstance(a, dict) and a.get("equals_year"):
            return f"{cols(r)}: равно году обследования"
        if isinstance(a, dict) and a.get("equals_column"):
            return f"{cols(r)}: совпадает с {a['equals_column']}"
        return f"{cols(r)}: допустимые значения"
    if t == "required":
        w = r.get("when")
        what = "хотя бы один из" if r.get("mode") == "any" else "заполнено"
        if r.get("mode") == "any":
            return f"{'Если ' + cond(w) + ' — ' if w else ''}отмечен хотя бы один из {cols(r)}"
        return f"{'Если ' + cond(w) + ' — ' if w else ''}{cols(r)} {what}"
    if t == "skip":
        return f"Если {cond(r.get('when'))} — {cols(r)} пусто (переход по анкете)"
    if t == "multi_select":
        return f"{cols(r)}: каждая отметка = 1 или пусто"
    if t == "consistency":
        ch = r.get("check")
        if ch == "implies" and r.get("if", {}).get("col") == "ROSTER_U18":
            has = r["if"]["in"] == [1]
            return (f"Если в Д-008 у домохозяйства {'есть член' if has else 'нет членов'} моложе 18 лет (тот же NOMER), "
                    f"то {cond(r.get('then'))}")
        if ch == "implies":
            return f"Если {cond(r.get('if'))}, то {cond(r.get('then'))}"
        if ch == "lte":
            return f"{r['a']} не больше {r['b']}"
        if ch == "unique":
            return f"{cols(r)} встречается один раз"
        if ch == "hh_size":
            return "KOL_CHL равно числу членов в списке"
        if ch == "one_head":
            return "в домохозяйстве ровно один глава"
        if ch == "head_is_member1":
            return "член номер 1 — глава домохозяйства"
        if ch == "refusal_all_or_none":
            return f"отказ ({r.get('code')}) — во всех вопросах {cols(r)} или ни в одном"
        if ch == "tables_agree":
            return f"{cols(r)} совпадают в двух частях анкеты"
        return "связь ответов (для проверки человеком)"
    if t == "cross_form":
        if r.get("check") == "regional_share_bounds":
            return (f"Доля {cond(r.get('this'))} по регионам не меньше доли собственников ({r['other_form']}: VLAD1 1–2) "
                    f"и не больше 100 минус платящие за жильё (VLAD1 4, 6)")
        return f"Доля {cond(r.get('this'))} по регионам согласуется с {r.get('other_form', 'другой формой')}"
    if t == "doc_issue":
        return "Противоречие в документации" + (f": {cols(r)}" if r.get("targets") else "")
    return t


rules = []
for p in sorted((ROOT / "rules").glob("*.json")):
    for r in json.load(open(p, encoding="utf-8"))["rules"]:
        if not r.get("superseded_by"):
            rules.append(r)
ex = pd.read_csv(OUT / "rules_export.csv").set_index("rule_id")
R = []
for r in rules:
    e = ex.loc[r["id"]] if r["id"] in ex.index else None
    R.append({"id": r["id"], "form": r["id"].split("-")[0], "type": r["type"], "ru": ru_rule(r),
              "quote": r.get("source", {}).get("quote", ""), "doc": DOC.get(r.get("source", {}).get("doc", ""), ""),
              "conf": r.get("confidence", ""), "note": r.get("note") or "", "added": bool(r.get("added_after_review")),
              "sql": (e["sql_first_column"] if e is not None and isinstance(e["sql_first_column"], str) else "")})
rule_by = {r["id"]: r for r in R}

cases = json.load(open(OUT / "cases.json", encoding="utf-8"))
NUM = json.load(open(OUT / "case_numbers.json", encoding="utf-8"))
RU_CASES = {
    "C1": ("Детский модуль: фильтр заполняют по-разному", f"В 2024 году в Улытау «есть дети до 18» (GR40) отмечено у {NUM['gr40_Ulytau_2024']} домохозяйств, а по списку членов Д-008 ребёнок есть у {NUM['roster_Ulytau_2024']}; г. Алматы — {NUM['gr40_Almaty city_2024']} против {NUM['roster_Almaty city_2024']}. Актобе: тот же сбой в 2023 ({NUM['gr40_Aktobe_2023']} против {NUM['roster_Aktobe_2023']}), в 2024 восстановился. По каждому домохозяйству (Д-002 и Д-008 по номеру NOMER): в г. Алматы {NUM['hh_Almaty city_2024'].replace(' of ', ' из ')} домохозяйств с ребёнком в Д-008 закодированы «нет детей» ({NUM['hhpct_Almaty city_2024']}), в Улытау {NUM['hh_Ulytau_2024'].replace(' of ', ' из ')} ({NUM['hhpct_Ulytau_2024']}), в Актобе в 2023 — {NUM['hh_Aktobe_2023'].replace(' of ', ' из ')}, в Жетысу в 2023 — {NUM['hh_Zhetysu_2023'].replace(' of ', ' из ')}; по стране GR40 совпадает с Д-008 у {NUM['hh_agree_2024']} домохозяйств с детьми. Есть и обратная ошибка: «есть дети» там, где в Д-008 нет никого моложе 18 (Туркестан {NUM['hhnopct_Turkistan_2024']} в 2024, Кызылорда {NUM['hhnopct_Kyzylorda_2023']} в 2023); она может идти и от года рождения в Д-008.",
           "Индикатор многоаспектной детской бедности (часть 4) в этих регионах и годах опирается на малую и неслучайную часть домохозяйств с детьми.",
           "GR40 нет в бумажной анкете: в структуре файла сказано, что вопрос добавлен. Каждый регион заполняет его по-своему.",
           "Выводить GR40 из списка членов Д-008 или напечатать вопрос в анкете; правило «часть 3, в. 17 = 1 ⇒ GR40 = 1» — при вводе."),
    "C2": ("Аренда: одна ситуация — два кода", f"Кто не снимает жильё, не может задолжать за аренду, поэтому доля «не актуально» должна быть не меньше доли собственников (Д-006: {NUM['owners_min']}–{NUM['owners_max']} в каждом регионе, 2024) и не больше 100 минус платящие за жильё (не меньше {NUM['upper_min_2024']}). Верхнюю границу не нарушает никто. Нижней достигают только {', '.join(REG[x] for x in NUM['rent_within_2024'].split(', '))} в 2024 ({', '.join(REG[x] for x in NUM['rent_within_2023'].split(', '))} в 2023); остальные {NUM['rent_below_2024']} из {NUM['rent_regions_2024']} регионов ставят большинству собственников 3 «нет», вплоть до {NUM['rent_nr_min']} в Мангистау. Кызылорда сменила практику: {NUM['rent_kyz_2023']} в 2023, {NUM['rent_kyz_2024']} в 2024.",
           "Любая доля задолженности «среди тех, для кого аренда актуальна» меняется с привычкой кодирования в регионе.",
           "Вариант 4: «маңызды емес» (не важно) по-казахски и «не актуально» по-русски; инструкция не говорит, как кодировать собственников.",
           "Одно предложение в инструкции: не арендующим ставится 4. Так делает меньшинство регионов, поэтому это общее правило, а не ошибка одного региона. Привести казахский текст к «қолданылмайды»; на реальных данных — «не актуально» среди собственников по регионам."),
    "C3": ("Казахский и русский тексты дают коду 2 разный смысл", f"Код 2 — «кем дегенде айына бір рет» (не реже раза в месяц) и «реже чем раз в месяц». Его доля — от {NUM['gr25_min']} до {NUM['gr25_max']} по регионам в 2024, в 2023 он замещает код 3 (r = {NUM['gr25_r_2023']}).",
           "Частота социальных контактов, показатели социальной изоляции.",
           "Ошибка перевода в анкете. Ещё семь расхождений в той же форме, сверенных с текстом: аренда (вариант 4), частота интернета (коды 1 и 2), воздух («қоқыс» — мусор против «выбросов»), причина долга («или» против «связанной с»), мебель («и» против «или»), «вне дома» нет в казахском тексте.",
           "Исправить казахский текст; для прошлых лет — разбивка по языку интервью, если он записан."),
    "C4": ("Одно время заполнения по умолчанию в нескольких регионах и формах", f"{NUM['mang_zt_2024']} анкет Д-002 в Мангистау (2024) — «1–2 часа» (в остальных {NUM['mang_zt_rest']}), {NUM['mang_gr1_2024']} ставят удовлетворённости 10 из 10 (в остальных {NUM['mang_gr1_rest']}). Тот же код в Астане в 2023 в двух формах (Д-002 {NUM['ast_zt_d002_2023']}, Д-006 {NUM['ast_zt_d006_2023']}).",
           "Удовлетворённость жизнью и все оценки части 1 для Мангистау 2024.", "Значение по умолчанию в программе ввода или ответы, внесённые интервьюером.",
           "Разбивка по интервьюерам на реальных данных; запретить значения по умолчанию в программе ввода."),
    "C5": ("Павлодар записывает числа с ведущим нулём", f"Число комнат — «03» вместо «3» в {NUM['pav_2023']} (2023) и {NUM['pav_2024']} (2024) записей Павлодара, в остальных — {NUM['pav_rest_2023']} и {NUM['pav_rest_2024']}.",
           "Само значение то же. Это след другой программы ввода в одном регионе — там вероятнее и другие различия.", "Другая программа ввода или выгрузки в Павлодаре.",
           "Единый формат выгрузки; первыми проверить другие поля Д-006 Павлодара."),
    "C6": ("Астана: половина месяцев рождения — январь", f"Месяц рождения «01» — у {NUM['ast_jan_2023']} (2023) и {NUM['ast_jan_2024']} (2024) записей Астаны, в остальных — {NUM['ast_jan_rest']}.",
           "Точный возраст, а значит, граничные возрастные группы (15, 16–72, 73+) и взвешивание по возрасту.", "Неизвестный месяц по умолчанию записывается как январь.",
           "Записывать «неизвестно» явно; восстанавливать из Д-008, где домохозяйство есть в обоих обследованиях."),
    "C7": ("Костанай: девять автомобилей на домохозяйство", f"Среди домохозяйств со значением число автомобилей (TDP35) в Костанае — {NUM['kos_cars_2023']} (2023) и {NUM['kos_cars_2024']} (2024), медиана в остальных — {NUM['cars_median_2024']}.",
           "Владение автомобилем и индексы активов домохозяйств.", "В столбце автомобилей записано другое число (сдвиг столбца или код вместо количества).",
           "Пределы правдоподобия по каждому пункту; проверить формат выгрузки Д-006 в Костанае."),
    "C8": ("Правила, нарушенные везде: вопросы к процессу", f"Часть 2, в. 2 (причины низкого дохода) пуст у {NUM['p2q2_2024']} тех, кому задаётся (2024). {NUM['minor89_2024']} респондентов младше 18 оценивают финансы семьи вместо кода 89, который инструкция советует детям (мягкая проверка: возраст в инструкции не назван). В Д-008 поле времени пустое у всех ({NUM['d008_zt_2024']}); {NUM['d008_code_2024']} кодов изменения состава — вне списка инструкции.",
           "Причины низкого дохода; изменения состава домохозяйства; цели займов.", "Вопросы пропускают на практике, инструкции не выполняются или списки кодов в инструкции неполны.",
           "Подтвердить на реальных данных; добавить правила при вводе."),
}
if (OUT / "case_numbers.json").exists() and "fin_saving_naive" in NUM:
    RU_CASES["C11"] = ("Финансы домохозяйств (Д-004): четыре поправки до показателя уязвимости",
        f"Если читать Д-004 напрямую, норма сбережений домохозяйств — {NUM['fin_saving_naive']} (2024). (1) В журнале нет раздела о питании: записанные расходы — {NUM['fin_spend_income']} дохода; если питание — половина расходов (официальная цифра), было бы около {NUM['fin_spend_income_food']}. Норму сбережений по одному Д-004 посчитать нельзя. (2) Доход: в анкете GR3 — «из него» внутри GR2, поэтому сумма всех 23 столбцов считает продажу сельхозпродукции дважды: +{NUM['fin_gr3_nat']} по стране, до +{NUM['fin_gr3_max']} ({REG.get(NUM['fin_gr3_max_region'], NUM['fin_gr3_max_region'])}). (3) Займы на питание: в Актобе {NUM['fin_aktobe_share_hh']} домохозяйств, но {NUM['fin_aktobe_share_food']} всех, кто занимал на питание ({NUM['fin_aktobe_food']} займов с указанной целью); доля займов на питание по стране {NUM['fin_food_nat']}, без Актобе {NUM['fin_food_wo_aktobe']}. (4) Раздел займов заполнен у {NUM['fin_cov_mang']} домохозяйств Мангистау при медиане {NUM['fin_cov_median']} (от {NUM['fin_cov_mang_range']} в каждом году 2021–2024); низко и в регионах {', '.join(REG.get(x.strip(), x.strip()) for x in NUM['fin_cov_low_regions'].split(','))} ({NUM['fin_cov_low_range']}). Доля погашающих кредиты по стране {NUM['fin_repay_nat']}, без этих четырёх регионов {NUM['fin_repay_wo_low']}; доля с выплатами больше 30% дохода — {NUM['fin_burden_nat']} и {NUM['fin_burden_wo_low']}. В синтетике {NUM['fin_rep_rows']} строк непродовольственных расходов повторяют товар (это названо в руководстве организаторов; {NUM['fin_rep_range']} по регионам, {NUM['fin_rep_value']} расходов), поэтому сравнение регионов не страдает; связи внутри домохозяйства слабые (r = {NUM['fin_corr_hh']} между логарифмами дохода и расходов), поэтому показываем только региональные цифры.",
        "Финансовая уязвимость: норма сбережений, нагрузка расходов и долга, займы на питание, по регионам.",
        "Отсутствующий раздел прочитан как нулевые расходы; строка «из него» сложена как отдельный доход; региональная практика кодирования неформальных займов; раздел, который четыре региона почти не заполняют.",
        "Не публиковать норму сбережений по Д-004 без дневника питания; не складывать GR3 с GR2 (правило D004-3-agri-within-self-employment и пометка в структуре файла); цели и источники займов в Актобе — по интервьюерам; на реальных данных — заполнение раздела займов в Мангистау, Шымкенте, Туркестанской и Жамбылской областях против региональных данных Нацбанка по кредитам.")
import re
RUC = lambda x: re.sub(r"(?<=\d)\.(?=\d)", ",", x)
dc = json.load(open(OUT / "decoder_cases.json", encoding="utf-8"))
kz, al = dc["kyzylorda"], dc["almaty"]
RU_CASES["C9"] = ("Кызылорда кодирует образование детей 7–10 лет по-своему (декодер)",
    f"Детей 7–10 лет, учащихся 1–4 классов, по инструкции Д-008 кодируют 1 «дошкольное» (если было дошкольное образование). В Кызылорде кодом 7 «не достигнут никакой уровень» записаны {kz['2023']['kyzylorda_pct_code7']}% таких детей в 2023 и {kz['2024']['kyzylorda_pct_code7']}% в 2024; в остальных регионах — не больше {kz['2023']['other_regions_max']}% и {kz['2024']['other_regions_max']}%.",
    "Уровень образования детей и любые показатели охвата дошкольным образованием, выведенные из Д-008.",
    "В Кызылорде код ставят по текущему посещению (сад — 1, школа без законченного начального — 7), а не по достигнутому уровню, как требует инструкция.",
    "Одно предложение в инструкции для интервьюеров; проверить на реальных данных и пересчитать 2023–2024.")
RU_CASES["C10"] = ("Алматинская обл.: тип работодателя и договор сменили код вместе (декодер)",
    f"Наёмные работники у физических лиц (статус 2): в 2023 — {al['2023']['status2_code2']} записей с типом работодателя 2 и {al['2023']['status2_code5']} с кодом 5; в 2024 — {al['2024']['status2_code2']} и {al['2024']['status2_code5']}. В том же году устный договор у этой группы — {al['2024']['no_contract_status2_almaty_pct']}% против {al['2024']['no_contract_status2_rest_pct']}% в остальных. Вне области код 5 тоже изменился: устный договор у {al['2023']['oral_among_code5_outside_almaty_pct']}% (2023) и {al['2024']['oral_among_code5_outside_almaty_pct']}% (2024).",
    "Доля работников без письменного договора (неформальная занятость) в Алматинской области и по стране за 2024.",
    "Похоже, в 2024 году код 5 переопределили, а Алматинская область перевела на него всех работников у физических лиц. Работы те же: по профилю коды 2 и 5 почти неотличимы.",
    "Уточнить в инструкции Т-001 за 2024 год смысл кода 5 и правило для договора; пересчитать неформальную занятость.")
C = []
for c in cases:
    t, f, ind, cause, fix = (RUC(x) for x in RU_CASES[c["id"]])
    C.append({"id": c["id"], "title": t, "finding": f, "indicator": ind, "cause": cause, "fix": fix, "rules": c["rules"],
              "status": "держится" if c["status"].startswith("holds") else ("документация" if c["status"].startswith("documentation") else "смешанный")})
case_of_rule = {r: c["id"] for c in C for r in c["rules"]}
# ML rows: the column named in a case, in priority order (Mangystau 2024 'GR25, ZT, GR33' -> C4; Turkistan 2024 'GR25, GR40, GR41' -> C1)
ML_CASE = [("ZT", "C4"), ("DH_DATROZH_2", "C6"), ("GR40", "C1"), ("GR41", "C1"), ("KOL_K", "C5"), ("GR25", "C3")]

iss = pd.read_csv(OUT / "scorecard_issues.csv")
I = []
for _, x in iss.iterrows():
    rid = x.rule_id
    is_ml = rid.startswith("ML")
    r = rule_by.get(rid)
    case = case_of_rule.get(rid)
    if not case and is_ml:
        _cols = [v.strip() for v in str(x.example_column).split(",")]   # 'columns' holds a count, the names are here
        case = next((c for k, c in ML_CASE if k in _cols), None)
    I.append({"form": x.form, "formRu": FORM.get(x.form, x.form), "year": int(x.year), "region": x.region, "rule": rid,
              "type": TYPE_RU.get(x.type, x.type), "ru": (r["ru"] if r else ("Ответы региона отличаются от остальной страны: " + str(x.columns))),
              "quote": r["quote"] if r else "", "doc": r["doc"] if r else "", "sql": r["sql"] if r else "",
              "col": str(x.example_column) if isinstance(x.example_column, str) else "",
              "records": None if pd.isna(x.records) else int(x.records), "rateRegion": float(x.rate_region), "rateRest": float(x.rate_rest),
              "trust": SYN.get(x.synthesis, x.synthesis), "status": STATUS.get(x.status, x.status), "evidence": x.evidence, "case": case})

for i, (_, x) in zip(I, iss.iterrows()):
    if x.evidence == "section coverage (finance case)":
        i.update({"type": "Охват раздела", "col": "kv_vopr12",
                  "ru": f"Раздел 2 «Заёмные средства» заполнен у {x.rate_region:.1f}% домохозяйств против медианы {x.rate_rest:.1f}% по другим регионам; так в 3–4 годах из 4",
                  "trust": "доли по регионам; разница может быть реальной", "case": "C11"})

sh = pd.read_csv(OUT / "decoder_code_shift.csv")
COLRU = {"UROV": "уровень образования", "ORB_PKHDHL": "тип работодателя", "ORB_STATUS": "статус занятости", "STATUS": "статус деятельности"}
for i, (_, x) in zip(I, iss.iterrows()):
    if x.evidence != "code shift (decoder)":
        continue
    m = sh[sh.flag & (sh.form.str.replace("-", "") == x.form) & (sh.year == x.year) & (sh.region == x.region)
           & (("code shift: " + sh.column + " " + sh.code.astype(str) + " → " + sh.behaves_like.astype(str)) == x.rule_id)].iloc[0]
    i.update({"formRu": m.form.replace("D-", "Д-").replace("T-", "Т-"), "type": "Декодер: сдвиг кода", "col": m.column,
              "ru": f"{COLRU.get(m.column, m.column)}: код {m.code} здесь ведёт себя как код {m.behaves_like} в остальной стране (сходство профиля {m.distance_to_match:.3f} против {m.distance_to_same_code:.3f} со своим кодом)",
              "rateRegion": None, "rateRest": None, "trust": "доли ответов" if m.n >= 90 else "мало записей",
              "case": "C9" if (x.region == "Kyzylorda" and m.column == "UROV") else None})
for i in I:
    if i["region"] == "Almaty oblast" and i["form"] == "T001":
        i["case"] = "C10"
ch = pd.read_csv(OUT / "child_impact.csv")
CH = [{"year": int(r.year), "region": r.region, "withKids": int(r.with_children_roster), "answered": int(r.answered_among_with_children),
       "coverage": float(r.coverage_pct), "deprived": None if pd.isna(r.deprived_pct) else float(r.deprived_pct),
       "moe": None if pd.isna(r.moe_pp) else float(r.moe_pp), "kidsAns": None if pd.isna(r.kids_per_hh_answered) else float(r.kids_per_hh_answered),
       "kidsAll": float(r.kids_per_hh_all)} for r in ch.itertuples()]

FIN, FIN_NAT = [], []
if (OUT / "finance_impact.csv").exists():
    fi = pd.read_csv(OUT / "finance_impact.csv")
    fc = pd.read_csv(OUT / "finance_section_coverage.csv")
    fc = fc[fc.section == "kv_vopr12"].set_index(["year", "region"])
    fv = lambda v: None if pd.isna(v) else float(v)
    FIN = [{"year": int(r.year), "region": r.region, "hh": int(r.household_quarters),
            "cov": float(fc.loc[(r.year, r.region), "households_pct"]), "covFlag": bool(fc.loc[(r.year, r.region), "flag"]),
            "burden": fv(r.burden_gt30_pct), "repaying": fv(r.repaying_pct), "borrowed": fv(r.borrowed_pct),
            "food": fv(r.food_loan_pct_of_purpose), "withPurpose": int(r.loans_with_purpose), "gr3": fv(r.gr3_added_pct),
            "saving": fv(r.savings_rate_form_pct)} for r in fi.itertuples()]
    FIN_NAT = json.load(open(OUT / "finance_impact_national.json", encoding="utf-8"))

# impact per case: numbers computed by analysis/*.py, decoder_cases.py and cases.py only; other cases get the indicator text
_nat = json.load(open(OUT / "child_impact_national.json"))
CASE_IMPACT = {
    "C1": [[f"{x['answered']} из {x['withKids']}", f"семей с детьми ответили на детский модуль: {REG.get(x['region'], x['region'])}, {x['year']} (погрешность индикатора ±{x['moe']:.1f} п.п.)"]
             for x in sorted([c for c in CH if c['coverage'] < 50], key=lambda c: c['coverage'])[:3]]
          + [[f"{r['coverage_national']:.1f}%", f"семей с детьми ответили на детский модуль по стране, {r['year']}"] for r in _nat],
    "C4": [[NUM["mang_gr1_2024"], f"респондентов в Мангистау (2024) оценивают удовлетворённость жизнью на 10 из 10 (в остальных регионах {NUM['mang_gr1_rest']})"]],
    "C9": [[f"{kz[y]['kyzylorda_pct_code7']}%", f"детей 7–10 лет в Кызылорде записаны кодом 7 вместо 1, {y} (в других регионах — не более {kz[y]['other_regions_max']}%)"] for y in ("2023", "2024")],
    "C10": [[f"{al['2024']['no_contract_status2_almaty_pct']}%", f"работников у физических лиц без письменного договора, Алматинская обл., 2024 (в остальных регионах {al['2024']['no_contract_status2_rest_pct']}%)"]],
}
if (OUT / "finance_impact_national.json").exists():
    _f = json.load(open(OUT / "finance_impact_national.json"))[-1]
    CASE_IMPACT["C11"] = [
        [f"{_f['food_loan_pct_of_purpose']}% → {_f['food_loan_pct_of_purpose_without_aktobe']}%", f"доля займов на питание по стране: с Актобе и без него, {_f['year']}"],
        [f"{_f['repaying_pct']}% → {_f['repaying_pct_without_low_coverage']}%", f"доля домохозяйств, погашающих кредиты: по стране и без четырёх регионов с почти незаполненным разделом займов, {_f['year']}"],
        [f"{_f['savings_rate_naive_pct']}%", "«норма сбережений» по Д-004 без поправки; показатель некорректен: в журнале нет раздела о питании"]]

CASE_IMPACT = {k: [[RUC(x) for x in pair] for pair in v] for k, v in CASE_IMPACT.items()}   # decimal comma in numbers only

_acc = OUT / "accuracy_d002_v1_vs_reviewed.csv"   # written by gold/score.py --out; the team-checked reference
acc = pd.read_csv(_acc if _acc.exists() else OUT / "accuracy_d002_v1_vs_draft.csv").set_index("type")
ACC = {k: {"precision": float(v.precision), "recall": float(v.recall), "reference": int(v.reference)} for k, v in acc.iterrows()}
sens, clean = pd.read_csv(OUT / "proof_sensitivity.csv"), pd.read_csv(OUT / "proof_sensitivity_clean.csv")
names = {"skip: Q14 asked after 'no internet'": "Вопрос 14 после «нет интернета»", "skip: Part 4 filled for 'no children'": "Часть 4 у «нет детей»",
         "required: reason blank after 'no home internet'": "Причина не указана", "domain: out-of-range time code": "Недопустимый код времени",
         "filter: 'no children' with a pre-school child": "«Нет детей» при дошкольнике"}
PROOF = []
for k in dict.fromkeys(sens.kind):
    a = sens[sens.kind == k].groupby("rate").detected.mean().mul(100)
    b = clean[clean.kind == k].groupby("rate").detected.mean().mul(100)
    PROOF.append({"kind": names.get(k, k), "background": float(sens[sens.kind == k].background_rate.iloc[0]),
                  "shipped": [round(float(a[r])) for r in a.index], "repaired": [round(float(b[r])) for r in b.index]})
okc = clean[(clean.eligible >= 30) & (clean.planted >= 10)].groupby("rate").detected.mean().mul(100)
spec = pd.read_csv(OUT / "proof_specificity.csv")
_ru = ROOT / "gold" / "d002_review_ru.csv"
rv = pd.read_csv(_ru, encoding="utf-8-sig") if _ru.exists() else pd.read_csv(ROOT / "gold" / "d002_review.csv")
_tick = rv["Ваша отметка (✓ согласна / ✗ нет)"] if "Ваша отметка (✓ согласна / ✗ нет)" in rv else rv.iloc[:, -1]
ticks = int(_tick.astype(str).str.strip().isin(["✓", "v", "V", "yes", "да", "1", "+"]).sum())

c2 = pd.read_csv(OUT / "compare_year_c2st.csv")
lfs = c2[c2.form == "T001/baza"].sort_values("auc", ascending=False)
sw = pd.read_csv(OUT / "compare_region_sweep.csv")
d4 = sw[(sw.form == "D004") & (sw.variable != "K")].sort_values("js", ascending=False).reset_index(drop=True)
akt = d4[(d4.region == "Aktobe") & (d4.table == "kv12[NOMVOPR=1211]") & (d4.variable == "KOD")]
DEMO = ROOT / "demo"
summ = json.load(open(DEMO / "summary.json", encoding="utf-8"))
BLIND = {"t001": [{"region": r.region, "auc": round(float(r.auc), 3), "top": r.top_features} for r in lfs.itertuples()],
         "aktobe": [{"year": int(r.year), "rank": int(i) + 1, "share": float(r.share_region), "rest": float(r.share_rest_same)} for i, r in akt.iterrows()],
         "d004Signals": int(len(d4)), "d004DocIssues": summ["d004_blind"]["doc_issues"]}

d22 = json.load(open(DEMO / "d002_2022_v2.json", encoding="utf-8"))["rules"]
f22 = pd.read_csv(DEMO / "d002_2022_region_flags.csv")
nr22 = pd.read_csv(DEMO / "d002_2022_not_run.csv")
NEW = {"rules": [{"id": r["id"], "type": r["type"], "typeRu": TYPE_RU.get(r["type"], r["type"]), "ru": ru_rule(r),
                  "quote": r.get("source", {}).get("quote", ""), "note": r.get("note") or ""} for r in d22],
       "flags": [{"rule": x.rule_id, "region": x.region, "rateRegion": float(x.rate_region), "rateRest": float(x.rate_rest),
                  "trust": SYN.get(x.synthesis, x.synthesis), "ru": ru_rule(next(r for r in d22 if r["id"] == x.rule_id))}
                 for x in f22[f22.flag].itertuples()],
       "notRun": [{"rule": x.rule_id, "reason": "модель отметила правило для проверки человеком" if "manual" in x.reason else x.reason} for x in nr22.itertuples()],
       "seconds": {"extraction": summ["d002_2022"]["extraction_seconds"], "engine": summ["d002_2022"]["engine_seconds"]}}

DEC = ROOT / "decoder"
vrep = json.load(open(DEC / "reply_validation.json", encoding="utf-8"))
grades = json.load(open(DEC / "validation_grades.json", encoding="utf-8"))
sys.path.insert(0, str(DEC))
import decode as DCM  # noqa: E402
truth = {"D-008/STATUS": DCM.D008_LABELS["STATUS"], "D-008/SEM_POL": DCM.D008_LABELS["SEM_POL"], "D-008/UROV": DCM.D008_LABELS["UROV"], "D-006/TIP_J": DCM.D006_LABELS["TIP_J"]}
VAL = [{"column": c["column"], "code": str(k["code"]), "model": k["meaning"], "conf": k["confidence"], "truth": truth[c["column"]].get(str(k["code"]), ""),
        "grade": grades["grades"][c["column"]][str(k["code"])]} for c in vrep["columns"] for k in c["codes"]]
trep = json.load(open(DEC / "reply_t001.json", encoding="utf-8"))
sis = pd.read_csv(OUT / "decoder_sister_match.csv")
sis_ok = {(r.t001_column, str(r.code)): (r.label, float(r.margin) if r.margin == r.margin else None) for r in sis.itertuples()}
T001 = []
for c in trep["columns"]:
    col = c["column"].split("/")[1]
    for k in c["codes"]:
        sm = sis_ok.get((col, str(k["code"])))
        T001.append({"column": col, "concept": c.get("concept", ""), "code": str(k["code"]), "meaning": k["meaning"], "conf": k["confidence"],
                     "evidence": k.get("evidence", ""), "sister": sm[0] if sm else None, "sisterMargin": sm[1] if sm else None})
vm = pd.read_csv(OUT / "decoder_validation_match.csv").groupby(["form", "column"]).agg(c=("correct", "sum"), t=("codes", "sum")).reset_index()
DECODER = {"validation": VAL, "t001": T001, "renumber": [{"form": r.form, "column": r.column, "pct": round(100 * r.c / r.t, 1)} for r in vm.itertuples()],
           "kyzylorda": kz, "almaty": al, "shiftsFlagged": int(sh.flag.sum()), "shiftsTested": int(len(sh))}

counts = {}
for p in sorted((ROOT / "rules").glob("*.json")):
    sp = json.load(open(p, encoding="utf-8"))
    counts[sp["form"]] = sum(1 for r in sp["rules"] if not r.get("superseded_by"))

data = {"regions": [{"key": k, "ru": REG[k], "col": TILE[k][0], "row": TILE[k][1]} for k in REG],
        "caseImpact": CASE_IMPACT, "rules": R, "cases": C, "issues": I, "child": CH, "fin": FIN, "finNat": FIN_NAT, "acc": ACC, "proof": PROOF,
        "proofRates": [int(100 * r) for r in sorted(sens.rate.unique())],
        "proofOk": {str(int(100 * k)): round(float(v)) for k, v in okc.items()},
        "proofRuns": int(len(sens) + len(clean)), "proofFp": int(sens.new_flags_other_regions.sum() + clean.new_flags_other_regions.sum()),
        "spec": {"runs": int(len(spec)), "flagged": int((spec.new_flags_in_region > 0).sum())},
        "review": {"rows": int(len(rv)), "ticked": ticks}, "blind": BLIND, "newForm": NEW, "ruleCounts": counts, "decoder": DECODER,
        "forms": FORM}
# data model (schema/profile.py, schema/draw.py): tables, links, column dictionary, diagrams
SCHEMA = None
if (OUT / "schema_tables.csv").exists():
    st = pd.read_csv(OUT / "schema_tables.csv")
    sl = pd.read_csv(OUT / "schema_links.csv")
    sc = pd.read_csv(OUT / "schema_columns.csv")
    sh_ = pd.read_csv(OUT / "schema_household_children.csv")
    dg = ROOT / "diagrams"
    svg = {n: (lambda t: t[t.find("<svg"):])((dg / f"{n}.svg").read_text(encoding="utf-8")) for n in ("links_ru_inline", "pipeline_ru_inline", "erd_data", "erd_outputs")
           if (dg / f"{n}.svg").exists()}
    t24 = st[st.year == st.year.max()]
    SCHEMA = {
        "tables": [{"form": r.form, "table": r.table, "grain": r.grain, "key": r.key, "rows": int(r.rows), "cols": int(r.columns),
                    "colsReal": int(r.columns_real), "unique": None if r.key_unique != r.key_unique else bool(r.key_unique),
                    "inRoster": None if r.households_in_roster_pct != r.households_in_roster_pct else float(r.households_in_roster_pct)}
                   for r in t24.itertuples()],
        "links": json.loads(sl.to_json(orient="records")),
        "household": json.loads(sh_.to_json(orient="records")),
        "columns": [{"f": r.form, "t": r.table, "c": r.column, "k": r.kind, "d": "" if r.description != r.description else r.description,
                     "fp": r.filled_pct, "n": int(r.distinct) if r.distinct == r.distinct else None,
                     "top": "" if r.top_values != r.top_values else r.top_values, "y": r.years,
                     "r": "" if r.rule_ids != r.rule_ids else r.rule_ids} for r in sc.itertuples()],
        "svg": svg,
    }

data["schema"] = SCHEMA
DEST.mkdir(parents=True, exist_ok=True)
(DEST / "data.json").write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":"), default=lambda o: None if o != o else o), encoding="utf-8")
print("rules", len(R), "issues", len(I), "cases", len(C), "child rows", len(CH), "bytes", (DEST / "data.json").stat().st_size)
