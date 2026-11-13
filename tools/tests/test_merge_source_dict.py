import os
import sys
import tempfile

TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOLS)

import unittest

from merge_source_dict import load_overrides, merge

LOCAL = """---
name: "cangjie5"
use_preset_vocabulary: false
...
日\ta
鿃\tbo
\ue815\thh
\ue999\tzz
"""

UPSTREAM = """---
name: "cangjie5"
use_preset_vocabulary: true
...
日\ta
曰\ta
⺁\thh
"""


class TestMergeSourceDict(unittest.TestCase):
    def test_keeps_local_only_entries(self):
        merged, kept, _, _ = merge(LOCAL, UPSTREAM)
        self.assertEqual(kept, 1)
        self.assertIn("鿃\tbo", merged)

    def test_drops_local_only_pua(self):
        merged, _, dropped, _ = merge(LOCAL, UPSTREAM)
        self.assertEqual(dropped, 2)
        self.assertNotIn("\ue815\thh", merged)
        self.assertNotIn("\ue999\tzz", merged)

    def test_upstream_wins_on_shared_key(self):
        merged, _, _, _ = merge(LOCAL, UPSTREAM)
        self.assertIn("日\ta", merged)
        self.assertIn("曰\ta", merged)

    def test_keeps_local_header_override(self):
        merged, _, _, _ = merge(LOCAL, UPSTREAM)
        self.assertIn("use_preset_vocabulary: false", merged)
        self.assertNotIn("use_preset_vocabulary: true", merged)

    def test_upstream_order_is_preserved(self):
        merged, _, _, _ = merge(LOCAL, UPSTREAM)
        self.assertLess(merged.index("曰\ta"), merged.index("鿃\tbo"))

    def test_idempotent(self):
        once, _, _, _ = merge(LOCAL, UPSTREAM)
        twice, _, _, _ = merge(once, UPSTREAM)
        self.assertEqual(once, twice)

    def test_override_replaces_weight(self):
        merged, _, _, applied = merge(LOCAL, UPSTREAM, [("日", "a", "0%")])
        self.assertEqual(applied, 1)
        self.assertIn("日\ta\t0%", merged)

    def test_override_appends_missing_entry(self):
        merged, _, _, applied = merge(LOCAL, UPSTREAM, [("暫", "zhan", "100%")])
        self.assertEqual(applied, 1)
        self.assertTrue(merged.endswith("暫\tzhan\t100%\n"))


class TestLoadOverrides(unittest.TestCase):
    def test_filters_by_dictionary(self):
        with tempfile.NamedTemporaryFile(
            "w", suffix=".tsv", delete=False, encoding="utf-8"
        ) as fh:
            fh.write("# comment\n")
            fh.write("luna_pinyin.dict.yaml\t暫\tzhan\t100%\n")
            fh.write("cangjie5.dict.yaml\t日\ta\t0%\n")
            path = fh.name
        try:
            rows = load_overrides(path, "luna_pinyin.dict.yaml")
        finally:
            os.unlink(path)
        self.assertEqual(rows, [("暫", "zhan", "100%")])


if __name__ == "__main__":
    unittest.main()
