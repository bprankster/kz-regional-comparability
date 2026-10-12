# Live demo: a new year's form in two minutes

Slide "A new year's form in two minutes" ("Форма нового года за две минуты"). Rehearse it twice before 20 October.

## What you need

- A laptop with the package unzipped, Python, and the synthetic archive (`DATA_DIR`).
- A Claude chat open in the browser (a Pro plan is enough; no API key, no extra cost).
- These files, already in this folder: `prompt_d002_2022_v2.txt` (the prompt), `reply_d002_2022_v2.txt` (the saved answer, as a backup).

## Steps on stage (about 3 minutes)

1. **Show the input.** Open `prompt_d002_2022_v2.txt`: the instructions, then the 2022 form and its file structure. Say: "the tool has never seen this year".
2. **Run the model.** Start a new Claude chat, paste the whole file, send. It answers with a JSON list of rules in 1–2 minutes. While it writes, explain what a rule is (slide "One line of the form becomes one test").
3. **Save the answer.** Copy the reply into `reply_live.txt`, then:

   ```
   python extract/llm_extract.py --form D002 --docs demo/docs_d002_2022 \
       --columns DATA_DIR/d002/2022/subject.csv DATA_DIR/d002/2022/ocenka.csv \
       --out demo/d002_2022_live.json --from-reply reply_live.txt
   ```

   It prints the number of rules and any rule that names a column the data does not have.
4. **Run the checks.**

   ```
   python engine/statquo.py --data DATA_DIR --rules demo/d002_2022_live.json --out demo/live --years 2022
   ```

   About 3 seconds. Open `demo/live/D002_region_flags.csv` (rows with `flag = True`) and `demo/live/D002_not_run.csv`.
5. **Read one flag aloud**, e.g. a region where the 'I use mobile internet' answers come from households that report no internet use.

## If something fails

- No internet, or the chat is slow: use `reply_d002_2022_v2.txt` in step 3. It is the same run as on the slide.
- The answer differs from the slide: that is expected, since each run is a new model run. The counts change a little; the kind of findings does not. Say so; it shows the run is live.
- A rule cannot be executed: it is listed in `D002_not_run.csv` with the reason, and the run continues.

## Make the prompt for any other form or year

```
python extract/llm_extract.py --form D006 --docs documentation/d006/2024 \
    --columns DATA_DIR/d006/2024/rio_2024.csv --out x --prompt-only prompt_d006.txt
```

Only the blank form, the instruction, the file structure and the column names go into the prompt. No survey record leaves the computer.
