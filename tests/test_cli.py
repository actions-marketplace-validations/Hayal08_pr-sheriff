import json
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
import tempfile
import unittest

from pr_sheriff.cli import github_escape, markdown_report, print_github_annotations, write_github_output
from pr_sheriff.cli import main
from pr_sheriff.core import DEFAULT_CONFIG, Report, load_config


class CliTests(unittest.TestCase):
    def test_init_writes_default_config(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            self.assertEqual(main(["init", "--config", str(path)]), 0)
            self.assertEqual(json.loads(path.read_text()), DEFAULT_CONFIG)

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

    def test_annotations_escape_workflow_commands(self):
        report = Report("high", 80, 4, 900, False, ["a%b.py"], ["bad\nchange"])
        output = StringIO()
        with redirect_stdout(output):
            print_github_annotations(report)
        self.assertIn("file=a%25b.py", output.getvalue())
        self.assertIn("bad%0Achange", output.getvalue())


if __name__ == "__main__":
    unittest.main()
