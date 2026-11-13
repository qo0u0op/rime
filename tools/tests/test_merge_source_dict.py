import os
import sys

TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, TOOLS)

import unittest

from merge_source_dict import merge

LOCAL = """---
name: "cangjie5"
use_preset_vocabulary: false
...
日\ta
鿃\tbo
"""

UPSTREAM = """---
name: "cangjie5"
use_preset_vocabulary: true
...
日\ta
曰\ta
"""


class TestMergeSourceDict(unittest.TestCase):
    def test_keeps_local_only_entries(self):
        merged, kept = merge(LOCAL, UPSTREAM)
        self.assertEqual(kept, 1)
        self.assertIn("鿃\tbo", merged)

    def test_upstream_wins_on_shared_key(self):
        merged, _ = merge(LOCAL, UPSTREAM)
        self.assertIn("日\ta", merged)
        self.assertIn("曰\ta", merged)

    def test_keeps_local_header_override(self):
        merged, _ = merge(LOCAL, UPSTREAM)
        self.assertIn("use_preset_vocabulary: false", merged)
        self.assertNotIn("use_preset_vocabulary: true", merged)

    def test_upstream_order_is_preserved(self):
        merged, _ = merge(LOCAL, UPSTREAM)
        self.assertLess(merged.index("曰\ta"), merged.index("鿃\tbo"))

    def test_idempotent(self):
        once, _ = merge(LOCAL, UPSTREAM)
        twice, _ = merge(once, UPSTREAM)
        self.assertEqual(once, twice)


if __name__ == "__main__":
    unittest.main()
