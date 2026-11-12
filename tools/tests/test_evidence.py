import os
import sys

TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOLS)

import unittest

from extract_evidence import parse_variants


class TestEvidence(unittest.TestCase):
    def test_variant_sources(self):
        text = (
            "眀 U+7700 `28`異體字`1`：`25`明`1` (U+660E)<br>"
            "[異体字（戸籍統一文字）]<br>[異體字（民國教育部）]"
        )
        self.assertEqual(
            parse_variants(text),
            [("明", "660E", ["異体字（戸籍統一文字）", "異體字（民國教育部）"])],
        )

    def test_no_variant_section(self):
        self.assertEqual(parse_variants("三 U+4E09"), [])


if __name__ == "__main__":
    unittest.main()
