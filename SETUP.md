<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: 2025 The Linux Foundation
-->

# Setup Guide

This guide covers installing `pull-request-fixer`, running it on a
schedule in GitHub Actions, and setting up a development environment.

## Table of Contents

- [Quick Start](#quick-start)
- [Installation Methods](#installation-methods)
- [Requirements](#requirements)
- [Running in GitHub Actions](#running-in-github-actions)
- [Development Setup](#development-setup)
- [Troubleshooting](#troubleshooting)

## Quick Start

```bash
# Install
uv tool install pull-request-fixer

# Provide a GitHub token
export GITHUB_TOKEN=ghp_xxxxxxxxxxxxx

# Preview title fixes for blocked pull requests in an organization
pull-request-fixer myorg --fix-title --dry-run
```

## Installation Methods

### Using uv

```bash
uv tool install pull-request-fixer
```

Or run it without installing:

```bash
uvx pull-request-fixer --help
```

### Using pip

```bash
pip install pull-request-fixer
```

### From source

```bash
git clone https://github.com/lfreleng-actions/pull-request-fixer.git
cd pull-request-fixer
uv tool install .
```

## Requirements

- Python 3.10 or higher
- A GitHub token; see the [README](README.md#authentication) for the
  access it needs
- `git` on `PATH` for `--fix-files`, except with
  `--update-method api --pr-content-only`
- For signed commits with the default `git` update method, a working
  signing setup in your global Git configuration (for example an SSH key
  loaded in `ssh-agent`, or `gpg-agent`)

## Running in GitHub Actions

The tool has no GitHub Action wrapper; install and run the CLI in a
workflow step. This example fixes the titles of blocked pull requests
across the repository owner's organization every weekday morning:

```yaml
name: 'Fix blocked pull requests'

# yamllint disable-line rule:truthy
on:
  schedule:
    - cron: '0 6 * * 1-5'
  workflow_dispatch:

permissions: {}

jobs:
  fix-titles:
    runs-on: ubuntu-latest
    timeout-minutes: 30
    steps:
      # yamllint disable-line rule:line-length
      - uses: astral-sh/setup-uv@c18668ad3cf93ea998bef934396af7bb5c839dc7  # v10.2.0

      - name: 'Fix pull request titles'
        env:
          GITHUB_TOKEN: ${{ secrets.PR_FIXER_TOKEN }}
          ORG: ${{ github.repository_owner }}
        run: |
          uvx pull-request-fixer@0.1.7 "$ORG" --fix-title
```

Notes:

- The workflow's own `GITHUB_TOKEN` only covers the repository that runs
  the workflow. To scan and update an organization, store a personal
  access token or GitHub App token with the access listed in the
  [README](README.md#authentication) as a secret, here `PR_FIXER_TOKEN`.
- Pin actions to commit SHAs and the tool to a version, as shown.
- Pass values such as the organization through `env:` rather than
  expanding `${{ }}` expressions inside `run:`, to avoid template
  injection.
- A runner has no signing keys, so use `--bot-identity` or
  `--disable-signing` with `--fix-files`, or `--update-method api` for
  pull requests whose branch lives in the base repository.
- Try a new configuration with `--dry-run` from `workflow_dispatch` first.

## Development Setup

### Prerequisites

- Python 3.10 or higher
- Git
- [uv](https://docs.astral.sh/uv/)
- [prek](https://github.com/j178/prek)

### Full Development Environment

```bash
git clone https://github.com/lfreleng-actions/pull-request-fixer.git
cd pull-request-fixer

# Install the package with the test and lint dependencies
uv sync --extra dev

# Install the Git hooks
prek install -t pre-commit -t commit-msg
```

### Running Tests

```bash
# Unit tests, with coverage
uv run pytest

# A single test file
uv run pytest tests/test_file_fixer_comprehensive.py -v

# Offline CLI integration tests
uv run bash scripts/integration-test.sh
```

### Code Quality Checks

```bash
# Hooks, on the files you changed
prek run --files <changed files>

# Individual tools
uv run ruff check src tests scripts
uv run ruff format --check src tests scripts
uv run mypy src
```

### Building the Package

```bash
uv build
```

The build writes a source distribution and a wheel to `dist/`. hatch-vcs
derives the version from the latest Git tag.

## Troubleshooting

### `pull-request-fixer: command not found`

`uv tool install` places the command in uv's tool directory. Run
`uv tool update-shell` to add it to `PATH`, then open a new shell.

### `ModuleNotFoundError: No module named 'pytest'`

Install the development dependencies with `uv sync --extra dev`. Plain
`uv sync` skips the `dev` extra.

### `GitHub token required`

Set `GITHUB_TOKEN` or pass `--token`.

### Git errors with `--fix-files`

- `git: command not found`: install Git, or use
  `--update-method api --pr-content-only` for pull requests whose branch
  lives in the base repository.
- Signing failures: make sure your signing agent is running, or pass
  `--disable-signing` or `--bot-identity`.
- `Push rejected`: someone pushed to the branch while the tool worked;
  run it again.

### macOS SSL errors

Update the certificate bundle:

```bash
pip install --upgrade certifi
```

## Getting Help

If you encounter issues not covered here:

1. Check the
   [GitHub Issues](https://github.com/lfreleng-actions/pull-request-fixer/issues)
2. Review the [README](README.md) and [TESTING.md](TESTING.md)
3. Open a new issue with your operating system, Python version, tool
   version, the command you ran (without the token) and its output with
   `--verbose`

## Next Steps

- Review [FEATURES.md](FEATURES.md) for a feature overview
- Read [IMPLEMENTATION.md](IMPLEMENTATION.md) for the internals
- Read [CONTRIBUTING.md](CONTRIBUTING.md) if you want to contribute
- Check [CHANGELOG.md](CHANGELOG.md) for version history
