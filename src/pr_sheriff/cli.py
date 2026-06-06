from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

from .core import DEFAULT_CONFIG, analyze, git_changes, load_config
from .github import pull_request_number, upsert_pull_request_comment


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
    check.add_argument(
        "--advisory", action="store_true", help="report violations without failing"
    )
    check.add_argument("--github-summary", type=Path, help=argparse.SUPPRESS)
    check.add_argument("--github-output", type=Path, help=argparse.SUPPRESS)
    check.add_argument("--github-annotations", action="store_true", help=argparse.SUPPRESS)
    check.add_argument("--github-comment", action="store_true", help=argparse.SUPPRESS)
    init = subparsers.add_parser("init", help="write a starter configuration")
    init.add_argument("--config", default=".pr-sheriff.json", type=Path)
    return parser


def print_report(report) -> None:
    print(f"PR risk: {report.risk.upper()} ({report.score}/100)")
    print(f"Changed: {report.changed_files} files, {report.changed_lines} lines")
    if report.score_breakdown:
        print(
            "Score: "
            f"lines +{report.score_breakdown['changed_lines']}, "
            f"files +{report.score_breakdown['changed_files']}, "
            f"sensitive +{report.score_breakdown['sensitive_files']}"
        )
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


def markdown_report(report, advisory: bool = False) -> str:
    status = "Advisory" if advisory and report.violations else "Failed" if report.violations else "Passed"
    tests = "yes" if report.tests_changed else "no"
    lines = [
        "## PR Sheriff report",
        "",
        f"**Policy: {status}** | **Risk: {report.risk.upper()} ({report.score}/100)**",
        "",
        "| Changed files | Changed lines | Tests changed |",
        "| ---: | ---: | :---: |",
        f"| {report.changed_files} | {report.changed_lines} | {tests} |",
    ]
    if report.score_breakdown:
        breakdown = report.score_breakdown
        lines.extend(
            [
                "",
                "<details>",
                "<summary>Risk score breakdown</summary>",
                "",
                "| Changed lines | Changed files | Sensitive files | Cap adjustment | Total |",
                "| ---: | ---: | ---: | ---: | ---: |",
                f"| +{breakdown['changed_lines']} | +{breakdown['changed_files']} | "
                f"+{breakdown['sensitive_files']} | {breakdown['cap_adjustment']} | "
                f"**{breakdown['total']}** |",
                "",
                "</details>",
            ]
        )
    if report.path_rule_results:
        lines.extend(["", "### Matched path rules"])
        for result in report.path_rule_results:
            status_text = "violated" if result["violations"] else "passed"
            lines.append(
                f"- **{result['name']}**: {result['changed_files']} files, "
                f"{result['changed_lines']} lines ({status_text})"
            )
    if report.sensitive_files:
        lines.extend(["", "### Sensitive files"])
        lines.extend(f"- `{path}`" for path in report.sensitive_files)
    if report.violations:
        lines.extend(["", "### Policy violations"])
        lines.extend(f"- {violation}" for violation in report.violations)
    return "\n".join(lines) + "\n"


def github_escape(value: str) -> str:
    return value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def write_github_output(path: Path, report) -> None:
    values = {
        "risk": report.risk,
        "score": report.score,
        "changed-files": report.changed_files,
        "changed-lines": report.changed_lines,
        "tests-changed": str(report.tests_changed).lower(),
        "policy-passed": str(not report.violations).lower(),
    }
    with path.open("a", encoding="utf-8") as output:
        for key, value in values.items():
            output.write(f"{key}={value}\n")


def print_github_annotations(report, advisory: bool = False) -> None:
    for path in report.sensitive_files:
        print(f"::warning file={github_escape(path)}::Sensitive file changed")
    for violation in report.violations:
        level = "warning" if advisory else "error"
        print(f"::{level}::{github_escape(violation)}")


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
    if args.github_summary:
        with args.github_summary.open("a", encoding="utf-8") as summary:
            summary.write(markdown_report(report, args.advisory))
    if args.github_output:
        write_github_output(args.github_output, report)
    if args.github_annotations:
        print_github_annotations(report, args.advisory)
    if args.github_comment:
        try:
            event_path = os.environ.get("GITHUB_EVENT_PATH")
            repository = os.environ.get("GITHUB_REPOSITORY")
            token = os.environ.get("GITHUB_TOKEN")
            api_url = os.environ.get("GITHUB_API_URL", "https://api.github.com")
            if event_path and repository and token:
                number = pull_request_number(Path(event_path))
                if number:
                    result = upsert_pull_request_comment(
                        markdown_report(report, args.advisory),
                        token,
                        repository,
                        number,
                        api_url,
                    )
                    print(f"PR comment {result}.")
                else:
                    print("PR comment skipped: workflow event is not a pull request.")
            else:
                print("PR comment skipped: GitHub environment is incomplete.")
        except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
            print(f"::warning::PR comment skipped: {github_escape(str(exc))}")
    return 1 if report.violations and not args.advisory else 0


if __name__ == "__main__":
    raise SystemExit(main())
