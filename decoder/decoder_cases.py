"""Numbers for the two findings the decoder adds, computed from the records.

1. Kyzylorda, D-008 education: children aged 7-10 coded 7 'не достигнут никакой уровень' instead of 1 'дошкольное'.
2. Almaty oblast, T-001: employees of individuals (status 2) moved from employer-type code 2 to code 5 in 2024, and their
   contract code moved from written to oral in the same year. Outside Almaty oblast, code 5 itself changed: its share of
   oral agreements rose from 17% (2023) to 84% (2024), so the code seems to have been redefined in 2024.

    python decoder/decoder_cases.py DATA_DIR out/
"""
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "engine"))
import statquo as S  # noqa: E402

D, OUT = sys.argv[1], Path(sys.argv[2])
res = {"kyzylorda": {}, "almaty": {}}
for y in (2023, 2024):
    r = S.read(D, f"d008/{y}/kontr_k.csv")
    age, u = y - S.num(r.GOD_ROJD), r.UROV.str.lstrip("0")
    m = (age >= 7) & (age <= 10)
    share7 = (u[m] == "7").groupby(r.TE[m]).mean().mul(100)
    res["kyzylorda"][y] = {"kyzylorda_pct_code7": round(float(share7["43"]), 1),
                           "other_regions_max": round(float(share7.drop("43").max()), 1),
                           "other_regions_median": round(float(share7.drop("43").median()), 1),
                           "children_7_10_kyzylorda": int(m[r.TE == "43"].sum())}
    t = S.read(D, f"t001/{y}/baza.csv")
    st, pk, tr = t.ORB_STATUS.str.lstrip("0"), t.ORB_PKHDHL.str.lstrip("0"), t.ORB_TRDDOG.str.lstrip("0")
    s2 = st == "2"
    al = t.TE == "19"
    res["almaty"][y] = {"status2_code2": int((al & s2 & (pk == "2")).sum()), "status2_code5": int((al & s2 & (pk == "5")).sum()),
                        "oral_among_code5_national_pct": round(float(100 * (tr[pk == "5"] == "2").mean()), 1),
                        "oral_among_code2_national_pct": round(float(100 * (tr[(pk == "2") & ~al] == "2").mean()), 1),
                        "no_contract_status2_almaty_pct": round(float(100 * (tr[al & s2] == "2").mean()), 1),
                        "no_contract_status2_rest_pct": round(float(100 * (tr[~al & s2] == "2").mean()), 1),
                        "code5_outside_almaty_n": int(((pk == "5") & ~al).sum()),
                        "oral_among_code5_outside_almaty_pct": round(float(100 * (tr[(pk == "5") & ~al] == "2").mean()), 1)}
json.dump(res, open(OUT / "decoder_cases.json", "w"), indent=1)
print(json.dumps(res, indent=1))
