import os
import tempfile
import unittest
from essay_lib import Pair, RankTable, format_weight, load_essay, load_pairs


class TestEssayLib(unittest.TestCase):
    def test_load_essay_takes_max_for_duplicate_keys(self):
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
            f.write("甲\t3\n乙\t5\n甲\t9\n")
            path = f.name
        try:
            self.assertEqual(load_essay(path), {"甲": 9.0, "乙": 5.0})
        finally:
            os.unlink(path)

    def test_load_pairs_skips_comments_and_blank_lines(self):
        with tempfile.NamedTemporaryFile("w", suffix=".tsv", delete=False, encoding="utf-8") as f:
            f.write("# comment\n\n為\t爲\tchar\tortho\tmoe\t\n")
            path = f.name
        try:
            self.assertEqual(
                load_pairs(path),
                [Pair("為", "爲", "char", "ortho", "moe", "")],
            )
        finally:
            os.unlink(path)

    def test_rank_table_orders_descending(self):
        table = RankTable([10, 30, 20])
        self.assertEqual(table.rank(30), 0)
        self.assertEqual(table.rank(20), 1)
        self.assertEqual(table.rank(10), 2)
        self.assertEqual(table.value_at(1), 20)

    def test_next_lower_returns_strictly_smaller(self):
        table = RankTable([100, 100, 50, 1])
        self.assertEqual(table.next_lower(100), 50)
        self.assertIsNone(table.next_lower(1))

    def test_format_weight_keeps_integers_and_one_decimal(self):
        self.assertEqual(format_weight(1234.0), "1234")
        self.assertEqual(format_weight(1234.5), "1234.5")
        self.assertEqual(format_weight(0.0), "0")


if __name__ == "__main__":
    unittest.main()
