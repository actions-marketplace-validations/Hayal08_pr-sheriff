import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pr_sheriff.github import COMMENT_MARKER, pull_request_number, upsert_pull_request_comment


class GithubTests(unittest.TestCase):
    def test_reads_pull_request_number(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "event.json"
            path.write_text('{"pull_request": {"number": 42}}')
            self.assertEqual(pull_request_number(path), 42)

    def test_non_pull_request_event_returns_none(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "event.json"
            path.write_text('{"ref": "refs/heads/main"}')
            self.assertIsNone(pull_request_number(path))

    @patch("pr_sheriff.github.api_request")
    def test_creates_comment_when_none_exists(self, request):
        request.side_effect = [[], {"id": 1}]
        result = upsert_pull_request_comment("report", "token", "owner/repo", 7)
        self.assertEqual(result, "created")
        self.assertEqual(request.call_args_list[1].kwargs["method"], "POST")
        self.assertIn(COMMENT_MARKER, request.call_args_list[1].kwargs["payload"]["body"])

    @patch("pr_sheriff.github.api_request")
    def test_updates_existing_bot_comment(self, request):
        request.side_effect = [
            [{"body": COMMENT_MARKER, "url": "https://api/comment/1", "user": {"type": "Bot"}}],
            {"id": 1},
        ]
        result = upsert_pull_request_comment("new report", "token", "owner/repo", 7)
        self.assertEqual(result, "updated")
        self.assertEqual(request.call_args_list[1].args[0], "https://api/comment/1")
        self.assertEqual(request.call_args_list[1].kwargs["method"], "PATCH")


if __name__ == "__main__":
    unittest.main()
