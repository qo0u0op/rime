import unittest

from tools.extract_opencc_pairs import derive_pair


def ortho(text):
    return {"裏面": "裡面"}.get(text, text)


def regional(text):
    return {"軟件": "軟體"}.get(text, text)


class TestOpenCC(unittest.TestCase):
    def test_ortho_wins_over_regional(self):
        p = derive_pair("裏面", ortho, regional)
        self.assertEqual((p.preferred, p.variant, p.type), ("裡面", "裏面", "ortho"))

    def test_regional_when_ortho_unchanged(self):
        p = derive_pair("軟件", ortho, regional)
        self.assertEqual((p.preferred, p.variant, p.type), ("軟體", "軟件", "regional"))

    def test_identity_returns_none(self):
        self.assertIsNone(derive_pair("吃飯", ortho, regional))


if __name__ == "__main__":
    unittest.main()
