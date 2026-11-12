import os
import sys

TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOLS)

import unittest

from essay_lib import Pair, RankTable, apply_pairs


def pair(p="主", v="異", t="ortho", scope="char"):
    return Pair(p, v, scope, t, "test", "")


class TestApplyPairs(unittest.TestCase):
    def test_char_variant_is_banded(self):
        essay = {"主": 5000.0, "異": 4000.0, "x": 10.0}
        out, _ = apply_pairs(essay, [pair()], variant_cap=1000, rare_cap=100)
        self.assertEqual(out["主"], 5000.0)
        self.assertEqual(out["異"], 1000.0)

    def test_char_variant_stays_below_preferred(self):
        essay = {"主": 50.0, "異": 40.0, "x": 10.0}
        out, _ = apply_pairs(essay, [pair()], variant_cap=1000, rare_cap=100)
        self.assertLess(out["異"], out["主"])

    def test_char_variant_is_added(self):
        essay = {"主": 5000.0, "a": 50.0}
        out, _ = apply_pairs(essay, [pair("主", "缺")], variant_cap=1000)
        self.assertEqual(out["缺"], 1000.0)

    def test_common_floor_is_above_variant_band(self):
        essay = {"主": 5000.0, "異": 4000.0, "低": 50.0}
        out, _ = apply_pairs(
            essay,
            [pair("主", "異")],
            common_chars={"主", "低"},
            variant_cap=1000,
            rare_cap=100,
        )
        self.assertEqual(out["異"], 1000.0)
        self.assertEqual(out["低"], 1001.0)

    def test_rare_variant_uses_rare_cap(self):
        essay = {"主": 5000.0, "罕": 4000.0, "x": 10.0}
        out, _ = apply_pairs(
            essay, [pair("主", "罕")], rare_chars={"罕"}, rare_cap=100
        )
        self.assertEqual(out["罕"], 100.0)

    def test_rare_char_is_capped(self):
        essay = {"主": 5000.0, "罕": 5000.0}
        out, _ = apply_pairs(
            essay, [], rare_chars={"罕"}, rare_cap=100
        )
        self.assertEqual(out["罕"], 100.0)

    def test_phrase_variant_is_zeroed(self):
        essay = {"為了": 5000.0, "爲了": 3000.0}
        pair_ = Pair("為了", "爲了", "phrase", "ortho", "test", "")
        out, report = apply_pairs(essay, [pair_])
        self.assertEqual(out["為了"], 5000.0)
        self.assertEqual(out["爲了"], 0.0)
        self.assertEqual(report[0]["action"], "zeroed")

    def test_regional_phrase_stays_below_preferred(self):
        essay = {f"k{i:02d}": float(100 - i) for i in range(80)}
        essay.update({"軟體": 90.0, "軟件": 40.0})
        pair_ = Pair("軟體", "軟件", "phrase", "regional", "test", "")
        out, _ = apply_pairs(essay, [pair_], phrase_gap_pages=20)
        self.assertLess(out["軟件"], out["軟體"])
        self.assertGreater(out["軟件"], 0.0)

    def test_reading_keeps_both_weights(self):
        essay = {"妳": 2085.0, "嬭": 103.0, "x": 10.0}
        out, _ = apply_pairs(essay, [pair("妳", "嬭", "reading")])
        self.assertEqual(out["妳"], 2085.0)
        self.assertEqual(out["嬭"], 103.0)

    def test_reading_gives_floor_only_when_zero(self):
        essay = {"妳": 2085.0, "嬭": 0.0, "x": 10.0}
        out, _ = apply_pairs(essay, [pair("妳", "嬭", "reading")])
        self.assertGreater(out["嬭"], 0)

    def test_both_missing_is_skipped(self):
        out, report = apply_pairs({}, [pair("甲", "乙")])
        self.assertEqual(out, {})
        self.assertEqual(report[0]["action"], "skip")

    def test_chain_conflict_is_skipped(self):
        essay = {"A": 100.0, "B": 50.0, "C": 10.0, "x": 1.0}
        pairs = [pair("A", "B"), pair("B", "C")]
        out, report = apply_pairs(essay, pairs)
        self.assertEqual(out["B"], 50.0)
        self.assertEqual(sorted(r["action"] for r in report), ["conflict", "conflict"])

    def test_preferred_takes_max_across_variants(self):
        essay = {"A": 10.0, "B": 100.0, "C": 5.0, "x": 1.0}
        pairs = [pair("A", "B"), pair("A", "C")]
        out, _ = apply_pairs(essay, pairs)
        self.assertEqual(out["A"], 100.0)

    def test_idempotent(self):
        essay = {"主": 5000.0, "異": 4000.0, "x": 10.0}
        once, _ = apply_pairs(essay, [pair()])
        twice, _ = apply_pairs(once, [pair()])
        self.assertEqual(once, twice)


if __name__ == "__main__":
    unittest.main()
