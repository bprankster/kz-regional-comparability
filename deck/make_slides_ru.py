"""Русская версия финальной презентации. Те же расчёты, что в make_slides.py: каждое число на слайде
берётся из результатов движка, переведён только текст.

    python deck/make_slides_ru.py out/ deck/build_ru/
"""
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

OUT, BUILD = Path(sys.argv[1]), Path(sys.argv[2])
(BUILD / "project" / "slides").mkdir(parents=True, exist_ok=True)

INK, MUTED, FAINT, LINE, BLUE, ORANGE, BG, PANEL = "#1F2933", "#52514E", "#75746F", "#E8E7E3", "#2A78D6", "#EB6834", "#FFFFFF", "#F6F5F2"
FONT = "'IBM Plex Sans', Arial, sans-serif"
SEC = f"background:{BG};color:{INK};font-family:{FONT};padding:60px 115px 160px;display:flex;flex-direction:column;gap:44px"
FOOT = "Все цифры: синтетические микроданные 2021–2024 (STAT.DATATHON 2026), расчёты команды."
CASES = {c["id"]: c for c in json.load(open(OUT / "cases.json", encoding="utf-8"))}
NUM = json.load(open(OUT / "case_numbers.json", encoding="utf-8"))

REG = {"Abai": "Абай", "Akmola": "Акмола", "Aktobe": "Актобе", "Almaty city": "г. Алматы", "Almaty oblast": "Алматинская обл.",
       "Astana": "г. Астана", "Atyrau": "Атырау", "East Kazakhstan": "ВКО", "Karaganda": "Караганда", "Kostanay": "Костанай",
       "Kyzylorda": "Кызылорда", "Mangystau": "Мангистау", "North Kazakhstan": "СКО", "Pavlodar": "Павлодар",
       "Shymkent": "г. Шымкент", "Turkistan": "Туркестан", "Ulytau": "Улытау", "West Kazakhstan": "ЗКО",
       "Zhambyl": "Жамбыл", "Zhetysu": "Жетысу"}


def R(name):
    return REG.get(name, name)


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def comma(html):
    """Десятичная запятая в тексте (не в атрибутах и стилях)."""
    return re.sub(r">([^<]*)<", lambda m: ">" + re.sub(r"(?<=\d)\.(?=\d)", ",", m.group(1)) + "<", html)


def head(title, sub):
    return (f'<div style="display:flex;flex-direction:column;gap:18px">'
            f'<h2 style="font-size:56px;font-weight:700;line-height:1.1;color:{INK}">{esc(title)}</h2>'
            f'<p style="font-size:26px;line-height:1.3;color:{FAINT}">{esc(sub)}</p></div>')


def foot(text=FOOT):
    return f'<p style="position:absolute;left:115px;bottom:64px;width:1690px;font-size:24px;color:{FAINT}">{esc(text)}</p>'


def block(title, text, size=28):
    return (f'<div style="display:flex;flex-direction:column;gap:10px"><h3 style="font-size:30px;font-weight:700;line-height:1.2;color:{INK}">{esc(title)}</h3>'
            f'<p style="font-size:{size}px;line-height:1.4;color:{MUTED}">{text}</p></div>')


def big(number, label, color=BLUE):
    return (f'<div style="flex:1;display:flex;flex-direction:column;gap:12px;background:{PANEL};padding:36px;border-radius:16px">'
            f'<p style="font-size:72px;font-weight:700;line-height:1;color:{color}">{esc(number)}</p>'
            f'<p style="font-size:26px;line-height:1.35;color:{MUTED}">{label}</p></div>')


def section(sid, body, notes, transition=True):
    t = ' data-transition="fade"' if transition else ""
    return comma(f'<section id="{sid}"{t} style="{SEC}">\n{body}\n<aside>{esc(notes)}</aside>\n</section>\n')


slides = {}

# 1 обложка
slides["cover"] = comma(f'<section id="cover" style="background:{BG};color:{INK};font-family:{FONT};padding:115px;display:flex;flex-direction:column;justify-content:center;gap:64px">'
    f'<div style="display:flex;flex-direction:column;gap:28px">'
    f'<h1 style="font-size:80px;font-weight:700;line-height:1.1;color:{INK}">Одинаково ли регионы записывают одни и те же ответы?</h1>'
    f'<p style="font-size:48px;line-height:1.2;color:{MUTED}">Инструмент, который превращает анкеты в проверки и запускает их по каждому региону</p></div>'
    f'<div style="display:flex;flex-direction:column;gap:14px">'
    f'<p style="font-size:30px;font-weight:700;color:{INK}">Команда StatQUO</p>'
    f'<p style="font-size:28px;color:{MUTED}">Aidai Totoeva · Baiirbek Kholikov · Almanbet Kaldybaev · Nargiza Zhumalieva</p>'
    f'<p style="font-size:26px;color:{FAINT}">STAT.DATATHON 2026 · Финал · Трек 2: AI for Official Statistics · 20 октября 2026</p></div>'
    f'<aside>Мы сделали инструмент для Бюро. Он читает анкеты, превращает их в проверки, запускает проверки по каждому региону и показывает, где регион записывает одну и ту же ситуацию по-другому. Всё, что вы увидите, посчитано на синтетических данных; на реальных данных инструмент работает без изменений.</aside></section>\n')

# 2 проблема
slides["problem"] = section("problem",
    head("Одна ситуация — два разных кода", "Д-002, часть 3, вопрос 1.1 «не смогли оплатить аренду» и собственность на жильё в Д-006, 20 регионов, 2024")
    + '<div style="display:flex;gap:40px">'
    + big(f"{NUM['owners_min']}–{NUM['owners_max']}", "домохозяйств живут в собственном жилье, в каждом регионе (Д-006)")
    + big(f"{NUM['rent_nr_min']}–{NUM['rent_nr_max']}", f"закодированы 4 «не актуально» для аренды: меньше всего — {R(NUM['rent_nr_min_region'])}, больше всего — {R(NUM['rent_nr_max_region'])}. Остальные собственники получают код 3 «нет»", ORANGE)
    + '</div>'
    + f'<p style="font-size:34px;line-height:1.35;color:{INK}">Доля задолженности «среди тех, для кого аренда актуальна» тогда измеряет привычку кодирования в регионе. Такие ошибки проходят любую проверку диапазона. Их видно, только если знать, что означает вопрос анкеты.</p>'
    + foot(),
    "Собственников везде от 89 до 98 процентов, а доля кода «не актуально» — от 9 до 98 процентов. Остальным собственникам ставят «нет». Оба кода допустимы, поэтому проверка диапазона проходит. Разницу видно, только если понимать смысл вопроса, а именно это наш инструмент и читает в анкете.")

# 3 инструмент
boxes = [("Анкеты", "формы, инструкции, структуры файлов, каз. + рус."), ("Правила (LLM)", "переходы, коды, смысл ответов; у каждого цитата"),
         ("Проверки по регионам", "правило × регион × год; сигнал с меткой доверия"), ("Карточки случаев (LLM)", "текст пишет модель, каждое число — код"),
         ("Карта + SQL", "Бюро перезапускает каждый квартал")]
w, gap, x0 = 300, 47, 0
svg = ['<svg aria-label="Конвейер: анкеты, правила от LLM, проверки по регионам, карточки случаев, карта сопоставимости и SQL. Сравнения (ML) дополняют проверки." width="1690" height="420" viewBox="0 0 1690 420" xmlns="http://www.w3.org/2000/svg">']
for i, (t, s) in enumerate(boxes):
    x = x0 + i * (w + gap)
    fill = BLUE if i in (1, 3) else PANEL
    tc = "#FFFFFF" if i in (1, 3) else INK
    sc = "#EAF2FC" if i in (1, 3) else MUTED
    svg.append(f'<rect x="{x}" y="40" width="{w}" height="210" rx="16" fill="{fill}"/>')
    tw, tl, tls = t.split(), "", []
    for wd in tw:
        if len(tl + " " + wd) > 16:
            tls.append(tl); tl = wd
        else:
            tl = (tl + " " + wd).strip()
    tls.append(tl)
    for j, ln in enumerate(tls):
        svg.append(f'<text x="{x + 24}" y="{92 + 34 * j}" font-size="28" font-weight="700" fill="{tc}" font-family="IBM Plex Sans, Arial">{esc(ln)}</text>')
    words, line, lines = s.split(), "", []
    for wd in words:
        if len(line + " " + wd) > 22:
            lines.append(line); line = wd
        else:
            line = (line + " " + wd).strip()
    lines.append(line)
    for j, ln in enumerate(lines):
        svg.append(f'<text x="{x + 24}" y="{100 + 34 * len(tls) + 30 * j}" font-size="22" fill="{sc}" font-family="IBM Plex Sans, Arial">{esc(ln)}</text>')
    if i < len(boxes) - 1:
        ax = x + w + 6
        svg.append(f'<path d="M{ax} 145 L{ax + gap - 14} 145" stroke="{FAINT}" stroke-width="3"/><path d="M{ax + gap - 14} 137 L{ax + gap - 4} 145 L{ax + gap - 14} 153 Z" fill="{FAINT}"/>')
mx = 2 * (w + gap)
svg.append(f'<rect x="{mx}" y="300" width="{w}" height="110" rx="16" fill="{PANEL}" stroke="{ORANGE}" stroke-width="3"/>')
svg.append(f'<text x="{mx + 24}" y="345" font-size="28" font-weight="700" fill="{INK}" font-family="IBM Plex Sans, Arial">Сравнения (ML)</text>')
svg.append(f'<text x="{mx + 24}" y="385" font-size="22" fill="{MUTED}" font-family="IBM Plex Sans, Arial">регион, год, форма</text>')
svg.append(f'<path d="M{mx + w / 2} 296 L{mx + w / 2} 262" stroke="{ORANGE}" stroke-width="3"/><path d="M{mx + w / 2 - 8} 270 L{mx + w / 2} 256 L{mx + w / 2 + 8} 270 Z" fill="{ORANGE}"/>')
svg.append("</svg>")
slides["tool"] = section("tool", head("Что мы сделали", "Один конвейер для четырёх форм обследования домохозяйств (Д-002, Д-004, Д-006, Д-008) и обследование рабочей силы (Т-001) в сравнениях ML")
    + "".join(svg)
    + f'<p style="font-size:30px;line-height:1.4;color:{MUTED}">LLM читает, код считает. Ни одно число в карточке случая не написано моделью.</p>' + foot(),
    "Пять шагов. LLM читает анкеты и пишет правила. Движок запускает каждое правило по каждому региону и году. Три сравнения ML ищут различия, которые не описывает ни одно правило: регион против остальной страны, один год против следующего и одна форма против другой. Затем LLM пишет карточки случаев, но каждое число в них подставляет код. Бюро получает правила в виде SQL и карту, которую можно перезапускать каждый квартал.")

# 4 правила
counts = {}
for p in sorted(Path(OUT).parent.glob("rules/*.json")):
    sp = json.load(open(p, encoding="utf-8"))
    counts[sp["form"]] = len(sp["rules"])
ex = pd.read_csv(OUT / "rules_export.csv")
code_style = f"font-size:24px;line-height:1.45;color:{INK};background:{PANEL};padding:28px;border-radius:12px;font-family:'Courier New', monospace"
slides["rules"] = section("rules", head("Одна строка анкеты становится одной проверкой", f"{sum(counts.values())} правил из четырёх форм: " + ", ".join(f"Д-{k[1:]} — {v}" for k, v in counts.items()) + ". У каждого — цитата из источника.")
    + '<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:32px">'
    + f'<div style="display:flex;flex-direction:column;gap:14px"><h3 style="font-size:30px;font-weight:700;color:{INK}">Анкета</h3><p style="{code_style}">17. Имеется ли в Вашем домашнем хозяйстве ребенок дошкольного возраста, не посещающий дошкольное учреждение?<br>да → 18<br>нет → 19</p></div>'
    + f'<div style="display:flex;flex-direction:column;gap:14px"><h3 style="font-size:30px;font-weight:700;color:{INK}">Правило (LLM)</h3><p style="{code_style}">type: skip<br>when: GR317 = 2<br>targets: GR318_1 … GR318_9<br>confidence: high</p></div>'
    + f'<div style="display:flex;flex-direction:column;gap:14px"><h3 style="font-size:30px;font-weight:700;color:{INK}">Проверка (код)</h3><p style="{code_style}">SELECT TE, COUNT(*)<br>FROM d002_ocenka<br>WHERE GR317 = 2<br>AND GR318_1 IS NOT NULL<br>GROUP BY TE;</p></div>'
    + '</div>'
    + f'<p style="font-size:28px;line-height:1.4;color:{MUTED}">Семь видов правил: допустимые коды, переходы, обязательные ответы, множественный выбор, связи между ответами, связи с другой формой и противоречия в самой документации.</p>'
    + foot(),
    "Вот одно правило. В вопросе 17 «да» ведёт к вопросу 18, «нет» — к 19. Модель записывает это как правило: если GR317 равно 2, причины в GR318 должны быть пустыми, и прикладывает цитату. Код превращает правило в проверку, а Бюро получает ту же проверку в виде SQL. Правила о противоречиях в документации — это место, где модель читает казахский и русский тексты рядом.")

# 5 точность
import importlib.util
spec_ = importlib.util.spec_from_file_location("score", Path(OUT).parent / "gold" / "score.py")
score = importlib.util.module_from_spec(spec_); spec_.loader.exec_module(score)
rules_d002 = json.load(open(Path(OUT).parent / "rules" / "d002_2023-2024.json", encoding="utf-8"))
ext = score.atoms_extracted({"rules": [r for r in rules_d002["rules"] if not r.get("added_after_review")]})
ref = score.atoms_reference(json.load(open(Path(OUT).parent / "gold" / "d002_gold_reviewed.json", encoding="utf-8")))
rep = score.report(*score.match(ext, ref)).set_index("type")
order = ["skip", "multi_select", "required", "domain", "required_any", "cross_form", "doc_issue", "consistency"]
label = {"skip": "Переходы", "multi_select": "Множ. выбор", "required": "Обязательные", "domain": "Допустимые коды",
         "required_any": "Хотя бы одна отметка", "cross_form": "Связи с др. формами", "doc_issue": "Документация", "consistency": "Связи ответов"}
H = 56 * len(order) + 60
svg = [f'<svg aria-label="Полнота и точность извлечённых правил по видам правил относительно эталонного набора." width="1100" height="{H}" viewBox="0 0 1100 {H}" xmlns="http://www.w3.org/2000/svg">']
X0, W = 360, 610
for k in (0, 50, 100):
    x = X0 + W * k / 100
    svg.append(f'<line x1="{x}" y1="20" x2="{x}" y2="{H - 30}" stroke="{LINE}" stroke-width="2"/><text x="{x}" y="{H - 4}" font-size="24" fill="{MUTED}" text-anchor="middle" font-family="IBM Plex Sans, Arial">{k}%</text>')
for i, t in enumerate(order):
    y = 30 + 56 * i
    rc, pr, n = rep.loc[t, "recall"], rep.loc[t, "precision"], int(rep.loc[t, "reference"])
    svg.append(f'<text x="{X0 - 16}" y="{y + 26}" font-size="24" fill="{INK}" text-anchor="end" font-family="IBM Plex Sans, Arial">{label[t]} ({n})</text>')
    svg.append(f'<rect x="{X0}" y="{y + 6}" width="{W * rc:.0f}" height="22" rx="4" fill="{BLUE}"/>')
    svg.append(f'<rect x="{X0}" y="{y + 32}" width="{W * pr:.0f}" height="10" rx="3" fill="{ORANGE}"/>')
    svg.append(f'<text x="{X0 + W * rc + 10:.0f}" y="{y + 26}" font-size="24" fill="{INK}" font-family="IBM Plex Sans, Arial">{100 * rc:.0f}%</text>')
svg.append("</svg>")
tot = rep.loc["ALL"]
_ru = Path(OUT).parent / "gold" / "d002_review_ru.csv"
rv = pd.read_csv(_ru, encoding="utf-8-sig") if _ru.exists() else pd.read_csv(Path(OUT).parent / "gold" / "d002_review.csv")
_tick = rv["Ваша отметка (✓ согласна / ✗ нет)"] if "Ваша отметка (✓ согласна / ✗ нет)" in rv else rv.iloc[:, -1]
n_dis, n_ok = len(rv), int(_tick.astype(str).str.strip().isin(["✓", "v", "V", "yes", "да", "1", "+"]).sum())
slides["accuracy"] = section("accuracy", head("Насколько точно LLM выписывает правила", f"Извлечение по Д-002 против эталона, собранного отдельно по тем же документам: {int(rep.loc['ALL', 'reference'])} правил, по одному на вид правила и столбец")
    + '<div style="display:flex;gap:56px;align-items:start">'
    + f'<div style="display:flex;flex-direction:column;gap:12px">{"".join(svg)}<p style="font-size:24px;color:{MUTED}"><span style="color:{BLUE}">■</span> полнота: доля найденных правил эталона  <span style="color:{ORANGE}">■</span> точность</p></div>'
    + '<div style="flex:1;display:flex;flex-direction:column;gap:28px">'
    + big(f"{100 * tot['precision']:.1f}%", "точность: доля извлечённых правил, которые есть в эталоне")
    + big(f"{100 * tot['recall']:.1f}%", "полнота: доля правил эталона, которые нашло извлечение", ORANGE)
    + f'<p style="font-size:26px;line-height:1.4;color:{MUTED}">Переходы и коды — почти без ошибок; слабое место — связи между ответами. {n_dis} расхождений сверены с анкетой; подпись команды: {n_ok} из {n_dis}.</p>'
    + '</div></div>' + foot("Эталон — второй запуск модели, не видевший извлечения; общие слепые зоны возможны, поэтому нужна проверка командой."),
    f"Чтобы понять, можно ли доверять модели, мы её оценили. Второй запуск, который не видел нашего извлечения, собрал эталон по тем же документам Д-002: {int(tot['reference'])} элементарных правил. Наше извлечение нашло {100 * tot['recall']:.1f} процента из них, и {100 * tot['precision']:.1f} процента написанного есть в эталоне. Переходы, множественный выбор и списки кодов почти без ошибок. Слабое место — связи между ответами, полнота {100 * rep.loc['consistency', 'recall']:.0f} процентов, поэтому здесь нужен человек. Пропущенные правила мы добавили в файл с пометкой «добавлено после ревью», но оценка на слайде — для первого извлечения.")

# 6 детский модуль
fl = pd.read_csv(OUT / "D002_region_flags.csv")
pre = fl[(fl.rule_id == "D002-preschool-implies-children") & (fl.year == 2024) & fl.flag].set_index("region")
bars = [(R(r), pre.loc[r, "rate_region"]) for r in pre.sort_values("rate_region", ascending=False).index] + [("Остальные 17", float(NUM["pre_rest_2024"].rstrip("%")))]
H = 72 * len(bars) + 50
svg = [f'<svg aria-label="Доля домохозяйств с ребёнком дошкольного возраста, не посещающим детский сад, у которых записано «нет детей», 2024: Улытау, г. Алматы и Жетысу против остальных 17 регионов." width="820" height="{H}" viewBox="0 0 820 {H}" xmlns="http://www.w3.org/2000/svg">']
X0, W = 250, 480
for i, (r, v) in enumerate(bars):
    y = 20 + 72 * i
    c = ORANGE if i < len(bars) - 1 else BLUE
    svg.append(f'<text x="{X0 - 16}" y="{y + 34}" font-size="26" fill="{INK}" text-anchor="end" font-family="IBM Plex Sans, Arial">{esc(r)}</text>')
    svg.append(f'<rect x="{X0}" y="{y + 8}" width="{W * v / 100:.0f}" height="36" rx="4" fill="{c}"/>')
    svg.append(f'<text x="{X0 + W * v / 100 + 12:.0f}" y="{y + 36}" font-size="26" font-weight="700" fill="{INK}" font-family="IBM Plex Sans, Arial">{v:.0f}%</text>')
svg.append("</svg>")
slides["child"] = section("child", head("Правила находят сбой детского модуля внутри одной формы", "Д-002, 2024: домохозяйства, где есть дошкольник, не посещающий сад (часть 3, вопрос 17), но записано «нет детей до 18 лет» (GR40)")
    + '<div style="display:flex;gap:64px;align-items:start">' + "".join(svg)
    + '<div style="flex:1;display:flex;flex-direction:column;gap:28px">'
    + block("Подтверждено списком членов Д-008", f"Отмечено «есть дети» против домохозяйств с ребёнком по списку: Улытау {NUM['gr40_Ulytau_2024']} против {NUM['roster_Ulytau_2024']}, г. Алматы {NUM['gr40_Almaty city_2024']} против {NUM['roster_Almaty city_2024']} (2024). Новое: Актобе {NUM['gr40_Aktobe_2023']} против {NUM['roster_Aktobe_2023']} в 2023, в 2024 снова {NUM['gr40_Aktobe_2024']}.")
    + block("Почему", "GR40 нет в бумажной анкете: в структуре файла сказано, что вопрос добавлен. Каждый регион заполняет его по-своему.")
    + block("Что исправить", "Выводить GR40 из списка членов и добавить при вводе правило «вопрос 17 = да ⇒ дети = да».")
    + '</div></div>' + foot(),
    f"На втором этапе мы нашли этот случай, сравнивая две формы. Теперь одно правило, которое модель прочитала в анкете, находит его внутри самой Д-002. Если в домохозяйстве есть дошкольник, не посещающий сад, значит, в нём есть дети до 18 лет. В Улытау {NUM['pre_Ulytau_2024']} и в г. Алматы {NUM['pre_Almaty city_2024']} таких домохозяйств записаны как «без детей»; в остальных регионах вместе — {NUM['pre_rest_2024']}. Сверка со списком членов это подтверждает и добавляет Актобе в 2023 году, который в 2024 восстановился, так что сбой бывает не только в 2024.")

# 7 доверие
u = fl[(fl.rule_id == "D002-preschool-implies-children") & (fl.year == 2024) & (fl.region == "Ulytau")].iloc[0]
tk = fl[(fl.rule_id == "D002-P4-skip") & (fl.year == 2024) & (fl.region == "Turkistan") & (fl.column == "GR44_1")].iloc[0]
u_pre = 100 * u.applicable / u.records
slides["trust"] = section("trust", head("Каким сигналам можно верить на синтетических данных", "Синтетика сохраняет доли ответов в каждом регионе, но не каждую связь между двумя столбцами")
    + '<div style="display:flex;gap:40px">'
    + '<div style="flex:1;display:flex;flex-direction:column;gap:20px;background:#EAF2FC;padding:40px;border-radius:16px">'
    + f'<h3 style="font-size:34px;font-weight:700;color:{INK}">Вытекает из долей ответов: надёжно</h3>'
    + f'<p style="font-size:28px;line-height:1.4;color:{MUTED}">Улытау, 2024: {u_pre:.1f}% домохозяйств сообщают о дошкольнике, но лишь {NUM["gr40_Ulytau_2024"]} отмечены как имеющие детей. При любых связях не меньше {u.floor:.0f}% первой группы нарушают правило. Доли переживают синтез — значит, и сигнал тоже.</p></div>'
    + '<div style="flex:1;display:flex;flex-direction:column;gap:20px;background:#FDEFE8;padding:40px;border-radius:16px">'
    + f'<h3 style="font-size:34px;font-weight:700;color:{INK}">Может быть разрывом связей: проверить на реальных данных</h3>'
    + f'<p style="font-size:28px;line-height:1.4;color:{MUTED}">Туркестан, 2024: {tk.rate_region:.1f}% домохозяйств «без детей» заполнили часть 4. Если бы столбцы были независимы, ждали бы {tk.independent:.0f}%. Генератор, разрывающий связи, даёт именно это, поэтому сигнал ждёт реальных данных.</p></div>'
    + '</div>'
    + f'<p style="font-size:28px;line-height:1.4;color:{MUTED}">У каждого сигнала одна из двух меток. Её вычисляют по двум числам: какую долю нарушений задают сами доли ответов и какой она была бы при независимых столбцах.</p>' + foot(),
    "Так мы не даём синтетическим данным нас обмануть. Для каждого сигнала считаем два числа. Первое — минимальная доля нарушений, которую задают доли двух столбцов; доли переживают синтез, и если этот минимум высок, сигнал настоящий. Второе — доля нарушений при независимых столбцах, то есть то, что даёт генератор, разрывающий связи; если наблюдаемая доля там, решить могут только реальные данные. Туркестан выглядел сильным случаем до этой проверки; теперь он в списке на проверку, а не в находках.")

# 8 доказательство
sens = pd.read_csv(OUT / "proof_sensitivity.csv")
spec_t = pd.read_csv(OUT / "proof_specificity.csv")
shift = pd.read_csv(OUT / "proof_specificity_shift.csv")
kinds = list(dict.fromkeys(sens["kind"]))
names = {"skip: Q14 asked after 'no internet'": "Вопрос 14 после «нет интернета»",
         "skip: Part 4 filled for 'no children'": "Часть 4 у «нет детей»",
         "required: reason blank after 'no home internet'": "Причина не указана",
         "domain: out-of-range time code": "Недопустимый код времени",
         "filter: 'no children' with a pre-school child": "«Нет детей» при дошкольнике"}
tab = sens.pivot_table(index="kind", columns="rate", values="detected", aggfunc="mean").mul(100)
bg = sens.groupby("kind")["background_rate"].first()
clean = pd.read_csv(OUT / "proof_sensitivity_clean.csv")
tabc = clean.pivot_table(index="kind", columns="rate", values="detected", aggfunc="mean").mul(100)
rates = list(tab.columns)


def cell(k, r):
    a, b = tab.loc[k, r], tabc.loc[k, r]
    return (f'<td style="text-align:right;white-space:nowrap"><span style="color:{FAINT}">{a:.0f}%</span>'
            f' <span style="color:{FAINT}">→</span> <span style="color:{BLUE if b >= 75 else INK};font-weight:{700 if b >= 75 else 400}">{b:.0f}%</span></td>')


rows_html = "".join(f'<tr><td>{esc(names.get(k, k))}</td><td style="text-align:right">{bg[k]:.1f}%</td>'
                    + "".join(cell(k, r) for r in rates) + "</tr>" for k in kinds)
nruns = len(sens) + len(clean)
fp_other = int(sens.new_flags_other_regions.sum()) + int(clean.new_flags_other_regions.sum())
okc = clean[(clean.eligible >= 30) & (clean.planted >= 10)]
ok_by = okc.groupby("rate").detected.mean().mul(100)
first_full = min([r for r in rates if ok_by.get(r, 0) >= 99.9], default=rates[-1])
n_spec = int((spec_t.new_flags_in_region > 0).sum())
slides["proof"] = section("proof", head("Внесённые ошибки находятся, реальные различия — нет", f"Ошибки внесены в записи одного региона (Д-002, 2024) с заданной частотой, {nruns} запусков. В клетке: найдено на синтетике как есть → после исправления фоновых ошибок")
    + f'<table style="width:1690px;font-size:24px;color:{INK}"><tr><th style="text-align:left;width:30%">Внесённая ошибка</th><th style="text-align:right">Фон</th>'
    + "".join(f'<th style="text-align:right">внесено {int(100 * r)}%</th>' for r in rates) + "</tr>" + rows_html + "</table>"
    + '<div style="display:flex;gap:40px">'
    + big(f"{ok_by.get(first_full, 0):.0f}%", f"найдено начиная с {int(100 * first_full)}% (исправленные данные) в регионах с 30+ записями, к которым относится правило, и 10+ ошибками; при {int(100 * rates[0])}% — {ok_by.get(rates[0], 0):.0f}%")
    + big(f"{fp_other}", f"новый сигнал в других регионах за {nruns} запусков" if fp_other == 1 else f"новых сигналов в других регионах за {nruns} запусков")
    + big(f"{n_spec} из {len(spec_t)}", f"регионов, получивших домохозяйства другого региона, дали новый сигнал (сдвинулось до {int(shift['vars_js_gt_0.05'].max())} из {int(shift['n_vars'].iloc[0])} переменных)")
    + '</div>' + foot("Фон: доля нарушений правила в исходной синтетике. Для сигнала нужны 30+ записей и 10+ лишних ошибок: ниже этого регион не отмечается ни при какой частоте."),
    f"Мы проверили инструмент так, как его будут использовать. Внесли пять видов ошибок в записи одного региона с известной частотой. В синтетике как есть у двух правил уже 7–15 процентов фоновых нарушений: синтез разрывает часть связей между столбцами, и небольшая внесённая ошибка в этом тонет. В реальных данных фон должен быть близок к нулю, поэтому мы повторили тест, сначала исправив фон. Там, где у региона не меньше 30 записей, к которым относится правило, и не меньше 10 ошибок, ошибка находится в каждом запуске начиная с {int(100 * first_full)} процентов и в {ok_by.get(rates[0], 0):.0f} процентах запусков при {int(100 * rates[0])} процентах. Ниже этих порогов регион не отмечается намеренно, чтобы горстка записей не поднимала тревогу. Поэтому строка вопроса 14 проседает на высоких частотах: эти запуски пришлись на регионы, где без интернета всего 8–11 домохозяйств. "
    f"Внесение ошибок в один регион дало {fp_other} сигнал в других регионах за {nruns} запусков. И обратный тест: мы отдали региону домохозяйства другого региона. Ответы сильно изменились, до {int(shift['vars_js_gt_0.05'].max())} из {int(shift['n_vars'].iloc[0])} переменных, но переходы остались верными, и новый сигнал появился в {n_spec} из {len(spec_t)} случаев. Реальное региональное различие — не ошибка, и инструмент не называет его ошибкой.")

# 8b слепой тест на известных Бюро случаях
c2 = pd.read_csv(OUT / "compare_year_c2st.csv")
lfs = c2[c2.form == "T001/baza"].sort_values("auc", ascending=False).reset_index(drop=True)
alm = lfs[lfs.region == "Almaty oblast"].iloc[0]
alm_rank, nxt = int(lfs.index[lfs.region == "Almaty oblast"][0]) + 1, lfs[lfs.region != "Almaty oblast"].iloc[0]
sw = pd.read_csv(OUT / "compare_region_sweep.csv")
d4 = sw[(sw.form == "D004") & (sw.variable != "K")].sort_values("js", ascending=False).reset_index(drop=True)
akt = d4[(d4.region == "Aktobe") & (d4.table == "kv12[NOMVOPR=1211]") & (d4.variable == "KOD")]
akt_ranks = [int(i) + 1 for i in akt.index]
a23, a24 = akt[akt.year == 2023].iloc[0], akt[akt.year == 2024].iloc[0]
DEMO = Path(OUT).parent / "demo"
summ = json.load(open(DEMO / "summary.json", encoding="utf-8"))
b4 = summ["d004_blind"]


def verdict(found, text):
    col, word = (BLUE, "Найдено") if found else (ORANGE, "Пропущено")
    return f'<p style="font-size:28px;font-weight:700;color:{col}">{word}</p><p style="font-size:26px;line-height:1.4;color:{MUTED}">{text}</p>'


cards = [
    ("Алматинская обл.: работники без договора (Т-001)", True,
     f"Модель «2023 против 2024» ставит регион на {alm_rank}-е место из 20 (AUC {alm.auc:.2f}; следующий — {R(nxt.region)}, {nxt.auc:.2f}). Она указывает на {esc(alm.top_features.split(',')[0].split(' ')[0])} — то же изменение переходов, что найдено вручную."),
    ("Актобе: займы на продукты питания (Д-004)", True,
     f"Обзор регионов ставит ответы Актобе о цели займа на {akt_ranks[0]}-е и {akt_ranks[1]}-е места из {len(d4)} сигналов Д-004: «покупка продуктов питания» — {a23.share_region:.0f}% против {a23.share_rest_same:.1f}% в остальных (2023), {a24.share_region:.0f}% против {a24.share_rest_same:.1f}% (2024)."),
    ("Норма сбережений 66% (Д-004)", False,
     f"Новое извлечение по форме Д-004 нашло {b4['doc_issues']} проблем в документации, но не заметило, что в журнале нет раздела о продуктах питания. Пробел между двумя инструментами не виден внутри одной формы — это следующая проверка."),
]
slides["blind"] = section("blind", head("Вслепую инструмент находит два из трёх случаев, известных Бюро",
    "Мы ничего не сообщали о них инструменту: те же обзор и модели, что работают по каждому региону и форме")
    + '<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:32px">'
    + "".join(f'<div style="display:flex;flex-direction:column;gap:16px;background:{PANEL};padding:36px;border-radius:16px">'
              f'<h3 style="font-size:30px;font-weight:700;line-height:1.2;color:{INK}">{esc(t)}</h3>{verdict(fd, tx)}</div>' for t, fd, tx in cards)
    + '</div>' + foot("Места: тип населённого пункта (город/село), переменная дизайна выборки, не учитывается. Извлечение: новый запуск модели только с промптом и формой."),
    "Бюро уже знает три аномалии в этих данных, поэтому мы устроили инструменту экзамен, к которому он не готовился. "
    "Записи обследования рабочей силы Алматинской области выходят на первое место из двадцати регионов, когда модель сравнивает 2023 и 2024 годы. Цели займов в Актобе — самые необычные ответы во всём журнале бюджета домохозяйств. "
    "Третий случай инструмент пропустил: норма сбережений 66 процентов возникает потому, что в журнале нет раздела о продуктах, а новое извлечение не заметило того, чего в форме нет. Отсюда следующая проверка: сравнивать, что покрывает каждый инструмент. Мы лучше покажем этот промах, чем скроем его.")

# 8c новый год за две минуты (живая демонстрация)
d22 = json.load(open(DEMO / "d002_2022_v2.json", encoding="utf-8"))["rules"]
f22 = pd.read_csv(DEMO / "d002_2022_region_flags.csv")
f22 = f22[f22.flag]
nr22 = pd.read_csv(DEMO / "d002_2022_not_run.csv") if (DEMO / "d002_2022_not_run.csv").exists() else pd.DataFrame()
s22 = summ["d002_2022"]
TYPE_WORD = {"domain": "допустимые коды", "required": "обязательные ответы", "doc_issue": "проблемы документации", "skip": "переходы",
             "consistency": "связи ответов", "multi_select": "множественный выбор", "cross_form": "связи форм"}
types = pd.Series([r["type"] for r in d22]).value_counts()
top = f22.sort_values("rate_region", ascending=False).iloc[0]
steps = [("1", "Форма 2022", "год, которого инструмент не видел: только бланк и структура файла"),
         ("2", f"{len(d22)} правила" if len(d22) % 10 in (2, 3, 4) and len(d22) % 100 not in (12, 13, 14) else f"{len(d22)} правил",
          f"новый запуск модели, {s22['extraction_seconds'] // 60} мин {s22['extraction_seconds'] % 60} с; " + ", ".join(f"{TYPE_WORD.get(k, k)} — {v}" for k, v in types.head(3).items())),
         ("3", f"{s22['engine_seconds']:.1f} с", f"каждое правило по каждому региону; {len(nr22)} правило — человеку, проблем документации — {int(types.get('doc_issue', 0))}"),
         ("4", f"{len(f22)} сигнала" if len(f22) in (2, 3, 4) else f"{len(f22)} сигналов",
          (f"например, {esc(R(top.region))}: {top.rate_region:.0f}% ответов «пользуюсь мобильным интернетом» — из домохозяйств без интернета ({top.rate_rest:.0f}% в остальных)"
           if top.rule_id == "D002-P3Q16opt4-implies-Q13" else f"например, {esc(R(top.region))}: {top.rate_region:.0f}% против {top.rate_rest:.0f}% в остальных"))]
slides["newyear"] = section("newyear", head("Форма нового года за две минуты", "Вживую: Д-002 за 2022 год, так, как Бюро запустит форму следующего года")
    + '<div style="display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:28px">'
    + "".join(f'<div style="display:flex;flex-direction:column;gap:14px;background:{PANEL};padding:32px;border-radius:16px">'
              f'<p style="font-size:26px;font-weight:700;color:{FAINT}">{n}</p><p style="font-size:44px;font-weight:700;line-height:1.1;color:{BLUE}">{esc(big_)}</p>'
              f'<p style="font-size:26px;line-height:1.35;color:{MUTED}">{txt}</p></div>' for n, big_, txt in steps)
    + '</div>'
    + f'<p style="font-size:28px;line-height:1.4;color:{MUTED}">Ключ API не нужен: промпт можно вставить в чат Claude и считать ответ. За пределы Бюро уходят только пустой бланк и названия столбцов.</p>'
    + foot("Синтетические записи Д-002 за 2022 год. Промпт v2 (prompts/extract_rules_v2.md); файлы — в папке demo/."),
    f"Теперь вживую. Мы даём инструменту форму, которую он не видел, — Д-002 за 2022 год, как Бюро даст ему форму следующего года. Модель читает её и пишет {len(d22)} правила меньше чем за две минуты. Движок запускает их по всем регионам примерно за три секунды. Одно правило, которое нельзя выразить кодом, остаётся человеку, и отдельно перечислены места, где документация противоречит сама себе. "
    f"Затем сигналы: например, {R(top.region)}, где {top.rate_region:.0f} процентов нарушают правило из анкеты против {top.rate_rest:.0f} процентов в остальных регионах. Если связь подведёт, этот же запуск сохранён в папке demo.")

# 9 карта сопоставимости
iss = pd.read_csv(OUT / "scorecard_issues.csv")
iss["form4"] = iss["form"].str.slice(0, 4)
cols = [("D002", 2023), ("D002", 2024), ("D004", 2023), ("D004", 2024), ("D006", 2023), ("D006", 2024), ("D008", 2023), ("D008", 2024), ("T001", 2023), ("T001", 2024)]
regions = sorted(REG, key=lambda r: REG[r].replace("г. ", ""))
cw, rh, X0, Y0 = 112, 31, 240, 60
Wd, Hd = X0 + cw * len(cols) + 10, Y0 + rh * len(regions) + 10
svg = [f'<svg aria-label="Карта: для каждого из 20 регионов и каждой формы и года — число проблем, которые держатся на синтетике, и число проблем для проверки на реальных данных." width="{Wd}" height="{Hd}" viewBox="0 0 {Wd} {Hd}" xmlns="http://www.w3.org/2000/svg">']
for j, (f, y) in enumerate(cols):
    x = X0 + cw * j + cw / 2
    fl_ = ("Д-" if f[0] == "D" else "Т-") + f[1:]
    svg.append(f'<text x="{x}" y="24" font-size="22" font-weight="700" fill="{INK}" text-anchor="middle" font-family="IBM Plex Sans, Arial">{fl_}</text><text x="{x}" y="50" font-size="20" fill="{MUTED}" text-anchor="middle" font-family="IBM Plex Sans, Arial">{y}</text>')
for i, r in enumerate(regions):
    y = Y0 + rh * i
    svg.append(f'<text x="{X0 - 12}" y="{y + 22}" font-size="22" fill="{INK}" text-anchor="end" font-family="IBM Plex Sans, Arial">{esc(R(r))}</text>')
    for j, (f, yr) in enumerate(cols):
        sub = iss[(iss.region == r) & (iss.form4 == f) & (iss.year == yr)]
        h, c = int((sub.status == "holds in synthetic data").sum()), int((sub.status == "check on real records").sum())
        x = X0 + cw * j
        fill = BLUE if h >= 2 else ("#9CC3EF" if h == 1 else PANEL)
        svg.append(f'<rect x="{x + 4}" y="{y + 3}" width="{cw - 8}" height="{rh - 6}" rx="5" fill="{fill}"/>')
        if c:
            svg.append(f'<circle cx="{x + cw - 18}" cy="{y + rh / 2}" r="8" fill="{ORANGE}"/>')
        if h:
            svg.append(f'<text x="{x + 16}" y="{y + 22}" font-size="20" font-weight="700" fill="{"#FFFFFF" if h >= 2 else INK}" font-family="IBM Plex Sans, Arial">{h}</text>')
svg.append("</svg>")
n_hold, n_check = int((iss.status == "holds in synthetic data").sum()), int((iss.status == "check on real records").sum())
slides["scorecard"] = section("scorecard", head("Карта сопоставимости регионов", f"По регионам, формам и годам: {n_hold} проблем держатся на синтетике (синий), {n_check} — проверить на реальных данных (точка)")
    + f'<div style="display:flex;gap:44px;align-items:start">{"".join(svg)}'
    + '<div style="flex:1;display:flex;flex-direction:column;gap:24px">'
    + block("Как читать", "Синяя клетка: регион записывает иначе, чем остальная страна, и синтетика это показывает.", 24)
    + block("Зачем", "Каждый квартал на реальных данных: супервайзер начинает с синих клеток.", 24)
    + '</div></div>' + foot("Источники: проверки правил, сравнение форм, обзор «регион против остальных» (ML)."),
    "Это продукт, который остаётся у Бюро: строка на регион, столбец на форму и год. Синий цвет — проблема, которая держится на синтетике, с числом; оранжевая точка — проблема для проверки на реальных данных. Выделяются Павлодар, Улытау, г. Алматы, Актобе, Жетысу и Мангистау. В интерактивной карте за каждой клеткой — правило, доли и цитата из источника.")

# 10 кодирование: аренда и формулировки
slides["coding"] = section("coding", head("Один ответ — разный смысл", "Два случая, где сама анкета разводит регионы")
    + '<div style="display:flex;gap:56px">'
    + '<div style="flex:1;display:flex;flex-direction:column;gap:24px">'
    + block("Казахский и русский тексты расходятся", f"Д-002, часть 2, вопрос 5, код 2: «кем дегенде айына бір рет» (не реже раза в месяц) против «реже чем раз в месяц». Его доля по регионам — от {NUM['gr25_min']} до {NUM['gr25_max']} в 2024, а в 2023 он замещает код 3 (r = {NUM['gr25_r_2023']}).")
    + block("Проверка", "Ответы по языку интервью на реальных данных.")
    + '</div><div style="flex:1;display:flex;flex-direction:column;gap:24px">'
    + block("Ещё семь расхождений в той же форме", "Найдены чтением двух языков рядом и сверены с бланком: аренда, вариант 4 — «маңызды емес» (не важно) против «не актуально»; частота интернета, коды 1 и 2; чистый воздух — «қоқыс» (мусор) против «выбросов»; мебель — «и» против «или»; «вне дома» нет в казахском тексте; причина долга.")
    + block("Что исправить", "Поправить казахский текст; одно предложение в инструкции о том, как кодировать собственников.")
    + '</div></div>' + foot(),
    f"Анкета напечатана на казахском и русском. Модель сравнила каждый вариант ответа. В части 2, вопросе 5 код 2 по-казахски означает «не реже раза в месяц», а по-русски — «реже чем раз в месяц», так что в казахской версии он пересекается с кодом 3. По регионам доля кода 2 — от {NUM['gr25_min']} до {NUM['gr25_max']}, а в 2023 году чем больше кода 2, тем меньше кода 3 (r = {NUM['gr25_r_2023']}). Именно это и предсказывает формулировка. Реальные данные позволят проверить это по языку интервью.")

# 11 следы ввода данных
slides["entry"] = section("entry", head("Следы ввода данных", "Закономерности, которые не создаёт ни один респондент: они указывают на программу, значения по умолчанию или интервьюеров")
    + '<div style="display:grid;grid-template-columns:1fr 1fr;gap:32px">'
    + big(NUM["pav_2024"], f"значений числа комнат в Павлодаре записаны как «03», а не «3» (в остальной стране {NUM['pav_rest_2024']}). Д-006, оба года")
    + big(NUM["ast_jan_2024"], f"месяцев рождения в Астане — январь (в остальных {NUM['ast_jan_rest']}). Т-001, 2024; в 2023 — {NUM['ast_jan_2023']}", ORANGE)
    + big(NUM["kos_cars_2024"], f"автомобиля на домохозяйство с автомобилем в Костанае (медиана в остальных {NUM['cars_median_2024']}). Д-006, 2024; в 2023 — {NUM['kos_cars_2023']}")
    + big(NUM["mang_zt_2024"], f"анкет Д-002 в Мангистау заполнялись «1–2 часа» (в остальных {NUM['mang_zt_rest']}). То же значение по умолчанию: Астана 2023 в Д-002 и Д-006", ORANGE)
    + '</div>' + foot("Найдено обзором «регион против остальных» (ML) и проверками правил; все четыре держатся на синтетике, потому что это доли ответов."),
    "Некоторые различия не может создать ни один респондент. Павлодар пишет числа с ведущим нулём — признак другой программы ввода. Половина месяцев рождения в Астане — январь, значение по умолчанию для неизвестного месяца, которое сдвигает точный возраст. В Костанае в среднем девять автомобилей на домохозяйство с автомобилем, значит, в этом столбце там записано что-то другое. А поле времени заполнения принимает одно значение по умолчанию в Мангистау в 2024 и в Астане в 2023, в двух разных формах. Каждое такое место дёшево исправить, если знать, куда смотреть.")

# 12 нарушено везде
nat = [("Д-002, часть 2, вопрос 2: причины низкого дохода", f"пусто у {NUM['p2q2_2024']} тех, кому вопрос задаётся"),
       ("Д-002: респонденты младше 18 лет", f"{NUM['minor89_2024']} оценивают финансы семьи вместо кода 89"),
       ("Д-002: «нет домашнего интернета, пользуюсь мобильным»", f"{NUM['mobile_2024']} — из домохозяйств без пользования интернетом"),
       ("Д-008: коды изменения состава", f"{NUM['d008_code_2024']} вне списка инструкции (код 29)"),
       ("Д-008: время заполнения", f"пусто у всех домохозяйств ({NUM['d008_zt_2024']})"),
       ("Д-004: цель и источник займа", f"{NUM['d004_purpose_2024']} строк у домохозяйств без займа в этом квартале"),
       ("Д-006: возраст членов на земельном участке", f"{NUM['d006_age0_2024']} содержат 0 вместо пустого значения")]
slides["national"] = section("national", head("Правила, нарушенные везде", "Не региональное различие, а вопросы к сбору и обработке форм, 2024")
    + f'<table style="width:1690px;font-size:28px;color:{INK}"><tr><th style="text-align:left;width:50%">Правило из документации</th><th style="text-align:left">Что показывают записи</th></tr>'
    + "".join(f"<tr><td>{esc(a)}</td><td>{esc(b)}</td></tr>" for a, b in nat) + "</table>"
    + f'<p style="font-size:28px;line-height:1.4;color:{MUTED}">Каждая строка — правило, которое модель прочитала в документации, а код проверил на каждой записи.</p>' + foot(),
    "Некоторые правила нарушены во всех регионах. Это не региональные различия, а вопросы к сбору и обработке. Причины низкого дохода почти никогда не заполнены, хотя отвечать должны три четверти респондентов. Поле времени в Д-008 пустое у всех. Код 29 для выбывшего члена используется, но его нет в списке инструкции. Каждая строка — одно правило, которое модель прочитала, а код проверил.")

# 13 что получает Бюро
slides["bureau"] = section("bureau", head("Что получает Бюро", "Работает на реальных данных на компьютере Бюро; ничего не уходит наружу")
    + '<div style="display:grid;grid-template-columns:1fr 1fr;gap:40px">'
    + block("Правила с источниками и SQL", f"{len(ex)} правил, у каждого — цитата из анкеты, а у {int(ex.sql_first_column.notna().sum())} — запрос, который считает нарушения по регионам.")
    + block("Карта, каждый квартал", "Регион × форма × год, с меткой доверия и правилом за каждой проблемой.")
    + block("Карточки случаев", "Тип ошибки, затронутый показатель, вероятная причина, исправление и проверка на реальных данных. Слова пишет LLM, каждое число — код.")
    + block("Новые формы и годы", "Тот же промпт превращает новую анкету в правила; оценщик сверяет их с эталоном до использования.")
    + '</div>' + foot("Код: Python (pandas, scikit-learn, LightGBM). Один ноутбук запускает всё в Colab или локально."),
    "Бюро получает четыре вещи. Файл правил с источником каждого правила и SQL-запросом по регионам. Карту сопоставимости, которую перезапускают каждый квартал на реальных данных. Карточки случаев, объясняющие каждую проблему, с числами из кода. И сам шаг извлечения: новая форма или новый год превращаются в правила за минуты и проверяются до использования. Всё работает на компьютере Бюро; ни одна запись его не покидает.")

# 14 проверки на реальных данных
slides["checks"] = section("checks", head("Проверки, которые решат только реальные данные", "Для Бюро: каждый ответ превращает гипотезу в проверенное правило или в правило, которое инструмент не должен поднимать")
    + f'<table style="width:1690px;font-size:26px;color:{INK}"><tr><th style="text-align:left;width:38%">Случай</th><th style="text-align:left">Проверка на реальных данных</th></tr>'
    + "".join(f"<tr><td>{esc(a)}</td><td>{esc(b)}</td></tr>" for a, b in [
        ("Фильтр детского модуля (GR40)", "Доля домохозяйств с детьми, ответивших на часть 4, по регионам, 2023–2024"),
        ("Аренда закодирована двумя способами", "Инструкция для собственников; «не актуально» среди собственников по регионам"),
        ("Казахская и русская формулировки", "Часть 2, вопрос 5 и кодирование аренды по языку интервью"),
        ("Время по умолчанию", "Длительность интервью по интервьюерам: Мангистау 2024, Астана 2023"),
        ("Следы ввода", "Формат выгрузки Павлодара; столбец автомобилей в Костанае; месяцы рождения в Астане"),
        ("Сигналы с меткой «проверить»", "Перезапустить инструмент: остаётся ли сигнал, когда связи между столбцами настоящие?")]) + "</table>"
    + foot(),
    "Это проверки, которые мы не можем сделать сами. Ответ «да» или «нет» по каждой покажет, какие случаи — реальные различия в записи. Подтверждённые станут проверенными правилами; отклонённые научат инструмент, что не нужно отмечать. Спасибо.")

order = ["cover", "problem", "tool", "rules", "accuracy", "child", "trust", "proof", "blind", "newyear", "scorecard", "coding", "entry", "national", "bureau", "checks"]
for sid in order:
    (BUILD / "project" / "slides" / f"{sid}.html").write_text(slides[sid], encoding="utf-8")
deck = {"v": 4, "createdOnFiles": {"v": 1, "at": "2026-10-10T10:30:00Z"}, "lists": "css",
        "title": "StatQUO, финал: одинаково ли регионы записывают одни и те же ответы?", "cover": "cover", "order": order,
        "sections": {"s1": {"description": "Проблема и инструмент", "start": "cover"},
                     "s2": {"description": "Можно ли доверять LLM и проверкам", "start": "accuracy"},
                     "s3": {"description": "Что находит инструмент", "start": "scorecard"},
                     "s4": {"description": "Что получает Бюро", "start": "bureau"}},
        "faces": {"ibm-plex-sans": {"family": "IBM Plex Sans", "href": "https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;700&display=swap"}},
        "designSystems": []}
(BUILD / "project" / "deck.json").write_text(json.dumps(deck, ensure_ascii=False), encoding="utf-8")
print("slides:", len(order))
