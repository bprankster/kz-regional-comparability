# Prompt: what does each code mean? (v1)

You are given columns from household and labour-force surveys of the Bureau of National Statistics of Kazakhstan. For each
column you see where it sits on the form (question number), and for every code its share of records and its fingerprint:
the categories of known variables that are over-represented among records with that code, against the whole file
("в целом"). Known variables: age group, city or village (K), industry section (ОКЭД = NACE Rev. 2), occupation major group
(НКЗ = ISCO-08), weekly hours, and other columns of the same form.

For every code, write the most likely meaning, as it would be printed on a Kazakhstani statistical form, in Russian.
Use only the fingerprints: no code meanings are given to you, and you must not assume a code order from other forms.
Say how sure you are (high / medium / low) and which fingerprint lines decide it. If two codes look like the same thing,
say so.

Return only a JSON object:

```json
{"columns": [{"column": "T-001/ORB_STATUS", "concept": "статус занятости", "codes": [
  {"code": "1", "meaning": "...", "confidence": "high", "evidence": "..."}
]}]}
```
