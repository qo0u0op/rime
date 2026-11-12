import os
import sys

TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOLS)

import unittest

from essay_lib import Pair
from moe_check import build_rows


class TestMoeCheck(unittest.TestCase):
    def test_row_contains_both_codes(self):
        pairs = [Pair("裡", "裏", "char", "ortho", "test", "")]
        luna = {"裡": [("li", "100%")], "裏": [("li", "")]}
        cangjie = {"裡": [("lwg", "")], "裏": [("ywgv", "")]}
        essay = {"裡": 100.0, "裏": 50.0}
        rows = build_rows(pairs, luna, cangjie, essay)
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["lisp_input"], "li")
        self.assertEqual(row["flypy_input"], "li")
        self.assertEqual(row["lisp_preferred"], "li/lg")
        self.assertEqual(row["lisp_variant"], "li/yv")
        self.assertEqual(row["flypy_preferred"], "li/lg")
        self.assertEqual(row["flypy_variant"], "li/yv")

    def test_pair_without_shared_reading_is_skipped(self):
        pairs = [Pair("妳", "嬭", "char", "ortho", "test", "")]
        luna = {"妳": [("ni", "100%")], "嬭": [("nai", "")]}
        cangjie = {"妳": [("vnf", "")], "嬭": [("vmb", "")]}
        self.assertEqual(build_rows(pairs, luna, cangjie, {}), [])


if __name__ == "__main__":
    unittest.main()
