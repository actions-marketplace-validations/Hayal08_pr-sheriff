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
