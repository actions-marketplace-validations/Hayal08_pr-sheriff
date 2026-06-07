import json
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pr_sheriff.cli import (
    github_escape,
    markdown_report,
    print_github_annotations,
    write_github_output,
)
from pr_sheriff.cli import main
from pr_sheriff.core import DEFAULT_CONFIG, Report, load_config
from pr_sheriff.presets import JAVASCRIPT_CONFIG, PYTHON_CONFIG


class CliTests(unittest.TestCase):
    def test_init_writes_default_config(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            self.assertEqual(main(["init", "--config", str(path)]), 0)
            self.assertEqual(json.loads(path.read_text()), DEFAULT_CONFIG)

    def test_init_writes_selected_preset(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            self.assertEqual(
                main(["init", "--config", str(path), "--preset", "python"]), 0
            )
            self.assertEqual(json.loads(path.read_text()), PYTHON_CONFIG)

    def test_install_github_writes_config_and_advisory_workflow(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / ".pr-sheriff.json"
            workflow = root / ".github/workflows/pr-sheriff.yml"
            self.assertEqual(
                main(
                    [
                        "install-github",
                        "--config",
                        str(config),
                        "--workflow",
                        str(workflow),
                        "--preset",
                        "javascript",
                    ]
                ),
                0,
            )
            self.assertEqual(json.loads(config.read_text()), JAVASCRIPT_CONFIG)
            self.assertIn("mode: advisory", workflow.read_text())
            self.assertIn("Hayal08/pr-sheriff@v0.5.0", workflow.read_text())
            self.assertIn("origin/${{ github.base_ref }}", workflow.read_text())

    def test_install_github_does_not_partially_overwrite_without_force(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / ".pr-sheriff.json"
            workflow = root / ".github/workflows/pr-sheriff.yml"
            config.write_text("keep me")
            self.assertEqual(
                main(
                    [
                        "install-github",
                        "--config",
                        str(config),
                        "--workflow",
                        str(workflow),
                    ]
                ),
                2,
            )
            self.assertEqual(config.read_text(), "keep me")
            self.assertFalse(workflow.exists())

    def test_install_github_force_overwrites_existing_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / ".pr-sheriff.json"
            workflow = root / "pr-sheriff.yml"
            config.write_text("old")
            workflow.write_text("old")
            self.assertEqual(
                main(
                    [
                        "install-github",
                        "--config",
                        str(config),
                        "--workflow",
                        str(workflow),
                        "--mode",
                        "enforce",
                        "--force",
                    ]
                ),
                0,
            )
            self.assertEqual(json.loads(config.read_text()), DEFAULT_CONFIG)
            self.assertIn("mode: enforce", workflow.read_text())

    def test_unknown_config_key_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_text('{"mystery": true}')
            with self.assertRaisesRegex(ValueError, "unknown configuration keys"):
                load_config(path)

    def test_markdown_report_contains_action_summary(self):
        report = Report("high", 80, 4, 900, False, ["auth/login.py"], ["too large"])
        markdown = markdown_report(report)
        self.assertIn("**Policy: Failed**", markdown)
        self.assertIn("`auth/login.py`", markdown)
        self.assertIn("- too large", markdown)

    def test_github_outputs_are_appended(self):
        report = Report("low", 8, 2, 20, True, [], [])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "output"
            write_github_output(path, report)
            output = path.read_text()
        self.assertIn("risk=low\n", output)
        self.assertIn("tests-changed=true\n", output)
        self.assertIn("policy-passed=true\n", output)

    def test_annotations_escape_workflow_commands(self):
        report = Report("high", 80, 4, 900, False, ["a%b.py"], ["bad\nchange"])
        output = StringIO()
        with redirect_stdout(output):
            print_github_annotations(report)
        self.assertIn("file=a%25b.py", output.getvalue())
        self.assertIn("bad%0Achange", output.getvalue())

    def test_advisory_mode_returns_success_for_violations(self):
        report = Report("high", 80, 4, 900, False, [], ["too large"])
        with patch("pr_sheriff.cli.git_changes", return_value=[]), patch(
            "pr_sheriff.cli.analyze", return_value=report
        ):
            self.assertEqual(main(["check", "--base", "HEAD", "--advisory"]), 0)

    def test_markdown_lists_matched_path_rules_and_breakdown(self):
        report = Report(
            "medium",
            30,
            2,
            30,
            True,
            [],
            [],
            {
                "changed_lines": 3,
                "changed_files": 2,
                "sensitive_files": 25,
                "cap_adjustment": 0,
                "total": 30,
            },
            [{"name": "api", "changed_files": 2, "changed_lines": 30, "violations": []}],
        )
        markdown = markdown_report(report)
        self.assertIn("Risk score breakdown", markdown)
        self.assertIn("**api**: 2 files, 30 lines (passed)", markdown)


if __name__ == "__main__":
    unittest.main()
