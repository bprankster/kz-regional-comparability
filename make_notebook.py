"""Build StatQUO_final.ipynb from the package files, so the notebook carries exactly the code that produced
the results. Run: python make_notebook.py"""
from pathlib import Path

import nbformat as nbf

ROOT = Path(__file__).parent
nb = nbf.v4.new_notebook()
C = nb.cells
md = lambda s: C.append(nbf.v4.new_markdown_cell(s))
code = lambda s: C.append(nbf.v4.new_code_cell(s))

md("""# StatQUO: do regions record the same answers the same way?

**STAT.DATATHON 2026 · Track 2: AI for Official Statistics · Final · Team StatQUO**

Aidai Totoeva · Baiirbek Kholikov · Almanbet Kaldybaev · Nargiza Zhumalieva

This notebook runs the whole tool on the synthetic microdata 2021–2024 and, unchanged, on the Bureau's real records:

1. **Questionnaire → rules (LLM).** The rule files were written from the blank forms, instructions and file structures; every rule quotes its source.
2. **How accurate is the extraction?** Scored against an independent reference set for D-002, checked by the team.
3. **Decoding undocumented codes.** What a code means when the documentation does not say, validated with labels hidden.
4. **Checks by region.** Every rule on every region and year; flags where a region stands out, and whether the flag can be trusted on synthetic data.
5. **Comparisons without rules.** Region vs rest, 2023 vs 2024, form vs form (ML), and code shifts by region (decoder).
6. **Proof.** Planted errors are found; real regional differences are not flagged.
7. **Scorecard, case files and the rules as SQL** for the Bureau to rerun each quarter.
8. **Blind tests.** The Bureau's known cases found without being told; a new year's form turned into rules by a fresh model run.
9. **Child poverty:** how many households the Part 4 indicator rests on, by region.

**How to run**
- *Colab:* set `STAT_ARCHIVE_ID` to the Drive file id of the organisers' archive (or upload the archive and set `ARCHIVE_PATH`), then Runtime → Run all. The data are not in this repository.
- *Real records:* set `DATA_DIR` below to a folder with the archive's layout (`d002/2024/ocenka.csv`, `d006/2024/rio_2024.csv`, …). Nothing leaves that computer.

All numbers in this notebook come from the synthetic release unless marked otherwise.""")

code("""# Folder with the archive layout. Leave as None in Colab: the next cell downloads the synthetic archive.
DATA_DIR = None
ARCHIVE_PATH = None   # or the .tar.gz itself
RUN_ML = True         # region sweep, year-vs-year models, form-vs-form search (about 10–30 minutes)
RUN_PROOF = False     # planted-error test, both baselines (about 40 minutes); saved results are shown when False""")

code("""import os, sys, re, json, tarfile, unicodedata, warnings
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
from IPython.display import display, Markdown
warnings.filterwarnings("ignore")
pd.set_option("display.max_columns", 40, "display.width", 200, "display.max_colwidth", 120)
IN_COLAB = "google.colab" in sys.modules
if IN_COLAB:
    os.system("pip install -q lightgbm xlrd")

ARCHIVE_ID = os.environ.get("STAT_ARCHIVE_ID", "")   # Drive file id of synthetic_microdata_2021-2024_20260921.tar.gz (from the organisers)
USED = re.compile(r"(d00[2468]/20(23|24)/.*\\.csv|t001/20(23|24)/baza\\.csv|documentation/.*)$")

def unpack(archive, target="/content/stat_data"):
    if Path(target, "d002", "2024", "ocenka.csv").exists():
        return target
    with tarfile.open(archive, "r:gz") as tar:
        for m in tar:
            name = unicodedata.normalize("NFC", m.name)
            hit = USED.search(name)
            if m.isfile() and hit:
                out = os.path.join(target, hit.group(0))
                os.makedirs(os.path.dirname(out), exist_ok=True)
                with tar.extractfile(m) as src, open(out, "wb") as dst:
                    dst.write(src.read())
    return target

def fetch_archive():
    import io
    from google.colab import auth
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaIoBaseDownload
    if not ARCHIVE_ID:
        raise SystemExit("Set STAT_ARCHIVE_ID to the Drive file id of the organisers' archive, or set ARCHIVE_PATH / DATA_DIR.")
    auth.authenticate_user()
    path = "/content/archive.tar.gz"
    if not os.path.exists(path):
        req = build("drive", "v3").files().get_media(fileId=ARCHIVE_ID, supportsAllDrives=True)
        with io.FileIO(path, "wb") as fh:
            dl, done = MediaIoBaseDownload(fh, req, chunksize=64 * 2**20), False
            while not done:
                status, done = dl.next_chunk()
                print(f"\\rDownloading: {status.progress():.0%}", end="")
    return unpack(path)

if DATA_DIR is None:
    if ARCHIVE_PATH:
        DATA_DIR = unpack(ARCHIVE_PATH, str(Path(ARCHIVE_PATH).with_name("stat_data")))
    elif IN_COLAB:
        DATA_DIR = fetch_archive()
    else:
        raise SystemExit("Set DATA_DIR (or ARCHIVE_PATH) in the cell above.")
print("Data:", DATA_DIR)""")

md("""## The package

The next cells write the tool's files (engine, rules, prompt, reference set) into `statquo/` next to this notebook. They are the same files as in the team's folder.""")

files = (["prompts/extract_rules_v1.md", "prompts/extract_rules_v2.md", "extract/llm_extract.py"]
         + [f"engine/{n}.py" for n in ("statquo", "compare", "scorecard", "cases", "export")]
         + ["gold/score.py", "proof/plant.py", "analysis/child_impact.py", "analysis/finance_impact.py", "decoder/decode.py", "decoder/decoder_cases.py",
            "decoder/prompt_decode_v1.md", "schema/profile.py", "decoder/reply_validation.json", "decoder/reply_t001.json", "decoder/validation_grades.json"]
         + sorted(str(p.relative_to(ROOT)) for p in (ROOT / "rules").glob("*.json"))
         + ["gold/d002_gold_draft.json", "gold/d002_gold_reviewed.json", "gold/d002_review.csv",
            "demo/d002_2022_v2.json", "demo/d004_blind.json", "demo/summary.json"])
for f in files:
    text = (ROOT / f).read_text(encoding="utf-8")
    code(f"%%writefile statquo/{f}\n{text}")
C.insert(len(C) - len(files), nbf.v4.new_code_cell(
    "for d in ('prompts','extract','engine','gold','proof','rules','out','demo','analysis','decoder','schema'):\n    os.makedirs(f'statquo/{d}', exist_ok=True)"))

code("""sys.path.insert(0, "statquo/engine")
import statquo as S, compare as CMP, scorecard as SC, cases as CS, export as EX
OUT = Path("statquo/out"); OUT.mkdir(exist_ok=True)
RULES = sorted(Path("statquo/rules").glob("*.json"))
for p in RULES:
    spec = json.load(open(p, encoding="utf-8"))
    print(f"{spec['form']}: {len(spec['rules'])} rules  ({p.name})")""")

md("""## 1. Questionnaire → rules

One rule from the D-002 file, as the LLM wrote it: the routing "Q13 no → Q15", the quote it comes from, and the check it compiles to.""")
code("""spec = json.load(open("statquo/rules/d002_2023-2024.json", encoding="utf-8"))
r = next(r for r in spec["rules"] if r["id"] == "D002-P3Q14-skip")
print(json.dumps(r, ensure_ascii=False, indent=1))
print()
print("SQL:", EX.violation_sql(r, "GR314"))""")

md("""## 2. How accurate is the extraction?

A second, independent model run built a reference set from the same D-002 documents (405 atomic rules after the team review, one per rule type and column) without seeing the extraction. Disagreements were adjudicated against the form text and checked by the team (`gold/d002_review.csv`). The scores below are for the v1 extraction, before anything was taken from the reference.""")
code("""import importlib.util
spec_ = importlib.util.spec_from_file_location("score", "statquo/gold/score.py"); score = importlib.util.module_from_spec(spec_); spec_.loader.exec_module(score)
ext = score.atoms_extracted({"rules": [r for r in spec["rules"] if not r.get("added_after_review")]})
for name in ("d002_gold_draft", "d002_gold_reviewed"):
    ref = score.atoms_reference(json.load(open(f"statquo/gold/{name}.json", encoding="utf-8")))
    es, rs = score.match(ext, ref)
    print(name); display(score.report(es, rs))
display(pd.read_csv("statquo/gold/d002_review.csv"))""")

md("""## 3. Decoding undocumented codes

Some columns have no code list in the documentation (all of T-001's questionnaire is missing from the archive). Before checking regions, the tool works out what each code means from the records: a fingerprint per code, matching against D-008 where the same concept is labelled, and an LLM reading of the fingerprints (`decoder/prompt_decode_v1.md`, saved replies). The method is validated twice: a hidden renumbering between years must be recovered, and the LLM must name documented codes whose labels it was not shown (about 1 minute).""")
code("""os.system(f"cd statquo && python decoder/decode.py '{DATA_DIR}' out/ meanings > out/decoder.log")
vm = pd.read_csv(OUT / "decoder_validation_match.csv").groupby(["form", "column"]).agg(correct=("correct", "sum"), total=("codes", "sum"))
print("Hidden renumbering between years recovered (%):"); display((100 * vm.correct / vm.total).round(1))
g = json.load(open("statquo/decoder/validation_grades.json", encoding="utf-8"))["grades"]
v = json.load(open("statquo/decoder/reply_validation.json", encoding="utf-8"))
rows = [(c["column"], k["code"], k["meaning"], k["confidence"], g[c["column"]][str(k["code"])]) for c in v["columns"] for k in c["codes"]]
blind = pd.DataFrame(rows, columns=["column", "code", "model", "confidence", "grade"])
print("Blind LLM decoding, labels hidden:", int((blind.grade == "correct").sum()), "of", len(blind), "correct"); display(blind)
t = json.load(open("statquo/decoder/reply_t001.json", encoding="utf-8"))
print("T-001 code meanings proposed (hypotheses until checked against the T-001 questionnaire):")
display(pd.DataFrame([(c["column"], k["code"], k["meaning"], k["confidence"]) for c in t["columns"] for k in c["codes"]],
                     columns=["column", "code", "meaning", "confidence"]))""")

md("""## 4. Checks by region

Every rule on every region, 2023 and 2024. A region is flagged when its violation rate is at least 5%, three times the rest of the country, beyond sampling noise (z > 3), and at least 10 records above what the national rate would give.

**Can a flag be trusted on synthetic data?** The synthetic release keeps each column's answer shares by region but does not keep every link between columns. For each flag we compute the violation rate the two columns' own shares *force* (this survives synthesis) and the rate if the columns were unrelated (what a generator that breaks links produces). Flags forced by the shares hold; the others are marked for checking on the real records.""")
code("""for p in RULES:
    spec_f = json.load(open(p, encoding="utf-8"))
    res = S.run_rules(spec_f["rules"], DATA_DIR, spec_f["form"], [2023, 2024])
    res.to_csv(OUT / f"{spec_f['form']}_results.csv", index=False)
    S.flag_regions(res).to_csv(OUT / f"{spec_f['form']}_region_flags.csv", index=False)
    xf = S.run_cross_form(spec_f["rules"], DATA_DIR, [2023, 2024])
    xf.to_csv(OUT / f"{spec_f['form']}_cross_form.csv", index=False)
    S.flag_cross_form(xf).to_csv(OUT / f"{spec_f['form']}_cross_form_flags.csv", index=False)
    print(spec_f["form"], len(res), "region × rule × year results")""")

md("""## 5. Comparisons without rules (ML and code shifts)

Region vs rest, 2023 vs 2024 and form vs form need no rules. The decoder adds a fourth comparison: a region whose code behaves like a different code in the rest of the country (code shift); its flags go into the scorecard. The next cells hold the saved ML results, so the scorecard works with `RUN_ML = False`; with `RUN_ML = True` they are recomputed and overwritten.""")
for f in ("compare_region_sweep.csv", "compare_year_c2st.csv", "compare_invariants.csv"):
    code("%%writefile statquo/out/" + f + "\n" + (ROOT / "out" / f).read_text(encoding="utf-8"))
code("""if RUN_ML:
    os.environ["PARTS"] = "sweep,c2st,inv"
    os.system(f"cd statquo/engine && python compare.py --data '{DATA_DIR}' --out ../out")
for f in ("compare_year_c2st.csv", "compare_invariants.csv"):
    if (OUT / f).exists():
        d = pd.read_csv(OUT / f)
        print(f); display(d.sort_values(d.columns[-1] if "robust_z" in d else "gap").head(12))""")
code("""os.system(f"cd statquo && python decoder/decode.py '{DATA_DIR}' out/ shift >> out/decoder.log && python decoder/decoder_cases.py '{DATA_DIR}' out/ > /dev/null")
sh = pd.read_csv(OUT / "decoder_code_shift.csv"); print("Code shifts tested:", len(sh), " flagged:"); display(sh[sh.flag])""")

md("""## 6. Proof

**Sensitivity:** errors of five kinds are planted into one region's 2024 D-002 records at known rates; detected = that region is flagged on that rule. Regions already near the threshold for a rule are left out for that rule.
The synthetic release breaks some links between columns, so two of the rules already carry 7–15% background errors and a small planted error drowns in them. Real records should be close to clean, so the test is run twice: on the data as shipped (lower bound) and after repairing the rule's background errors (upper bound).
**Specificity:** a region's households are replaced by another region's (answers shift, routing intact); a real regional difference must raise no new flag.""")
for f in ("proof_sensitivity.csv", "proof_sensitivity_clean.csv", "proof_specificity.csv", "proof_specificity_shift.csv"):
    if (ROOT / "out" / f).exists():   # saved results, so the section shows without the 40-minute run
        code("%%writefile statquo/out/" + f + "\n" + (ROOT / "out" / f).read_text(encoding="utf-8"))
code("""if RUN_PROOF:
    os.system(f"cd statquo && python proof/plant.py '{DATA_DIR}' rules/d002_2023-2024.json out/")
    os.system(f"cd statquo && CLEAN=1 python proof/plant.py '{DATA_DIR}' rules/d002_2023-2024.json out/")
for f, label in (("proof_sensitivity.csv", "synthetic data as shipped"), ("proof_sensitivity_clean.csv", "background errors of the rule repaired first")):
    if (OUT / f).exists():
        s = pd.read_csv(OUT / f)
        print("Detected (% of runs),", label)
        display(s.pivot_table(index=["kind", "background_rate"], columns="rate", values="detected", aggfunc="mean").mul(100).round(0))
        print("New flags in other regions:", int(s.new_flags_other_regions.sum()), "in", len(s), "trials")
if (OUT / "proof_specificity.csv").exists():
    sp = pd.read_csv(OUT / "proof_specificity.csv")
    print("Transplants with new flags:", int((sp.new_flags_in_region > 0).sum()), "of", len(sp))""")

md("""## 7. Scorecard, case files and the rules as SQL

The household-finance step (section 9b) runs first: the scorecard reads its section-coverage flags and case C11 reads its numbers.""")
code("""os.system(f"cd statquo && python analysis/finance_impact.py '{DATA_DIR}' out/ > /dev/null")
iss, mat = SC.build(OUT)
display(iss[["status", "form", "year", "region", "rule_id", "columns", "rate_region", "rate_rest"]])
cases = CS.render(CS.facts(DATA_DIR, OUT))
json.dump(cases, open(OUT / "cases.json", "w"), ensure_ascii=False, indent=1)
for c in cases:
    display(Markdown(f"**{c['id']}. {c['title']}** ({c['forms']}; {c['status']})\\n\\n{c['finding']}\\n\\n*Indicator:* {c['indicator']}  \\n*Likely cause:* {c['cause']}  \\n*Fix:* {c['fix']}"))""")

code("""EX.main([str(p) for p in RULES], str(OUT / "rules_export.csv"))
display(pd.read_csv(OUT / "rules_export.csv").head(10))""")

md("""## 8. Blind tests

**The Bureau's three known cases, found without being told.** The same sweep and models that run on every region and form; nothing points them at these cases.

**A new year's form.** A fresh model run (no context from the project) was given only the prompt (`prompts/extract_rules_v2.md`) and the 2022 D-002 form and file structure. Its rules (`demo/d002_2022_v2.json`) run here on the 2022 records. To repeat it live, build the prompt with `extract/llm_extract.py --prompt-only`, paste it into a Claude chat, and read the answer back with `--from-reply` (see `demo/DEMO.md` in the package).""")
code("""c2 = pd.read_csv(OUT / "compare_year_c2st.csv")
lfs = c2[c2.form == "T001/baza"].sort_values("auc", ascending=False).reset_index(drop=True)
print("T-001, 2023 vs 2024, regions by AUC:"); display(lfs[["region", "auc", "top_features"]].head(5))
sw = pd.read_csv(OUT / "compare_region_sweep.csv")
d4 = sw[(sw.form == "D004") & (sw.variable != "K")].sort_values("js", ascending=False).reset_index(drop=True)
print("D-004, most unusual regional answers (settlement type left out):"); display(d4[["year", "table", "variable", "region", "share_region", "share_rest_same"]].head(5))
b4 = json.load(open("statquo/demo/d004_blind.json", encoding="utf-8"))["rules"]
print("Fresh D-004 extraction:", len(b4), "rules;", sum(r["type"] == "doc_issue" for r in b4), "documentation problems; none about the missing food section")""")
code("""S.NOT_RUN.clear()
spec22 = json.load(open("statquo/demo/d002_2022_v2.json", encoding="utf-8"))
res22 = S.run_rules(spec22["rules"], DATA_DIR, "D002", [2022])
f22 = S.flag_regions(res22)
print(len(spec22["rules"]), "rules from the 2022 form;", len({r["rule_id"] for r in S.NOT_RUN}), "left to a person")
display(f22[f22["flag"]][["rule_id", "column", "region", "rate_region", "rate_rest", "synthesis"]])""")

md("""## 9. Child poverty: how many households the indicator rests on

Indicator: share of households with children that cannot afford 3 or more of the 14 items in D-002 Part 4 Q5 (code 2). Coverage: households with a child under 18 in the D-008 roster that answered Part 4.""")
code("""os.system(f"cd statquo && python analysis/child_impact.py '{DATA_DIR}' out/ > /dev/null")
ci = pd.read_csv(OUT / "child_impact.csv")
display(ci.sort_values(["year", "coverage_pct"])[["year", "region", "with_children_roster", "answered_among_with_children", "coverage_pct", "deprived_pct", "moe_pp"]].groupby("year").head(5))""")

md("""## 9b. Household finances (D-004): four corrections before a vulnerability indicator

Second indicator case (C11), computed in section 7 by `analysis/finance_impact.py`. Unit: a household-quarter that took part (REZ = 1), unweighted. (1) D-004 has no food section, so income minus recorded spending is not a savings rate. (2) GR3 is 'of which' under GR2 on the form; summing all 23 income columns counts it twice. (3) Aktobe's coding of loan purpose drives the national share of loans taken for food. (4) Four regions leave the loan section almost empty. The synthetic release also repeats non-food items (15% of rows, named in the organisers' guide); it is uniform by region, so regional comparisons hold.""")
code("""nat = pd.DataFrame(json.load(open(OUT / "finance_impact_national.json", encoding="utf-8"))).set_index("year")
display(nat[["savings_rate_naive_pct", "recorded_spend_to_income_pct", "implied_spend_to_income_if_food_half_pct", "gr3_added_pct",
             "food_loan_pct_of_purpose", "food_loan_pct_of_purpose_without_aktobe", "aktobe_share_of_food_loans_pct",
             "repaying_pct", "repaying_pct_without_low_coverage", "burden_gt30_pct", "kv1_repeat_rows_pct", "corr_log_income_spend_household"]].T)
fc = pd.read_csv(OUT / "finance_section_coverage.csv")
display(fc[fc.flag & (fc.year == 2024)][["region", "section", "households_pct", "median_others", "years_low"]])
fi = pd.read_csv(OUT / "finance_impact.csv")
display(fi[fi.year == 2024].sort_values("burden_gt30_pct")[["region", "household_quarters", "repaying_pct", "burden_gt30_pct", "food_loan_pct_of_purpose", "loans_with_purpose", "gr3_added_pct"]])""")

md("""## 10. Data model: how the forms link

`NOMER` is the same household in D-002, D-004, D-006 and D-008; the D-008 roster (one row per person) is the hub. T-001 has no identifier. Joined on `NOMER`, the D-002 child filter (GR40) is checked household by household against the members under 18 in the roster. Diagrams and `DATA_MODEL.md`: `python schema/draw.py --out out/ --to diagrams/` (needs Graphviz).""")
code("""os.system(f"cd statquo && python schema/profile.py --data '{DATA_DIR}' --out out/ > /dev/null")
lk = pd.read_csv(OUT / "schema_links.csv")
display(lk[lk.year == 2024][["link", "key", "found_pct", "region_agrees_pct", "respondent_differs", "share_if_condition_pct", "share_if_not_condition_pct"]])
hc = pd.read_csv(OUT / "schema_household_children.csv")
display(hc[hc.year == 2024].sort_values("missed_pct", ascending=False).head(5))""")

md("""## 11. From problem to fix: the case files as one chain

The console tab "Проблема → влияние → рекомендация" shows each case file as problem → impact → fix. The cell below lists the same chain from `out/cases.json`. The impact column is the indicator the problem changes; a number is given only where code computed it (sections 7–9 and the decoder). `analysis/viz_export.py` writes the full table (every scorecard issue with its case, shares, trust level and impact) as CSV and Excel, from the console's `data.json`.""")
code("""cs = pd.DataFrame(json.load(open(OUT / "cases.json", encoding="utf-8")))
pd.set_option("display.max_colwidth", 160)
display(cs[["id", "title", "status", "indicator", "fix"]].rename(columns={"title": "problem", "indicator": "impact (indicator affected)"}))""")

md("""## Limits

- All figures come from the synthetic release (STAT.DATATHON 2026). Flags marked *check on real records* may come from links the generator does not keep.
- T-001 has no questionnaire in the archive, so it has no rules; it is covered by the ML comparisons only.
- The reference set for D-002 was built by an independent model run and adjudicated; the team checked each decision in `gold/d002_review.csv` on 11 Oct 2026 (12 confirmed, 1 rejected).""")

nbf.write(nb, ROOT / "StatQUO_final.ipynb")
print("cells:", len(C))
