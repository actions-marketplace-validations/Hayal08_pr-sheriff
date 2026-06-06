# Roadmap

PR Sheriff aims to make pull request risk visible without replacing human
review. The roadmap is intentionally small and driven by maintainer feedback.

## Now: make adoption easy

- Add ready-to-copy policy presets for Python, JavaScript, and Rust projects.
- Improve error messages and configuration validation.
- Add documentation examples for common repository layouts.
- Collect feedback from the first repositories using the Action.

## Next: better policy checks

- Require changelog entries for user-visible changes.
- Support path-specific thresholds and policies.
- Detect dependency and public API changes.
- Explain how each part of the risk score was calculated.

## Later: larger repositories

- Add first-class monorepo support.
- Report risk separately for affected packages.
- Support reusable organization-wide policy presets.
- Explore a non-blocking advisory mode for gradual adoption.

## Not planned

- AI-generated code review or claims that a pull request is correct.
- Uploading repository code to an external service.
- Rules that cannot explain why they passed or failed.

## Help shape the roadmap

Open a feature request with a concrete maintainer workflow and example
repository structure. Small, testable improvements are preferred over broad
feature bundles.
