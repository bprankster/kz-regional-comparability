"""How much does the child-module filter change the published child-deprivation indicator?

Indicator (D-002 Part 4 Q5): share of households with children that cannot afford 3 or more of the 14 items
(code 2 = "Нет. Хотелось бы иметь, но в данный момент не можем позволить").
For every region and year: households with a child under 18 in the D-008 roster (the population the indicator is
about), how many of them answered Part 4, the indicator on those who answered, and its 95% margin of error.

    python analysis/child_impact.py DATA_DIR out/
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
import statquo as S  # noqa: E402

D, OUT = sys.argv[1], Path(sys.argv[2])
rows = []
for y in (2023, 2024):
    oc = S.read(D, f"d002/{y}/ocenka.csv")
    ro = S.read(D, f"d008/{y}/kontr_k.csv")
    age = y - S.num(ro["GOD_ROJD"])
    kids = (age < 18).groupby(ro["NOMER"]).sum()
    oc["kids"] = oc["NOMER"].map(kids).fillna(0)
    q5 = [f"GR45_{i}" for i in range(1, 15)]
    lack = (oc[q5].apply(S.num) == 2).sum(axis=1)
    answered = oc[q5].apply(S.filled).any(axis=1)
    oc["deprived"] = (lack >= 3).astype(float)
    for te, g in oc.groupby("TE"):
        withk = g[g.kids > 0]
        ans = g[answered.loc[g.index]]
        ans_k = withk[answered.loc[withk.index]]
        n, p = len(ans), ans["deprived"].mean() if len(ans) else np.nan
        moe = 1.96 * np.sqrt(p * (1 - p) / n) * 100 if n else np.nan
        rows.append({"year": y, "te": te, "region": S.REGION.get(te, te), "households": len(g),
                     "with_children_roster": len(withk), "answered_part4": n,
                     "answered_among_with_children": len(ans_k),
                     "coverage_pct": round(100 * len(ans_k) / max(1, len(withk)), 1),
                     "deprived_pct": round(100 * p, 1) if n else np.nan, "moe_pp": round(moe, 1) if n else np.nan,
                     "kids_per_hh_answered": round(ans_k.kids.mean(), 2) if len(ans_k) else np.nan,
                     "kids_per_hh_all": round(withk.kids.mean(), 2),
                     "urban_answered_pct": round(100 * (S.num(ans_k.K) == 1).mean(), 1) if len(ans_k) else np.nan,
                     "urban_all_pct": round(100 * (S.num(withk.K) == 1).mean(), 1)})
t = pd.DataFrame(rows)
nat = []
for y, g in t.groupby("year"):
    nat.append({"year": y, "coverage_national": round(100 * g.answered_among_with_children.sum() / g.with_children_roster.sum(), 1),
                "median_coverage": float(g.coverage_pct.median())})
t.to_csv(OUT / "child_impact.csv", index=False)
json.dump(nat, open(OUT / "child_impact_national.json", "w"))
pd.set_option("display.width", 250)
print(t.sort_values(["year", "coverage_pct"]).to_string(index=False))
print(nat)
