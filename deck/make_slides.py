"""Write the final deck's slide files from the engine's outputs, so every number on a slide comes from code.

    python deck/make_slides.py out/ deck/build/
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

OUT, BUILD = Path(sys.argv[1]), Path(sys.argv[2])
(BUILD / "project" / "slides").mkdir(parents=True, exist_ok=True)

INK, MUTED, FAINT, LINE, BLUE, ORANGE, BG, PANEL = "#1F2933", "#52514E", "#75746F", "#E8E7E3", "#2A78D6", "#EB6834", "#FFFFFF", "#F6F5F2"
FONT = "'Lato', Calibri, Arial, sans-serif"
SEC = f"background:{BG};color:{INK};font-family:{FONT};padding:60px 115px 160px;display:flex;flex-direction:column;gap:44px"
FOOT = "All figures: synthetic microdata 2021–2024 (STAT.DATATHON 2026), team calculations."
CASES = {c["id"]: c for c in json.load(open(OUT / "cases.json", encoding="utf-8"))}
NUM = json.load(open(OUT / "case_numbers.json", encoding="utf-8"))


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def head(title, sub):
    return (f'<div style="display:flex;flex-direction:column;gap:18px">'
            f'<h2 style="font-size:56px;font-weight:700;line-height:1.1;color:{INK}">{esc(title)}</h2>'
            f'<p style="font-size:26px;line-height:1.3;color:{FAINT}">{esc(sub)}</p></div>')


def foot(text=FOOT, page=None):
    p = f" · {page}" if page else ""
    return f'<p style="position:absolute;left:115px;bottom:64px;width:1690px;font-size:24px;color:{FAINT}">{esc(text)}{p}</p>'


def block(title, text, size=28):
    return (f'<div style="display:flex;flex-direction:column;gap:10px"><h3 style="font-size:30px;font-weight:700;line-height:1.2;color:{INK}">{esc(title)}</h3>'
            f'<p style="font-size:{size}px;line-height:1.4;color:{MUTED}">{text}</p></div>')


def big(number, label, color=BLUE):
    return (f'<div style="flex:1;display:flex;flex-direction:column;gap:12px;background:{PANEL};padding:36px;border-radius:16px">'
            f'<p style="font-size:72px;font-weight:700;line-height:1;color:{color}">{esc(number)}</p>'
            f'<p style="font-size:26px;line-height:1.35;color:{MUTED}">{label}</p></div>')


def section(sid, body, notes, transition=True):
    t = ' data-transition="fade"' if transition else ""
    return f'<section id="{sid}"{t} style="{SEC}">\n{body}\n<aside>{esc(notes)}</aside>\n</section>\n'


slides = {}

# 1 cover
slides["cover"] = (f'<section id="cover" style="background:{BG};color:{INK};font-family:{FONT};padding:115px;display:flex;flex-direction:column;justify-content:center;gap:64px">'
    f'<div style="display:flex;flex-direction:column;gap:28px">'
    f'<h1 style="font-size:80px;font-weight:700;line-height:1.1;color:{INK}">Do regions record the same answers the same way?</h1>'
    f'<p style="font-size:48px;line-height:1.2;color:{MUTED}">A tool that turns the questionnaires into tests and runs them region by region</p></div>'
    f'<div style="display:flex;flex-direction:column;gap:14px">'
    f'<p style="font-size:30px;font-weight:700;color:{INK}">Team StatQUO</p>'
    f'<p style="font-size:28px;color:{MUTED}">Aidai Totoeva · Baiirbek Kholikov · Almanbet Kaldybaev · Nargiza Zhumalieva</p>'
    f'<p style="font-size:26px;color:{FAINT}">STAT.DATATHON 2026 · Final · Track 2: AI for Official Statistics · 20 October 2026</p></div>'
    f'<aside>We built a tool for the Bureau. It reads the questionnaires, turns them into tests, runs the tests on every region, and says where a region records the same situation differently. Everything you will see was run on the synthetic release; the tool runs unchanged on the real records.</aside></section>\n')

# 2 problem
slides["problem"] = section("problem",
    head("The same situation, coded two ways", "D-002 Part 3 Q1.1 'could not pay rent' and D-006 ownership, 20 regions, 2024")
    + '<div style="display:flex;gap:40px">'
    + big(f"{NUM['owners_min']}–{NUM['owners_max']}", "of households live in a dwelling they own, in every region (D-006)")
    + big(f"{NUM['rent_nr_min']}–{NUM['rent_nr_max']}", f"are coded 4 'not relevant' for rent: {NUM['rent_nr_min_region']} lowest, {NUM['rent_nr_max_region']} highest. The other owners are coded 3 'no'", ORANGE)
    + '</div>'
    + f'<p style="font-size:34px;line-height:1.35;color:{INK}">An arrears rate "among households for whom rent is relevant" then measures each region\'s coding habit. Errors like this pass every range check. They show only when you know what the questionnaire means.</p>'
    + foot(),
    "Owners are 89 to 98 percent everywhere, yet the share coded not relevant runs from 9 to 98 percent. The rest of the owners are coded no. Both codes are valid, so a range check passes. The difference shows only when you know what the question means, and that is what our tool reads from the questionnaire.")

# 3 the tool (pipeline)
boxes = [("Questionnaires", "forms, instructions, file structures, KZ + RU"), ("Rules (LLM)", "routing, codes, meanings; each quotes its source"),
         ("Checks by region", "every rule × region × year; flags with a trust label"), ("Case files (LLM)", "text by the model, every number from code"),
         ("Scorecard + SQL", "the Bureau reruns it each quarter")]
w, gap, x0 = 300, 47, 0
svg = ['<svg aria-label="Pipeline: questionnaires, rules written by the LLM, checks by region, case files, scorecard and SQL. The ML comparisons feed the checks." width="1690" height="420" viewBox="0 0 1690 420" xmlns="http://www.w3.org/2000/svg">']
for i, (t, s) in enumerate(boxes):
    x = x0 + i * (w + gap)
    fill = BLUE if i in (1, 3) else PANEL
    tc = "#FFFFFF" if i in (1, 3) else INK
    sc = "#EAF2FC" if i in (1, 3) else MUTED
    svg.append(f'<rect x="{x}" y="40" width="{w}" height="190" rx="16" fill="{fill}"/>')
    svg.append(f'<text x="{x + 24}" y="100" font-size="30" font-weight="700" fill="{tc}" font-family="Lato, Arial">{esc(t)}</text>')
    words, line, lines = s.split(), "", []
    for wd in words:
        if len(line + " " + wd) > 22:
            lines.append(line); line = wd
        else:
            line = (line + " " + wd).strip()
    lines.append(line)
    for j, ln in enumerate(lines):
        svg.append(f'<text x="{x + 24}" y="{145 + 32 * j}" font-size="24" fill="{sc}" font-family="Lato, Arial">{esc(ln)}</text>')
    if i < len(boxes) - 1:
        ax = x + w + 6
        svg.append(f'<path d="M{ax} 135 L{ax + gap - 14} 135" stroke="{FAINT}" stroke-width="3"/><path d="M{ax + gap - 14} 127 L{ax + gap - 4} 135 L{ax + gap - 14} 143 Z" fill="{FAINT}"/>')
mx = 2 * (w + gap)
svg.append(f'<rect x="{mx}" y="300" width="{w}" height="110" rx="16" fill="{PANEL}" stroke="{ORANGE}" stroke-width="3"/>')
svg.append(f'<text x="{mx + 24}" y="345" font-size="30" font-weight="700" fill="{INK}" font-family="Lato, Arial">Comparisons (ML)</text>')
svg.append(f'<text x="{mx + 24}" y="385" font-size="24" fill="{MUTED}" font-family="Lato, Arial">region, year, form</text>')
svg.append(f'<path d="M{mx + w / 2} 296 L{mx + w / 2} 242" stroke="{ORANGE}" stroke-width="3"/><path d="M{mx + w / 2 - 8} 250 L{mx + w / 2} 236 L{mx + w / 2 + 8} 250 Z" fill="{ORANGE}"/>')
svg.append("</svg>")
slides["tool"] = section("tool", head("What we built", "One pipeline for four household forms (D-002, D-004, D-006, D-008), plus the labour force survey (T-001) in the ML comparisons")
    + "".join(svg)
    + f'<p style="font-size:30px;line-height:1.4;color:{MUTED}">The LLM reads; code counts. No number in a case file is written by the model.</p>' + foot(),
    "Five steps. The LLM reads the questionnaires and writes rules. The engine runs every rule on every region and year. Three ML comparisons look for differences no rule describes: region against the rest of the country, one year against the next, and one form against another. The LLM then writes the case files, but every number in them is filled in by code. The Bureau gets the rules as SQL and a scorecard it can rerun each quarter.")

# 4 rules
counts = {}
for p in sorted(Path(OUT).parent.glob("rules/*.json")):
    sp = json.load(open(p, encoding="utf-8"))
    counts[sp["form"]] = len(sp["rules"])
ex = pd.read_csv(OUT / "rules_export.csv")
row = ex[ex.rule_id == "D002-P3Q18-skip"].iloc[0]
code_style = f"font-size:24px;line-height:1.45;color:{INK};background:{PANEL};padding:28px;border-radius:12px;font-family:'Courier New', monospace"
slides["rules"] = section("rules", head("One line of the form becomes one test", f"{sum(counts.values())} rules from four forms: " + ", ".join(f"{k[0]}-{k[1:]} {v}" for k, v in counts.items()) + ". Each quotes the passage it comes from.")
    + '<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:32px">'
    + f'<div style="display:flex;flex-direction:column;gap:14px"><h3 style="font-size:30px;font-weight:700;color:{INK}">The questionnaire</h3><p style="{code_style}">17. Имеется ли в Вашем домашнем хозяйстве ребенок дошкольного возраста, не посещающий дошкольное учреждение?<br>да → 18<br>нет → 19</p></div>'
    + f'<div style="display:flex;flex-direction:column;gap:14px"><h3 style="font-size:30px;font-weight:700;color:{INK}">The rule (LLM)</h3><p style="{code_style}">type: skip<br>when: GR317 = 2<br>targets: GR318_1 … GR318_9<br>confidence: high</p></div>'
    + f'<div style="display:flex;flex-direction:column;gap:14px"><h3 style="font-size:30px;font-weight:700;color:{INK}">The test (code)</h3><p style="{code_style}">SELECT TE, COUNT(*)<br>FROM d002_ocenka<br>WHERE GR317 = 2<br>AND GR318_1 IS NOT NULL<br>GROUP BY TE;</p></div>'
    + '</div>'
    + f'<p style="font-size:28px;line-height:1.4;color:{MUTED}">Seven kinds of rule: allowed codes, routing, required answers, tick boxes, links between answers, links to another form, and contradictions in the documentation itself.</p>'
    + foot(),
    "Here is one rule. Question 17 says yes goes to 18 and no goes to 19. The model writes that as a rule: if GR317 is 2, the reasons in GR318 must be blank, with the quote attached. The code turns it into a test, and the Bureau gets the same test as SQL. The documentation-issue type is where the model reads Kazakh and Russian side by side.")

# 5 accuracy
acc_rows = []
import importlib.util
spec_ = importlib.util.spec_from_file_location("score", Path(OUT).parent / "gold" / "score.py")
score = importlib.util.module_from_spec(spec_); spec_.loader.exec_module(score)
rules_d002 = json.load(open(Path(OUT).parent / "rules" / "d002_2023-2024.json", encoding="utf-8"))
ext = score.atoms_extracted({"rules": [r for r in rules_d002["rules"] if not r.get("added_after_review")]})
ref = score.atoms_reference(json.load(open(Path(OUT).parent / "gold" / "d002_gold_reviewed.json", encoding="utf-8")))
rep = score.report(*score.match(ext, ref)).set_index("type")
order = ["skip", "multi_select", "required", "domain", "required_any", "cross_form", "doc_issue", "consistency"]
label = {"skip": "Routing (skip)", "multi_select": "Tick boxes", "required": "Required answers", "domain": "Allowed codes",
         "required_any": "At least one ticked", "cross_form": "Links to other forms", "doc_issue": "Documentation issues", "consistency": "Links between answers"}
H = 56 * len(order) + 60
svg = [f'<svg aria-label="Recall and precision of the extracted rules by rule type, against the independent reference set." width="1100" height="{H}" viewBox="0 0 1100 {H}" xmlns="http://www.w3.org/2000/svg">']
X0, W = 330, 640
for k in (0, 50, 100):
    x = X0 + W * k / 100
    svg.append(f'<line x1="{x}" y1="20" x2="{x}" y2="{H - 30}" stroke="{LINE}" stroke-width="2"/><text x="{x}" y="{H - 4}" font-size="24" fill="{MUTED}" text-anchor="middle" font-family="Lato, Arial">{k}%</text>')
for i, t in enumerate(order):
    y = 30 + 56 * i
    rc, pr, n = rep.loc[t, "recall"], rep.loc[t, "precision"], int(rep.loc[t, "reference"])
    svg.append(f'<text x="{X0 - 16}" y="{y + 26}" font-size="24" fill="{INK}" text-anchor="end" font-family="Lato, Arial">{label[t]} ({n})</text>')
    svg.append(f'<rect x="{X0}" y="{y + 6}" width="{W * rc:.0f}" height="22" rx="4" fill="{BLUE}"/>')
    svg.append(f'<rect x="{X0}" y="{y + 32}" width="{W * pr:.0f}" height="10" rx="3" fill="{ORANGE}"/>')
    svg.append(f'<text x="{X0 + W * rc + 10:.0f}" y="{y + 26}" font-size="24" fill="{INK}" font-family="Lato, Arial">{100 * rc:.0f}%</text>')
svg.append("</svg>")
tot = rep.loc["ALL"]
_ru = Path(OUT).parent / "gold" / "d002_review_ru.csv"
rv = pd.read_csv(_ru, encoding="utf-8-sig") if _ru.exists() else pd.read_csv(Path(OUT).parent / "gold" / "d002_review.csv")
_tick = rv["Ваша отметка (✓ согласна / ✗ нет)"] if "Ваша отметка (✓ согласна / ✗ нет)" in rv else rv.iloc[:, -1]
n_dis, n_ok = len(rv), int(_tick.astype(str).str.strip().isin(["✓", "v", "V", "yes", "да", "1", "+"]).sum())
slides["accuracy"] = section("accuracy", head("How often the LLM gets the rules right", f"D-002 extraction against a reference set built separately from the same documents: {int(rep.loc['ALL', 'reference'])} rules, one per rule type and column")
    + '<div style="display:flex;gap:56px;align-items:start">'
    + f'<div style="display:flex;flex-direction:column;gap:12px">{"".join(svg)}<p style="font-size:24px;color:{MUTED}"><span style="color:{BLUE}">■</span> recall: share of reference rules found  <span style="color:{ORANGE}">■</span> precision</p></div>'
    + '<div style="flex:1;display:flex;flex-direction:column;gap:28px">'
    + big(f"{100 * tot['precision']:.1f}%", "precision: extracted rules that are in the reference")
    + big(f"{100 * tot['recall']:.1f}%", "recall: reference rules the extraction found", ORANGE)
    + f'<p style="font-size:26px;line-height:1.4;color:{MUTED}">Routing and code lists are near perfect. Links between answers are the gap: the model wrote the obvious ones and missed the rest. The {n_dis} disagreements were each checked against the form; team sign-off: {n_ok} of {n_dis}.</p>'
    + '</div></div>' + foot("Reference: a second model run that never saw the extraction. Same model family, so shared blind spots are possible; the team review is the independent check. Scores are for the first extraction."),
    f"To know whether the model can be trusted we scored it. A second run, which never saw our extraction, built a reference set from the same D-002 documents: {int(tot['reference'])} atomic rules. Our extraction found {100 * tot['recall']:.1f} percent of them, and {100 * tot['precision']:.1f} percent of what it wrote is in the reference. Routing, tick boxes and code lists are near perfect. The weak spot is links between answers, {100 * rep.loc['consistency', 'recall']:.0f} percent recall, so those are where a person must review. We added the ones it missed to the rule file, marked as added after review, but the score you see is for the first extraction.")

# 6 child module
fl = pd.read_csv(OUT / "D002_region_flags.csv")
pre = fl[(fl.rule_id == "D002-preschool-implies-children") & (fl.year == 2024) & fl.flag].set_index("region")
bars = [(r, pre.loc[r, "rate_region"]) for r in pre.sort_values("rate_region", ascending=False).index] + [("Other 17 regions", float(NUM["pre_rest_2024"].rstrip("%")))]
H = 72 * len(bars) + 50
svg = [f'<svg aria-label="Share of households with a pre-school child not in kindergarten that are coded no children, 2024: Ulytau, Almaty city and Zhetysu against the other 17 regions together." width="820" height="{H}" viewBox="0 0 820 {H}" xmlns="http://www.w3.org/2000/svg">']
X0, W = 250, 480
for i, (r, v) in enumerate(bars):
    y = 20 + 72 * i
    c = ORANGE if i < len(bars) - 1 else BLUE
    svg.append(f'<text x="{X0 - 16}" y="{y + 34}" font-size="26" fill="{INK}" text-anchor="end" font-family="Lato, Arial">{esc(r)}</text>')
    svg.append(f'<rect x="{X0}" y="{y + 8}" width="{W * v / 100:.0f}" height="36" rx="4" fill="{c}"/>')
    svg.append(f'<text x="{X0 + W * v / 100 + 12:.0f}" y="{y + 36}" font-size="26" font-weight="700" fill="{INK}" font-family="Lato, Arial">{v:.0f}%</text>')
svg.append("</svg>")
c1 = CASES["C1"]
slides["child"] = section("child", head("The rules find the child-module break inside one form", "D-002 2024: households that report a pre-school child not in kindergarten (Part 3 Q17) but are coded 'no children under 18' (GR40)")
    + '<div style="display:flex;gap:64px;align-items:start">' + "".join(svg)
    + '<div style="flex:1;display:flex;flex-direction:column;gap:28px">'
    + block("Confirmed against the D-008 roster", f"Marked 'has children' vs households with a child in the roster: Ulytau {NUM['gr40_Ulytau_2024']} vs {NUM['roster_Ulytau_2024']}, Almaty city {NUM['gr40_Almaty city_2024']} vs {NUM['roster_Almaty city_2024']} (2024). New: Aktobe {NUM['gr40_Aktobe_2023']} vs {NUM['roster_Aktobe_2023']} in 2023, back to {NUM['gr40_Aktobe_2024']} in 2024.")
    + block("Why", "GR40 is not printed on the paper form; the file structure says it was added. Each region fills it its own way.")
    + block("Fix", "Derive GR40 from the roster, and enter the rule 'Q17 = yes ⇒ children = yes'.")
    + '</div></div>' + foot(),
    f"In stage 2 we found this case by comparing two forms. Now one rule the model read from the questionnaire finds it inside D-002 alone. A household that has a pre-school child not in kindergarten must have children under 18. In Ulytau {NUM['pre_Ulytau_2024']} and in Almaty city {NUM['pre_Almaty city_2024']} of those households are coded no children; in the other regions together {NUM['pre_rest_2024']}. The roster check confirms it and adds Aktobe in 2023, which recovers in 2024, so the break is not only a 2024 event.")

# 7 trust
u = fl[(fl.rule_id == "D002-preschool-implies-children") & (fl.year == 2024) & (fl.region == "Ulytau")].iloc[0]
tk = fl[(fl.rule_id == "D002-P4-skip") & (fl.year == 2024) & (fl.region == "Turkistan") & (fl.column == "GR44_1")].iloc[0]
u_pre = 100 * u.applicable / u.records
slides["trust"] = section("trust", head("Which flags hold on synthetic data", "The synthetic release keeps each region's answer shares, but not every link between two columns")
    + '<div style="display:flex;gap:40px">'
    + '<div style="flex:1;display:flex;flex-direction:column;gap:20px;background:#EAF2FC;padding:40px;border-radius:16px">'
    + f'<h3 style="font-size:34px;font-weight:700;color:{INK}">Forced by the answer shares: holds</h3>'
    + f'<p style="font-size:28px;line-height:1.4;color:{MUTED}">Ulytau 2024: {u_pre:.1f}% of households report a pre-school child, but only {NUM["gr40_Ulytau_2024"]} are coded as having children. Whatever the links, at least {u.floor:.0f}% of the first group must break the rule. Shares survive synthesis, so the flag does too.</p></div>'
    + '<div style="flex:1;display:flex;flex-direction:column;gap:20px;background:#FDEFE8;padding:40px;border-radius:16px">'
    + f'<h3 style="font-size:34px;font-weight:700;color:{INK}">Could be broken links: check on real records</h3>'
    + f'<p style="font-size:28px;line-height:1.4;color:{MUTED}">Turkistan 2024: {tk.rate_region:.1f}% of \'no children\' households answered Part 4. If the two columns were unrelated, we would expect {tk.independent:.0f}%. A generator that breaks links produces exactly this, so the flag waits for the real records.</p></div>'
    + '</div>'
    + f'<p style="font-size:28px;line-height:1.4;color:{MUTED}">Every flag carries one of the two labels, computed from two numbers: the violation rate the shares force, and the rate if the columns were unrelated.</p>' + foot(),
    "This is how we keep the synthetic data from fooling us. For every flag we compute two numbers. The first is the smallest violation rate the two columns' own shares force; shares survive synthesis, so if that floor is high the flag is real. The second is the rate if the two columns were unrelated, which is what a generator that breaks links produces; if the observed rate sits there, only the real records can settle it. Turkistan looked like a strong case until this check; we now list it as one to check, not as a finding.")

# 8 proof
sens = pd.read_csv(OUT / "proof_sensitivity.csv")
spec_t = pd.read_csv(OUT / "proof_specificity.csv")
shift = pd.read_csv(OUT / "proof_specificity_shift.csv")
kinds = list(dict.fromkeys(sens["kind"]))
names = {"skip: Q14 asked after 'no internet'": "Q14 asked after 'no internet'",
         "skip: Part 4 filled for 'no children'": "Part 4 filled for 'no children'",
         "required: reason blank after 'no home internet'": "Reason left blank",
         "domain: out-of-range time code": "Invalid time code",
         "filter: 'no children' with a pre-school child": "'No children' with a pre-school child"}
tab = sens.pivot_table(index="kind", columns="rate", values="detected", aggfunc="mean").mul(100)
bg = sens.groupby("kind")["background_rate"].first()
cpath = OUT / "proof_sensitivity_clean.csv"
clean = pd.read_csv(cpath) if cpath.exists() else None
tabc = clean.pivot_table(index="kind", columns="rate", values="detected", aggfunc="mean").mul(100) if clean is not None else None
rates = list(tab.columns)


def cell(k, r):
    a = tab.loc[k, r]
    if tabc is None:
        return f'<td style="text-align:right">{a:.0f}%</td>'
    b = tabc.loc[k, r]
    return (f'<td style="text-align:right;white-space:nowrap"><span style="color:{FAINT}">{a:.0f}%</span>'
            f' <span style="color:{FAINT}">→</span> <span style="color:{BLUE if b >= 75 else INK};font-weight:{700 if b >= 75 else 400}">{b:.0f}%</span></td>')


rows_html = "".join(f'<tr><td>{esc(names.get(k, k))}</td><td style="text-align:right">{bg[k]:.1f}%</td>'
                    + "".join(cell(k, r) for r in rates) + "</tr>" for k in kinds)
nruns = len(sens) + (len(clean) if clean is not None else 0)
fp_other = int(sens.new_flags_other_regions.sum()) + (int(clean.new_flags_other_regions.sum()) if clean is not None else 0)
c_all = {r: 100 * clean[clean.rate == r].detected.mean() for r in rates} if clean is not None else {}
if clean is not None:
    okc = clean[(clean.eligible >= 30) & (clean.planted >= 10)]
    ok_by = okc.groupby("rate").detected.mean().mul(100)
    first_full = min([r for r in rates if ok_by.get(r, 0) >= 99.9], default=None)
sub_ = (f"Errors planted into one region's 2024 D-002 records at known rates, {nruns} runs. "
        "Each cell: detected on the synthetic data as shipped → after its background errors are repaired")
slides["proof"] = section("proof", head("Planted errors are found; real differences are not flagged", sub_)
    + f'<table style="width:1690px;font-size:24px;color:{INK}"><tr><th style="text-align:left;width:30%">Planted error</th><th style="text-align:right">Background</th>'
    + "".join(f'<th style="text-align:right">{int(100 * r)}% planted</th>' for r in rates) + "</tr>" + rows_html + "</table>"
    + '<div style="display:flex;gap:40px">'
    + (big(f"{ok_by.get(first_full, 0):.0f}%", f"found from {int(100 * first_full)}% planted (repaired data), in regions with 30+ applicable records and 10+ errors; {ok_by.get(rates[0], 0):.0f}% at {int(100 * rates[0])}%") if clean is not None and first_full else "")
    + big(f"{fp_other}", f"new flag{'' if fp_other == 1 else 's'} in other regions, {nruns} planted runs")
    + big(f"{int((spec_t.new_flags_in_region > 0).sum())} of {len(spec_t)}", f"regions given another region's households raised a new flag (up to {int(shift['vars_js_gt_0.05'].max())} of {int(shift['n_vars'].iloc[0])} variables shifted)")
    + '</div>' + foot("Background: the rule's violation rate in the data as shipped. A flag needs 30+ applicable records and 10+ excess errors: below that a region cannot be flagged at any rate."),
    f"We tested the tool the way it will be used. We planted five kinds of error into one region's records at known rates. On the synthetic data as shipped, two rules already carry 7 to 15 percent background errors, because synthesis breaks some links between columns, so a small planted error drowns. Real records should be close to clean, so we repeated the test after repairing the background: "
    + (f"wherever a region has at least 30 records the rule applies to and at least 10 errors, the error is found in every run from {int(100 * first_full)} percent planted, and in {ok_by.get(rates[0], 0):.0f} percent of runs at {int(100 * rates[0])} percent. Below those two minimums a region is never flagged, by design, so that a handful of records cannot raise an alarm. That is why the Q14 row drops at high rates: those runs fell on regions with only 8 to 11 households without internet. " if clean is not None and first_full else "")
    + f"Planting in one region raised {fp_other} flag{'' if fp_other == 1 else 's'} in other regions across {nruns} runs. Then the opposite test: we gave a region another region's households. Its answers changed a lot, in up to {int(shift['vars_js_gt_0.05'].max())} of {int(shift['n_vars'].iloc[0])} variables, but routing stayed correct, and the tool raised a new flag in {int((spec_t.new_flags_in_region > 0).sum())} of {len(spec_t)} trials. A real regional difference is not an error, and the tool does not call it one.")

# 8b blind test on the Bureau's known cases
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


def ordinal(n):
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


def verdict(found, text):
    col, word = (BLUE, "Found") if found else (ORANGE, "Missed")
    return f'<p style="font-size:28px;font-weight:700;color:{col}">{word}</p><p style="font-size:26px;line-height:1.4;color:{MUTED}">{text}</p>'


cards = [
    ("Almaty oblast: workers without a contract (T-001)", True,
     f"The 2023-vs-2024 model ranks the region {ordinal(alm_rank)} of 20 (AUC {alm.auc:.2f}; next {nxt.region} {nxt.auc:.2f}). It points to {esc(alm.top_features.split(',')[0].split(' ')[0])}, the routing change found by hand."),
    ("Aktobe: loans taken for food (D-004)", True,
     f"The region sweep ranks Aktobe's loan-purpose answers {ordinal(akt_ranks[0])} and {ordinal(akt_ranks[1])} of {len(d4)} D-004 signals: 'buying food' is {a23.share_region:.0f}% against {a23.share_rest_same:.1f}% elsewhere (2023), {a24.share_region:.0f}% against {a24.share_rest_same:.1f}% (2024)."),
    ("The 66% savings rate (D-004)", False,
     f"A fresh extraction of the D-004 form listed {b4['doc_issues']} documentation problems, but not that the journal has no food section. A gap between two instruments does not show inside one form: the next check to add."),
]
slides["blind"] = section("blind", head("Run blind, the tool finds two of the three cases the Bureau knows",
    "We told the tool nothing about them: the same sweep and models that run on every region and form")
    + '<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:32px">'
    + "".join(f'<div style="display:flex;flex-direction:column;gap:16px;background:{PANEL};padding:36px;border-radius:16px">'
              f'<h3 style="font-size:30px;font-weight:700;line-height:1.2;color:{INK}">{esc(t)}</h3>{verdict(fd, tx)}</div>' for t, fd, tx in cards)
    + '</div>' + foot("Ranks: settlement type (city/rural), a design variable, left out. Extraction: a fresh model run given only the prompt and the form."),
    "The Bureau already knows three anomalies in these data, so we used them as an exam the tool did not see in advance. "
    f"Almaty oblast's labour force records come out first of twenty regions when the model compares 2023 with 2024. Aktobe's loan purposes are the most unusual answers in the whole household budget journal. "
    "The third one it missed: the 66 percent savings rate comes from the journal having no food section, and a fresh extraction of the form did not notice what is absent. That tells us the next check to build: compare what each instrument covers. We would rather show you the miss than hide it.")

# 8c a new year in minutes (the live demo)
d22 = json.load(open(DEMO / "d002_2022_v2.json", encoding="utf-8"))["rules"]
f22 = pd.read_csv(DEMO / "d002_2022_region_flags.csv")
f22 = f22[f22.flag]
nr22 = pd.read_csv(DEMO / "d002_2022_not_run.csv") if (DEMO / "d002_2022_not_run.csv").exists() else pd.DataFrame()
s22 = summ["d002_2022"]
TYPE_WORD = {"domain": "code lists", "required": "required answers", "doc_issue": "documentation problems", "skip": "routing",
             "consistency": "links between answers", "multi_select": "tick boxes", "cross_form": "links to other forms"}
types = pd.Series([r["type"] for r in d22]).value_counts()
top = f22.sort_values("rate_region", ascending=False).iloc[0]
steps = [("1", "The 2022 form", "a year the tool had not seen: blank form and file structure only"),
         ("2", f"{len(d22)} rules", f"a fresh model run, {s22['extraction_seconds'] // 60} min {s22['extraction_seconds'] % 60} s; " + ", ".join(f"{v} {TYPE_WORD.get(k, k)}" for k, v in types.head(3).items())),
         ("3", f"{s22['engine_seconds']:.1f} s", f"every rule on every region; {len(nr22)} rule left to a person, {int(types.get('doc_issue', 0))} documentation problems"),
         ("4", f"{len(f22)} flags", (f"e.g. {esc(top.region)}: {top.rate_region:.0f}% of 'I use mobile internet' answers come from households with no internet use ({top.rate_rest:.0f}% elsewhere)"
                                    if top.rule_id == "D002-P3Q16opt4-implies-Q13" else f"e.g. {esc(top.region)}: {top.rate_region:.0f}% against {top.rate_rest:.0f}% elsewhere"))]
slides["newyear"] = section("newyear", head("A new year's form in two minutes", "Live: D-002 2022, run the way the Bureau would run next year's form")
    + '<div style="display:grid;grid-template-columns:1fr 1fr 1fr 1fr;gap:28px">'
    + "".join(f'<div style="display:flex;flex-direction:column;gap:14px;background:{PANEL};padding:32px;border-radius:16px">'
              f'<p style="font-size:26px;font-weight:700;color:{FAINT}">{n}</p><p style="font-size:44px;font-weight:700;line-height:1.1;color:{BLUE}">{esc(big_)}</p>'
              f'<p style="font-size:26px;line-height:1.35;color:{MUTED}">{txt}</p></div>' for n, big_, txt in steps)
    + '</div>'
    + f'<p style="font-size:28px;line-height:1.4;color:{MUTED}">No API key needed: the prompt can be pasted into a Claude chat and the answer read back. Nothing but the blank form and the column names leaves the Bureau.</p>'
    + foot("D-002 2022 synthetic records. Prompt v2 (prompts/extract_rules_v2.md); files in demo/."),
    f"Now the live part. We give the tool a form it has never seen, D-002 for 2022, as the Bureau would give it next year's form. The model reads it and writes {len(d22)} rules in under two minutes. The engine runs them on every region in about three seconds. One rule it cannot express as code is left for a person, and it lists the places where the documentation contradicts itself. "
    f"Then the flags: for example {top.region}, where {top.rate_region:.0f} percent break a rule the form states, against {top.rate_rest:.0f} percent elsewhere. If the connection fails, the same run is saved in the demo folder.")

# 9 scorecard grid
iss = pd.read_csv(OUT / "scorecard_issues.csv")
iss["form4"] = iss["form"].str.slice(0, 4)
cols = [("D002", 2023), ("D002", 2024), ("D004", 2023), ("D004", 2024), ("D006", 2023), ("D006", 2024), ("D008", 2023), ("D008", 2024), ("T001", 2023), ("T001", 2024)]
regions = sorted(iss["region"].unique().tolist() + [r for r in ["Abai", "Akmola", "Aktobe", "Almaty city", "Almaty oblast", "Astana", "Atyrau", "East Kazakhstan", "Karaganda", "Kostanay", "Kyzylorda", "Mangystau", "North Kazakhstan", "Pavlodar", "Shymkent", "Turkistan", "Ulytau", "West Kazakhstan", "Zhambyl", "Zhetysu"] if r not in iss["region"].unique()])
cw, rh, X0, Y0 = 118, 31, 250, 60
Wd, Hd = X0 + cw * len(cols) + 10, Y0 + rh * len(regions) + 10
svg = [f'<svg aria-label="Scorecard: for each of 20 regions and each form and year, the number of issues that hold on synthetic data and the number to check on the real records." width="{Wd}" height="{Hd}" viewBox="0 0 {Wd} {Hd}" xmlns="http://www.w3.org/2000/svg">']
for j, (f, y) in enumerate(cols):
    x = X0 + cw * j + cw / 2
    svg.append(f'<text x="{x}" y="24" font-size="22" font-weight="700" fill="{INK}" text-anchor="middle" font-family="Lato, Arial">{f[0]}-{f[1:]}</text><text x="{x}" y="50" font-size="20" fill="{MUTED}" text-anchor="middle" font-family="Lato, Arial">{y}</text>')
for i, r in enumerate(regions):
    y = Y0 + rh * i
    svg.append(f'<text x="{X0 - 12}" y="{y + 22}" font-size="22" fill="{INK}" text-anchor="end" font-family="Lato, Arial">{esc(r)}</text>')
    for j, (f, yr) in enumerate(cols):
        sub = iss[(iss.region == r) & (iss.form4 == f) & (iss.year == yr)]
        h, c = int((sub.status == "holds in synthetic data").sum()), int((sub.status == "check on real records").sum())
        x = X0 + cw * j
        fill = BLUE if h >= 2 else ("#9CC3EF" if h == 1 else PANEL)
        svg.append(f'<rect x="{x + 4}" y="{y + 3}" width="{cw - 8}" height="{rh - 6}" rx="5" fill="{fill}"/>')
        if c:
            svg.append(f'<circle cx="{x + cw - 18}" cy="{y + rh / 2}" r="8" fill="{ORANGE}"/>')
        if h:
            svg.append(f'<text x="{x + 16}" y="{y + 22}" font-size="20" font-weight="700" fill="{"#FFFFFF" if h >= 2 else INK}" font-family="Lato, Arial">{h}</text>')
svg.append("</svg>")
n_hold, n_check = int((iss.status == "holds in synthetic data").sum()), int((iss.status == "check on real records").sum())
slides["scorecard"] = section("scorecard", head("The regional comparability scorecard", f"Issues by region, form and year: {n_hold} hold on synthetic data (blue, count), {n_check} to check on real records (orange dot)")
    + f'<div style="display:flex;gap:48px;align-items:start">{"".join(svg)}'
    + '<div style="flex:1;display:flex;flex-direction:column;gap:24px">'
    + block("How to read it", "A blue cell is a form and year where the region records something differently from the rest of the country, and the synthetic data can show it.", 26)
    + block("What it is for", "The Bureau reruns it each quarter on the real records. A region that turns blue is where a supervisor looks first.", 26)
    + '</div></div>' + foot("Sources: rule checks, form-vs-form shares and the region-vs-rest sweep (ML). The interactive version lists every issue."),
    "This is the product the Bureau keeps: one row per region, one column per form and year. Blue means an issue that holds on synthetic data, with the count; an orange dot means one to check on the real records. Pavlodar, Ulytau, Almaty city, Aktobe, Zhetysu and Mangystau stand out. The interactive scorecard lists every issue behind each cell, with the rule, the rates and the source quote.")

# 10 coding: rent + wording
c3 = CASES["C3"]
slides["coding"] = section("coding", head("Same answer, different meaning", "Two cases where the questionnaire itself sets regions apart")
    + '<div style="display:flex;gap:56px">'
    + '<div style="flex:1;display:flex;flex-direction:column;gap:24px">'
    + block("Kazakh and Russian disagree", f"D-002 Part 2 Q5, code 2: 'кем дегенде айына бір рет' (at least once a month) vs 'реже чем раз в месяц' (less than once a month). Its share runs from {NUM['gr25_min']} to {NUM['gr25_max']} across regions in 2024, and in 2023 it trades off against code 3 (r = {NUM['gr25_r_2023']}).")
    + block("Check", "Answers by interview language on the real records.")
    + '</div><div style="flex:1;display:flex;flex-direction:column;gap:24px">'
    + block("Seven more in the same form", "Found by reading the two languages side by side, each checked against the form: rent arrears option 4 ('not important' vs 'not relevant'); internet use codes 1 and 2; clean air, 'garbage' vs 'emissions'; furniture 'worn and damaged' vs 'worn or damaged'; 'outside the home' missing in Kazakh; the debt reason.")
    + block("Fix", "Correct the Kazakh text; one sentence in the instruction on how to code owners.")
    + '</div></div>' + foot(),
    f"The questionnaire is printed in Kazakh and Russian. The model compared every answer option. In Part 2 question 5, code 2 means at least once a month in Kazakh and less than once a month in Russian, so in Kazakh it overlaps code 3. Across regions code 2 runs from {NUM['gr25_min']} to {NUM['gr25_max']}, and in 2023 regions with more code 2 have less code 3 (r = {NUM['gr25_r_2023']}). That is what the wording predicts. The real records can test it by interview language.")

# 11 entry signatures
slides["entry"] = section("entry", head("Data-entry fingerprints", "Patterns no respondent produces: they point to software, defaults or interviewers")
    + '<div style="display:grid;grid-template-columns:1fr 1fr;gap:32px">'
    + big(NUM["pav_2024"], f"of Pavlodar's room counts are written '03', not '3' (rest of the country {NUM['pav_rest_2024']}). D-006, both years")
    + big(NUM["ast_jan_2024"], f"of Astana's birth months are January (rest {NUM['ast_jan_rest']}). T-001, 2024; {NUM['ast_jan_2023']} in 2023", ORANGE)
    + big(NUM["kos_cars_2024"], f"cars per car-owning household in Kostanay (median elsewhere {NUM['cars_median_2024']}). D-006, 2024; {NUM['kos_cars_2023']} in 2023")
    + big(NUM["mang_zt_2024"], f"of Mangystau's D-002 forms took '1–2 hours' (rest {NUM['mang_zt_rest']}). The same default: Astana 2023 in D-002 and D-006", ORANGE)
    + '</div>' + foot("Found by the ML region-vs-rest sweep and the rule checks; all four hold on synthetic data, since they are answer shares."),
    "Some differences no respondent could produce. Pavlodar writes counts with a leading zero, a sign of different entry software. Half of Astana's birth months are January, a default for unknown months, which shifts exact ages. Kostanay averages nine cars per car-owning household, so that column holds something else there. And the time-to-complete field takes one default value in Mangystau 2024 and in Astana 2023, in two different forms. Each is cheap to fix once you know where to look.")

# 12 national
c8 = CASES["C8"]
nat = [("D-002 Part 2 Q2: reasons for low income", f"blank for {NUM['p2q2_2024']} of those it applies to"),
       ("D-002: respondents under 18", f"{NUM['minor89_2024']} rate family finances instead of coding 89"),
       ("D-002: 'no home internet, I use mobile'", f"{NUM['mobile_2024']} from households with no internet use"),
       ("D-008: composition-change codes", f"{NUM['d008_code_2024']} outside the instruction's list (code 29)"),
       ("D-008: time to complete", f"blank for every household ({NUM['d008_zt_2024']})"),
       ("D-004: loan purpose and source", f"{NUM['d004_purpose_2024']} of rows with no loan that quarter"),
       ("D-006: land-plot member ages", f"{NUM['d006_age0_2024']} hold 0 instead of blank")]
slides["national"] = section("national", head("Rules broken everywhere", "Not regional: questions for how the forms are collected and processed, 2024")
    + f'<table style="width:1690px;font-size:28px;color:{INK}"><tr><th style="text-align:left;width:50%">Rule from the documentation</th><th style="text-align:left">What the records show</th></tr>'
    + "".join(f"<tr><td>{esc(a)}</td><td>{esc(b)}</td></tr>" for a, b in nat) + "</table>"
    + f'<p style="font-size:28px;line-height:1.4;color:{MUTED}">Each line is a rule the model read from the documentation and the code tested on every record.</p>' + foot(),
    "Some rules break in every region. These are not regional differences but questions about collection and processing. The reasons for low income are almost never filled although three quarters of respondents should answer. The D-008 time field is empty for everyone. Code 29 for a member who moved away is used but missing from the instruction's list. Each line is one rule the model read and the code tested.")

# 13 bureau
slides["bureau"] = section("bureau", head("What the Bureau gets", "Runs on the real records on the Bureau's own computer; nothing leaves it")
    + '<div style="display:grid;grid-template-columns:1fr 1fr;gap:40px">'
    + block("Rules, with sources and SQL", f"{len(ex)} rules, each with its questionnaire quote and, for {int(ex.sql_first_column.notna().sum())} of them, a query that counts violations by region.")
    + block("Scorecard, every quarter", "Region × form × year, with the trust label and the rule behind each issue.")
    + block("Case files", "Error type, indicator affected, likely cause, fix and the check on the real records. The LLM writes the words, code fills every number.")
    + block("New forms and years", "The same prompt turns a new questionnaire into rules; the scorer measures it against a reference before it is used.")
    + '</div>' + foot("Code: Python (pandas, scikit-learn, LightGBM). One notebook runs everything in Colab or locally."),
    "The Bureau gets four things. The rules file, with every rule's source and a SQL query by region. The scorecard, rerun each quarter on the real records. Case files that explain each issue, with numbers from code. And the extraction step itself, so a new form or year becomes rules in minutes, scored before use. It all runs on the Bureau's computer; no record leaves it.")

# 14 checks / next
slides["checks"] = section("checks", head("Checks only the real records can settle", "For the Bureau: each answer turns a hypothesis into a tested rule or a rule the tool must not raise")
    + f'<table style="width:1690px;font-size:26px;color:{INK}"><tr><th style="text-align:left;width:38%">Case</th><th style="text-align:left">Check on the real records</th></tr>'
    + "".join(f"<tr><td>{esc(a)}</td><td>{esc(b)}</td></tr>" for a, b in [
        ("Child module filter (GR40)", "Share of households with children that answered Part 4, by region, 2023–2024"),
        ("Rent coded two ways", "Instruction for owners; 'not relevant' among owners by region"),
        ("Kazakh and Russian wording", "Part 2 Q5 and rent coding by interview language"),
        ("Default times", "Interview duration by interviewer: Mangystau 2024, Astana 2023"),
        ("Entry fingerprints", "Pavlodar's export format; Kostanay's car column; Astana's birth months"),
        ("Flags marked 'check'", "Rerun the tool: does the flag stay when links between columns are real?")]) + "</table>"
    + foot(),
    "These are the checks we cannot run ourselves. A yes or no on each tells us which cases are real recording differences. Confirmed ones become tested rules; rejected ones teach the tool what not to flag. Thank you.")

order = ["cover", "problem", "tool", "rules", "accuracy", "child", "trust", "proof", "blind", "newyear", "scorecard", "coding", "entry", "national", "bureau", "checks"]
for sid in order:
    (BUILD / "project" / "slides" / f"{sid}.html").write_text(slides[sid], encoding="utf-8")
deck = {"v": 4, "createdOnFiles": {"v": 1, "at": "2026-10-10T08:15:00Z"}, "lists": "css",
        "title": "StatQUO final: do regions record the same answers the same way?", "cover": "cover", "order": order,
        "sections": {"s1": {"description": "The problem and the tool", "start": "cover"},
                     "s2": {"description": "Can the LLM and the checks be trusted", "start": "accuracy"},
                     "s3": {"description": "What the tool finds", "start": "scorecard"},
                     "s4": {"description": "What the Bureau gets", "start": "bureau"}},
        "faces": {"lato": {"family": "Lato", "href": "https://fonts.googleapis.com/css2?family=Lato:wght@400;700&display=swap"}},
        "designSystems": []}
(BUILD / "project" / "deck.json").write_text(json.dumps(deck, ensure_ascii=False), encoding="utf-8")
print("slides:", len(order))
