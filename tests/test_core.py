import unittest
from unittest.mock import patch

from pr_sheriff.core import DEFAULT_CONFIG, FileChange, analyze, git_changes, parse_numstat


class ParseNumstatTests(unittest.TestCase):
    def test_parses_text_and_binary_changes(self):
        changes = parse_numstat("10\t2\tsrc/app.py\n-\t-\tlogo.png\n")
        self.assertEqual(changes[0], FileChange("src/app.py", 10, 2))
        self.assertEqual(changes[1].lines, 2)

    @patch("pr_sheriff.core.subprocess.run")
    def test_git_error_has_readable_message(self, run):
        from subprocess import CalledProcessError

        run.side_effect = CalledProcessError(128, ["git"], stderr="bad base ref\n")
        with self.assertRaisesRegex(RuntimeError, "bad base ref"):
            git_changes("missing")


class AnalyzeTests(unittest.TestCase):
    def test_small_change_passes(self):
        report = analyze([FileChange("src/app.py", 5, 1)], DEFAULT_CONFIG)
        self.assertEqual(report.risk, "low")
        self.assertEqual(report.violations, [])

    def test_large_change_requires_tests(self):
        report = analyze([FileChange("src/app.py", 120, 0)], DEFAULT_CONFIG)
        self.assertTrue(any("tests required" in item for item in report.violations))

    def test_test_change_satisfies_requirement(self):
        report = analyze(
            [FileChange("src/app.py", 120, 0), FileChange("tests/test_app.py", 5, 0)],
            DEFAULT_CONFIG,
        )
        self.assertFalse(any("tests required" in item for item in report.violations))

    def test_sensitive_file_increases_risk(self):
        report = analyze(
            [FileChange(".github/workflows/release.yml", 20, 0)], DEFAULT_CONFIG
        )
        self.assertEqual(report.risk, "medium")
        self.assertEqual(report.sensitive_files, [".github/workflows/release.yml"])

    def test_docs_are_ignored_from_size_budget(self):
        report = analyze([FileChange("docs/guide.md", 1000, 0)], DEFAULT_CONFIG)
        self.assertEqual(report.changed_lines, 0)
        self.assertEqual(report.violations, [])

    def test_root_markdown_is_ignored_by_recursive_pattern(self):
        report = analyze([FileChange("README.md", 1000, 0)], DEFAULT_CONFIG)
        self.assertEqual(report.changed_lines, 0)
        self.assertEqual(report.violations, [])


if __name__ == "__main__":
    unittest.main()
