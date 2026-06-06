from __future__ import annotations

from dataclasses import asdict, dataclass
from fnmatch import fnmatch
import json
from pathlib import Path
import subprocess
from typing import Iterable


DEFAULT_CONFIG = {
    "max_changed_lines": 800,
    "max_changed_files": 30,
    "require_tests_after_lines": 120,
    "test_patterns": ["tests/**", "test/**", "**/*_test.*", "**/*.test.*", "**/*.spec.*"],
    "sensitive_patterns": [
        ".github/workflows/**",
        "**/auth/**",
        "**/security/**",
        "**/migrations/**",
        "Dockerfile",
        "**/Dockerfile",
        "package-lock.json",
        "poetry.lock",
    ],
    "ignore_patterns": ["**/*.md", "docs/**"],
}


@dataclass(frozen=True)
class FileChange:
    path: str
    additions: int
    deletions: int

    @property
    def lines(self) -> int:
        return self.additions + self.deletions


@dataclass(frozen=True)
class Report:
    risk: str
    score: int
    changed_files: int
    changed_lines: int
    tests_changed: bool
    sensitive_files: list[str]
    violations: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


def matches(path: str, patterns: Iterable[str]) -> bool:
    return any(
        fnmatch(path, pattern)
        or (pattern.startswith("**/") and fnmatch(path, pattern.removeprefix("**/")))
        for pattern in patterns
    )


def parse_numstat(text: str) -> list[FileChange]:
    changes = []
    for line in text.splitlines():
        parts = line.split("\t", 2)
        if len(parts) != 3:
            continue
        added, deleted, path = parts
        # Git uses "-" for binary files. Counting one line keeps them visible.
        additions = int(added) if added.isdigit() else 1
        deletions = int(deleted) if deleted.isdigit() else 1
        changes.append(FileChange(path, additions, deletions))
    return changes


def git_changes(base: str, head: str = "HEAD") -> list[FileChange]:
    try:
        result = subprocess.run(
            ["git", "diff", "--numstat", f"{base}...{head}"],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr.strip() or "git diff failed"
        raise RuntimeError(detail) from exc
    return parse_numstat(result.stdout)


def load_config(path: Path) -> dict:
    config = DEFAULT_CONFIG.copy()
    if path.exists():
        loaded = json.loads(path.read_text(encoding="utf-8"))
        unknown = sorted(set(loaded) - set(DEFAULT_CONFIG))
        if unknown:
            raise ValueError(f"unknown configuration keys: {', '.join(unknown)}")
        config.update(loaded)
    return config


def analyze(changes: list[FileChange], config: dict) -> Report:
    relevant = [c for c in changes if not matches(c.path, config["ignore_patterns"])]
    changed_lines = sum(c.lines for c in relevant)
    tests_changed = any(matches(c.path, config["test_patterns"]) for c in changes)
    sensitive = [c.path for c in changes if matches(c.path, config["sensitive_patterns"])]

    violations = []
    if changed_lines > config["max_changed_lines"]:
        violations.append(
            f"changed lines {changed_lines} exceed limit {config['max_changed_lines']}"
        )
    if len(relevant) > config["max_changed_files"]:
        violations.append(
            f"changed files {len(relevant)} exceed limit {config['max_changed_files']}"
        )
    if changed_lines >= config["require_tests_after_lines"] and not tests_changed:
        violations.append(
            f"tests required for changes of {config['require_tests_after_lines']}+ lines"
        )

    score = min(100, changed_lines // 10 + len(relevant) * 2 + len(sensitive) * 25)
    risk = "high" if score >= 60 else "medium" if score >= 25 else "low"
    return Report(
        risk=risk,
        score=score,
        changed_files=len(relevant),
        changed_lines=changed_lines,
        tests_changed=tests_changed,
        sensitive_files=sensitive,
        violations=violations,
    )
