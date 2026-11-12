import os
import sys

TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOLS)

import unittest

from generate_lisp_quick5_phrases import phrase_spellings


class TestLispPhraseSpellings(unittest.TestCase):
    def test_variant_to_preferred_spelling(self):
        self.assertIn("著實", phrase_spellings("着實", {"着": "著"}))

    def test_preferred_to_variant_spelling(self):
        self.assertIn("着實", phrase_spellings("著實", {"著": "着"}))

    def test_original_is_kept(self):
        self.assertIn("着實", phrase_spellings("着實", {}))


if __name__ == "__main__":
    unittest.main()
