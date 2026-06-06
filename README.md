# PR Sheriff

[![CI](https://github.com/Hayal08/pr-sheriff/actions/workflows/ci.yml/badge.svg)](https://github.com/Hayal08/pr-sheriff/actions/workflows/ci.yml)

PR Sheriff is a tiny, deterministic pull request risk checker for busy open-source
maintainers. It catches oversized changes, missing tests, and edits to sensitive
files before review time is spent.

It has no runtime dependencies, sends no code anywhere, and works in any Git
repository.

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
      - uses: Hayal08/pr-sheriff@v0.3.0
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

The Action exposes `risk`, `score`, `changed-files`, `changed-lines`, and
`tests-changed` outputs for later workflow steps.

## Configuration

Run `pr-sheriff init` or add `.pr-sheriff.json` manually:

```json
{
  "max_changed_lines": 800,
  "max_changed_files": 30,
  "require_tests_after_lines": 120,
  "test_patterns": ["tests/**", "**/*_test.*", "**/*.test.*"],
  "sensitive_patterns": [".github/workflows/**", "**/auth/**", "**/migrations/**"],
  "ignore_patterns": ["**/*.md", "docs/**"]
}
```

Unknown configuration keys are rejected so typos cannot silently weaken a
policy.

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
