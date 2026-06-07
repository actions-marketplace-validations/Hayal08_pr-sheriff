from __future__ import annotations

from copy import deepcopy

from .core import DEFAULT_CONFIG


PYTHON_CONFIG = {
    **DEFAULT_CONFIG,
    "test_patterns": [
        "tests/**",
        "test/**",
        "**/test_*.py",
        "**/*_test.py",
    ],
    "sensitive_patterns": [
        ".github/workflows/**",
        "**/auth/**",
        "**/security/**",
        "**/migrations/**",
        "Dockerfile",
        "**/Dockerfile",
        "pyproject.toml",
        "poetry.lock",
        "uv.lock",
        "requirements*.txt",
    ],
    "path_rules": [
        {
            "name": "database migrations",
            "patterns": ["**/migrations/**"],
            "max_changed_lines": 100,
            "require_tests_after_lines": 1,
        }
    ],
}

JAVASCRIPT_CONFIG = {
    **DEFAULT_CONFIG,
    "test_patterns": [
        "test/**",
        "tests/**",
        "**/__tests__/**",
        "**/*.test.*",
        "**/*.spec.*",
    ],
    "sensitive_patterns": [
        ".github/workflows/**",
        "**/auth/**",
        "**/security/**",
        "**/migrations/**",
        "Dockerfile",
        "**/Dockerfile",
        "package.json",
        "package-lock.json",
        "pnpm-lock.yaml",
        "yarn.lock",
    ],
    "path_rules": [
        {
            "name": "database migrations",
            "patterns": ["**/migrations/**"],
            "max_changed_lines": 100,
            "require_tests_after_lines": 1,
        }
    ],
}

PRESETS = {
    "default": DEFAULT_CONFIG,
    "python": PYTHON_CONFIG,
    "javascript": JAVASCRIPT_CONFIG,
}


def get_preset(name: str) -> dict:
    return deepcopy(PRESETS[name])


def merge_presets(*names: str) -> dict:
    configs = [get_preset(name) for name in names]
    merged = get_preset("default")
    for key in ("max_changed_lines", "max_changed_files", "require_tests_after_lines"):
        merged[key] = min(config[key] for config in configs)
    for key in ("test_patterns", "sensitive_patterns", "ignore_patterns"):
        merged[key] = list(
            dict.fromkeys(item for config in configs for item in config[key])
        )
    rules = {}
    for config in configs:
        for rule in config["path_rules"]:
            rules.setdefault(rule["name"], rule)
    merged["path_rules"] = list(rules.values())
    return merged
