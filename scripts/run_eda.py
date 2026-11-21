"""M4 EDA — one-file runner (development-period-only exploration).

Usage (from the demandlens project root):
    python scripts/run_eda.py

Reads config/config.yaml for the primary (multi_store) development window and
the 10-category daily table path, then writes 5 PNG figures under
reports/figures/.

Scope (spec "EDA, windows & features"):
  * uses ONLY the development window (no validation/test leakage);
  * five figures;
  * dependency-light: standard-library CSV + numpy + matplotlib
    (mirrors src/demandlens/data/quality.py, which is stdlib-only).

Figures written (default reports/figures/):
  eda_category_concentration.png  — category concentration
  eda_zero_purchase.png           — zero-purchase ratio
  eda_weekday.png                 — weekday effect
  eda_trend.png                   — trend
  eda_funnel.png                  — view -> cart -> purchase funnel
"""
from __future__ import annotations

import csv
import re
from collections import defaultdict
from datetime import date
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless PNG rendering, must precede pyplot import
import matplotlib.pyplot as plt
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]

FIELDS = ["date", "category_id", "category_code", "views", "cart", "purchase"]
EVENTS = FIELDS[3:]
WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


# --------------------------------------------------------------------------- #
# Data loading (stdlib csv, mirrors quality.read_daily)
# --------------------------------------------------------------------------- #
def read_daily(path) -> list[dict]:
    with Path(path).open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        missing = set(FIELDS) - set(reader.fieldnames or [])
        if missing:
            raise ValueError("Missing daily columns: " + ",".join(sorted(missing)))
        return list(reader)


def to_numeric(rows: list[dict]) -> list[dict]:
    out = []
    for r in rows:
        out.append(
            {
                "date": date.fromisoformat(r["date"]),
                "category_id": r["category_id"],
                "category_code": r["category_code"],
                "views": int(r["views"]),
                "cart": int(r["cart"]),
                "purchase": int(r["purchase"]),
            }
        )
    return out


def filter_dev(rows: list[dict], dev_start: str, dev_end: str) -> list[dict]:
    a, b = date.fromisoformat(dev_start), date.fromisoformat(dev_end)
    return [r for r in rows if a <= r["date"] <= b]


def category_info(rows: list[dict]) -> dict:
    """Per-category totals + day/zero-day counts."""
    info = defaultdict(
        lambda: {"code": "", "views": 0, "cart": 0, "purchase": 0, "days": 0, "zero": 0}
    )
    for r in rows:
        c = info[r["category_id"]]
        c["code"] = r["category_code"]
        c["views"] += r["views"]
        c["cart"] += r["cart"]
        c["purchase"] += r["purchase"]
        c["days"] += 1
        if r["purchase"] == 0:
            c["zero"] += 1
    return info


def short_label(cid: str, code: str) -> str:
    """Short label: last code token, or a compact id when the code is empty."""
    return code.split(".")[-1] if code else f"id:{cid[-6:]}"


# --------------------------------------------------------------------------- #
# Plot 1 — category concentration
# --------------------------------------------------------------------------- #
def plot_category_concentration(rows: list[dict], out_dir: Path) -> None:
    info = category_info(rows)
    items = sorted(info.items(), key=lambda kv: kv[1]["purchase"], reverse=True)
    labels = [short_label(cid, v["code"]) for cid, v in items]
    purchases = np.array([v["purchase"] for _, v in items], dtype=float)
    total = purchases.sum()
    shares = purchases / total * 100.0
    cum = np.cumsum(shares)

    fig, ax1 = plt.subplots(figsize=(9, 5))
    x = np.arange(len(items))
    ax1.bar(x, purchases, color="#4C72B0")
    ax1.set_xticks(x)
    ax1.set_xticklabels(labels, rotation=45, ha="right")
    ax1.set_ylabel("Total purchase events (dev period)")
    ax1.set_title("Category concentration (dev-period purchases)")

    ax2 = ax1.twinx()
    ax2.plot(x, cum, color="#C44E52", marker="o", label="Cumulative share")
    ax2.set_ylabel("Cumulative share %")
    ax2.set_ylim(0, 105)
    ax2.axhline(100, color="grey", lw=0.6, ls="--")

    for xi, (p, s) in enumerate(zip(purchases, shares)):
        if s >= 4.0:
            ax1.annotate(
                f"{s:.1f}%", (xi, p * 0.55),
                ha="center", va="center", color="white",
                fontsize=8, fontweight="bold",
            )
        else:
            ax1.annotate(f"{s:.1f}%", (xi, p), ha="center", va="bottom", fontsize=8)

    fig.legend(loc="upper right")
    fig.tight_layout()
    fig.savefig(out_dir / "eda_category_concentration.png", dpi=130, bbox_inches="tight")


# --------------------------------------------------------------------------- #
# Plot 2 — zero-purchase ratio
# --------------------------------------------------------------------------- #
def plot_zero_purchase(rows: list[dict], out_dir: Path) -> None:
    info = category_info(rows)
    items = sorted(
        info.items(), key=lambda kv: kv[1]["zero"] / kv[1]["days"], reverse=True
    )
    labels = [short_label(cid, v["code"]) for cid, v in items]
    ratios = [100.0 * v["zero"] / v["days"] for _, v in items]

    fig, ax = plt.subplots(figsize=(9, 5))
    x = np.arange(len(items))
    ax.bar(x, ratios, color="#55A868")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=45, ha="right")
    ax.set_ylabel("Zero-purchase days share %")
    ax.set_title("Zero-purchase ratio (dev period, by category)")
    ax.set_ylim(0, 20)
    for xi, rv in enumerate(ratios):
        ax.annotate(f"{rv:.1f}%", (xi, rv), ha="center", va="bottom", fontsize=8)
    fig.tight_layout()
    fig.savefig(out_dir / "eda_zero_purchase.png", dpi=130, bbox_inches="tight")


# --------------------------------------------------------------------------- #
# Plot 3 — weekday effect
# --------------------------------------------------------------------------- #
def plot_weekday(rows: list[dict], out_dir: Path) -> None:
    per = {i: {"views": 0, "cart": 0, "purchase": 0} for i in range(7)}
    days = {i: set() for i in range(7)}
    for r in rows:
        w = r["date"].weekday()
        per[w]["views"] += r["views"]
        per[w]["cart"] += r["cart"]
        per[w]["purchase"] += r["purchase"]
        days[w].add(r["date"])

    # Mean daily events (not totals), so weekdays with unequal day counts
    # (e.g. 5 Tuesdays vs 4 Mondays in a 31-day window) stay comparable.
    n_days = np.array([len(days[i]) for i in range(7)], dtype=float)
    x = np.arange(7)
    purchase = np.array([per[i]["purchase"] for i in range(7)], dtype=float) / n_days
    cart = np.array([per[i]["cart"] for i in range(7)], dtype=float) / n_days

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(x, purchase, marker="o", color="#C44E52", label="Purchase")
    ax.plot(x, cart, marker="s", color="#4C72B0", label="Cart")
    ax.set_xticks(x)
    ax.set_xticklabels(WEEKDAYS)
    ax.set_ylabel("Mean daily events (dev period)")
    ax.set_title("Weekday effect (dev period)")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_dir / "eda_weekday.png", dpi=130, bbox_inches="tight")


# --------------------------------------------------------------------------- #
# Plot 4 — trend
# --------------------------------------------------------------------------- #
def plot_trend(rows: list[dict], out_dir: Path) -> None:
    per = defaultdict(lambda: {"views": 0, "cart": 0, "purchase": 0})
    for r in rows:
        per[r["date"]]["views"] += r["views"]
        per[r["date"]]["cart"] += r["cart"]
        per[r["date"]]["purchase"] += r["purchase"]

    dates = sorted(per)
    purchase = np.array([per[d]["purchase"] for d in dates], dtype=float)
    x = np.arange(len(dates))

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(x, purchase, marker=".", color="#4C72B0")
    ax.set_xticks(x[::5])
    ax.set_xticklabels([d.isoformat()[5:] for d in dates[::5]], rotation=45)
    ax.set_ylabel("Total purchase events (selected categories)")
    ax.set_title("Trend (dev-period daily purchases, selected categories)")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_dir / "eda_trend.png", dpi=130, bbox_inches="tight")


# --------------------------------------------------------------------------- #
# Plot 5 — view -> cart -> purchase funnel
# --------------------------------------------------------------------------- #
def plot_funnel(rows: list[dict], out_dir: Path) -> None:
    views = sum(r["views"] for r in rows)
    cart = sum(r["cart"] for r in rows)
    purchase = sum(r["purchase"] for r in rows)
    stages = ["View", "Cart", "Purchase"]
    values = [views, cart, purchase]

    fig, ax = plt.subplots(figsize=(8, 5))
    y = np.arange(len(stages))[::-1]  # top = view
    ax.barh(y, values, color=["#4C72B0", "#55A868", "#C44E52"], height=0.55)
    ax.set_yticks(y)
    ax.set_yticklabels(stages)
    ax.set_xscale("log")
    ax.set_xlabel("Total events (dev period, selected categories, log axis)")
    ax.set_title("View -> Cart -> Purchase funnel (dev period)")
    stage_ratios = [
        "",
        f" ({cart / views * 100:.1f}% of View)",
        f" ({purchase / cart * 100:.1f}% of Cart / {purchase / views * 100:.1f}% of View)",
    ]
    for yi, v, rt in zip(y, values, stage_ratios):
        ax.annotate(f"{v:,}{rt}", (v, yi), va="center", ha="left", fontsize=9)
    fig.tight_layout()
    fig.savefig(out_dir / "eda_funnel.png", dpi=130, bbox_inches="tight")


# --------------------------------------------------------------------------- #
# Orchestrator
# --------------------------------------------------------------------------- #
def run_all(csv_path, dev_start: str, dev_end: str, out_dir) -> None:
    """Run all five figures."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = to_numeric(read_daily(csv_path))
    rows = filter_dev(rows, dev_start, dev_end)
    if not rows:
        raise ValueError(f"No rows in development window {dev_start}..{dev_end}")

    n_cats = len({r["category_id"] for r in rows})
    n_days = len({r["date"] for r in rows})
    print(
        f"[eda] rows={len(rows)} categories={n_cats} "
        f"days={n_days} window={dev_start}..{dev_end}"
    )

    plot_category_concentration(rows, out_dir)
    plot_zero_purchase(rows, out_dir)
    plot_weekday(rows, out_dir)
    plot_trend(rows, out_dir)
    plot_funnel(rows, out_dir)
    plt.close("all")


# --------------------------------------------------------------------------- #
# Config reading (dev window + daily-table path), with a PyYAML-free fallback
# --------------------------------------------------------------------------- #
def load_config(path: Path) -> dict:
    text = Path(path).read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore

        return yaml.safe_load(text)
    except ImportError:
        pass

    def first(pattern: str):
        m = re.search(pattern, text, re.M)
        return m.group(1) if m else None

    # First occurrence in the file belongs to the primary multi_store block
    # (the cosmetics block appears later in config.yaml).
    return {
        "paths": {"processed_dir": "data/processed"},
        "m3": {
            "sources": {
                "multi_store": {
                    "development_start": first(r"development_start:\s*'([^']+)'"),
                    "development_end": first(r"development_end:\s*'([^']+)'"),
                    "variants": {"10": {"output": "daily_category.csv"}},
                }
            }
        },
    }


def resolve(cfg: dict):
    src = cfg["m3"]["sources"]["multi_store"]
    dev_start = src["development_start"]
    dev_end = src["development_end"]
    csv_name = src["variants"]["10"]["output"]
    processed = cfg["paths"]["processed_dir"]
    return dev_start, dev_end, PROJECT_ROOT / processed / csv_name


def main() -> None:
    cfg = load_config(PROJECT_ROOT / "config" / "config.yaml")
    dev_start, dev_end, csv_path = resolve(cfg)
    out_dir = PROJECT_ROOT / "reports" / "figures"

    run_all(csv_path, dev_start, dev_end, out_dir)
    print(f"[figures written to] {out_dir}")


if __name__ == "__main__":
    main()
