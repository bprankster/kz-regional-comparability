# Prompt: questionnaire → executable rules (v1)

You are given the documentation of one statistical form of the Bureau of National Statistics of Kazakhstan:
the blank questionnaire (Kazakh and Russian), the interviewer instruction, and the file structure that maps
data columns to questions. You are also given the list of column names that actually occur in the data file.

Your task is to write down every rule the documentation implies about the data, as JSON that a program
can execute. Do not invent rules. Every rule must quote the passage it comes from.

## Rule types

| type | meaning | example |
|---|---|---|
| `domain` | the column may only hold these codes (blank is allowed unless a `required` rule says otherwise) | Part 1 scale: 1–10 or 89 |
| `required` | when `when` holds (or always), the column must not be blank | Part 2 Q1 is asked of everyone |
| `skip` | when `when` holds, the column must be blank (the questionnaire routes past it) | Part 3 Q13 "no → 15", so Q14 is blank |
| `multi_select` | a tick-box group: each column is 1 or blank; `exclusive` lists options that cannot be ticked with others | Part 2 Q8 option 5 "not applicable" |
| `consistency` | a logical relation between two answers in the same record | a pre-school child not attending kindergarten implies "there are children" |
| `cross_form` | a relation between this form and another form of the same household, checked on regional shares | D-002 "has children" vs D-008 roster |
| `doc_issue` | the documentation contradicts itself (Kazakh vs Russian wording, instruction vs form, structure vs data) | — |

`meaning` gives code labels (Russian, as printed) for `domain` rules when the form prints them.

## Output

A JSON object `{"form": ..., "years": [...], "rules": [...]}`. Each rule:

```json
{
  "id": "D002-P3Q14-skip",
  "type": "skip",
  "table": "ocenka",
  "targets": ["GR314"],
  "when": {"col": "GR313", "in": [2]},
  "allowed": null,
  "meaning": null,
  "source": {"doc": "form", "quote": "иә→ 14 / да → 14; жоқ→ 15 / нет → 15"},
  "confidence": "high",
  "note": "Q13 'no' routes to Q15"
}
```

`when` is either `{"col": C, "in": [...]}`, `{"col": C, "blank": true}`, `{"col": C, "filled": true}`,
`{"all": [...]}` or `{"any": [...]}`. Use `"confidence": "medium"` when the rule is implied rather than printed
(for example, a question with an arrow on "yes" only). Use the data column names exactly as listed.

Write the most complete list you can. A rule the form states but the data breaks is exactly what we want to find.
