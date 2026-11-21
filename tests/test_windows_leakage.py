"""Leakage and structural checks for M4 window construction.

Run from the project root with the bundled Python::

    PYTHONPATH=src python -m unittest tests.test_windows_leakage -v
"""
import math
import unittest
from datetime import date, timedelta

from demandlens.features.build_features import build_features
from demandlens.features.windows import detect_missing_dates, make_windows


def build_daily(category_ids, start, end, purchase_fn=None):
    """Build a synthetic daily table with one purchase per day by default."""
    rows = []
    day = start
    while day <= end:
        for cid in category_ids:
            value = purchase_fn(cid, day) if purchase_fn else 1
            rows.append({
                "date": day.isoformat(),
                "category_id": cid,
                "views": "1",
                "cart": "0",
                "purchase": str(value),
            })
        day += timedelta(days=1)
    return rows


class MakeWindowsLeakageTests(unittest.TestCase):
    def setUp(self):
        self.start = date(2019, 10, 1)
        self.end = date(2019, 11, 30)  # 61 days
        self.rows = build_daily(["1", "2"], self.start, self.end)

    def test_target_dates_are_after_input_dates(self):
        windows, _ = make_windows(self.rows, lookback=7, horizon=7, step=1)
        self.assertGreater(len(windows), 0)
        for w in windows:
            a = date.fromisoformat(w["input_start_date"])
            b = date.fromisoformat(w["input_end_date"])
            c = date.fromisoformat(w["target_start_date"])
            d = date.fromisoformat(w["target_end_date"])
            self.assertLessEqual(a, b)
            self.assertLess(b, c)
            self.assertLessEqual(c, d)
            # Target must start exactly one day after the input ends.
            self.assertEqual(c, b + timedelta(days=1))

    def test_window_lengths_match_lookback_and_horizon(self):
        windows, _ = make_windows(self.rows, lookback=14, horizon=7, step=1)
        for w in windows:
            a = date.fromisoformat(w["input_start_date"])
            b = date.fromisoformat(w["input_end_date"])
            c = date.fromisoformat(w["target_start_date"])
            d = date.fromisoformat(w["target_end_date"])
            self.assertEqual((b - a).days + 1, 14)
            self.assertEqual((d - c).days + 1, 7)

    def test_sliding_is_per_category_and_contiguous(self):
        windows, _ = make_windows(self.rows, lookback=7, horizon=7, step=1)
        by_cat = {}
        for w in windows:
            by_cat.setdefault(w["category_id"], []).append(w)
        self.assertEqual(set(by_cat), {"1", "2"})
        for cid, ws in by_cat.items():
            origins = [date.fromisoformat(w["input_end_date"]) for w in ws]
            self.assertEqual(origins, sorted(origins))
            self.assertEqual(len(origins), len(set(origins)))
            # step=1 on gap-free data must yield contiguous origins.
            for i in range(1, len(origins)):
                self.assertEqual((origins[i] - origins[i - 1]).days, 1)

    def test_y_sums_only_the_target_period(self):
        # purchase = day-of-month for category "1"; category "2" is all zero.
        rows = build_daily(
            ["1", "2"], self.start, self.end,
            purchase_fn=lambda cid, day: day.day if cid == "1" else 0,
        )
        windows, _ = make_windows(rows, lookback=7, horizon=7, step=1)
        w = next(
            x for x in windows
            if x["category_id"] == "1" and x["input_end_date"] == "2019-10-07"
        )
        # target 2019-10-08 .. 2019-10-14 -> 8+9+10+11+12+13+14 = 77
        self.assertEqual(w["y"], 77)

    def test_gap_overlapping_windows_are_excluded(self):
        rows = [
            r for r in self.rows
            if not (r["category_id"] == "2" and r["date"] == "2019-10-15")
        ]
        gaps = detect_missing_dates(rows)
        self.assertIn("2019-10-15", gaps["2"])
        windows, _ = make_windows(rows, lookback=7, horizon=7, step=1)
        for w in windows:
            if w["category_id"] != "2":
                continue
            a = date.fromisoformat(w["input_start_date"])
            d = date.fromisoformat(w["target_end_date"])
            span = set()
            day = a
            while day <= d:
                span.add(day.isoformat())
                day += timedelta(days=1)
            self.assertNotIn("2019-10-15", span)

    def test_step_controls_origin_stride(self):
        windows_step1, _ = make_windows(self.rows, lookback=7, horizon=7, step=1)
        windows_step7, _ = make_windows(self.rows, lookback=7, horizon=7, step=7)
        self.assertGreater(len(windows_step1), len(windows_step7))

    def test_window_count_matches_calendar_formula(self):
        for lookback, expected in ((7, 48), (14, 41), (28, 27)):
            windows, _ = make_windows(self.rows, lookback=lookback, horizon=7, step=1)
            self.assertEqual(len(windows), expected * 2, f"lookback={lookback}")

    def test_invalid_parameters_raise(self):
        with self.assertRaises(ValueError):
            make_windows(self.rows, lookback=0, horizon=7, step=1)
        with self.assertRaises(ValueError):
            make_windows(self.rows, lookback=7, horizon=7, step=0)
        with self.assertRaises(ValueError):
            make_windows(self.rows, lookback="7", horizon=7, step=1)


class BuildFeaturesLeakageTests(unittest.TestCase):
    def setUp(self):
        self.start = date(2019, 10, 1)
        self.end = date(2019, 11, 30)
        self.rows = build_daily(
            ["1", "2"], self.start, self.end,
            purchase_fn=lambda cid, day: day.day,
        )
        self.windows, _ = make_windows(self.rows, lookback=7, horizon=7, step=1)

    def _config(self, **kw):
        cfg = {"daily_rows": self.rows, "category_ids": ["1", "2"], "holidays": []}
        cfg.update(kw)
        return cfg

    def test_purchase_features_use_input_window_only(self):
        table = build_features(self.windows, self._config(), True, True)
        w = next(r for r in table if r["input_end_date"] == "2019-10-07")
        # input 10-01..10-07 -> purchase = 1+..+7 = 28; target 10-08..10-14 = 77.
        self.assertEqual(w["purchase_last7_total"], 28)
        self.assertEqual(w["purchase_prev7_total"], 0)      # pre-input, clipped
        self.assertEqual(w["purchase_last14_total"], 28)    # clipped to input
        self.assertAlmostEqual(w["purchase_last7_avg"], 4.0)
        self.assertEqual(w["y"], 77)                        # target, kept separate

    def test_features_ignore_target_period_events(self):
        rows_a = build_daily(["1"], self.start, self.end, purchase_fn=lambda c, d: d.day)
        rows_b = build_daily(
            ["1"], self.start, self.end,
            purchase_fn=lambda c, d: 999 if d >= date(2019, 10, 8) else d.day,
        )
        wa, _ = make_windows(rows_a, lookback=7, horizon=7, step=1)
        wb, _ = make_windows(rows_b, lookback=7, horizon=7, step=1)
        ta = build_features(wa, {"daily_rows": rows_a, "category_ids": ["1"], "holidays": []}, True, True)
        tb = build_features(wb, {"daily_rows": rows_b, "category_ids": ["1"], "holidays": []}, True, True)
        ra = next(r for r in ta if r["input_end_date"] == "2019-10-07")
        rb = next(r for r in tb if r["input_end_date"] == "2019-10-07")
        for key in ra:
            if key == "y":
                continue
            self.assertEqual(ra[key], rb[key], f"feature {key} leaked target data")
        self.assertNotEqual(ra["y"], rb["y"])

    def test_use_behavior_switch(self):
        full = build_features(self.windows, self._config(), True, False)
        reduced = build_features(self.windows, self._config(), False, False)
        self.assertIn("views_last7_total", full[0])
        self.assertNotIn("views_last7_total", reduced[0])
        self.assertIn("purchase_last7_total", reduced[0])   # always present
        self.assertIn("cal_target_weekday", reduced[0])     # always present

    def test_use_category_switch(self):
        with_cat = build_features(self.windows, self._config(), False, True)
        without_cat = build_features(self.windows, self._config(), False, False)
        self.assertIn("cat_is_1", with_cat[0])
        self.assertNotIn("cat_is_1", without_cat[0])
        w1 = next(r for r in with_cat if r["category_id"] == "1")
        w2 = next(r for r in with_cat if r["category_id"] == "2")
        self.assertEqual(w1["cat_is_1"], 1)
        self.assertEqual(w1["cat_is_2"], 0)
        self.assertEqual(w2["cat_is_1"], 0)
        self.assertEqual(w2["cat_is_2"], 1)

    def test_ratio_denominator_zero_is_safe(self):
        # build_daily keeps views="1" and cart="0", so prev7==0 and cart==0.
        # Neutral fallbacks: trend=0.0, wow_ratio=1.0, conversion ratios=0.0.
        table = build_features(self.windows, self._config(), True, True)
        w = next(r for r in table if r["input_end_date"] == "2019-10-07")
        self.assertEqual(w["purchase_trend"], 0.0)       # prev7 == 0
        self.assertEqual(w["views_trend"], 0.0)          # prev7 == 0
        self.assertEqual(w["cart_trend"], 0.0)           # prev7 == 0
        self.assertEqual(w["purchase_wow_ratio"], 1.0)   # prev7 == 0
        self.assertEqual(w["purchase_cart_ratio"], 0.0)  # cart == 0
        self.assertEqual(w["cart_view_ratio"], 0.0)      # cart == 0
        for key in ("cart_view_ratio", "purchase_cart_ratio", "purchase_wow_ratio",
                    "purchase_trend", "views_trend", "cart_trend"):
            self.assertTrue(math.isfinite(float(w[key])), key)


if __name__ == "__main__":
    unittest.main()
