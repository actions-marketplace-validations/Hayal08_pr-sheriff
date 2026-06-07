# Changelog

All notable changes to PR Sheriff are documented here.

## 0.6.0 - 2026-06-07

- Add `pr-sheriff install-github --detect` for automatic policy selection.
- Detect Python, JavaScript/TypeScript, mixed, and unknown repositories.
- Explain the selected preset and the project markers used as evidence.

## 0.5.0 - 2026-06-07

- Add ready-made Python and JavaScript/TypeScript policy presets.
- Add `pr-sheriff install-github` for a one-command GitHub Action setup.
- Default generated workflows to advisory mode for a gradual rollout.
- Add a manual trusted-publishing workflow for PyPI.
- Validate installer paths, custom config wiring, annotations, and package builds.
- Generate Node.js 24-compatible GitHub Actions workflows.

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
