<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: 2025 The Linux Foundation
-->

<!-- markdownlint-configure-file { "MD024": { "siblings_only": true } } -->

# Changelog

All notable changes to this project will appear in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

This file records user-facing changes. The
[GitHub releases](https://github.com/lfreleng-actions/pull-request-fixer/releases)
list every merged pull request, including dependency updates.

## [Unreleased]

### Changed

- Rename the base exception `PRTitleFixerError` to `PullRequestFixerError`;
  the old name remains as an alias
- Rewrite the documentation, which still described the parent
  `markdown-table-fixer` project in places, to match the tool's behaviour
- Replace the inherited `scripts/integration-test.sh` with offline tests
  of this CLI

### Removed

- The placeholder `action.yaml`, which never ran the tool
- The `.pre-commit-hooks.yaml` hook definition; the tool acts on remote
  pull requests and cannot run as a pre-commit hook
- The unused `pull_request_fixer.pr_fixer` module and the unused
  `OutputFormat`, `BlockedPR` and `GitHubScanResult` models

### Fixed

- Stop tracking the generated `_version.py` (#351)

## [0.1.7] - 2026-09-23

### Fixed

- Keep the coverage data file outside the working tree (#323)

## [0.1.6] - 2026-07-24

### Changed

- Clear aislop findings and typing warnings (#258)

## [0.1.5] - 2026-07-22

### Changed

- Reduce code complexity (#251)
- Require `dependamerge>=0.9.1` (#250)

### Security

- Resolve zizmor workflow findings (#211, #236)
- Bump setuptools to 83.0.0 for GHSA-h35f-9h28-mq5c (#252)

## [0.1.4] - 2026-06-18

### Fixed

- Point project URLs at the `lfreleng-actions` organization (#115)
- Resolve CodeQL findings, including validating the host when parsing
  organization URLs (#200)

### Added

- Security policy (#196)

## [0.1.3] - 2026-04-01

### Security

- Bump Pygments to 2.20.0 (#107)

## [0.1.2] - 2026-03-27

### Fixed

- Match file patterns against paths with a `./` prefix in the `api`
  update method (#8)
- Linting and typing failures (#14, #104)

### Changed

- Detect blocked pull requests with dependamerge's logic (#14)

## [0.1.1] - 2025-12-03

### Added

- `--fix-files`: regex search/replace and line removal for files in pull
  requests (#3)
- The `api` update method for file fixes (#5)

### Changed

- Clearer pull request comment format (#4)

## [0.1.0] - 2025-11-27

### Added

- Initial release, derived from the `markdown-table-fixer` codebase
- Fix pull request titles and descriptions from the first commit's
  message, for one pull request or across a GitHub organization
- Blocked pull request filtering, dry-run mode and parallel processing

[Unreleased]: https://github.com/lfreleng-actions/pull-request-fixer/compare/v0.1.7...HEAD
[0.1.7]: https://github.com/lfreleng-actions/pull-request-fixer/compare/v0.1.6...v0.1.7
[0.1.6]: https://github.com/lfreleng-actions/pull-request-fixer/compare/v0.1.5...v0.1.6
[0.1.5]: https://github.com/lfreleng-actions/pull-request-fixer/compare/v0.1.4...v0.1.5
[0.1.4]: https://github.com/lfreleng-actions/pull-request-fixer/compare/v0.1.3...v0.1.4
[0.1.3]: https://github.com/lfreleng-actions/pull-request-fixer/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/lfreleng-actions/pull-request-fixer/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/lfreleng-actions/pull-request-fixer/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/lfreleng-actions/pull-request-fixer/releases/tag/v0.1.0
