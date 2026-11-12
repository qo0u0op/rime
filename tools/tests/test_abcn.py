import os
import sys

TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOLS)

import unittest

from extract_abcn import parse_abcn_rows


class TestAbcn(unittest.TestCase):
    def test_class_comes_from_the_number_prefix(self):
        rows = [
            {"A": "unicode", "B": "char", "C": "id"},
            {"B": "三", "C": "A00004"},
            {"B": "㐁", "C": "C00005"},
            {"B": "𠀀", "C": "C00002"},
        ]
        self.assertEqual(
            parse_abcn_rows(rows),
            {"三": ("A", "A00004"), "㐁": ("C", "C00005"), "𠀀": ("C", "C00002")},
        )

    def test_rows_without_number_are_skipped(self):
        self.assertEqual(parse_abcn_rows([{"B": "x", "C": ""}]), {})


if __name__ == "__main__":
    unittest.main()
