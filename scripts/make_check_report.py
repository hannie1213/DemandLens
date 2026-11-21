#!/usr/bin/env python3
"""Generate the M2 aggregation check report reports/aggregation_check_report.md.

Reads reports/tables/aggregation_check.csv, each month's interim daily aggregate, and the
merged processed table, then produces a check report with real numbers (including the
zero-purchase ratio and other reference figures M3 will use).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))


def fmt(n) -> str:
    return f"{int(n):,}" if pd.notna(n) else "—"


def main() -> int:
    check_path = PROJECT_ROOT / "reports" / "tables" / "aggregation_check.csv"
    if not check_path.exists():
        print("aggregation_check.csv not found; run scripts/build_daily.py first")
        return 1
    check = pd.read_csv(check_path)

    lines: list[str] = []
    lines.append("# Aggregation Check Report (M2 deliverable)\n")
    lines.append(f"Generated at: {pd.Timestamp.now().isoformat(timespec='seconds')}\n")
    lines.append("Data contract per assignment 3.6; per-item figures in `reports/tables/aggregation_check.csv`. "
                 "This report only interprets the numbers; quality review, category selection, and calendar "
                 "gap-filling are M3's responsibility.\n")

    n_fail = int((check["status"] == "FAIL").sum())
    n_ok = int((check["status"] == "OK").sum())
    lines.append(f"## Conclusion\n\n- Consistency checks **{n_ok} OK / {n_fail} FAIL**"
                 + ("; totals per event type are all consistent before vs after aggregation (D2 acceptance passed)." if n_fail == 0
                    else "; inconsistencies exist and must be resolved before handoff."))
    lines.append("\n## Dataset overview\n")

    def month_key(m):
        import datetime
        return datetime.datetime.strptime(m, "%Y-%b")

    overall = []
    for ds in check["dataset"].unique():
        sub = check[check["dataset"] == ds]
        months = sorted((m for m in sub["month"].unique() if m != "ALL"), key=month_key)
        kept = {e: int(sub[sub["check"] == f"count:{e}"]["raw_value"].sum())
                for e in ("view", "cart", "purchase")}
        aggregated_kept = sum(int(sub[(sub["month"] == m) & (sub["check"] == "aggregatable_rows")]["raw_value"].iloc[0]) for m in months)
        removed = int(sub[sub["check"] == "excluded:other_event_types"]["raw_value"].sum())
        raw_rows = sum(
            int(sub[(sub["month"] == m) & (sub["check"] == c)]["raw_value"].sum())
            for m in months
            for c in ("aggregatable_rows", "excluded:valid_but_other_event",
                      "invalid:date_rows", "invalid:category_rows"))
        files = sum(int(sub[(sub["month"] == m) & (sub["check"] == "file:size_bytes")]["raw_value"].sum()) for m in months)
        overall.append((ds, len(months), months[0], months[-1], raw_rows, kept, removed, files))
        lines.append(f"- **{ds}**: {len(months)} months ({months[0]} .. {months[-1]}), "
                     f"raw events {fmt(raw_rows)} (of which aggregated {fmt(aggregated_kept)}; out-of-contract events {fmt(removed)}), "
                     f"raw files total {files / 2**30:.2f} GiB")
    lines.append("")

    lines.append("## Monthly detail\n")
    lines.append("| Dataset | Month | view | cart | purchase | Categories | Dates | Zero-purchase row ratio |")
    lines.append("|---|---|---:|---:|---:|---:|---:|---:|")
    for ds in check["dataset"].unique():
        sub = check[check["dataset"] == ds]
        for m in sorted((x for x in sub["month"].unique() if x != "ALL"), key=month_key):
            row = lambda c: int(sub[(sub["month"] == m) & (sub["check"] == c)]["raw_value"].iloc[0])
            cats, dates = row("coverage:categories"), row("coverage:dates")
            interim = PROJECT_ROOT / "data" / "interim"
            daily_path = interim / f"daily_{ds}_{m}.csv"
            zero_ratio = "—"
            if daily_path.exists():
                d = pd.read_csv(daily_path, usecols=["purchase"])
                zero_ratio = f"{(d['purchase'] == 0).mean() * 100:.1f}%"
            lines.append(f"| {ds} | {m} | {fmt(row('count:view'))} | {fmt(row('count:cart'))} "
                         f"| {fmt(row('count:purchase'))} | {cats} | {dates} | {zero_ratio} |")
    lines.append("")

    lines.append("## Quality reference figures (for M3 review; not a substitute for the quality report)\n")
    for ds in check["dataset"].unique():
        sub = check[check["dataset"] == ds]
        s = lambda c: int(sub[sub["check"] == c]["raw_value"].sum())
        lines.append(f"- **{ds}**: invalid date rows {fmt(s('invalid:date_rows'))}; "
                     f"invalid category rows {fmt(s('invalid:category_rows'))}; "
                     f"out-of-contract events {fmt(s('excluded:other_event_types'))}; "
                     f"estimated duplicate contract-4-col rows {fmt(s('duplicate:same_contract_cols_est'))}; "
                     f"category code conflicts (within-month {fmt(s('consistency:category_code_conflicts'))} / "
                     f"cross-month {fmt(s('cross_month:category_code_conflicts'))})")
    lines.append("")
    lines.append("## Limitations (consistent with assignment 3.7)\n\n"
                 "- 'Contract-4-col identical rows' is a suspected-duplicate signal (no user_id; normal same-second "
                 "same-product events also count), not a true duplicate; cross-chunk duplicates are not covered, and "
                 "full dedup is too costly, so it is documented as a limitation.\n"
                 "- The zero-purchase row ratio is the ratio among recorded rows; unrecorded (category, date) pairs "
                 "are not in the table and must not be treated as zero purchase; M3 must judge collection gaps.\n"
                 "- The cosmetics shop has a high category_code missing ratio; readable category names are auxiliary only.\n"
                 "- Event count != order count != units sold; the purchase event is a proxy for demand.\n")

    out = PROJECT_ROOT / "reports" / "aggregation_check_report.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print("written:", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
