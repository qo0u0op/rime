import os
import subprocess
import tempfile
import unittest


class TestHook(unittest.TestCase):
    def test_dry_run_prints_message_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            rime = os.path.join(tmp, "u", ".local/share/fcitx5/rime")
            os.makedirs(rime)
            env = dict(
                os.environ,
                RIME_ESSAY_TW_DRY_RUN="1",
                RIME_ESSAY_TW_ROOT=tmp,
            )
            r = subprocess.run(
                ["./rime-essay-tw", "--user", "u"],
                capture_output=True,
                text=True,
                env=env,
            )
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("已更新", r.stdout)
            self.assertEqual(os.listdir(rime), [])

    def test_missing_rime_dir_reports_and_exits_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = dict(
                os.environ,
                RIME_ESSAY_TW_DRY_RUN="1",
                RIME_ESSAY_TW_ROOT=tmp,
            )
            r = subprocess.run(
                ["./rime-essay-tw", "--user", "nobody"],
                capture_output=True,
                text=True,
                env=env,
            )
            self.assertEqual(r.returncode, 0)
            self.assertIn("找不到", r.stdout)


if __name__ == "__main__":
    unittest.main()
