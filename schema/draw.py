"""Diagrams of the data model and of the pipeline's outputs.

Two simple pictures for the jury (Russian and English), drawn by hand as SVG with every number read
from out/ (schema/profile.py and the pipeline's own outputs), and two full technical diagrams
(Graphviz) for the Bureau's staff: every table with its keys, and every output file with its columns.

    python schema/draw.py --out out/ --to diagrams/

diagrams/links_{ru,en}.svg       how the forms link (jury)
diagrams/pipeline_{ru,en}.svg    what the tool reads and writes (jury)
diagrams/erd_data.svg            all tables, keys, grain, columns by kind (technical)
diagrams/erd_outputs.svg         all output files, their columns and the keys that join them (technical)
diagrams/*_inline.svg            the same jury pictures without colours, themed by the page (console)
"""
import argparse
import json
import subprocess
from html import escape
from pathlib import Path

import pandas as pd

BLUE, ORANGE, INK, INK2, INK3, LINE, SUNK = "#2a6fd6", "#d96a33", "#18202b", "#47505e", "#6a7381", "#c3cbd7", "#eef1f5"
FONT = "'IBM Plex Sans', 'Segoe UI', Arial, sans-serif"

# Colours live in classes. The standalone file carries a <style> block with the light palette;
# the console embeds the same markup without it and styles the classes with its theme variables.
STYLE = f"""
.t {{ font-family: {FONT}; fill: {INK}; }}
.t2 {{ fill: {INK2}; }} .t3 {{ fill: {INK3}; }} .tb {{ fill: {BLUE}; }} .to {{ fill: #9a4313; }}
.box {{ fill: #ffffff; stroke: {LINE}; stroke-width: 1.2; }}
.sunk {{ fill: {SUNK}; stroke: none; }}
.hub {{ fill: #dce8fa; stroke: {BLUE}; stroke-width: 1.6; }}
.call {{ fill: #fbe7dc; stroke: {ORANGE}; stroke-width: 1.4; }}
.island {{ fill: #ffffff; stroke: {INK3}; stroke-width: 1.2; stroke-dasharray: 5 4; }}
.e-ok {{ stroke: {BLUE}; stroke-width: 2.6; fill: none; }}
.e-broken {{ stroke: {ORANGE}; stroke-width: 2.2; stroke-dasharray: 8 5; fill: none; }}
.e-key {{ stroke: {INK2}; stroke-width: 1.6; fill: none; }}
.e-region {{ stroke: {INK3}; stroke-width: 1.6; stroke-dasharray: 2 4; fill: none; }}
.e-flow {{ stroke: {INK2}; stroke-width: 1.6; fill: none; }}
.m-ok {{ fill: {BLUE}; }} .m-key {{ fill: {INK2}; }} .m-broken {{ fill: {ORANGE}; }}
"""

L = {
    "ru": {
        "links_title": "Одно домохозяйство — один номер во всех формах",
        "links_sub": "NOMER связывает Д-002, Д-004, Д-006 и Д-008; Т-001 связана только регионом",
        "roster": "Д-008 · контрольная карточка", "roster2": "{hh} домохозяйств · {p} человек",
        "roster3": "ключ NOMER + NOMP (человек)",
        "d002": "Д-002 · качество жизни", "subject": "subject", "ocenka": "ocenka",
        "d002b": "{hh} домохозяйств, один респондент",
        "pair": "один человек? расходится: {diff}",
        "d006": "Д-006 · основное интервью", "d006b": "{hh} домохозяйств · жильё, удобства",
        "d004": "Д-004 · квартальный журнал", "d004b": "kv_vopr0: визит × квартал ({v})",
        "d004c": "+ {n} таблиц строк расходов ({l} строк)",
        "t001": "Т-001 · обследование занятости", "t001b": "{p} респондентов",
        "t001c": "нет номера домохозяйства",
        "e002": "NOMER + NOMP: найдено {f}%, пол совпадает {s}%",
        "e002b": "ответы согласованы: «есть дети» {a}% против {b}%",
        "e006": "NOMER: найдено {f}%", "e006b": "ответы не связаны (синтетика)|→ только доли по регионам",
        "e004": "NOMER: найдено {f}%, регион совпадает {r}%",
        "et001": "только регион TE и квартал",
        "et001b": "декодер сравнивает поведение кодов",
        "call1": "Проверка по каждому домохозяйству (2024)",
        "call2": "Ребёнок в Д-008, но в Д-002 «нет детей»:",
        "call3": "{r1} — {a} из {b} ({p}%)", "call4": "{r2} — {c} из {d} ({q}%)",
        "leg_ok": "связь по записям работает", "leg_broken": "ключ есть, ответы не связаны → регионы",
        "leg_key": "ключ есть, сравнений пока нет", "leg_region": "только регион",
        "pipe_title": "Что инструмент читает и что выдаёт",
        "pipe_sub": "каждое число в сводке и делах посчитано кодом по записям, не языковой моделью",
        "docs": "бланк, инструкция,", "docs2": "структура файлов", "docs_t": "Документы",
        "rules_t": "Правила",
        "eng_t": "Проверки", "eng2": "каждое правило|по регионам и годам",
        "card_t": "Сводка",
        "cases_t": "Дела",
        "cons_t": "Консоль", "cons2": "карта, досье,|правила в SQL",
        "ml": "ML-сравнения", "ml2": "регион, год, форма|без правил",
        "dec": "Декодер кодов", "dec2": "значения кодов|и их сдвиги",
        "sql_t": "SQL для базы Бюро", "sql2": "{n} правил,|каждый квартал",
        "acc": "Точность извлечения правил (Д-002)", "acc2": "точность {p}%, полнота {r}%",
        "proof": "Доказательство", "proof2": "{n} прогонов с подложенными ошибками",
        "k_rule": "rule_id", "k_cell": "регион × год", "k_issue": "issue → дело",
        "k_llm": "LLM", "k_rec": "записи",
        "data": "Записи Д-002…Д-008, Т-001",
    },
    "en": {
        "links_title": "One household, one number in every form",
        "links_sub": "NOMER links D-002, D-004, D-006 and D-008; T-001 links by region only",
        "roster": "D-008 · household roster", "roster2": "{hh} households · {p} people",
        "roster3": "key NOMER + NOMP (person)",
        "d002": "D-002 · quality of life", "subject": "subject", "ocenka": "ocenka",
        "d002b": "{hh} households, one respondent",
        "pair": "same person? differs: {diff}",
        "d006": "D-006 · main interview", "d006b": "{hh} households · dwelling, amenities",
        "d004": "D-004 · quarterly journal", "d004b": "kv_vopr0: visit × quarter ({v})",
        "d004c": "+ {n} tables of spending lines ({l} lines)",
        "t001": "T-001 · labour force survey", "t001b": "{p} respondents",
        "t001c": "no household number",
        "e002": "NOMER + NOMP: {f}% found, sex agrees {s}%",
        "e002b": "answers agree: 'has children' {a}% vs {b}%",
        "e006": "NOMER: {f}% found", "e006b": "answers unlinked (synthetic)|→ regional shares only",
        "e004": "NOMER: {f}% found, region agrees {r}%",
        "et001": "region TE and quarter only",
        "et001b": "the decoder compares how codes behave",
        "call1": "Household-by-household check (2024)",
        "call2": "Child in D-008, but 'no children' in D-002:",
        "call3": "{r1}: {a} of {b} ({p}%)", "call4": "{r2}: {c} of {d} ({q}%)",
        "leg_ok": "record link works", "leg_broken": "key exists, answers unlinked → regions",
        "leg_key": "key exists, no comparison yet", "leg_region": "region only",
        "pipe_title": "What the tool reads and what it writes",
        "pipe_sub": "every number in the scorecard and the case files is computed from the records by code, not by the language model",
        "docs": "form, instruction,", "docs2": "file structure", "docs_t": "Documents",
        "rules_t": "Rules",
        "eng_t": "Checks", "eng2": "every rule|by region and year",
        "card_t": "Scorecard",
        "cases_t": "Case files",
        "cons_t": "Console", "cons2": "map, dossiers,|rules as SQL",
        "ml": "ML comparisons", "ml2": "region, year, form|no rules needed",
        "dec": "Code decoder", "dec2": "code meanings|and code shifts",
        "sql_t": "SQL for the Bureau", "sql2": "{n} rules,|rerun every quarter",
        "acc": "Rule extraction accuracy (D-002)", "acc2": "precision {p}%, recall {r}%",
        "proof": "Proof", "proof2": "{n} runs with planted errors",
        "k_rule": "rule_id", "k_cell": "region × year", "k_issue": "issue → case",
        "k_llm": "LLM", "k_rec": "records",
        "data": "Records D-002…D-008, T-001",
    },
}

REGION_RU = {"Almaty city": "г. Алматы", "Ulytau": "Улытау", "Zhetysu": "Жетысу", "Aktobe": "Актобе"}


def fmt(x, lang, dec=0):
    s = f"{x:,.{dec}f}"
    return s.replace(",", " ").replace(".", ",") if lang == "ru" else s


# ---------- SVG helpers ----------

class SVG:
    def __init__(self, w, h, label, prefix):
        self.w, self.h, self.label, self.parts, self.prefix = w, h, label, [], prefix

    def add(self, s):
        self.parts.append(s)

    def text(self, x, y, s, size=14, cls="", weight=400, anchor="start"):
        self.add(f'<text class="t {cls}" x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" '
                 f'text-anchor="{anchor}">{escape(s)}</text>')

    def rect(self, x, y, w, h, cls="box", r=10):
        self.add(f'<rect class="{cls}" x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}"/>')

    def line(self, pts, cls, marker=None):
        d = " ".join(f"{x},{y}" for x, y in pts)
        m = f' marker-end="url(#{self.prefix}-{marker})"' if marker else ""
        self.add(f'<polyline class="{cls}" points="{d}"{m}/>')

    def render(self, standalone):
        defs = "<defs>" + "".join(
            f'<marker id="{self.prefix}-{m}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
            f'<path class="{m}" d="M0,0 L10,5 L0,10 z"/></marker>' for m in ("m-ok", "m-key", "m-broken")) + "</defs>"
        style = f"<style>{STYLE}</style>" if standalone else ""
        bg = f'<rect x="0" y="0" width="{self.w}" height="{self.h}" fill="#ffffff"/>' if standalone else ""
        ns = ' xmlns="http://www.w3.org/2000/svg"'
        return (f'<svg{ns} viewBox="0 0 {self.w} {self.h}" role="img" aria-label="{escape(self.label)}" '
                f'class="sq-diagram">{style}{defs}{bg}' + "".join(self.parts) + "</svg>")


# ---------- jury picture 1: how the forms link ----------

def links_svg(o, lang):
    T = L[lang]
    tab = o["tables"]
    lk = o["links"]
    y = 2024
    t24 = tab[tab.year == y].set_index(["form", "table"])
    l24 = lk[lk.year == y].set_index("link")
    diff = lk[lk.link == "D002.subject <-> D002.ocenka"].set_index("year")["respondent_differs"].astype(int)
    hc = o["household"]
    hc = hc[hc.year == y].sort_values("missed_pct", ascending=False)
    a, b = hc.iloc[0], hc.iloc[1]
    rn = (lambda r: REGION_RU.get(r, r)) if lang == "ru" else (lambda r: r)
    kids = l24.loc["D002.ocenka GR40 'has children' vs D008 member under 18"]
    rent = l24.loc["D002.ocenka GR31_1 'rent: not relevant' vs D006 owner (VLAD1 1-2)"]

    s = SVG(1200, 700, f'{T["links_title"]}. {T["links_sub"]}.', f"sq-links-{lang}")
    s.text(40, 46, T["links_title"], 26, weight=600)
    s.text(40, 74, T["links_sub"], 15, "t3")

    # hub: the roster
    hx, hy, hw, hh = 455, 290, 290, 112
    s.rect(hx, hy, hw, hh, "hub", 12)
    s.text(hx + hw / 2, hy + 34, T["roster"], 17, weight=600, anchor="middle")
    s.text(hx + hw / 2, hy + 62, T["roster2"].format(hh=fmt(t24.loc[("D008", "kontr_k"), "households"], lang),
                                                     p=fmt(t24.loc[("D008", "kontr_k"), "rows"], lang)), 14, "t2", anchor="middle")
    s.text(hx + hw / 2, hy + 88, T["roster3"], 13, "tb", anchor="middle")

    # D-002, two halves
    x2, y2 = 40, 120
    s.rect(x2, y2, 330, 168, "box", 12)
    s.text(x2 + 18, y2 + 32, T["d002"], 17, weight=600)
    s.text(x2 + 18, y2 + 56, T["d002b"].format(hh=fmt(t24.loc[("D002", "subject"), "households"], lang)), 13, "t2")
    for i, name in enumerate(("subject", "ocenka")):
        s.rect(x2 + 18 + i * 160, y2 + 72, 134, 34, "sunk", 6)
        s.text(x2 + 85 + i * 160, y2 + 94, name, 14, anchor="middle")
    s.line([(x2 + 152, y2 + 89), (x2 + 178, y2 + 89)], "e-key")
    dtxt = ", ".join(f"{yy}: {fmt(v, lang)}" for yy, v in diff.items() if yy >= 2022)
    s.text(x2 + 18, y2 + 132, T["pair"].format(diff=""), 13, "t2")
    s.text(x2 + 18, y2 + 152, dtxt, 13, "to", weight=600)

    # D-006
    x6, y6 = 830, 120
    s.rect(x6, y6, 330, 92, "box", 12)
    s.text(x6 + 18, y6 + 34, T["d006"], 17, weight=600)
    s.text(x6 + 18, y6 + 60, T["d006b"].format(hh=fmt(t24.loc[("D006", "rio"), "households"], lang)), 13, "t2")

    # D-004
    x4, y4 = 400, 530
    s.rect(x4, y4, 400, 110, "box", 12)
    s.text(x4 + 18, y4 + 32, T["d004"], 17, weight=600)
    s.text(x4 + 18, y4 + 58, T["d004b"].format(v=fmt(t24.loc[("D004", "kv_vopr0"), "rows"], lang)), 13, "t2")
    lines = t24[(t24.index.get_level_values(0) == "D004") & (t24.index.get_level_values(1) != "kv_vopr0")]
    s.text(x4 + 18, y4 + 82, T["d004c"].format(n=len(lines), l=fmt(lines["rows"].sum(), lang)), 13, "t2")

    # T-001, an island
    xt, yt = 850, 530
    s.rect(xt, yt, 310, 110, "island", 12)
    s.text(xt + 18, yt + 32, T["t001"], 17, weight=600)
    s.text(xt + 18, yt + 58, T["t001b"].format(p=fmt(t24.loc[("T001", "baza"), "rows"], lang)), 13, "t2")
    s.text(xt + 18, yt + 82, T["t001c"], 13, "to", weight=600)

    # edges, labelled
    e2 = l24.loc["D002.subject respondent -> D008.kontr_k person"]
    s.line([(x2 + 330, 272), (hx - 4, 336)], "e-ok", "m-ok")
    s.text(398, 258, T["e002"].format(f=fmt(e2.found_pct, lang), s=fmt(e2.sex_agrees_pct, lang)), 13, "tb", 600)
    s.text(398, 278, T["e002b"].format(a=fmt(kids.share_if_condition_pct, lang),
                                       b=fmt(kids.share_if_not_condition_pct, lang)), 13, "tb")
    e6 = l24.loc["D006.rio -> D008.kontr_k"]
    s.line([(x6 + 30, y6 + 92), (hx + hw - 10, hy - 4)], "e-broken", "m-broken")
    s.text(930, 240, T["e006"].format(f=fmt(e6.found_pct, lang)), 13, "to", 600)
    for j, ln in enumerate(T["e006b"].split("|")):
        s.text(930, 260 + j * 20, ln, 13, "to")
    e4 = l24.loc["D004.kv_vopr0 -> D008.kontr_k"]
    s.line([(600, y4), (600, hy + hh + 4)], "e-key", "m-key")
    s.text(588, 500, T["e004"].format(f=fmt(e4.found_pct, lang), r=fmt(e4.region_agrees_pct, lang)), 13, "t2", anchor="end")
    s.line([(xt + 60, yt), (hx + hw + 4, hy + hh - 20)], "e-region")
    s.text(905, 452, T["et001"], 13, "t3")
    s.text(905, 472, T["et001b"], 13, "t3")

    # the finding the join makes possible
    cx, cy = 40, 330
    s.rect(cx, cy, 384, 134, "call", 12)
    s.text(cx + 18, cy + 30, T["call1"], 15, weight=600)
    s.text(cx + 18, cy + 56, T["call2"], 13, "t2")
    s.text(cx + 18, cy + 84, T["call3"].format(r1=rn(a.region), a=fmt(a.coded_no_children, lang),
                                               b=fmt(a.with_child_in_roster, lang), p=fmt(a.missed_pct, lang, 1)), 15, "to", 600)
    s.text(cx + 18, cy + 110, T["call4"].format(r2=rn(b.region), c=fmt(b.coded_no_children, lang),
                                                d=fmt(b.with_child_in_roster, lang), q=fmt(b.missed_pct, lang, 1)), 15, "to", 600)

    # legend: the four line styles repeat, so they get one
    lx, ly = 40, 520
    for i, (cls, key) in enumerate((("e-ok", "leg_ok"), ("e-broken", "leg_broken"), ("e-key", "leg_key"), ("e-region", "leg_region"))):
        yy = ly + i * 28
        s.line([(lx, yy), (lx + 44, yy)], cls)
        s.text(lx + 56, yy + 5, T[key], 13, "t2")
    return s


# ---------- jury picture 2: what the tool reads and writes ----------

def ru_plural(n, one, few, many):
    n = int(n) % 100
    if 11 <= n <= 14:
        return many
    return one if n % 10 == 1 else few if n % 10 in (2, 3, 4) else many


def pipeline_svg(o, lang):
    T = L[lang]
    s = SVG(1200, 560, f'{T["pipe_title"]}. {T["pipe_sub"]}.', f"sq-pipe-{lang}")
    s.text(28, 46, T["pipe_title"], 26, weight=600)
    s.text(28, 74, T["pipe_sub"], 15, "t3")
    W, H, Y, G = 164, 100, 120, 32
    x = [28 + i * (W + G) for i in range(6)]
    n = {"rules": o["rules"], "issues": o["issues"], "cases": o["cases"], "sql": o["sql"]}
    if lang == "ru":
        sub = {"rules": (f'{n["rules"]} {ru_plural(n["rules"], "правило", "правила", "правил")}', "каждое с цитатой"),
               "card": (f'{n["issues"]} {ru_plural(n["issues"], "проблема", "проблемы", "проблем")}', "регион × форма × год"),
               "cases": (f'{n["cases"]} {ru_plural(n["cases"], "дело", "дела", "дел")}:', "причина, исправление")}
    else:
        sub = {"rules": (f'{n["rules"]} rules', "each with a quote"), "card": (f'{n["issues"]} issues', "region × form × year"),
               "cases": (f'{n["cases"]} case files:', "cause, fix")}
    boxes = [("docs", (T["docs"], T["docs2"]), "box"), ("rules", sub["rules"], "hub"), ("eng", T["eng2"].split("|"), "box"),
             ("card", sub["card"], "hub"), ("cases", sub["cases"], "box"), ("cons", T["cons2"].split("|"), "box")]
    for xi, (key, lines, cls) in zip(x, boxes):
        s.rect(xi, Y, W, H, cls, 10)
        s.text(xi + 14, Y + 32, T[key + "_t"], 17, weight=600)
        for j, ln in enumerate(lines):
            s.text(xi + 14, Y + 58 + j * 20, ln, 13, "t2")
    for i in range(5):
        s.line([(x[i] + W + 2, Y + H / 2), (x[i + 1] - 4, Y + H / 2)], "e-flow", "m-key")
    s.text((x[0] + W + x[1]) / 2, Y + H / 2 - 8, "LLM", 11, "tb", 600, "middle")

    # SQL for the Bureau, from the rules
    s.rect(x[1], 270, W, 84, "call", 10)
    s.text(x[1] + 14, 300, T["sql_t"], 15, weight=600)
    for j, ln in enumerate(T["sql2"].format(n=n["sql"]).split("|")):
        s.text(x[1] + 14, 324 + j * 18, ln, 13, "t2")
    s.line([(x[1] + W / 2, Y + H + 2), (x[1] + W / 2, 266)], "e-flow", "m-key")

    # comparisons without rules, into the scorecard
    for xi, key in ((x[3], "ml"), (x[4], "dec")):
        s.rect(xi, 270, W, 84, "box", 10)
        s.text(xi + 14, 300, T[key], 15, weight=600)
        for j, ln in enumerate(T[key + "2"].split("|")):
            s.text(xi + 14, 324 + j * 18, ln, 13, "t2")
    s.line([(x[3] + W / 2, 270), (x[3] + W / 2, Y + H + 4)], "e-flow", "m-key")
    s.line([(x[4] + 30, 270), (x[3] + W - 20, Y + H + 4)], "e-flow", "m-key")

    # the records feed the checks and both comparisons
    s.rect(x[2], 420, x[4] + W - x[2], 46, "sunk", 8)
    s.text((x[2] + x[4] + W) / 2, 449, T["data"], 14, "t2", 600, "middle")
    for xi in (x[2] + W / 2, x[3] + W / 2, x[4] + W / 2):
        top = Y + H + 4 if xi == x[2] + W / 2 else 358
        s.line([(xi, 420), (xi, top)], "e-flow", "m-key")

    # why the output can be trusted
    s.rect(x[0], 420, 2 * W + G, 112, "sunk", 10)
    s.text(x[0] + 14, 446, T["acc"], 14, weight=600)
    s.text(x[0] + 14, 466, T["acc2"].format(p=fmt(o["precision"], lang, 1), r=fmt(o["recall"], lang, 1)), 13, "t2")
    s.text(x[0] + 14, 496, T["proof"], 14, weight=600)
    s.text(x[0] + 14, 516, T["proof2"].format(n=fmt(o["proof_runs"], lang)), 13, "t2")
    return s


# ---------- technical diagrams (Graphviz) ----------

def gv_label(rows, head, sub):
    out = [f'<TR><TD ALIGN="LEFT" BGCOLOR="#dce8fa"><B>{escape(head)}</B><BR/><FONT POINT-SIZE="10" COLOR="{INK3}">{escape(sub)}</FONT></TD></TR>']
    for port, txt, colour in rows:
        p = f' PORT="{port}"' if port else ""
        out.append(f'<TR><TD ALIGN="LEFT"{p}><FONT COLOR="{colour}">{escape(txt)}</FONT></TD></TR>')
    return '<<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" CELLPADDING="4" COLOR="#c3cbd7">' + "".join(out) + "</TABLE>>"


def erd_data(o):
    tab, cols = o["tables"], o["columns"]
    t24 = tab[tab.year == 2024]
    lines = ["digraph G {", 'graph [rankdir=LR, fontname="Helvetica", nodesep=0.35, ranksep=1.1, bgcolor="white", '
             'label="Survey files: tables, keys, grain (rows in 2024). PK = key of the table, FK = points to the roster. '
             'Full column list: schema_columns.csv", labelloc=t, fontsize=14];',
             'node [shape=plain, fontname="Helvetica", fontsize=11]; edge [fontname="Helvetica", fontsize=10];']
    keyed = {"NOMER", "NOMP", "KVARTAL", "KODNU", "TE", "K", "GOD", "GODO"}
    lines_t = t24[(t24.form == "D004") & (t24.table != "kv_vopr0")]
    rows = [("NOMER", "PK NOMER FK→D008 + KVARTAL (+ KODNU)", BLUE)]
    for _, t in lines_t.iterrows():
        c = cols[(cols.form == "D004") & (cols.table == t.table)]
        rows.append((None, f"{t.table}: {int(t.rows):,} rows · {t.columns} columns · {int((c.rules > 0).sum())} used by rules", INK2))
    rows.append((None, "one row = one spending line; key NOMER+KVARTAL+KODNU is not unique", INK3))
    lines.append(f'"D004.lines" [label={gv_label(rows, f"D004.kv_vopr1…12 ({len(lines_t)} tables)", "household x quarter x item")}];')
    for _, t in t24.drop(lines_t.index).iterrows():
        c = cols[(cols.form == t.form) & (cols.table == t.table)]
        rows = []
        for k in str(t.key).split("+"):
            if k in set(c.column) or (k == "KVARTAL" and t.form == "D004"):
                fk = " FK→D008" if k in ("NOMER", "NOMP") and t.table != "kontr_k" else ""
                rows.append((k, f"PK {k}{fk}", BLUE))
        if t.form == "D002":   # the respondent: a person in the roster
            rows.append(("NOMP", "NOMP FK→D008 (respondent)", BLUE))
        for k in ("TE", "K"):
            if k in set(c.column):
                rows.append((k, f"{k}  region / settlement code", INK2))
        rest = c[~c.column.isin(keyed)]
        kinds = rest.kind.value_counts()
        rows.append((None, f"{len(rest)} more: " + ", ".join(f"{n} {k}" for k, n in kinds.items()), INK2))
        ruled = int((rest.rules > 0).sum())
        doc = int(rest.documented.sum())
        rows.append((None, f"{ruled} used by rules · {doc} documented", INK3))
        if t.form == "T001":
            rows.append((None, f"released {t.columns} of {t.columns_real} columns; no ID", ORANGE))
        uniq = {True: " · key unique", False: " · key not unique"}.get(t.key_unique, "" if t.key != "none" else " · no key")
        sub = f"{t.grain} · {int(t.rows):,} rows{uniq}"
        lines.append(f'"{t.form}.{t.table}" [label={gv_label(rows, f"{t.form}.{t.table}", sub)}];')
    lk = o["links"][o["links"].year == 2024].set_index("link")
    def found(name):
        return f'{lk.loc[name, "found_pct"]:.0f}% found'
    lines += [
        f'"D002.subject":NOMER -> "D008.kontr_k":NOMER [color="{BLUE}", penwidth=2, label="NOMER+NOMP · {found("D002.subject respondent -> D008.kontr_k person")}"];',
        f'"D002.subject":NOMER -> "D002.ocenka":NOMER [dir=both, color="{INK2}", label="1:1 · respondent differs in {int(lk.loc["D002.subject <-> D002.ocenka", "respondent_differs"])}"];',
        f'"D002.ocenka":NOMER -> "D008.kontr_k":NOMER [color="{BLUE}", penwidth=2, label="GR40 vs age: answers agree"];',
        f'"D006.rio":NOMER -> "D008.kontr_k":NOMER [color="{ORANGE}", style=dashed, label="NOMER · {found("D006.rio -> D008.kontr_k")} · answers unlinked in synthetic"];',
        f'"D004.kv_vopr0":NOMER -> "D008.kontr_k":NOMER [color="{INK2}", label="NOMER · {found("D004.kv_vopr0 -> D008.kontr_k")}"];',
    ]
    lines.append(f'"D004.lines":NOMER -> "D004.kv_vopr0":NOMER [color="{INK2}", label="NOMER+KVARTAL · {min(lk.loc["D004.kv_vopr1 -> D004.kv_vopr0", "found_pct"], lk.loc["D004.kv_vopr12 -> D004.kv_vopr0", "found_pct"]):.0f}% found (kv_vopr1, 12)"];')
    lines.append(f'"T001.baza":TE -> "D008.kontr_k":TE [color="{INK3}", style=dotted, label="TE + quarter only"];')
    lines.append("}")
    return "\n".join(lines)


OUTPUTS = [  # file, what one row is, key, written by, [(file it reads, join key)] — as the scripts read them
    ("rules/<form>.json", "one rule", "id", "extract (LLM), team review", []),
    ("rules_export.csv", "one rule, with SQL", "rule_id", "engine/export.py", [("rules/<form>.json", "rule_id = id")]),
    ("<FORM>_results.csv", "rule × column × year × region", "rule_id, column, year, te", "engine/statquo.py",
     [("rules/<form>.json", "rule_id = id")]),
    ("<FORM>_region_flags.csv", "flagged region", "rule_id, column, year, region", "engine/statquo.py",
     [("<FORM>_results.csv", "rule_id, column, year")]),
    ("<FORM>_cross_form.csv", "two-form share check", "rule_id, year, te", "engine/statquo.py", [("rules/<form>.json", "rule_id = id")]),
    ("<FORM>_cross_form_flags.csv", "region outside the bounds", "rule_id, year, region", "engine/statquo.py",
     [("<FORM>_cross_form.csv", "rule_id, year, te")]),
    ("compare_region_sweep.csv", "variable × region (Jensen-Shannon)", "form, table, year, variable, te", "engine/compare.py", []),
    ("compare_year_c2st.csv", "region, year vs year", "form, te, compare", "engine/compare.py", []),
    ("compare_invariants.csv", "form-vs-form invariant", "year, a, b, region", "engine/compare.py", []),
    ("decoder_code_shift.csv", "code that moved", "form, year, region, column, code", "decoder/decode.py", []),
    ("decoder_cases.json", "decoder numbers for cases", "case", "decoder/decoder_cases.py", [("decoder_code_shift.csv", "form, column, code")]),
    ("scorecard_issues.csv", "one issue", "form, rule_id, year, region", "engine/scorecard.py",
     [("<FORM>_region_flags.csv", "rule_id, year, region"), ("<FORM>_cross_form_flags.csv", "rule_id, year, region"),
      ("decoder_code_shift.csv", "form, year, region"), ("compare_region_sweep.csv", "form, year, region")]),
    ("cases.json", "one case file", "id", "engine/cases.py",
     [("<FORM>_results.csv", "rule_id, year, te"), ("<FORM>_region_flags.csv", "rule_id, year, region"),
      ("<FORM>_cross_form.csv", "rule_id, year, te"), ("decoder_cases.json", "case"), ("compare_region_sweep.csv", "form, year, te")]),
    ("child_impact.csv", "region × year", "year, te", "analysis/child_impact.py", []),
    ("proof_sensitivity.csv", "one planted-error run", "baseline, kind, rule, rate, trial, region", "proof/plant.py",
     [("rules/<form>.json", "rule = id")]),
    ("schema_columns.csv", "one column of the survey files", "form, table, column", "schema/profile.py",
     [("rules/<form>.json", "rule_ids ∋ id")]),
    ("console data.json", "everything the console shows", "", "console/build_console.py",
     [("rules_export.csv", "rule_id"), ("scorecard_issues.csv", "form, year, region"), ("cases.json", "id"),
      ("child_impact.csv", "year, te"), ("compare_year_c2st.csv", "te"), ("proof_sensitivity.csv", "")]),
]


def erd_outputs(out_dir):
    lines = ["digraph G {", 'graph [rankdir=LR, fontname="Helvetica", nodesep=0.3, ranksep=0.9, bgcolor="white", '
             'label="Outputs: what one row is, its key (blue), the script that writes it, and which files each script reads (arrow = read, label = join key)", labelloc=t, fontsize=14];',
             'node [shape=plain, fontname="Helvetica", fontsize=10]; edge [fontname="Helvetica", fontsize=9, color="#47505e"];']
    for f, grain, key, by, _ in OUTPUTS:
        if f.startswith("rules/"):
            sample = next(iter(sorted(Path(out_dir).parent.glob("rules/d002*.json"))), None)
        else:
            sample = Path(out_dir, f.replace("<FORM>", "D002"))
            sample = sample if sample.exists() else None
        cols = []
        if sample is not None and sample.suffix == ".csv":
            cols = list(pd.read_csv(sample, nrows=0).columns)
        elif sample is not None and sample.suffix == ".json":
            j = json.load(open(sample))
            item = j["rules"][0] if isinstance(j, dict) and "rules" in j else (j[0] if isinstance(j, list) else {})
            cols = list(item.keys())
        keys = [k.strip() for k in key.split(",")]
        rows = [(None, "PK " + key, BLUE)] if key else []
        other = [c for c in cols if c not in keys]
        for i in range(0, len(other), 4):
            rows.append((None, ", ".join(other[i:i + 4]), INK2))
        rows.append((None, f"written by {by}", INK3))
        lines.append(f'"{f}" [label={gv_label(rows, f, grain)}];')
    for f, _, _, _, joins in OUTPUTS:
        for other, on in joins:
            lines.append(f'"{other}" -> "{f}" [label="{on}"];')
    lines.append("}")
    return "\n".join(lines)


def md_table(df):
    cols = list(df.columns)
    out = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for r in df.itertuples(index=False):
        out.append("| " + " | ".join("" if v is None or (isinstance(v, float) and v != v) else str(v) for v in r) + " |")
    return "\n".join(out)


def write_reference(o, path):
    """DATA_MODEL.md: the data model for the Bureau's staff. Tables and numbers are filled from out/."""
    tab, lk, hc, cols = o["tables"], o["links"], o["household"], o["columns"]
    y = int(tab.year.max())
    t = tab[tab.year == y]
    tt = pd.DataFrame({"table": t.form + "." + t.table, "one row is": t.grain, "key": t.key,
                       f"rows {y}": t.rows.map(lambda v: f"{int(v):,}"),
                       "columns (release / real)": t["columns"].astype(int).astype(str) + " / " + t.columns_real.astype(int).astype(str),
                       "key unique": t.key_unique.map({True: "yes", False: "no"}).fillna("–"),
                       "households in D008 roster": t.households_in_roster_pct.map(lambda v: "" if v != v else f"{v:.0f}%")})
    piv = []
    for name, g in lk.groupby("link", sort=False):
        row = {"link": name, "key": g.key.iloc[0]}
        for _, r in g.iterrows():
            if r.share_if_condition_pct == r.share_if_condition_pct:
                v = f"{r.share_if_condition_pct:.1f} / {r.share_if_not_condition_pct:.1f}"
            elif r.respondent_differs == r.respondent_differs:
                v = f"{r.found_pct:.0f}% found; other person in {int(r.respondent_differs)}"
            else:
                v = f"{r.found_pct:.0f}% found" + (f", region {r.region_agrees_pct:.0f}%" if r.region_agrees_pct == r.region_agrees_pct else "") \
                    + (f", sex {r.sex_agrees_pct:.0f}%" if r.sex_agrees_pct == r.sex_agrees_pct else "")
            row[str(int(r.year))] = v
        piv.append(row)
    h = hc[hc.year == y].sort_values("missed_pct", ascending=False)
    hh = pd.DataFrame({"region": h.region, "child in D008": h.with_child_in_roster, "coded 'no children'": h.coded_no_children,
                       "missed %": h.missed_pct, "no child in D008, coded 'has children' %": h.false_yes_pct})
    cov = cols.groupby(["form", "table"]).agg(columns=("column", "size"), documented=("documented", "sum"),
                                              used_by_rules=("rules", lambda v: int((v > 0).sum()))).reset_index()
    cov.insert(0, "t", cov.form + "." + cov.table)
    cov = cov.drop(columns=["form", "table"]).rename(columns={"t": "table"})
    outs = pd.DataFrame([{"file": f, "one row is": g, "key": k, "written by": b, "reads": "; ".join(f"{x} ({on})" for x, on in j)}
                         for f, g, k, b, j in OUTPUTS])
    kids = lk[(lk.year == y) & lk.link.str.startswith("D002.ocenka GR40")].iloc[0]
    rent = lk[(lk.year == y) & lk.link.str.startswith("D002.ocenka GR31_1")].iloc[0]
    diff = lk[lk.link == "D002.subject <-> D002.ocenka"].set_index("year").respondent_differs.astype(int)
    a, b = h.iloc[0], h.iloc[1]
    text = f"""# StatQUO data model

For the Bureau's technical staff: what each survey file holds, its key, how the files join, and what the tool writes.
Everything below is generated by `schema/profile.py` and `schema/draw.py` from the synthetic release
(2021–2024); rerun both on the real records and this file, the diagrams and the console's "Данные" tab update.

## In short

- **One household number in four forms.** `NOMER` identifies the same household in D-002, D-004, D-006 and D-008.
  Every record finds its household in the D-008 roster, and region (`TE`) and settlement type (`K`) agree,
  in every year. The D-008 roster (`kontr_k`, one row per person, key `NOMER + NOMP`) is the hub.
- **Join within one year.** In this release `NOMER` starts with the year (`{y}000001`), so a household cannot be followed from one year to the next.
- **D-002 has two halves of one questionnaire** (`subject`, `ocenka`), 1:1 on `NOMER`, with one respondent, who is a
  person in the roster (`NOMER + NOMP`). The respondent recorded in the two halves differs in
  {", ".join(f"{k}: {v}" for k, v in diff.items())} households (2021 without age; see rule `D002-same-person`).
- **D-004 is a quarterly journal.** `kv_vopr0` is one row per household and quarter (visit result); `kv_vopr1…12`
  are spending lines, joined to the visit on `NOMER + KVARTAL`. `NOMER + KVARTAL + KODNU` is not unique: one item can appear on several lines.
- **T-001 has no household or person number** in the release ({int(t[t.form == "T001"]["columns"].iloc[0])} of
  {int(t[t.form == "T001"].columns_real.iloc[0])} columns). It joins the other forms only by region and quarter; the decoder compares how its codes behave with D-008 and D-006.
- **Which links survive synthesis.** D-002 ↔ D-008 holds household by household: GR40 'has children' is 1 for
  {kids.share_if_condition_pct:.1f}% of households with a member under 18 in the roster against
  {kids.share_if_not_condition_pct:.1f}% without. D-002 ↔ D-006 does not: GR31_1 'not relevant' is
  {rent.share_if_condition_pct:.1f}% for owners and {rent.share_if_not_condition_pct:.1f}% for the rest. So the rent
  rule is checked on regional shares, and the children rule can be checked household by household.
- **The join as a check ({y}):** rules `D002-x-D008-child-household` and `D002-x-D008-nochild-household` run it
  region by region with the same flag test as every other rule; flagged regions go to the scorecard and case C1.
  Households with a child in the roster coded 'no children': {a.region}
  {int(a.coded_no_children)} of {int(a.with_child_in_roster)} ({a.missed_pct:.1f}%), {b.region}
  {int(b.coded_no_children)} of {int(b.with_child_in_roster)} ({b.missed_pct:.1f}%). The reverse, households with no one under 18 in the roster coded 'has children':
  {", ".join(f"{r.region} {r.false_yes_pct:.1f}%" for r in h.sort_values("false_yes_pct", ascending=False).head(3).itertuples())}.

Diagrams: `diagrams/links_en.svg` (and `_ru`), `diagrams/erd_data.svg` (all tables and keys),
`diagrams/pipeline_en.svg`, `diagrams/erd_outputs.svg` (all output files).

## Tables ({y})

{md_table(tt)}

## How to join them

```sql
-- the two halves of D-002
SELECT * FROM d002_subject s JOIN d002_ocenka o ON o.NOMER = s.NOMER;
-- the D-002 respondent in the roster
SELECT * FROM d002_subject s JOIN d008_kontr_k k ON k.NOMER = s.NOMER AND k.NOMP = s.NOMP;
-- one row per household from the roster, then any household form
SELECT k.NOMER, k.TE, MAX(CASE WHEN {y} - CAST(k.GOD_ROJD AS INT) < 18 THEN 1 ELSE 0 END) AS child_in_roster
FROM d008_kontr_k k GROUP BY k.NOMER, k.TE;
-- D-004 spending lines to the visit record of the same quarter
SELECT * FROM d004_kv_vopr1 l JOIN d004_kv_vopr0 v ON v.NOMER = l.NOMER AND v.KVARTAL = l.KVARTAL;
-- household-level children check, by region
WITH r AS (SELECT NOMER, MAX(CASE WHEN {y} - CAST(GOD_ROJD AS INT) < 18 THEN 1 ELSE 0 END) AS kid
           FROM d008_kontr_k GROUP BY NOMER)
SELECT o.TE, SUM(r.kid) AS with_child, SUM(CASE WHEN r.kid = 1 AND CAST(o.GR40 AS INT) <> 1 THEN 1 ELSE 0 END) AS coded_no_children
FROM d002_ocenka o JOIN r ON r.NOMER = o.NOMER GROUP BY o.TE ORDER BY coded_no_children DESC;
```

All columns are read as text; codes keep leading zeros (`NOMP` '01'). `TE` is the two-digit region code.

## Links, year by year

For the last two rows the cells are the answer's share with and without the condition (%):
close numbers mean the two forms are not linked household by household in this release.

{md_table(pd.DataFrame(piv))}

## Household-by-household children check ({y})

{md_table(hh)}

## Column dictionary

`out/schema_columns.csv`, one row per column: years present, inferred kind (code, integer, number, text, empty),
share filled and distinct values in the latest year, the five most frequent values, the type, length and
description from the Bureau's structure file where it gives them, and the rules that check the column.
The D-006 structure file is written as prose, so only the columns it names next to a question get a description.

{md_table(cov)}

## What the tool writes

{md_table(outs)}

## Rerun

```bash
python schema/profile.py --data DATA_DIR --out out/   # about 2 minutes
python schema/draw.py --out out/ --to diagrams/       # needs Graphviz (dot) for the two technical diagrams
python console/build_console.py out/ console/ && python console/make_page.py
```
"""
    Path(path).write_text(text, encoding="utf-8")


def numbers(out_dir):
    out_dir = Path(out_dir)
    o = {"tables": pd.read_csv(out_dir / "schema_tables.csv"), "columns": pd.read_csv(out_dir / "schema_columns.csv"),
         "links": pd.read_csv(out_dir / "schema_links.csv"), "household": pd.read_csv(out_dir / "schema_household_children.csv")}
    r = pd.read_csv(out_dir / "rules_export.csv")
    acc = pd.read_csv(out_dir / "accuracy_d002_v1_vs_reviewed.csv").set_index("type").loc["ALL"]
    proof = sum(len(pd.read_csv(out_dir / f)) for f in ("proof_sensitivity.csv", "proof_sensitivity_clean.csv"))
    o.update(rules=len(r), sql=int(r.sql_first_column.notna().sum()), issues=len(pd.read_csv(out_dir / "scorecard_issues.csv")),
             cases=len(json.load(open(out_dir / "cases.json"))), precision=100 * acc.precision, recall=100 * acc.recall,
             proof_runs=proof)
    return o


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="out")
    ap.add_argument("--to", default="diagrams")
    a = ap.parse_args()
    to = Path(a.to)
    to.mkdir(parents=True, exist_ok=True)
    o = numbers(a.out)
    for lang in ("ru", "en"):
        for name, fn in (("links", links_svg), ("pipeline", pipeline_svg)):
            svg = fn(o, lang)
            (to / f"{name}_{lang}.svg").write_text(svg.render(True), encoding="utf-8")
            (to / f"{name}_{lang}_inline.svg").write_text(svg.render(False), encoding="utf-8")
    for name, dot in (("erd_data", erd_data(o)), ("erd_outputs", erd_outputs(a.out))):
        (to / f"{name}.dot").write_text(dot, encoding="utf-8")
        subprocess.run(["dot", "-Tsvg", str(to / f"{name}.dot"), "-o", str(to / f"{name}.svg")], check=True)
    write_reference(o, Path(a.out).parent / "DATA_MODEL.md")
    print("written to", to, "and DATA_MODEL.md")


if __name__ == "__main__":
    main()
