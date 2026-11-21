"""M4 batch feature export: write one window-feature CSV per configured lookback.

Reads the window parameters, the M3 selected-category daily table, the category
list and the holiday calendar from ``config/config.yaml`` (regex reader, no
PyYAML), builds windows with ``make_windows`` and features with
``build_features``, and writes ``data/processed/windows_lookback{7,14,28}.csv``
(metadata columns + feature columns + y).

The two ablation switches are exposed on ``build_features`` itself (for M6);
this script emits the default full feature set (both switches ``True``).

Run from the project root with the bundled Python (which provides pandas)::

    python scripts/build_features.py
"""
from pathlib import Path
import re
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from demandlens.data.quality import read_daily, write_csv  # noqa: E402
from demandlens.features.windows import make_windows  # noqa: E402
from demandlens.features.build_features import (  # noqa: E402
    WINDOW_META_FIELDS,
    build_features,
    feature_columns,
)


def _grab(pattern, source, flags=0):
    match = re.search(pattern, source, flags)
    if not match:
        raise ValueError(f"config.yaml: missing {pattern!r}")
    return match


def load_feature_config(text):
    """Extract window + feature parameters from config.yaml without PyYAML.

    Every value is read from the file, never hardcoded: ``task.lookback_days``,
    ``task.horizon_days``, ``task.step_days``, ``paths.processed_dir``, the
    primary M3 variant's ``output`` filename and ``selected_ids`` category list,
    and ``calendar.holidays``.
    """
    task_block = _grab(r"\ntask:\n(.*?)(?=\n\w)", text, re.S).group(1)
    v10_block = _grab(r"'10':\s*\n(.*?)\n\s*'20':", text, re.S).group(1)
    holiday_block = _grab(r"\ncalendar:\n(.*?)(?=\n\w)", text, re.S).group(1)

    return {
        "lookback_days": [
            int(v) for v in re.findall(r"^\s*-\s*(\d+)\s*$", task_block, re.M)
        ],
        "horizon_days": int(_grab(r"horizon_days:\s*(\d+)", task_block).group(1)),
        "step_days": int(_grab(r"step_days:\s*(\d+)", task_block).group(1)),
        "processed_dir": _grab(r"processed_dir:\s*(\S+)", text).group(1),
        "variant_output": _grab(r"'10':\s*\n.*?output:\s*(\S+)", text, re.S).group(1),
        "category_ids": re.findall(r"-\s*'(\d+)'", v10_block),
        "holidays": re.findall(r"-\s*'(\d{4}-\d{2}-\d{2})'", holiday_block),
    }


def main():
    root = PROJECT_ROOT.resolve()
    text = (root / "config" / "config.yaml").read_text(encoding="utf-8-sig")
    cfg = load_feature_config(text)

    processed = root / cfg["processed_dir"]
    daily_rows = read_daily(processed / cfg["variant_output"])

    use_behavior = True
    use_category = True
    config = {
        "daily_rows": daily_rows,
        "category_ids": cfg["category_ids"],
        "holidays": cfg["holidays"],
    }

    summary = []
    for lookback in cfg["lookback_days"]:
        windows, _ = make_windows(daily_rows, lookback, cfg["horizon_days"], cfg["step_days"])
        table = build_features(windows, config, use_behavior, use_category)
        feat_cols = feature_columns(config, use_behavior, use_category)
        cols = WINDOW_META_FIELDS + feat_cols + ["y"]
        out_path = processed / f"windows_lookback{lookback}.csv"
        write_csv(out_path, table, cols)
        summary.append((lookback, len(table), len(feat_cols), out_path.relative_to(root).as_posix()))

    print(f"daily rows: {len(daily_rows)}")
    print(f"use_behavior={use_behavior} use_category={use_category}")
    for lookback, n_windows, n_features, rel in summary:
        print(f"lookback={lookback}: {n_windows} windows, {n_features} features -> {rel}")
    return summary


if __name__ == "__main__":
    main()
