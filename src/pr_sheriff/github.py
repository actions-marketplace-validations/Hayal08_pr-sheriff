from __future__ import annotations

import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen


COMMENT_MARKER = "<!-- pr-sheriff-report -->"


def pull_request_number(event_path: Path) -> int | None:
    event = json.loads(event_path.read_text(encoding="utf-8"))
    pull_request = event.get("pull_request")
    if not pull_request:
        return None
    return int(pull_request["number"])


def api_request(url: str, token: str, method: str = "GET", payload: dict | None = None):
    data = json.dumps(payload).encode() if payload is not None else None
    request = Request(
        url,
        data=data,
        method=method,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urlopen(request, timeout=20) as response:
            return json.loads(response.read() or b"null")
    except HTTPError as exc:
        detail = exc.read().decode(errors="replace")
        raise RuntimeError(f"GitHub API returned {exc.code}: {detail}") from exc


def upsert_pull_request_comment(
    body: str,
    token: str,
    repository: str,
    number: int,
    api_url: str = "https://api.github.com",
) -> str:
    comments_url = f"{api_url}/repos/{repository}/issues/{number}/comments"
    comments = api_request(f"{comments_url}?per_page=100", token)
    existing = next(
        (
            comment
            for comment in comments
            if COMMENT_MARKER in comment.get("body", "")
            and comment.get("user", {}).get("type") == "Bot"
        ),
        None,
    )
    payload = {"body": f"{COMMENT_MARKER}\n{body}"}
    if existing:
        api_request(existing["url"], token, method="PATCH", payload=payload)
        return "updated"
    api_request(comments_url, token, method="POST", payload=payload)
    return "created"
