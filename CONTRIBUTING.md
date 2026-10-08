<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: 2025 The Linux Foundation
-->

# Contributing to Pull Request Fixer

Thank you for your interest in contributing to `pull-request-fixer`. This
document explains how to set up a development environment and what a
pull request needs before maintainers can merge it.

Contributions follow the `lfreleng-actions` organization guidelines:
<https://github.com/lfreleng-actions/.github/blob/main/AGENTS.md>. Where
this document and those guidelines disagree, the guidelines win.

## Code of Conduct

This project follows The Linux Foundation's Code of Conduct. Please be
respectful and professional in all interactions.

## Getting Started

### Prerequisites

- Python 3.10 or higher
- [uv](https://docs.astral.sh/uv/)
- Git, with commit signing configured
- [prek](https://github.com/j178/prek) to run the pre-commit hooks

### Development Setup

1. Fork the repository on GitHub.
2. Clone your fork:

   ```bash
   git clone https://github.com/YOUR_USERNAME/pull-request-fixer.git
   cd pull-request-fixer
   ```

3. Install the package and its development dependencies. The test
   dependencies live in the `dev` extra, so plain `uv sync` is not
   enough:

   ```bash
   uv sync --extra dev
   ```

4. Install the Git hooks:

   ```bash
   prek install -t pre-commit -t commit-msg
   ```

## Development Workflow

### Making Changes

1. Create a branch for your change.
2. Write the code, following the coding standards below.
3. Add or update tests.
4. Update the documentation when behaviour or options change: the
   [README](README.md) documents every option.
5. Run the tests and hooks.

### Testing

```bash
uv run pytest
uv run bash scripts/integration-test.sh
```

The unit tests mock the GitHub API and need no token. Changes to the
GitHub flows also need a manual check against real pull requests; see
[TESTING.md](TESTING.md).

### Code Quality

Run every hook against the files you changed:

```bash
prek run --files <changed files>
```

The hooks include ruff, mypy, basedpyright, markdownlint, write-good,
shellcheck, actionlint, reuse, gitlint and pytest. Do not bypass them
with `--no-verify`.

### Commit Messages

Commit subjects use a capitalized
[Conventional Commits](https://www.conventionalcommits.org/) type, which
gitlint enforces:

```text
Type(scope): Imperative description
```

The allowed types are `Fix`, `Feat`, `Chore`, `Docs`, `Style`,
`Refactor`, `Perf`, `Test`, `Revert`, `CI` and `Build`. The scope is
optional.

- Use the imperative mood ("Add option", not "Added option").
- Keep the subject short and omit a trailing period.
- Separate the subject from the body with a blank line, and wrap the body
  at 72 characters.
- Explain what the change does and why in the body.

Example:

```text
Docs: Explain anchoring in file patterns

An unanchored --file-pattern matches anywhere in a path, so
'./action.yaml' also selects action.yaml files in subdirectories.
Show anchored patterns in the README examples.
```

### Signing and Sign-off

Every commit must carry a cryptographic signature and a Developer
Certificate of Origin sign-off:

```bash
git commit --gpg-sign --signoff
```

`--gpg-sign` (`-S`) signs the commit and `--signoff` (`-s`) adds the
`Signed-off-by` line certifying that you have the right to submit the
code under the project's license.
Maintainers cannot merge a pull request containing any unsigned commit.

If an AI coding agent helped write the change, add a `Co-authored-by`
trailer naming it.

## Pull Request Process

1. Ensure tests and hooks pass.
2. Open a pull request against `main`.
3. For a pull request with a single commit, make the pull request title
   identical to the commit subject; a CI check enforces this.
4. Respond to review feedback. A maintainer from the Release Engineering
   team must approve the pull request before it merges.

Keep each pull request focused on one change.

## Coding Standards

### Python Style

- ruff handles linting and formatting; the line length limit is 80
  characters
- type hints on every function; mypy runs in strict mode
- double quotes for strings
- new source files need SPDX license headers; `reuse lint` checks them

### Documentation

- Docstrings for all public modules, classes and functions, in Google
  style
- Keep the README options table in step with the CLI

Example docstring:

```python
def parse_commit_message(message: str) -> tuple[str, str]:
    """Parse a commit message into subject and body.

    Args:
        message: Full commit message

    Returns:
        Tuple of (subject, body) where body has trailers removed
    """
```

## Test Coverage

- Write tests for new features and bug fixes
- Mock GitHub API calls; unit tests must not need network access
- Use descriptive test names and fixtures for shared setup

## Reporting Issues

### Bug Reports

Include:

- a clear description of the problem
- the command you ran, with the token removed
- the output with `--verbose`
- expected and actual behaviour
- your environment (OS, Python version, tool version)

Report security vulnerabilities privately; see [SECURITY.md](SECURITY.md).

### Feature Requests

Include:

- the problem the feature solves
- how you would expect it to work
- any alternatives you considered

## License

By contributing to this project, you agree that your contributions will
fall under the Apache License 2.0.

## Questions?

If you have questions about contributing, please open an issue on GitHub
or reach out to the maintainers.
