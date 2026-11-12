import os
import subprocess
import tempfile
import unittest


def make_rime(home: str) -> str:
    rime = os.path.join(home, ".local/share/fcitx5/rime")
    os.makedirs(rime)
    for name in ("generate_essay.py", "essay_pairs.tsv"):
        with open(os.path.join(rime, name), "w", encoding="utf-8") as f:
            f.write("")
    with open(os.path.join(rime, "essay_report.txt"), "w", encoding="utf-8") as f:
        f.write("input entries: 10\noutput entries: 12\n")
    return rime


def make_runuser(bin_dir: str, fail_marker: str = "") -> str:
    path = os.path.join(bin_dir, "runuser")
    with open(path, "w", encoding="utf-8") as f:
        f.write("#!/bin/sh\n")
        f.write('printf "%s\\n" "$*" >> "$RIME_TEST_LOG"\n')
        if fail_marker:
            f.write(f'case "$*" in *"{fail_marker}"*) exit 1;; esac\n')
        f.write("exit 0\n")
    os.chmod(path, 0o755)
    return path


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

    def test_real_path_uses_runuser_and_prints_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            rime = make_rime(os.path.join(tmp, "u"))
            bin_dir = os.path.join(tmp, "bin")
            os.makedirs(bin_dir)
            make_runuser(bin_dir)
            log = os.path.join(tmp, "calls.log")
            env = dict(
                os.environ,
                RIME_ESSAY_TW_ROOT=tmp,
                RIME_TEST_LOG=log,
                PATH=bin_dir + os.pathsep + os.environ["PATH"],
            )
            r = subprocess.run(
                ["./rime-essay-tw", "--user", "u"],
                capture_output=True,
                text=True,
                env=env,
            )
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("10 → 12", r.stdout)
            with open(log, encoding="utf-8") as f:
                calls = f.read()
            self.assertIn("generate_essay.py", calls)
            self.assertIn("--pairs", calls)
            self.assertTrue(os.path.exists(os.path.join(rime, "essay.txt")) is False)

    def test_one_user_failure_does_not_stop_the_next(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_rime(os.path.join(tmp, "u1"))
            make_rime(os.path.join(tmp, "u2"))
            bin_dir = os.path.join(tmp, "bin")
            os.makedirs(bin_dir)
            make_runuser(bin_dir, fail_marker="/u1/")
            log = os.path.join(tmp, "calls.log")
            env = dict(
                os.environ,
                RIME_ESSAY_TW_ROOT=tmp,
                RIME_TEST_LOG=log,
                PATH=bin_dir + os.pathsep + os.environ["PATH"],
            )
            r = subprocess.run(
                ["./rime-essay-tw"],
                capture_output=True,
                text=True,
                env=env,
            )
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("u1 更新失敗", r.stdout)
            self.assertIn("u2", r.stdout)


if __name__ == "__main__":
    unittest.main()
