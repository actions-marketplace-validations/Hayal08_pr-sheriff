import json
from pathlib import Path
import tempfile
import unittest

from pr_sheriff.cli import main
from pr_sheriff.core import DEFAULT_CONFIG, load_config


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


if __name__ == "__main__":
    unittest.main()
