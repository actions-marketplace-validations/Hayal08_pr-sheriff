# PR Sheriff

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

## GitHub Actions

```yaml
- uses: actions/checkout@v4
  with:
    fetch-depth: 0
- run: pip install .
- run: pr-sheriff check --base origin/${{ github.base_ref }}
```

## Philosophy

PR Sheriff does not claim to decide whether code is good. It gives maintainers a
consistent early warning so they can ask for smaller PRs, tests, or a deeper
security review.

See [CONTRIBUTING.md](CONTRIBUTING.md) to help shape the project.
