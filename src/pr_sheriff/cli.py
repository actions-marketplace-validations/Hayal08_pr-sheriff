from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .core import DEFAULT_CONFIG, analyze, git_changes, load_config


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pr-sheriff", description="Deterministic risk checks for pull requests."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    check = subparsers.add_parser("check", help="analyze the current pull request")
    check.add_argument("--base", default="origin/main", help="base git ref")
    check.add_argument("--head", default="HEAD", help="head git ref")
    check.add_argument("--config", default=".pr-sheriff.json", type=Path)
    check.add_argument("--json", action="store_true", dest="as_json")
    init = subparsers.add_parser("init", help="write a starter configuration")
    init.add_argument("--config", default=".pr-sheriff.json", type=Path)
    return parser


def print_report(report) -> None:
    print(f"PR risk: {report.risk.upper()} ({report.score}/100)")
    print(f"Changed: {report.changed_files} files, {report.changed_lines} lines")
    if report.sensitive_files:
        print("Sensitive files:")
        for path in report.sensitive_files:
            print(f"  - {path}")
    if report.violations:
        print("Policy violations:")
        for violation in report.violations:
            print(f"  - {violation}")
    else:
        print("Policy check passed.")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "init":
        if args.config.exists():
            print(f"{args.config} already exists", file=sys.stderr)
            return 2
        args.config.write_text(json.dumps(DEFAULT_CONFIG, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {args.config}")
        return 0

    try:
        config = load_config(args.config)
        report = analyze(git_changes(args.base, args.head), config)
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        print(f"pr-sheriff: {exc}", file=sys.stderr)
        return 2
    if args.as_json:
        print(json.dumps(report.to_dict(), indent=2))
    else:
        print_report(report)
    return 1 if report.violations else 0


if __name__ == "__main__":
    raise SystemExit(main())
