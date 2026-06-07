import json
from pathlib import Path
import tempfile
import unittest

from pr_sheriff.detect import detect_repository
from pr_sheriff.presets import JAVASCRIPT_CONFIG, PYTHON_CONFIG


class DetectTests(unittest.TestCase):
    def detect(self, files):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for filename in files:
                path = root / filename
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("{}" if path.suffix == ".json" else "")
            return detect_repository(root)

    def test_detects_python_repository(self):
        detection = self.detect(["pyproject.toml", "requirements-dev.txt"])
        self.assertEqual(detection.preset, "python")
        self.assertEqual(detection.evidence, ("pyproject.toml", "requirements-dev.txt"))
        self.assertEqual(detection.config, PYTHON_CONFIG)

    def test_detects_javascript_repository(self):
        detection = self.detect(["package.json", "tsconfig.json"])
        self.assertEqual(detection.preset, "javascript")
        self.assertEqual(detection.evidence, ("package.json", "tsconfig.json"))
        self.assertEqual(detection.config, JAVASCRIPT_CONFIG)

    def test_mixed_repository_combines_test_and_sensitive_patterns(self):
        detection = self.detect(["pyproject.toml", "package.json"])
        self.assertEqual(detection.preset, "python + javascript")
        self.assertIn("**/test_*.py", detection.config["test_patterns"])
        self.assertIn("**/__tests__/**", detection.config["test_patterns"])
        self.assertIn("pyproject.toml", detection.config["sensitive_patterns"])
        self.assertIn("package.json", detection.config["sensitive_patterns"])
        self.assertEqual(len(detection.config["path_rules"]), 1)
        json.dumps(detection.config)

    def test_unknown_repository_uses_default(self):
        detection = self.detect(["README.md"])
        self.assertEqual(detection.preset, "default")
        self.assertEqual(detection.evidence, ())

    def test_nested_manifests_do_not_guess_monorepo_policy(self):
        detection = self.detect(["examples/package.json"])
        self.assertEqual(detection.preset, "default")


if __name__ == "__main__":
    unittest.main()
