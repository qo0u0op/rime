import unittest

from generate_flypy_quick5 import cangjie_quick, pinyin_to_flypy


class TestFlypyCodes(unittest.TestCase):
    def test_zhong(self):
        self.assertEqual(pinyin_to_flypy("zhong"), {"vs"})

    def test_shi(self):
        self.assertEqual(pinyin_to_flypy("shi"), {"ui"})

    def test_zhuang(self):
        self.assertEqual(pinyin_to_flypy("zhuang"), {"vl"})

    def test_qu_derives_two_codes(self):
        self.assertEqual(pinyin_to_flypy("qu"), {"qu", "qv"})

    def test_nv(self):
        self.assertEqual(pinyin_to_flypy("nv"), {"nv"})

    def test_cangjie_quick(self):
        self.assertEqual(cangjie_quick("lwg"), "lg")
        self.assertEqual(cangjie_quick("l"), "ll")
        self.assertIsNone(cangjie_quick(""))


if __name__ == "__main__":
    unittest.main()
