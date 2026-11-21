"""M4 batch window export: write one window CSV per configured lookback.

Reads the window parameters and the M3 selected-category daily table from
``config/config.yaml`` (via a small regex reader, so PyYAML is not required),
builds windows with ``make_windows``, and writes
``data/processed/windows_lookback{7,14,28}.csv``.

Run from the project root with the bundled Python (which provides pandas,
required by the ``demandlens`` package)::

    python scripts/build_windows.py
"""
from pathlib import Path
import re
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from demandlens.data.quality import read_daily, write_csv  # noqa: E402
from demandlens.features.windows import WINDOW_FIELDS, make_windows  # noqa: E402


def load_window_config(text):
    """Extract the window parameters from config.yaml without PyYAML.

    Every value is read from the file, never hardcoded: ``task.lookback_days``,
    ``task.horizon_days``, ``task.step_days``, ``paths.processed_dir`` and the
    primary M3 variant's ``output`` filename (the 10-category daily table).
    """
    task_match = re.search(r"\ntask:\n(.*?)(?=\n\w)", text, re.S)
    if not task_match:
        raise ValueError("config.yaml: missing 'task' section")
    task_block = task_match.group(1)

    def grab(pattern, source=text, flags=0):
        match = re.search(pattern, source, flags)
        if not match:
            raise ValueError(f"config.yaml: missing {pattern!r}")
        return match

    return {
        "lookback_days": [
            int(v) for v in re.findall(r"^\s*-\s*(\d+)\s*$", task_block, re.M)
        ],
        "horizon_days": int(grab(r"horizon_days:\s*(\d+)", task_block).group(1)),
        "step_days": int(grab(r"step_days:\s*(\d+)", task_block).group(1)),
        "processed_dir": grab(r"processed_dir:\s*(\S+)").group(1),
        "variant_output": grab(r"'10':\s*\n.*?output:\s*(\S+)", text, re.S).group(1),
    }


def main():
    root = PROJECT_ROOT.resolve()
    text = (root / "config" / "config.yaml").read_text(encoding="utf-8-sig")
    cfg = load_window_config(text)

    processed = root / cfg["processed_dir"]
    daily_path = processed / cfg["variant_output"]
    rows = read_daily(daily_path)

    horizon = cfg["horizon_days"]
    step = cfg["step_days"]
    summary = []
    for lookback in cfg["lookback_days"]:
        windows, meta = make_windows(rows, lookback, horizon, step)
        out_path = processed / f"windows_lookback{lookback}.csv"
        write_csv(out_path, windows, WINDOW_FIELDS)
        summary.append({
            "lookback": lookback,
            "windows": meta["n_windows"],
            "categories": meta["n_categories"],
            "input_span": f"{meta['input_start']}..{meta['input_end']}",
            "target_span": f"{meta['target_start']}..{meta['target_end']}",
            "file": out_path.relative_to(root).as_posix(),
        })

    print(f"daily rows: {len(rows)}")
    for item in summary:
        print(
            f"lookback={item['lookback']}: {item['windows']} windows "
            f"({item['categories']} categories) -> {item['file']}"
        )
    return summary


if __name__ == "__main__":
    main()
