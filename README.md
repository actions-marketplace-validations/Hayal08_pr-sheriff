# PR Sheriff

[![CI](https://github.com/Hayal08/pr-sheriff/actions/workflows/ci.yml/badge.svg)](https://github.com/Hayal08/pr-sheriff/actions/workflows/ci.yml)
[![GitHub Marketplace](https://img.shields.io/badge/Marketplace-PR%20Sheriff-blue?logo=github)](https://github.com/marketplace/actions/pr-sheriff)
[![Good first issues](https://img.shields.io/github/issues/Hayal08/pr-sheriff/good%20first%20issue)](https://github.com/Hayal08/pr-sheriff/labels/good%20first%20issue)

PR Sheriff is a tiny, deterministic pull request risk checker for busy open-source
maintainers. It catches oversized changes, missing tests, and edits to sensitive
files before review time is spent.

It has no runtime dependencies, sends no code anywhere, and works in any Git
repository.

## Why PR Sheriff?

Large or sensitive pull requests consume disproportionate review time. PR
Sheriff gives contributors fast, predictable feedback before a maintainer starts
reviewing:

- contributors learn when a change needs tests or should be split;
- maintainers see sensitive paths and review risk immediately;
- teams keep policy in a small, version-controlled JSON file;
- every decision remains deterministic and explainable.

## Quick start

```bash
python -m pip install .
pr-sheriff init
pr-sheriff check --base origin/main
```

Example output:

```text
PR risk: MEDIUM (39/100)
Changed: 3 files, 94 lines
Sensitive files:
  - .github/workflows/release.yml
Policy check passed.
```

The command exits with `1` when policy violations exist, making it suitable for
CI and pre-push hooks. Use `--json` for integrations.

Start with `--advisory` to report violations without blocking contributors:

```bash
pr-sheriff check --base origin/main --advisory
```

## What it checks

- Maximum changed lines and files
- Whether non-trivial changes include tests
- Sensitive paths such as workflows, authentication, migrations, and lockfiles
- A simple risk score that is explainable and stable
- Ignored paths that should not consume the review budget

Customize the generated `.pr-sheriff.json` to fit your repository. All matching
uses portable glob patterns.

## GitHub Action

Add `.github/workflows/pr-sheriff.yml` to your repository:

```yaml
name: PR Sheriff

on:
  pull_request:

permissions:
  contents: read
  pull-requests: write

jobs:
  review-risk:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: Hayal08/pr-sheriff@v0.4.0
        with:
          base: origin/${{ github.base_ref }}
```

The Action adds a report to the GitHub Job Summary, emits annotations for
sensitive files and policy violations, creates or updates one pull request
comment, and fails when policy is violated.

### Action inputs

| Input | Default | Purpose |
| --- | --- | --- |
| `base` | `origin/main` | Base git ref for the three-dot diff |
| `head` | `HEAD` | Head git ref for the three-dot diff |
| `config` | `.pr-sheriff.json` | Path to repository policy |
| `comment` | `true` | Create or update a report comment on pull requests |
| `mode` | `enforce` | Use `advisory` to report without failing the check |

The Action exposes `risk`, `score`, `changed-files`, `changed-lines`, and
`tests-changed` outputs for later workflow steps. The `policy-passed` output is
`false` when violations exist, including in advisory mode.

### Gradual rollout

Use advisory mode to learn what the policy would flag before making it a
required check:

```yaml
- uses: Hayal08/pr-sheriff@v0.4.0
  with:
    base: origin/${{ github.base_ref }}
    mode: advisory
```

Advisory mode keeps the Job Summary, PR comment, outputs, and annotations, but
turns policy errors into warnings and returns a successful exit code.

## Configuration

Run `pr-sheriff init` or add `.pr-sheriff.json` manually:

```json
{
  "max_changed_lines": 800,
  "max_changed_files": 30,
  "require_tests_after_lines": 120,
  "test_patterns": ["tests/**", "**/*_test.*", "**/*.test.*"],
  "sensitive_patterns": [".github/workflows/**", "**/auth/**", "**/migrations/**"],
  "ignore_patterns": ["**/*.md", "docs/**"],
  "path_rules": []
}
```

Unknown configuration keys are rejected so typos cannot silently weaken a
policy.

### Path-specific rules

Different parts of a repository can have stricter review policies. Each matched
rule is shown separately in the report:

```json
{
  "path_rules": [
    {
      "name": "database migrations",
      "patterns": ["**/migrations/**"],
      "max_changed_lines": 100,
      "require_tests_after_lines": 1
    },
    {
      "name": "frontend",
      "patterns": ["web/**"],
      "max_changed_files": 15,
      "require_tests_after_lines": 80
    }
  ]
}
```

Path rules support `max_changed_lines`, `max_changed_files`, and
`require_tests_after_lines`. Global limits still apply.

### Explainable risk score

Human-readable, JSON, Job Summary, and PR comment reports now show how changed
lines, changed files, and sensitive paths contribute to the risk score. JSON
consumers can use `score_breakdown` and `path_rule_results` for custom
dashboards or workflow decisions.

## Try it safely

Open a pull request that changes more than `require_tests_after_lines` without
changing a test file. PR Sheriff will add a policy violation to its single
updatable PR comment and fail the check. Add a test file and push again to see
the same comment update and the check pass.

For pull requests from forks, GitHub may provide a read-only token. In that
case, PR Sheriff still runs but reports that it could not update the comment.

## Philosophy

PR Sheriff does not claim to decide whether code is good. It gives maintainers a
consistent early warning so they can ask for smaller PRs, tests, or a deeper
security review.

See [CONTRIBUTING.md](CONTRIBUTING.md) to help shape the project.

## Contributing

First-time contributors are welcome. Start with a
[`good first issue`](https://github.com/Hayal08/pr-sheriff/labels/good%20first%20issue)
or read [CONTRIBUTING.md](CONTRIBUTING.md) for the local development workflow.

Useful ways to help:

- try PR Sheriff in a real repository and report confusing behavior;
- improve docs and policy examples;
- add focused policy checks with tests;
- share maintainer workflows that should influence the
  [roadmap](ROADMAP.md).

Please open an issue before starting a large change. Small pull requests are
easier to review and are a good way to get involved.
