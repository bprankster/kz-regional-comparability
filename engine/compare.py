"""StatQUO comparison engine (ML).

Three comparisons that need no rules, run on any form:
1. Region vs rest: for every region × variable, Jensen–Shannon divergence between the region's answer
   distribution and the rest of the country's (missing counted as its own answer). Scored against the same
   variable's spread across regions, so a variable that differs everywhere does not dominate.
2. Year vs year: a classifier two-sample test per region. A LightGBM model tries to tell 2023 records from
   2024 records within one region; AUC near 0.5 means the year left no trace, AUC well above the other
   regions means something in that region's recording changed. Top features say where.
3. Form vs form: region-level answer shares from different forms of the same households; pairs that agree
   1:1 across nearly all regions are invariants, and a region far off such a line is flagged.

    python engine/compare.py --data DATA_DIR --out out/
"""
import argparse
import itertools
from pathlib import Path

import warnings

import numpy as np
import pandas as pd

import statquo as S

warnings.filterwarnings("ignore")

ID_COLS = {"TE", "NOMER", "GODO", "GOD", "YEAR", "NOMP", "Q_FOLDER", "KVARTAL", "KVINT"}
# birth year and age move by one year between survey years by construction; keep them out of the year test
AGE_COLS = {"GOD_ROJD", "AGE", "DH_DATROZH_3", "VOSR", "VOZ"} | {f"VOZ{i}" for i in range(1, 9)}


def categorical_columns(df, max_levels=30):
    cols = []
    for c in df.columns:
        if c in ID_COLS:
            continue
        n = df[c].nunique(dropna=True)
        if 1 < n <= max_levels:
            cols.append(c)
    return cols


def js(p, q):
    p, q = np.asarray(p, float), np.asarray(q, float)
    p, q = p / p.sum(), q / q.sum()
    m = 0.5 * (p + q)
    with np.errstate(divide="ignore", invalid="ignore"):
        kl = lambda a, b: np.nansum(np.where(a > 0, a * np.log2(a / b), 0))
    return 0.5 * kl(p, m) + 0.5 * kl(q, m)


def region_sweep(df, form, table, year, max_levels=30):
    rows = []
    te = df["TE"]
    for c in categorical_columns(df, max_levels):
        x = df[c].fillna("∅")
        ct = pd.crosstab(te, x)
        tot = ct.sum()
        for code in ct.index:
            p = ct.loc[code]
            if p.sum() < 50:
                continue
            q = tot - p
            rows.append({"form": form, "table": table, "year": year, "variable": c, "te": code,
                         "region": S.REGION.get(code, code), "n": int(p.sum()), "js": js(p.values, q.values),
                         "top_answer_region": p.idxmax(), "share_region": round(100 * p.max() / p.sum(), 1),
                         "share_rest_same": round(100 * q[p.idxmax()] / q.sum(), 1)})
    out = pd.DataFrame(rows)
    if out.empty:
        return out
    g = out.groupby("variable")["js"]
    med, mad = g.transform("median"), g.transform(lambda s: (s - s.median()).abs().median() + 1e-6)
    out["robust_z"] = ((out["js"] - med) / (1.4826 * mad)).round(1)
    return out


def c2st(df_a, df_b, label_a, label_b, max_levels=60, seed=0):
    """Per region: AUC of a classifier telling the two years apart, and its top features."""
    import lightgbm as lgb
    from sklearn.metrics import roc_auc_score
    from sklearn.model_selection import StratifiedKFold

    cols = [c for c in df_a.columns if c in df_b.columns and c not in ID_COLS and c not in AGE_COLS]
    both = pd.concat([df_a[cols + ["TE"]].assign(_y=0), df_b[cols + ["TE"]].assign(_y=1)], ignore_index=True)
    feats = [c for c in cols if both[c].nunique() <= max_levels or pd.to_numeric(both[c], errors="coerce").notna().mean() > 0.9]
    X = np.column_stack([pd.Categorical(both[c].fillna("∅")).codes if both[c].nunique() <= max_levels
                         else pd.to_numeric(both[c], errors="coerce").fillna(-1).values for c in feats]).astype(np.float32)
    rows = []
    for code in sorted(both["TE"].dropna().unique()):
        m = (both["TE"] == code).values
        y = both["_y"].values[m]
        if min(np.bincount(y, minlength=2)) < 100:
            continue
        Xr, oof, gain = X[m], np.zeros(m.sum()), np.zeros(len(feats))
        for tr, va in StratifiedKFold(2, shuffle=True, random_state=seed).split(Xr, y):
            mdl = lgb.LGBMClassifier(n_estimators=150, learning_rate=0.08, num_leaves=15, min_child_samples=20,
                                     subsample=0.8, colsample_bytree=0.8, verbose=-1, random_state=seed)
            mdl.fit(Xr[tr], y[tr])
            oof[va] = mdl.predict_proba(Xr[va])[:, 1]
            gain += mdl.booster_.feature_importance("gain")
        top = np.argsort(-gain)[:3]
        rows.append({"te": code, "region": S.REGION.get(code, code), "auc": round(roc_auc_score(y, oof), 3),
                     "top_features": ", ".join(f"{feats[i]} {100 * gain[i] / gain.sum():.0f}%" for i in top),
                     "compare": f"{label_a} vs {label_b}"})
    out = pd.DataFrame(rows)
    if len(out):
        med = out["auc"].median()
        mad = (out["auc"] - med).abs().median() + 1e-3
        out["robust_z"] = ((out["auc"] - med) / (1.4826 * mad)).round(1)
    return out


def region_shares(df, prefix, max_levels=12, min_share=2.0):
    feats = {}
    for c in categorical_columns(df, max_levels):
        if c == "K" and prefix == "D002" and feats and any(k.startswith("D002:K=") for k in feats):
            continue
        ct = pd.crosstab(df["TE"], df[c].fillna("∅"), normalize="index") * 100
        for v in ct.columns:
            s = ct[v]
            if s.mean() >= min_share:
                feats[f"{prefix}:{c}={v}"] = s
    return pd.DataFrame(feats)


def invariants(A, B, min_regions=17, r2_min=0.9, slope=(0.8, 1.2), icpt=6.0, off=15.0, refit_off=10.0):
    """All pairs (a in A, b in B): keep 1:1 fits across >= min_regions regions, flag regions off the line."""
    A, B = A.align(B, join="inner", axis=0)
    out = []
    a_vals, b_vals = A.values, B.values
    for i, j in itertools.product(range(A.shape[1]), range(B.shape[1])):
        x, y = b_vals[:, j], a_vals[:, i]
        if np.nanstd(x) < 2 or np.nanstd(y) < 2:
            continue
        gap = y - x
        keep = np.abs(gap) < off
        if keep.sum() < min_regions or keep.sum() == len(x):
            continue
        xs, ys = x[keep], y[keep]
        sl, ic = np.polyfit(xs, ys, 1)
        # one refit without regions far from the first fitted line, so a single half-off region cannot tilt it
        resid = y - (sl * x + ic)
        keep2 = keep & (np.abs(resid) < refit_off)
        if refit_off and keep2.sum() >= min_regions and keep2.sum() < keep.sum():
            keep = keep2
            xs, ys = x[keep], y[keep]
            sl, ic = np.polyfit(xs, ys, 1)
        r2 = np.corrcoef(xs, ys)[0, 1] ** 2
        if r2 >= r2_min and slope[0] <= sl <= slope[1] and abs(ic) <= icpt:
            for k in np.where(~keep)[0]:
                out.append({"a": A.columns[i], "b": B.columns[j], "region": S.REGION.get(A.index[k], A.index[k]),
                            "a_share": round(y[k], 1), "b_share": round(x[k], 1), "gap": round(gap[k], 1),
                            "r2": round(r2, 2), "slope": round(sl, 2), "regions_on_line": int(keep.sum())})
    return pd.DataFrame(out)


def household_roster_features(roster, year):
    age = year - pd.to_numeric(roster["GOD_ROJD"], errors="coerce")
    g = pd.DataFrame({"TE": roster["TE"], "NOMER": roster["NOMER"], "u18": age < 18, "u7": age < 7,
                      "a65": age >= 65})
    hh = g.groupby(["TE", "NOMER"]).agg(u18=("u18", "any"), u7=("u7", "any"), a65=("a65", "any")).reset_index()
    return hh.groupby("TE")[["u18", "u7", "a65"]].mean().mul(100).add_prefix("D008:hh_has_")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", default="out")
    a = ap.parse_args()
    D = a.data
    ap2 = __import__("os").environ.get("PARTS", "sweep,c2st,inv").split(",")
    sweeps, tests = [], []
    for y in ((2023, 2024) if "sweep" in ap2 else ()):
        for form in ("D002", "D006", "D008"):
            for t, df in S.load(D, form, y).items():
                if t == "hh":
                    continue
                sweeps.append(region_sweep(df, form, t, y))
        for t, df in S.load(D, "D004", y).items():   # quarterly journal, quarters pooled; long tables split by question
            if t == "kv11":   # income amounts (loaded for rule D004-3-...); amounts are covered by analysis/finance_impact.py
                continue
            if "NOMVOPR" in df.columns:
                for v, part in df.groupby("NOMVOPR"):
                    sweeps.append(region_sweep(part.drop(columns=["NOMVOPR"]), "D004", f"{t}[NOMVOPR={v}]", y))
            else:
                sweeps.append(region_sweep(df, "D004", t, y))
        lfs = S.read(D, f"t001/{y}/baza.csv")
        sweeps.append(region_sweep(lfs, "T001", "baza", y))
    if sweeps:
        sw = pd.concat(sweeps, ignore_index=True)
        sw.to_csv(Path(a.out, "compare_region_sweep.csv"), index=False)
        print("region sweep:", len(sw))

    for form, tab in ((("D002", "ocenka"), ("D002", "subject"), ("D006", "rio"), ("D008", "kontr_k")) if "c2st" in ap2 else ()):
        t = c2st(S.load(D, form, 2023)[tab], S.load(D, form, 2024)[tab], "2023", "2024")
        t.insert(0, "form", f"{form}/{tab}")
        tests.append(t)
        print(form, tab, "c2st done", flush=True)
    if "c2st" in ap2:
        l23, l24 = S.read(D, "t001/2023/baza.csv"), S.read(D, "t001/2024/baza.csv")
        t = c2st(l23, l24, "2023", "2024")
        t.insert(0, "form", "T001/baza")
        tests.append(t)
        pd.concat(tests, ignore_index=True).to_csv(Path(a.out, "compare_year_c2st.csv"), index=False)

    inv = []
    for y in ((2023, 2024) if "inv" in ap2 else ()):
        d2 = S.load(D, "D002", y)
        A = pd.concat([region_shares(d2["subject"], "D002"), region_shares(d2["ocenka"], "D002")], axis=1)
        B = pd.concat([region_shares(S.load(D, "D006", y)["rio"], "D006"),
                       household_roster_features(S.read(D, f"d008/{y}/kontr_k.csv"), y)], axis=1)
        r = invariants(A, B)
        r.insert(0, "year", y)
        inv.append(r)
        print(y, "invariants:", len(r), flush=True)
    if inv:
        pd.concat(inv, ignore_index=True).drop_duplicates().to_csv(Path(a.out, "compare_invariants.csv"), index=False)
