from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

from .core import analyze, git_changes, load_config
from .detect import detect_repository
from .github import pull_request_number, upsert_pull_request_comment
from .presets import PRESETS, get_preset


WORKFLOW_TEMPLATE = """name: PR Sheriff

on:
  pull_request:

permissions:
  contents: read
  pull-requests: write

jobs:
  review-risk:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v6
        with:
          fetch-depth: 0
      - uses: Hayal08/pr-sheriff@v0.6.0
        with:
          base: origin/${{{{ github.base_ref }}}}
          config: {config}
          mode: {mode}
"""


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
    init.add_argument("--preset", choices=PRESETS, default="default")
    install = subparsers.add_parser(
        "install-github", help="install configuration and a GitHub Actions workflow"
    )
    install.add_argument("--config", default=".pr-sheriff.json", type=Path)
    install.add_argument(
        "--workflow", default=".github/workflows/pr-sheriff.yml", type=Path
    )
    install_policy = install.add_mutually_exclusive_group()
    install_policy.add_argument("--preset", choices=PRESETS, default="default")
    install_policy.add_argument(
        "--detect", action="store_true", help="detect a policy preset from repository files"
    )
    install.add_argument("--mode", choices=("advisory", "enforce"), default="advisory")
    install.add_argument("--force", action="store_true")
    return parser


def write_file(path: Path, content: str, force: bool = False) -> bool:
    if path.exists() and not force:
        print(f"{path} already exists", file=sys.stderr)
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"Wrote {path}")
    return True


def install_files(files: list[tuple[Path, str]]) -> None:
    originals: dict[Path, bytes | None] = {}
    written = []
    try:
        for path, content in files:
            if path.exists() and not path.is_file():
                raise OSError(f"{path} exists and is not a file")
            originals[path] = path.read_bytes() if path.exists() else None
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            written.append(path)
    except OSError:
        for path in reversed(written):
            original = originals[path]
            if original is None:
                path.unlink(missing_ok=True)
            else:
                path.write_bytes(original)
        raise
    for path, _ in files:
        print(f"Wrote {path}")


def repository_path(path: Path, label: str) -> Path:
    root = Path.cwd().resolve()
    resolved = path.resolve() if path.is_absolute() else (root / path).resolve()
    try:
        relative = resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"{label} must be a path inside the repository") from exc
    if not relative.parts:
        raise ValueError(f"{label} must point to a file")
    return relative


def render_workflow(mode: str, config: Path) -> str:
    return WORKFLOW_TEMPLATE.format(mode=mode, config=json.dumps(config.as_posix()))


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


def github_escape(value: str, property_value: bool = False) -> str:
    escaped = value.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
    if property_value:
        escaped = escaped.replace(":", "%3A").replace(",", "%2C")
    return escaped


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
        escaped_path = github_escape(path, property_value=True)
        print(f"::warning file={escaped_path}::Sensitive file changed")
    for violation in report.violations:
        level = "warning" if advisory else "error"
        print(f"::{level}::{github_escape(violation)}")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "init":
        content = json.dumps(get_preset(args.preset), indent=2) + "\n"
        try:
            return 0 if write_file(args.config, content) else 2
        except OSError as exc:
            print(f"pr-sheriff: could not write configuration: {exc}", file=sys.stderr)
            return 2
    if args.command == "install-github":
        try:
            config_path = repository_path(args.config, "config")
            workflow_path = repository_path(args.workflow, "workflow")
            if config_path == workflow_path:
                raise ValueError("config and workflow must point to different files")
        except (OSError, ValueError) as exc:
            print(f"pr-sheriff: {exc}", file=sys.stderr)
            return 2
        existing = [path for path in (config_path, workflow_path) if path.exists()]
        if existing and not args.force:
            for path in existing:
                print(f"{path} already exists", file=sys.stderr)
            print("Use --force to overwrite existing files.", file=sys.stderr)
            return 2
        if args.detect:
            detection = detect_repository(Path.cwd())
            preset = detection.config
            print(f"Detected preset: {detection.preset}")
            if detection.evidence:
                print(f"Evidence: {', '.join(detection.evidence)}")
            else:
                print("Evidence: no known project markers; using the default policy")
        else:
            preset = get_preset(args.preset)
        config = json.dumps(preset, indent=2) + "\n"
        try:
            install_files(
                [
                    (config_path, config),
                    (workflow_path, render_workflow(args.mode, config_path)),
                ]
            )
        except OSError as exc:
            print(f"pr-sheriff: could not install GitHub workflow: {exc}", file=sys.stderr)
            return 2
        print("PR Sheriff is installed. Open a pull request to see the first report.")
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
