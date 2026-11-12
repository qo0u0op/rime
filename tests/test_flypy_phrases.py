import unittest

from essay_lib import Pair
from generate_flypy_quick5_phrases import phrase_codes

CANGJIE = {
    "時": [("agdi", "")],
    "中": [("l", "")],
    "裏": [("ywgv", "")],
    "裡": [("lwg", "")],
    "面": [("mwsl", "")],
}


class TestPhraseCodes(unittest.TestCase):
    def test_basic_phrase(self):
        self.assertIn(
            ("時中", "ui/ai vs/ll"),
            phrase_codes("時中", ["shi", "zhong"], CANGJIE, []),
        )

    def test_variant_spelling_added(self):
        pairs = [Pair("裡", "裏", "char", "ortho", "test", "")]
        got = phrase_codes("裏面", ["li", "mian"], CANGJIE, pairs)
        self.assertIn(("裏面", "li/yv mm/ml"), [c for c in got if c[0] == "裏面"])
        self.assertIn("裡面", [c[0] for c in got])

    def test_missing_cangjie_skips_only_that_char(self):
        self.assertEqual(phrase_codes("時X", ["shi", "zhong"], CANGJIE, []), [])


if __name__ == "__main__":
    unittest.main()
