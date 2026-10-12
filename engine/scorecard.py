"""Regional comparability scorecard.

Collects every region flag from the rule checks, the cross-form comparisons, the region-vs-rest model and the
decoder's code-shift detector into one table of issues
(one row per form × rule × year × region), labels each as
- "holds in synthetic data": the violation is forced by the answer shares, or does not depend on a link
  between columns, or comes from comparing two forms' regional shares; or
- "check on real records": it could be produced by the synthetic generator breaking links between columns;
and writes a region × form matrix for the scorecard view.

    python engine/scorecard.py out/
"""
import sys
from pathlib import Path

import pandas as pd

import statquo as S

LABEL = {"forced by the answer shares": "holds in synthetic data", "not conditional": "holds in synthetic data",
         "partly forced": "check on real records", "could be broken links in the synthetic data": "check on real records",
         "region-level code profile": "holds in synthetic data", "small group": "check on real records",
         "section coverage; could be a real difference": "check on real records"}


def build(out):
    out = Path(out)
    issues, checks = [], []
    for form in ("D002", "D004", "D006", "D008"):
        res = pd.read_csv(out / f"{form}_results.csv")
        checks.append(res.groupby("year").apply(lambda g: g[["rule_id", "column"]].drop_duplicates().shape[0])
                      .rename("checks").reset_index().assign(form=form))
        f = pd.read_csv(out / f"{form}_region_flags.csv")
        if f.empty:
            continue
        f = f[f["flag"]]
        g = f.groupby(["rule_id", "type", "year", "region"]).agg(
            columns=("column", "nunique"), example_column=("column", "first"),
            records=("applicable", "max"), rate_region=("rate_region", "median"),
            rate_rest=("rate_rest", "median"), excess=("excess", "sum"),
            synthesis=("synthesis", lambda s: s.mode().iloc[0])).reset_index()
        g.insert(0, "form", form)
        g["evidence"] = "rule check"
        issues.append(g)
    xf = pd.read_csv(out / "D002_cross_form_flags.csv")
    # the rent bound (D002-x-D006-owners-rent) is broken by most regions: a national coding rule, reported as case C2
    xf = xf[xf["flag"] & (xf["rule_id"] == "D002-x-D008-children")]
    if len(xf):
        issues.append(pd.DataFrame({
            "form": "D002×D008", "rule_id": xf["rule_id"], "type": "cross_form", "year": xf["year"],
            "region": xf["region"], "columns": 1, "example_column": "GR40", "records": None,
            "rate_region": xf["this_share"], "rate_rest": xf["other_share"], "excess": None,
            "synthesis": "not conditional", "evidence": "regional shares, two forms"}))
    # code shifts (decoder): a region's code behaves like a different code in the rest of the country
    cs_path = out / "decoder_code_shift.csv"
    if cs_path.exists():
        cs = pd.read_csv(cs_path)
        cs = cs[cs["flag"]]
        if len(cs):
            issues.append(pd.DataFrame({
                "form": cs["form"].str.replace("-", ""), "rule_id": "code shift: " + cs["column"] + " " + cs["code"].astype(str)
                + " → " + cs["behaves_like"].astype(str), "type": "code shift", "year": cs["year"], "region": cs["region"],
                "columns": 1, "example_column": cs["column"], "records": cs["n"],
                "rate_region": (100 * cs["distance_to_match"]).round(1), "rate_rest": (100 * cs["distance_to_same_code"]).round(1),
                "excess": None,
                # a code profile needs enough records; small groups wait for the real records
                "synthesis": ["region-level code profile" if n >= 90 else "small group" for n in cs["n"]],
                "evidence": "code shift (decoder)"}))
    sw_path = out / "compare_region_sweep.csv"
    if sw_path.exists():
        sw = pd.read_csv(sw_path)
        lead = sw[(sw["variable"] != "K") & (sw["robust_z"] >= 20) & (sw["n"] >= 100)
                  & ((sw["share_region"] - sw["share_rest_same"]) >= 30)].drop_duplicates(["form", "year", "variable", "region"])
        if len(lead):
            g = lead.groupby(["form", "year", "region"]).agg(
                columns=("variable", "nunique"), example_column=("variable", lambda v: ", ".join(list(v)[:3])),
                rate_region=("share_region", "median"), rate_rest=("share_rest_same", "median")).reset_index()
            issues.append(g.assign(rule_id="ML: region vs rest", type="answer shares", records=None, excess=None,
                                   synthesis="not conditional", evidence="region vs rest (ML)"))
    # D-004 sections a region leaves almost empty (analysis/finance_impact.py): below half the other regions'
    # median in 3 of 4 years. Fewer loans can be real, so these wait for the real records.
    cov_path = out / "finance_section_coverage.csv"
    if cov_path.exists():
        cv = pd.read_csv(cov_path, dtype={"te": str})
        cv = cv[cv["flag"] & cv["year"].isin([2023, 2024])]
        if len(cv):
            issues.append(pd.DataFrame({
                "form": "D004", "rule_id": "section coverage: " + cv["section"] + " (" + cv["label"] + ")",
                "type": "section coverage", "year": cv["year"], "region": cv["region"], "columns": 1,
                "example_column": cv["section"], "records": None, "rate_region": cv["households_pct"],
                "rate_rest": cv["median_others"], "excess": None,
                "synthesis": "section coverage; could be a real difference", "evidence": "section coverage (finance case)"}))
    iss = pd.concat(issues, ignore_index=True)
    iss["status"] = iss["synthesis"].map(LABEL)
    # a check that compares two tables record by record depends on links the synthetic data may not keep
    iss.loc[iss["rule_id"].str.contains("same-person"), ["synthesis", "status"]] = \
        ["links between the two halves of the form", "check on real records"]
    iss = iss.sort_values(["status", "form", "year", "rule_id", "region"])
    iss.to_csv(out / "scorecard_issues.csv", index=False)

    mat = (iss.assign(col=iss["form"].str.slice(0, 4) + " " + iss["year"].astype(str))
           .pivot_table(index="region", columns=["col", "status"], values="rule_id", aggfunc="nunique", fill_value=0))
    mat = mat.reindex(sorted(S.REGION.values()), fill_value=0)
    mat.to_csv(out / "scorecard_matrix.csv")
    pd.concat(checks).to_csv(out / "scorecard_checks.csv", index=False)
    return iss, mat


if __name__ == "__main__":
    iss, mat = build(sys.argv[1] if len(sys.argv) > 1 else "out")
    pd.set_option("display.width", 250, "display.max_rows", 200)
    print(iss[["status", "form", "year", "region", "rule_id", "columns", "rate_region", "rate_rest"]].to_string(index=False))
