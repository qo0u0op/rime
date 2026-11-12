import os
import sys

TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOLS)

import tempfile
import unittest

from generate_flypy_quick5 import generate_char_entries, load_reading_weights


class TestReadingWeights(unittest.TestCase):
    def test_load_reading_weights(self):
        with tempfile.NamedTemporaryFile(
            "w", suffix=".tsv", delete=False, encoding="utf-8"
        ) as f:
            f.write("# comment\n參\tsan\t20000\n弎\tsan\t100\n")
            path = f.name
        try:
            self.assertEqual(
                load_reading_weights(path),
                {("參", "san"): "20000", ("弎", "san"): "100"},
            )
        finally:
            os.unlink(path)

    def test_override_changes_generated_weight(self):
        luna = {"甲": [("san", "100%")]}
        cangjie = {"甲": [("abc", "")]}
        entries = generate_char_entries(
            luna, cangjie, {("甲", "san"): "20000"}
        )
        self.assertEqual(entries, [("甲", "sj/ac", "20000")])

    def test_without_override_keeps_luna_weight(self):
        luna = {"甲": [("san", "100%")]}
        cangjie = {"甲": [("abc", "")]}
        entries = generate_char_entries(luna, cangjie)
        self.assertEqual(entries, [("甲", "sj/ac", "100%")])


if __name__ == "__main__":
    unittest.main()
