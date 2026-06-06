# Changelog

All notable changes to PR Sheriff are documented here.

## 0.4.0 - 2026-06-06

- Add path-specific thresholds and test requirements.
- Show an explainable risk score breakdown in every report.
- Add advisory mode for gradual, non-blocking adoption.
- Validate numeric thresholds and nested path rule configuration.
- Expose `policy-passed` as a GitHub Action output.

## 0.3.1 - 2026-06-06

- Publish PR Sheriff to the GitHub Actions Marketplace.
- Update the recommended pinned Action version.

## 0.3.0 - 2026-06-06

- Create or update a single report comment on pull requests.
- Continue analysis when fork pull requests have a read-only token.
- Add a dogfooding workflow that runs PR Sheriff on its own pull requests.
- Document the permissions and workflow needed for PR comments.

## 0.2.0 - 2026-06-06

- Add a reusable composite GitHub Action.
- Publish risk reports to the GitHub Job Summary.
- Emit GitHub annotations for sensitive files and policy violations.
- Expose risk metrics as Action outputs.

## 0.1.0 - 2026-06-06

- Initial CLI with deterministic risk scoring and policy checks.
