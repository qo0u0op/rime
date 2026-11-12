import os
import sys

TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOLS)

import unittest

from extract_moe_pairs import parse_moe_rows

ROWS = [
    {"字詞名": "裡", "多音排序": "0", "注音一式": "ㄌㄧˇ", "釋義": "內部。", "異體字": ""},
    {"字詞名": "裏", "多音排序": "0", "注音一式": "", "釋義": "「裡」的異體字。", "異體字": "異體字"},
    {"字詞名": "妳", "多音排序": "0", "注音一式": "ㄋㄧˇ", "釋義": "女性的第二人稱。", "異體字": ""},
    {"字詞名": "妳", "多音排序": "0", "注音一式": "", "釋義": "「嬭」的異體字。", "異體字": "異體字"},
]


class TestMoe(unittest.TestCase):
    def test_pure_variant_is_auto(self):
        auto, review = parse_moe_rows(ROWS)
        self.assertIn(("裡", "裏"), [(p.preferred, p.variant) for p in auto])
        self.assertNotIn(("裡", "裏"), [(p.preferred, p.variant) for p in review])

    def test_head_with_own_reading_goes_to_review(self):
        auto, review = parse_moe_rows(ROWS)
        self.assertIn(("嬭", "妳"), [(p.preferred, p.variant) for p in review])
        self.assertNotIn(("嬭", "妳"), [(p.preferred, p.variant) for p in auto])

    def test_unparsable_definition_is_skipped(self):
        auto, review = parse_moe_rows(
            [
                {
                    "字詞名": "X",
                    "多音排序": "0",
                    "注音一式": "",
                    "釋義": "沒有關係",
                    "異體字": "異體字",
                }
            ]
        )
        self.assertEqual((auto, review), ([], []))


if __name__ == "__main__":
    unittest.main()
