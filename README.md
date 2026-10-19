# StatQUO: do regions record the same answers the same way?

STAT.DATATHON 2026 · Track 2 "AI for Official Statistics" · team StatQUO
(Aidai Totoeva, Baiirbek Kholikov, Almanbet Kaldybaev, Nargiza Zhumalieva)

**Web app (the IT solution, in Russian):** https://bprankster.github.io/kz-regional-comparability/app/ (the site root opens it) — also `app/StatQUO_app.html`, works offline.

Four stages: (0) questionnaire → rules: the model is called from the page (an Anthropic API key, streamed; or a Claude chat, copy and paste; or the saved D-002 2022 run) with the blank form, instruction, file structure and column names only, and the rules are checked and applied to the next stages (`app/ai_stage.js`, same prompt as `extract/llm_extract.py`); (1) checks while a questionnaire is filled in, on a form built from the rules (D-002, D-006, D-008, or rules from stage 0); (2) upload survey CSV files (D-002, D-006, D-008) and get rule checks by region with CSV and SQL downloads; (3) analysis — results (region map with questionnaire quotes and SQL, eleven case files problem → impact → fix, child poverty, household finances; after a file check the model can group the deviations into case files from the regional summary alone, and every number in its text is matched against the computation) and method (all 176 rules, new-form demo, decoder, trust checks, data model; these sections come from the former console, `app/analysis_extra.js`). All checks run in the browser; data never leaves the computer. `app/engine.js` is a JavaScript port of `engine/statquo.py`, verified row by row against the Python results for 2024. Rebuild: `python app/build_app.py`. The former console is kept as an archive at https://bprankster.github.io/kz-regional-comparability/console/.

> **Кратко.** Инструмент для Бюро национальной статистики: читает анкеты обследований домохозяйств (Д-002, Д-004, Д-006, Д-008),
> превращает их в исполняемые проверки (LLM) и сравнивает регионы, годы и формы (ML), чтобы найти, где одна и та же ситуация
> записывается по-разному. На синтетическом выпуске 2023–2024: 176 правил (142 в виде SQL-запросов для Бюро), 102 отклонения
> по регионам, 11 разобранных дел — от проблемы через затронутый показатель к рекомендации. Точность извлечения правил из анкеты
> Д-002 — 99,2% (precision) и 94,8% (recall) против эталона, проверенного командой. Все цифры получены кодом из этого репозитория;
> модель пишет только формулировки.

**Data.** The synthetic microdata (STAT.DATATHON 2026, Bureau of National Statistics) and the organisers' documentation are not in
this repository. Get the archive from the organisers and point `DATA_DIR` at it (layout `d002/2024/ocenka.csv`, …). Everything in
`out/` is region-level output computed from it.

A tool for the Bureau of National Statistics that reads the survey questionnaires, turns them into checks,
and runs the checks on the records region by region. It answers one question: do regions record the same
situation in the same way? It is rerun every quarter on the Bureau's own records; nothing leaves that computer.

## What it does

1. **Questionnaire → rules (LLM).** The blank form, the interviewer instruction and the file structure are
   turned into executable rules: allowed codes, routing ("no → go to 15"), answers that must be filled,
   tick-box groups, logical links between answers, links to other forms, and contradictions in the
   documentation itself (Kazakh vs Russian wording, instruction vs form). Every rule quotes its source.
   - `prompts/extract_rules_v1.md`: the prompt the rule files were made with. `prompts/extract_rules_v2.md`: the same
     prompt plus the fields the engine needs to run every rule type (use v2 for new forms).
   - `rules/*.json`: the rule files for D-002, D-004, D-006, D-008.
   - `extract/llm_extract.py`: the same step for a new form or year, through the Claude API, or with no API key:
     `--prompt-only` writes the prompt to paste into a Claude chat, `--from-reply` reads the answer back.
   - A rule the engine cannot execute is listed in `<FORM>_not_run.csv` with the reason; the run continues.
2. **Accuracy of the extraction.** `gold/`: a reference set for D-002 built independently from the same
   documents (403 atomic rules), the adjudication sheet, and `gold/score.py` (precision and recall by rule type).
3. **Decoding undocumented codes** (`decoder/decode.py … meanings`). Where the documentation gives no code list (all of
   T-001's questionnaire is missing from the archive), what each code means is worked out from the records: a fingerprint
   per code (age, city/village, industry ОКЭД, occupation НКЗ, hours, other columns), matching against D-008 where the same
   concept is labelled, and an LLM reading of the fingerprints (`decoder/prompt_decode_v1.md`). Validated with labels
   hidden: 21 of 24 codes right, 11 of 12 high-confidence proposals right; a hidden renumbering between years recovered
   in 8 of 9 columns. The T-001 meanings stay hypotheses until checked against the questionnaire.

4. **Checks by region (engine).** `engine/statquo.py` runs every rule on every region and year and flags a
   region when its violation rate stands out from the rest of the country (rate ≥ 5%, ≥ 3× the rest,
   z > 3, at least 10 excess records). Each flag says whether it can be trusted on synthetic data:
   *forced by the answer shares* (survives synthesis) or *could be broken links in the synthetic data*
   (needs the real records).
5. **Comparisons without rules.** `engine/compare.py`: region vs rest (Jensen–Shannon divergence on every
   variable), 2023 vs 2024 (a LightGBM classifier per region; AUC well above the other regions means the
   region's recording changed) and form vs form (region-level shares from two forms that must agree).
   `decoder/decode.py … shift`: code shifts, where a region's code behaves like a different code in the rest of the
   country (found on its own: Kyzylorda codes children aged 7–10 as "no level" (7) instead of "preschool" (1), 85% in
   2023 and 99.6% in 2024 against at most 10% elsewhere). Code shifts enter the scorecard; `decoder/decoder_cases.py`
   computes the numbers for case files C9 and C10.
6. **Proof.** `proof/plant.py`: plants routing and coding errors into one region at known rates and checks
   they are found; gives a region another region's households (answers shift, routing intact) and checks
   that nothing new is flagged. Run twice: on the data as shipped, and with `CLEAN=1`, which first repairs
   the rule's background violations (the synthetic release breaks some links between columns; real records
   should be close to clean). On the repaired baseline every planted error is found from 10% planted, wherever
   the region has 30+ records the rule applies to and 10+ errors (68% of runs at 5%).
7. **Case files, scorecard, rules export.** `engine/cases.py` (text by the LLM, every number from code),
   `engine/scorecard.py` (issues by region, form and year from the rule checks, the cross-form children check, the region-vs-rest model, code shifts and D-004 section coverage), `engine/export.py` (every rule as a SQL query by region).

8. **Blind tests** (`demo/`). Without being told, the region sweep and the year-vs-year models rank two of the
   Bureau's three known cases first (Almaty oblast in T-001, Aktobe's food loans in D-004); a fresh extraction of
   D-004 missed the third (no food section, so the 66% "savings rate"). A fresh model run turned the 2022 D-002 form,
   which the tool had not seen, into 43 rules in 1 min 45 s; they ran on the 2022 records in 3.4 s.
   `demo/DEMO.md` is the script for the live demo.

9. **Child poverty** (`analysis/child_impact.py`). How many households the Part 4 child-poverty indicator rests on,
   by region: households with children in the D-008 roster against those that answered Part 4 of D-002, and how
   wide the indicator's margin of error becomes where few answered (Ulytau and Almaty city, 2024).

9b. **Household finances** (`analysis/finance_impact.py`, case C11). The second indicator case, on D-004: what a
   household financial-vulnerability indicator looks like before and after four corrections. (1) The journal has no food
   section, so income minus recorded spending (65.8% in 2024) is not a savings rate. (2) On the form GR3 is "of which"
   under GR2; summing all 23 income columns counts agricultural sales twice (rule `D004-3-agri-within-self-employment`).
   (3) Aktobe's loan-purpose coding drives the national share of loans for food (9.7%, 3.7% without Aktobe).
   (4) Mangystau, Shymkent, Turkistan and Zhambyl leave the loan section almost empty (section-coverage flags in the
   scorecard). The synthetic release repeats non-food items in 15% of rows (organisers' guide); it is uniform by region.
   Writes `finance_impact.csv`, `finance_impact_national.json`, `finance_section_coverage.csv`. Runs in about 2 minutes,
   and must run before step 7.

10. **Data model** (`schema/`, `DATA_MODEL.md`, `diagrams/`). `schema/profile.py` lists every table with its grain and
   key, every column with its kind, fill rate, description from the structure file and the rules that check it, and tests
   how the tables link: `NOMER` is the same household in D-002, D-004, D-006 and D-008 (every record finds its household
   in the D-008 roster, region agrees); T-001 has no identifier. Joined on `NOMER`, the D-002 child filter (GR40) is
   checked household by household against the roster: rules `D002-x-D008-child-household` and
   `D002-x-D008-nochild-household` (the engine adds `ROSTER_U18` from D-008); flagged regions enter the scorecard and case C1. `schema/draw.py` draws the diagrams (Russian and English for
   slides, two full technical diagrams) and writes `DATA_MODEL.md`.

11. **Console** (`console/`, archive; its sections now live in the app's Analysis tab): one page in Russian with the map, the tab "Проблема → влияние → рекомендация", child-poverty coverage,
   household finances, decoder, new-form demo, rules, trust checks and the data model. `python console/build_console.py out/ console/ && python console/make_page.py`.
   The tab "Проблема → влияние → рекомендация" shows each of the 11 case files as one chain: the problem (the case finding and its scorecard
   rows by region), the impact (the indicator affected, with a number only where code computed it: C1 child-indicator coverage, C4, C9, C10, C11),
   and the fix with its likely cause. Issues with no case file are listed below it. Scorecard rows are linked to cases by the cases' rule lists,
   and ML rows by the column the case names.

12. **Problem → impact → fix as a table** (`analysis/viz_export.py`): the same view as CSV and Excel (`statquo_issues_for_viz.csv`, one row per
   scorecard issue with its case, shares, trust level, indicator, fix and impact number; `statquo_cases_for_viz.csv`; `.xlsx` with a field
   dictionary). It reads `out/` and `console/data.json` and recomputes nothing, so it matches the console row by row.

## Run

```
pip install pandas numpy scipy scikit-learn lightgbm xlrd openpyxl
# 2. accuracy of the extraction (no data needed)
python gold/score.py rules/d002_2023-2024.json gold/d002_gold_reviewed.json --out out/
# 3. decoding undocumented codes
python decoder/decode.py DATA_DIR out/ meanings
# 4. checks by region, one rule file per form
for f in d002 d004 d006 d008; do python engine/statquo.py --data DATA_DIR --rules rules/${f}_2023-2024.json --out out/; done
# 5. comparisons without rules: ML, then code shifts
python engine/compare.py --data DATA_DIR --out out/
python decoder/decode.py DATA_DIR out/ shift && python decoder/decoder_cases.py DATA_DIR out/
# 6. proof (about 25 minutes each)
python proof/plant.py DATA_DIR rules/d002_2023-2024.json out/
CLEAN=1 python proof/plant.py DATA_DIR rules/d002_2023-2024.json out/
# 9b. household finances (before 7: the scorecard and case C11 read it)
python analysis/finance_impact.py DATA_DIR out/
# 7. scorecard, case files, rules as SQL
python engine/scorecard.py out/
python engine/cases.py DATA_DIR out/
python engine/export.py rules/*.json --out out/rules_export.csv
# 9. child poverty
python analysis/child_impact.py DATA_DIR out/
# 10. data model: tables, keys, links, column dictionary, diagrams, DATA_MODEL.md (Graphviz for the technical diagrams)
python schema/profile.py --data DATA_DIR --out out/      # or in two halves: --only tables, then --only links
python schema/draw.py --out out/ --to diagrams/
# 11. console page from everything above
python console/build_console.py out/ console/ && python console/make_page.py
# 12. problem -> impact -> fix as CSV / Excel (after the console)
python analysis/viz_export.py out/ console/data.json out/viz/
```

`DATA_DIR` has the archive's layout (`d002/2024/ocenka.csv`, `d006/2024/rio_2024.csv`, …). The notebook
`StatQUO_final.ipynb` runs all of it in order, in Colab or locally.

## Limits

- All numbers here come from the synthetic release. It keeps each region's answer shares close to the real
  ones but not every link between columns or between forms, so some flags can only be settled on the real records.
- The T-001 questionnaire is not in the archive, so T-001 has no rules; it enters through the ML comparisons and the decoder, whose code meanings are hypotheses until checked against the form.
- The D-002 reference set was built by a second, independent model run and adjudicated; the team checked all 13
  decisions on 11 Oct 2026 (`gold/d002_review.csv`: 12 confirmed; the D-006 owners-vs-rent rule rejected as an equality and rewritten as bounds: 'not relevant' between the owners' share and 100 minus those paying for their dwelling) and added
  one documentation issue the reference had missed. Final accuracy of the v1 extraction: precision 99.2%, recall 94.8% (`out/accuracy_d002_v1_vs_reviewed.csv`).
