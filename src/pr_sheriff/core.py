from __future__ import annotations

from dataclasses import asdict, dataclass, field
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
    "path_rules": [],
}

PATH_RULE_KEYS = {
    "name",
    "patterns",
    "max_changed_lines",
    "max_changed_files",
    "require_tests_after_lines",
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
    score_breakdown: dict[str, int] = field(default_factory=dict)
    path_rule_results: list[dict] = field(default_factory=list)

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
    config = {**DEFAULT_CONFIG, "path_rules": []}
    if path.exists():
        loaded = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            raise ValueError("configuration must be a JSON object")
        unknown = sorted(set(loaded) - set(DEFAULT_CONFIG))
        if unknown:
            raise ValueError(f"unknown configuration keys: {', '.join(unknown)}")
        config.update(loaded)
    validate_config(config)
    return config


def validate_config(config: dict) -> None:
    numeric_keys = ("max_changed_lines", "max_changed_files", "require_tests_after_lines")
    for key in numeric_keys:
        value = config[key]
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"{key} must be a non-negative integer")
    for key in ("test_patterns", "sensitive_patterns", "ignore_patterns"):
        if not isinstance(config[key], list) or not all(
            isinstance(item, str) for item in config[key]
        ):
            raise ValueError(f"{key} must be a list of strings")
    if not isinstance(config["path_rules"], list):
        raise ValueError("path_rules must be a list")
    names = set()
    for index, rule in enumerate(config["path_rules"]):
        prefix = f"path_rules[{index}]"
        if not isinstance(rule, dict):
            raise ValueError(f"{prefix} must be an object")
        unknown = sorted(set(rule) - PATH_RULE_KEYS)
        if unknown:
            raise ValueError(f"{prefix} has unknown keys: {', '.join(unknown)}")
        name = rule.get("name")
        patterns = rule.get("patterns")
        if not isinstance(name, str) or not name.strip():
            raise ValueError(f"{prefix}.name must be a non-empty string")
        if name in names:
            raise ValueError(f"path rule name must be unique: {name}")
        names.add(name)
        if not isinstance(patterns, list) or not patterns or not all(
            isinstance(item, str) for item in patterns
        ):
            raise ValueError(f"{prefix}.patterns must be a non-empty list of strings")
        for key in numeric_keys:
            if key in rule:
                value = rule[key]
                if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                    raise ValueError(f"{prefix}.{key} must be a non-negative integer")


def check_limits(
    changes: list[FileChange],
    tests_changed: bool,
    limits: dict,
    prefix: str = "",
) -> list[str]:
    changed_lines = sum(change.lines for change in changes)
    violations = []
    if "max_changed_lines" in limits and changed_lines > limits["max_changed_lines"]:
        violations.append(
            f"{prefix}changed lines {changed_lines} exceed limit {limits['max_changed_lines']}"
        )
    if "max_changed_files" in limits and len(changes) > limits["max_changed_files"]:
        violations.append(
            f"{prefix}changed files {len(changes)} exceed limit {limits['max_changed_files']}"
        )
    if (
        "require_tests_after_lines" in limits
        and changed_lines >= limits["require_tests_after_lines"]
        and not tests_changed
    ):
        violations.append(
            f"{prefix}tests required for changes of "
            f"{limits['require_tests_after_lines']}+ lines"
        )
    return violations


def analyze(changes: list[FileChange], config: dict) -> Report:
    relevant = [c for c in changes if not matches(c.path, config["ignore_patterns"])]
    changed_lines = sum(c.lines for c in relevant)
    tests_changed = any(matches(c.path, config["test_patterns"]) for c in changes)
    sensitive = [c.path for c in changes if matches(c.path, config["sensitive_patterns"])]

    violations = check_limits(relevant, tests_changed, config)
    path_rule_results = []
    for rule in config["path_rules"]:
        rule_changes = [change for change in relevant if matches(change.path, rule["patterns"])]
        if not rule_changes:
            continue
        rule_violations = check_limits(
            rule_changes, tests_changed, rule, prefix=f"[{rule['name']}] "
        )
        violations.extend(rule_violations)
        path_rule_results.append(
            {
                "name": rule["name"],
                "changed_files": len(rule_changes),
                "changed_lines": sum(change.lines for change in rule_changes),
                "violations": rule_violations,
            }
        )

    line_points = changed_lines // 10
    file_points = len(relevant) * 2
    sensitive_points = len(sensitive) * 25
    uncapped_score = line_points + file_points + sensitive_points
    score = min(100, uncapped_score)
    score_breakdown = {
        "changed_lines": line_points,
        "changed_files": file_points,
        "sensitive_files": sensitive_points,
        "cap_adjustment": score - uncapped_score,
        "total": score,
    }
    risk = "high" if score >= 60 else "medium" if score >= 25 else "low"
    return Report(
        risk=risk,
        score=score,
        changed_files=len(relevant),
        changed_lines=changed_lines,
        tests_changed=tests_changed,
        sensitive_files=sensitive,
        violations=violations,
        score_breakdown=score_breakdown,
        path_rule_results=path_rule_results,
    )
