"""StatQUO code decoder: what does an undocumented code mean?

Three tools, all computed from the records:
1. Fingerprints. For each code of a column, its profile over anchor variables whose meaning is known: age, city or
   village, sex, industry section (from the 4-digit activity code, ОКЭД = NACE Rev. 2), occupation major group (from the
   4-digit occupation code, НКЗ = ISCO-08), hours, and the codes of the other columns.
2. Matching against a documented sister form. The same concept (sex, marital status, education) is labelled in D-008;
   each T-001 code is assigned to the D-008 code whose profile on the shared anchors (age, city/village) is closest
   (Hungarian assignment). Confidence is the gap to the second-best assignment.
3. Code-shift detection. For every region and year, each code's profile is matched against the profiles of the same
   column in the rest of the country (the region itself left out). A region whose code x behaves like the national code y (x != y) is recording the same thing under
   another code.

The fingerprints also feed the LLM step (decoder/prompt_decode_v1.md): the model proposes a meaning for each code, and
the proposals are validated on columns whose labels are documented but hidden from the model.

    python decoder/decode.py DATA_DIR out/ meanings   # tools 1-2 and the fingerprints (pipeline step 3)
    python decoder/decode.py DATA_DIR out/ shift      # tool 3 (pipeline step 5, feeds the scorecard)
    python decoder/decode.py DATA_DIR out/            # both
"""
import itertools
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import linear_sum_assignment

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
import statquo as S  # noqa: E402

AGE_BINS = [-1, 6, 14, 17, 24, 34, 44, 54, 64, 79, 200]
AGE_LAB = ["0–6", "7–14", "15–17", "18–24", "25–34", "35–44", "45–54", "55–64", "65–79", "80+"]
OKED = [((1, 3), "A Сельское хозяйство"), ((5, 9), "B Горнодобывающая"), ((10, 33), "C Обрабатывающая"), ((35, 35), "D Энергия"),
        ((36, 39), "E Водоснабжение"), ((41, 43), "F Строительство"), ((45, 47), "G Торговля"), ((49, 53), "H Транспорт"),
        ((55, 56), "I Гостиницы, питание"), ((58, 63), "J Связь"), ((64, 66), "K Финансы"), ((68, 68), "L Недвижимость"),
        ((69, 75), "M Профессиональная"), ((77, 82), "N Административная"), ((84, 84), "O Госуправление"), ((85, 85), "P Образование"),
        ((86, 88), "Q Здравоохранение"), ((90, 93), "R Искусство"), ((94, 96), "S Прочие услуги"), ((97, 98), "T Домашние хозяйства"), ((99, 99), "U Экстерриториальные")]
ISCO = {"0": "0 Военнослужащие", "1": "1 Руководители", "2": "2 Специалисты высшего уровня", "3": "3 Специалисты среднего уровня",
        "4": "4 Служащие", "5": "5 Сфера обслуживания и торговля", "6": "6 Сельское хозяйство (квалиф.)", "7": "7 Рабочие ремёсел",
        "8": "8 Операторы машин", "9": "9 Неквалифицированные"}
D008_LABELS = {
    "POL": {"1": "мужской", "2": "женский"},
    "SEM_POL": {"1": "никогда не состоял(а) в браке", "2": "состоит в браке", "3": "вдовец, вдова", "4": "разведён(а)"},
    "UROV": {"1": "дошкольное", "2": "начальное", "3": "основное среднее", "4": "среднее (общее, ТиПО)", "5": "высшее", "6": "послевузовское", "7": "не достигнут никакой уровень"},
    "STATUS": {"1": "работающий по найму", "2": "работающий не по найму", "3": "безработный", "4": "пенсионер", "5": "учащийся, студент",
               "6": "домашнее хозяйство, уход за детьми", "7": "нетрудоспособный", "8": "не работает и не ищет по другим причинам"},
    "RODSTVO": {"1": "глава", "2": "муж, жена", "3": "сын, дочь", "4": "отец, мать", "5": "брат, сестра", "6": "дедушка, бабушка", "7": "внук, внучка", "8": "другая степень родства", "9": "не родственник"},
}
D006_LABELS = {"TIP_J": {"1": "одноквартирный (индивидуальный) дом", "2": "комната в доме", "3": "двухквартирный дом", "4": "трёх и более квартирный дом", "5": "комната в квартире"}}
SISTER = [("DH_POLRESP", "POL", "пол"), ("DH_SEMSOST", "SEM_POL", "семейное положение"), ("DH_OBRAZOV", "UROV", "образование")]
T001_TARGETS = ["DH_POLRESP", "DH_SEMSOST", "DH_OBRAZOV", "ORB_STATUS", "ORB_PKHDHL", "ORB_TRDDOG", "ORB_TERRIT", "ORB_MESTOR"]
T001_STRUCT = {"DH_POLRESP": "вопрос 3", "DH_SEMSOST": "вопрос 6", "DH_OBRAZOV": "вопрос 7", "ORB_STATUS": "(основной) вопрос 16",
               "ORB_TRDDOG": "(основной) вопрос 17", "ORB_PKHDHL": "(основной) вопрос 29", "ORB_TERRIT": "(основной) вопрос 34", "ORB_MESTOR": "(основной) вопрос 26"}


def oked(code):
    try:
        k = int(str(code)[:2])
    except ValueError:
        return np.nan
    return next((n for (a, b), n in OKED if a <= k <= b), np.nan)


def code_str(s):
    return s.astype(str).str.strip().str.lstrip("0").replace({"": "0", "nan": np.nan, "<NA>": np.nan})


def load_t001(D, y):
    t = S.read(D, f"t001/{y}/baza.csv")
    a = pd.DataFrame({"TE": t.TE})
    a["age"] = pd.cut(S.num(t.VOSR), AGE_BINS, labels=AGE_LAB)
    a["K"] = t.K.map({"1": "город", "2": "село"})
    a["industry"] = t.ORB_OTRASLKOD.map(oked)
    a["occupation"] = t.ORB_PROFES.astype(str).str[0].map(ISCO)
    h = S.num(t.ZAN_VREMYA_2)
    a["hours"] = pd.cut(h, [-1, 0, 19, 34, 40, 48, 200], labels=["0", "1–19", "20–34", "35–40", "41–48", "49+"])
    for c in T001_TARGETS:
        a[c] = code_str(t[c])
    return a


def load_d008(D, y):
    r = S.read(D, f"d008/{y}/kontr_k.csv")
    a = pd.DataFrame({"TE": r.TE})
    a["age"] = pd.cut(y - S.num(r.GOD_ROJD), AGE_BINS, labels=AGE_LAB)
    a["K"] = r.K.map({"1": "город", "2": "село"})
    for c in D008_LABELS:
        a[c] = code_str(r[c])
    return a


def load_d006(D, y):
    d = S.read(D, S.D006_FILES[y])
    a = pd.DataFrame({"TE": d.TE})
    a["K"] = d.K.map({"1": "город", "2": "село"})
    a["area"] = pd.cut(S.num(d.OB_PL), [0, 30, 45, 60, 80, 120, 10000], labels=["≤30 м²", "31–45", "46–60", "61–80", "81–120", ">120"])
    a["rooms"] = code_str(d.KOL_K).map(lambda x: x if x in ("1", "2", "3", "4") else ("5+" if isinstance(x, str) else np.nan))
    a["TIP_J"] = code_str(d.TIP_J)
    return a


def profiles(df, col, anchors, min_n=30):
    """P(anchor category | code) for every code with at least min_n records."""
    out = {}
    g = df[df[col].notna()]
    for code, part in g.groupby(col):
        if len(part) < min_n:
            continue
        out[code] = {"n": int(len(part)), **{a: part[a].value_counts(normalize=True) for a in anchors}}
    return out


def js(p, q):
    idx = p.index.union(q.index)
    p, q = p.reindex(idx, fill_value=0).values + 1e-9, q.reindex(idx, fill_value=0).values + 1e-9
    p, q = p / p.sum(), q / q.sum()
    m = (p + q) / 2
    return float(0.5 * (p * np.log2(p / m)).sum() + 0.5 * (q * np.log2(q / m)).sum())


def distance(pa, pb, anchors):
    return float(np.mean([js(pa[a], pb[a]) for a in anchors]))


def match(unknown, reference, anchors):
    """Hungarian assignment of unknown codes to reference codes. Returns rows with the assignment, its distance and the
    margin: how much the total distance rises when this pair is forbidden (bigger = more certain)."""
    u, r = list(unknown), list(reference)
    if not u or not r:
        return []
    M = np.array([[distance(unknown[a], reference[b], anchors) for b in r] for a in u])
    ri, ci = linear_sum_assignment(M)
    base = M[ri, ci].sum()
    rows = []
    for i, j in zip(ri, ci):
        M2 = M.copy(); M2[i, j] = 1e3
        r2, c2 = linear_sum_assignment(M2)
        rows.append({"code": u[i], "matched": r[j], "distance": round(float(M[i, j]), 4),
                     "margin": round(float(M2[r2, c2].sum() - base), 4),
                     "runner_up": r[int(np.argsort(M[i])[1])] if len(r) > 1 else None})
    for i in set(range(len(u))) - set(ri):
        rows.append({"code": u[i], "matched": None, "distance": None, "margin": None, "runner_up": r[int(np.argmin(M[i]))]})
    return rows


def describe(prof, overall, anchors, k=3):
    """Text fingerprint of one code for the LLM step: size, then the anchor categories most over-represented."""
    lines = []
    for a in anchors:
        p, o = prof[a], overall[a]
        lift = (p / o.reindex(p.index).replace(0, np.nan)).dropna()
        top = lift[(p.reindex(lift.index) >= 0.05)].sort_values(ascending=False).head(k)
        lines.append(f"{a}: " + "; ".join(f"{cat} {100 * p[cat]:.0f}% (в целом {100 * o.get(cat, 0):.0f}%)" for cat in top.index))
    return lines


def main(D, out, part="all"):
    out = Path(out)
    meanings, shift = part in ("all", "meanings"), part in ("all", "shift")
    res = {"sister": [], "validation_match": [], "shift": [], "fingerprints": {}}
    t24, t23 = load_t001(D, 2024), load_t001(D, 2023)
    d24, d23 = load_d008(D, 2024), load_d008(D, 2023)
    f24, f23 = load_d006(D, 2024), load_d006(D, 2023)

    # 1. matching against the documented sister form (shared anchors: age, city/village)
    for tcol, dcol, concept in (SISTER if meanings else []):
        ref = profiles(d24, dcol, ["age", "K"])
        unk = profiles(t24, tcol, ["age", "K"])
        for r in match(unk, ref, ["age", "K"]):
            r.update({"t001_column": tcol, "concept": concept, "label": D008_LABELS[dcol].get(r["matched"], "—") if r["matched"] else "нет пары в Д-008",
                      "runner_up_label": D008_LABELS[dcol].get(r["runner_up"], "") if r["runner_up"] else "", "share": round(100 * unk[r["code"]]["n"] / sum(v["n"] for v in unk.values()), 1)})
            res["sister"].append(r)

    # 2. validation of matching: recover a hidden renumbering between two independent years
    rng = np.random.default_rng(20261010)
    vsets = [("D-008", d23, d24, c, ["age", "K"] + [x for x in ("POL", "RODSTVO") if x != c]) for c in ("POL", "SEM_POL", "UROV", "STATUS", "RODSTVO")]
    vsets += [("D-006", f23, f24, "TIP_J", ["K", "area", "rooms"])]
    vsets += [("T-001", t23, t24, c, ["age", "K", "industry", "occupation", "hours"]) for c in ("ORB_STATUS", "ORB_PKHDHL", "DH_OBRAZOV")]
    for form, a, b, col, anchors in (vsets if meanings else []):
        for trial in range(20):
            codes = sorted(set(b[col].dropna()))
            perm = dict(zip(codes, rng.permutation(codes)))
            bb = b.copy(); bb[col] = bb[col].map(perm)
            rows = match(profiles(bb, col, anchors), profiles(a, col, anchors), anchors)
            inv = {v: k for k, v in perm.items()}
            ok = [r["matched"] == inv[r["code"]] for r in rows if r["matched"] is not None]
            res["validation_match"].append({"form": form, "column": col, "anchors": ", ".join(anchors), "trial": trial,
                                            "codes": len(ok), "correct": int(sum(ok))})

    # 3. code-shift detection: region-year profile against the national profile of the same column and year
    for name, frames, cols, anchors in [("T-001", {2023: t23, 2024: t24}, ["ORB_STATUS", "ORB_PKHDHL", "ORB_TRDDOG", "DH_OBRAZOV"], ["age", "K", "industry", "occupation", "hours"]),
                                        ("D-008", {2023: d23, 2024: d24}, ["STATUS", "UROV", "SEM_POL"], ["age", "K", "POL"])] if shift else []:
        for y, df in frames.items():
            for col in cols:
                anc = [x for x in anchors if x != col]
                for te, part in df.groupby("TE"):
                    nat = profiles(df[df.TE != te], col, anc, min_n=100)   # the rest of the country, without this region
                    reg = profiles(part, col, anc, min_n=40)
                    rows = match(reg, nat, anc)
                    for r in rows:
                        if r["matched"] is not None and r["matched"] != r["code"]:
                            same = distance(reg[r["code"]], nat[r["code"]], anc) if r["code"] in nat else None
                            res["shift"].append({"form": name, "year": y, "region": S.REGION.get(te, te), "column": col, "code": r["code"],
                                                 "behaves_like": r["matched"], "distance_to_match": r["distance"],
                                                 "distance_to_same_code": round(same, 4) if same is not None else None,
                                                 "n": reg[r["code"]]["n"]})

    # 4. fingerprints for the LLM step (targets and hidden-label validation columns)
    def fp(df, col, anchors, struct):
        prof, overall = profiles(df, col, anchors), {a: df[a].value_counts(normalize=True) for a in anchors}
        tot = sum(v["n"] for v in prof.values())
        return {"structure": struct, "codes": {c: {"share_pct": round(100 * v["n"] / tot, 1), "profile": describe(v, overall, anchors)} for c, v in sorted(prof.items(), key=lambda kv: -kv[1]["n"])}}
    t_anc = ["age", "K", "industry", "occupation", "hours"]
    for c in (T001_TARGETS if meanings else []):
        res["fingerprints"][f"T-001/{c}"] = fp(t24, c, t_anc + [x for x in ("DH_POLRESP", "ORB_STATUS", "ORB_TRDDOG") if x != c], f"Т-001, {T001_STRUCT[c]}; ответ — код")
    for c in (("STATUS", "SEM_POL", "UROV") if meanings else ()):
        res["fingerprints"][f"D-008/{c}"] = fp(d24.assign(POL=d24.POL.map(D008_LABELS["POL"]), RODSTVO=d24.RODSTVO.map(D008_LABELS["RODSTVO"])), c,
                                               ["age", "K", "POL", "RODSTVO"], "Д-008, контрольная карточка; ответ — код (метки скрыты для проверки)")
    if meanings:
        res["fingerprints"]["D-006/TIP_J"] = fp(f24, "TIP_J", ["K", "area", "rooms"], "Д-006, вопрос 1 «Каков тип помещения…»; ответ — код (метки скрыты для проверки)")

    if meanings:
        pd.DataFrame(res["sister"]).to_csv(out / "decoder_sister_match.csv", index=False)
        v = pd.DataFrame(res["validation_match"])
        v.to_csv(out / "decoder_validation_match.csv", index=False)
        json.dump(res["fingerprints"], open(out / "decoder_fingerprints.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        s = v.groupby(["form", "column"]).agg(codes=("codes", "first"), accuracy=("correct", "sum"), total=("codes", "sum"))
        s["accuracy"] = (100 * s.accuracy / s.total).round(1)
        print(pd.DataFrame(res["sister"])[["t001_column", "code", "share", "label", "margin", "runner_up_label"]].to_string(index=False))
        print(s.to_string())
    if shift:
        sh = pd.DataFrame(res["shift"])
        if len(sh):
            sh["gain"] = (sh.distance_to_same_code - sh.distance_to_match).round(4)
            sh["ratio"] = (sh.distance_to_match / sh.distance_to_same_code).round(3)
            # flag: the region's code is at least twice as close to another national code as to its own, by a clear margin
            sh["flag"] = (sh.ratio <= 0.5) & (sh.gain >= 0.03)
        sh.to_csv(out / "decoder_code_shift.csv", index=False)
        print(len(sh), "candidate shifts,", int(sh.flag.sum()) if len(sh) else 0, "flagged")
        if len(sh):
            print(sh[sh.flag].to_string(index=False))

if __name__ == "__main__":
    main(*sys.argv[1:4])
