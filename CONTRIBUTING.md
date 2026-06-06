# Contributing

Thank you for helping make pull request review more manageable.

## First contribution

1. Pick a [`good first issue`](https://github.com/Hayal08/pr-sheriff/labels/good%20first%20issue)
   and comment that you would like to work on it.
2. Fork the repository and create a focused branch.
3. Make the change and add or update tests.
4. Run `PYTHONPATH=src python -m unittest discover -s tests -v`.
5. Open a pull request and explain the behavior change.

No issue is too small to ask questions on. Maintainers should respond with
clarification or a smaller suggested scope when needed.

## Development

PR Sheriff supports Python 3.10 and newer and has no runtime dependencies.

```bash
git clone https://github.com/Hayal08/pr-sheriff.git
cd pr-sheriff
PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONPATH=src python -m pr_sheriff --help
```

## Pull request guidelines

- Open an issue before large behavior changes.
- Keep pull requests focused and include tests.
- Update README or changelog text for user-visible behavior.
- Explain tradeoffs and anything maintainers should verify manually.
- Preserve zero runtime dependencies unless there is a strong, documented
  reason otherwise.

By contributing, you agree to follow the [Code of Conduct](CODE_OF_CONDUCT.md).
