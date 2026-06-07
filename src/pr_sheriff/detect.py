from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .presets import get_preset, merge_presets


PYTHON_MARKERS = (
    "pyproject.toml",
    "setup.py",
    "setup.cfg",
    "poetry.lock",
    "uv.lock",
    "Pipfile",
)
JAVASCRIPT_MARKERS = (
    "package.json",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "bun.lock",
    "bun.lockb",
    "tsconfig.json",
)


@dataclass(frozen=True)
class Detection:
    preset: str
    evidence: tuple[str, ...]
    config: dict


def existing_markers(root: Path, markers: tuple[str, ...]) -> list[str]:
    return [marker for marker in markers if (root / marker).is_file()]


def detect_repository(root: Path) -> Detection:
    python = existing_markers(root, PYTHON_MARKERS)
    python.extend(
        path.name for path in sorted(root.glob("requirements*.txt")) if path.is_file()
    )
    javascript = existing_markers(root, JAVASCRIPT_MARKERS)
    evidence = tuple(python + javascript)
    if python and javascript:
        return Detection(
            "python + javascript",
            evidence,
            merge_presets("python", "javascript"),
        )
    if python:
        return Detection("python", evidence, get_preset("python"))
    if javascript:
        return Detection("javascript", evidence, get_preset("javascript"))
    return Detection("default", (), get_preset("default"))
