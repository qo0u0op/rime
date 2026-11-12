import unittest

from essay_lib import Pair, apply_pairs


def pair(p="主", v="異", t="ortho", scope="char"):
    return Pair(p, v, scope, t, "test", "")


class TestApplyPairs(unittest.TestCase):
    def test_ortho_gap_is_fifteen_ranks(self):
        essay = {f"k{i:02d}": float(100 - i) for i in range(40)}
        essay["主"] = 90.0
        essay["異"] = 40.0
        out, _ = apply_pairs(essay, [pair()], page_size=5)
        self.assertEqual(out["主"], 90.0)
        from essay_lib import RankTable

        table = RankTable(list(essay.values()))
        self.assertEqual(table.rank(out["異"]) - table.rank(90.0), 15)

    def test_ortho_adds_missing_variant(self):
        essay = {"主": 100.0, "a": 50.0, "b": 40.0}
        out, _ = apply_pairs(essay, [pair("主", "缺")], page_size=5)
        self.assertIn("缺", out)
        self.assertLess(out["缺"], out["主"])

    def test_reading_keeps_both_weights(self):
        essay = {"妳": 2085.0, "嬭": 103.0, "x": 10.0}
        out, _ = apply_pairs(essay, [pair("妳", "嬭", "reading")], page_size=5)
        self.assertEqual(out["妳"], 2085.0)
        self.assertEqual(out["嬭"], 103.0)

    def test_reading_gives_floor_only_when_zero(self):
        essay = {"妳": 2085.0, "嬭": 0.0, "x": 10.0}
        out, _ = apply_pairs(essay, [pair("妳", "嬭", "reading")], page_size=5)
        self.assertGreater(out["嬭"], 0)

    def test_both_missing_is_skipped(self):
        out, report = apply_pairs({}, [pair("甲", "乙")], page_size=5)
        self.assertEqual(out, {})
        self.assertEqual(report[0]["action"], "skip")

    def test_tie_block_reports_overshoot(self):
        essay = {f"tie{i}": 100.0 for i in range(20)}
        essay.update({f"low{i}": 50.0 for i in range(200)})
        essay["主"] = 100.0
        essay["異"] = 100.0
        out, report = apply_pairs(essay, [pair()], page_size=5)
        self.assertLess(out["異"], out["主"])
        self.assertEqual(report[0]["action"], "overshoot")

    def test_idempotent(self):
        essay = {f"k{i}": float(i + 1) for i in range(60)}
        essay["主"] = 55.0
        essay["異"] = 5.0
        once, _ = apply_pairs(essay, [pair()], page_size=5)
        twice, _ = apply_pairs(once, [pair()], page_size=5)
        self.assertEqual(once, twice)


if __name__ == "__main__":
    unittest.main()
