<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: 2025 The Linux Foundation
-->

# Changelog

All notable changes to this project will appear in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Initial release of pull-request-fixer
- Direct command interface (no subcommands)
- Support for fixing individual pull requests
- Support for bulk operations across entire GitHub organizations
- Automatic PR formatting and validation
- Dry-run mode for previewing changes
- Pre-commit hook integration
- CLI with Typer for user-friendly interface
- Rich terminal output with progress tracking
- GitHub client with GraphQL API support
- Parallel processing of repositories and PRs
- Flexible sync strategies (none, rebase, merge)
- Conflict resolution strategies

### Changed

- Project forked from markdown-table-fixer
- Renamed from pr-title-fixer to pull-request-fixer
- Removed lint command (not needed)
- Removed github subcommand (everything runs on base command)
- Updated all package references from markdown_table_fixer to pull_request_fixer
- Updated documentation to focus on PR fixing functionality
- Removed all table-related code and dependencies

## [0.1.0] - 2025-01-24

### Initial Release

- Initial project structure forked from markdown-table-fixer
- Core PR fixing functionality
- GitHub integration for bulk operations
- Command-line interface (direct command, no subcommands)
- Pre-commit configuration
- Documentation (README, CONTRIBUTING)

[Unreleased]: https://github.com/lfit/pull-request-fixer/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/lfit/pull-request-fixer/releases/tag/v0.1.0
