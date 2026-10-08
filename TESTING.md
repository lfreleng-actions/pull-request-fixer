<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: 2025 The Linux Foundation
-->

# Testing Guide

This guide covers the automated tests and how to check the tool by hand
against live pull requests.

## Automated tests

Set up the development environment first. The test dependencies live in
the `dev` extra:

```bash
uv sync --extra dev
```

### Unit tests

```bash
uv run pytest
```

The suite in `tests/` mocks the GitHub API, so it needs no token or
network access. It covers:

| File                               | Area                                 |
| ---------------------------------- | ------------------------------------ |
| `test_file_fixer_comprehensive.py` | Regex search/replace, line removal   |
| `test_pr_file_fixer_api.py`        | The `api` update method              |
| `test_pr_file_fixer_404.py`        | Handling of missing pull requests    |
| `test_git_config.py`               | Git identity and signing modes       |
| `test_graphql_queries.py`          | GraphQL queries and the client       |
| `test_pr_blocking.py`              | Blocked PR detection in `PRScanner`  |
| `test_org_result_reporting.py`     | Organization summary counts          |

pytest also writes a coverage report, and fails when coverage drops below
25%.

### CLI integration tests

```bash
uv run bash scripts/integration-test.sh
```

This script checks the installed command's help, version and argument
validation. It runs offline; see [scripts/README.md](scripts/README.md).

### Linting

```bash
prek run --files <changed files>
```

The hooks include ruff, mypy, basedpyright, markdownlint, write-good,
shellcheck, actionlint, gitleaks, reuse and gitlint. basedpyright checks
the whole project and fails on warnings as well as errors.

## Manual testing against GitHub

Changes that touch the GitHub API flows need a check against real pull
requests. Without `--dry-run` the tool edits pull requests, pushes commits
and posts comments, so:

- use repositories you control, or a test organization
- run every command with `--dry-run` first
- prefer single PR mode before organization mode

Set a token with the access described in the
[README](README.md#authentication):

```bash
export GITHUB_TOKEN=ghp_xxxxxxxxxxxxx
```

By default the tool only processes blocked pull requests. To test against
a pull request that is not blocked, add `--no-blocked-only`.

### 1. Title fix, single pull request

Pick a pull request whose title differs from its first commit's subject.

```bash
pull-request-fixer https://github.com/OWNER/REPO/pull/NUMBER \
  --fix-title --dry-run
```

Expected output for a blocked pull request, abbreviated:

```text
🔍 Processing PR: https://github.com/OWNER/REPO/pull/NUMBER
🔧 Will fix: title
...
📥 Fetching pull request metadata...
🔄 OWNER/REPO#NUMBER
     Current: <current title>
     Fixed:   <first commit subject>

✅ [DRY RUN] Would fix this PR
```

The elided lines announce dry-run mode and give the reason the pull
request counts as blocked.

Run again without `--dry-run`, then check that:

- [ ] the title now matches the first commit's subject
- [ ] the pull request has a `🛠️ Pull Request Fixer` comment
- [ ] failed check runs on the head commit restarted

### 2. Description fix and trailer removal

Use a pull request whose first commit has a body ending in trailers, for
example:

```text
Fix: Correct the widget

Explain the change.

Signed-off-by: Jane Doe <jane@example.com>
Change-Id: I0123456789abcdef0123456789abcdef01234567
```

```bash
pull-request-fixer https://github.com/OWNER/REPO/pull/NUMBER --fix-body
```

- [ ] the description reads `Explain the change.` with no trailers

### 3. Blocked-state filtering

Run against a pull request that is not blocked:

```bash
pull-request-fixer https://github.com/OWNER/REPO/pull/NUMBER --fix-title
```

- [ ] the tool prints `pull request is NOT in a blocked state` and exits
  with status 1
- [ ] adding `--no-blocked-only` processes the pull request

Run against a merged or closed pull request:

- [ ] the tool reports the state, changes nothing and exits with status 0

### 4. File fix with the `git` method

```bash
pull-request-fixer https://github.com/OWNER/REPO/pull/NUMBER \
  --fix-files \
  --file-pattern '^\./README\.md$' \
  --search-pattern 'teh' \
  --replacement 'the' \
  --dry-run --show-diff
```

- [ ] the dry run prints `Would fix 1 file` and a unified diff
- [ ] without `--dry-run`, the branch's last commit gets amended rather
  than a new commit added, keeping its message and sign-off
- [ ] the amended commit carries your signature if your Git configuration
  signs commits
- [ ] `--bot-identity` commits as `pull-request-fixer` without signing
- [ ] the pull request has a comment showing the command options and diff

### 5. File fix with the `api` method

Use a pull request whose branch lives in the base repository, such as a
Dependabot pull request:

```bash
pull-request-fixer https://github.com/OWNER/REPO/pull/NUMBER \
  --fix-files --update-method api \
  --file-pattern '^\./README\.md$' \
  --search-pattern 'teh' --replacement 'the'
```

- [ ] the branch gains one new commit titled `Fix 1 file(s) in PR #NUMBER`
  (if the batch commit fails, the tool falls back to one `Fix <path>`
  commit per file)
- [ ] `--pr-content-only` limits changes to files the pull request already
  changes

### 6. Organization scan

```bash
pull-request-fixer myorg --fix-title --dry-run
```

Expected output, abbreviated:

```text
🔍 Scanning organization: myorg
🔧 Will fix: titles
🚫 Only processing blocked/unmergeable PRs (default)
...
✓ Token validated for user: <login>

✅ Scan completed
📊 Found 3 blocked PRs out of 40 total PRs across 25 repositories

🔍 Examining blocked pull requests

🔄 myorg/repo-a#12
     Current: Bump foo from 1.0 to 2.0
     Fixed:   Chore: Bump foo
☑️  Would apply fixes to 1 blocked pull request
```

- [ ] the organization URL form (`https://github.com/myorg`) behaves the
  same
- [ ] `--no-blocked-only` prints `Processing ALL PRs (not just blocked
  ones)` and considers every open pull request
- [ ] `--include-drafts` adds draft pull requests
- [ ] `--workers 2` bounds concurrency
- [ ] `--quiet` prints errors only

### 7. Input validation

These cases need no token:

```bash
pull-request-fixer                                  # missing TARGET
pull-request-fixer myorg                            # no --fix-* option
pull-request-fixer myorg --fix-files --search-pattern x --replacement y
pull-request-fixer myorg --fix-title --update-method ftp
pull-request-fixer myorg --fix-title --bot-identity --disable-signing
```

Each prints an error and exits with status 1.
`scripts/integration-test.sh` automates these checks.

## Reporting issues

When reporting a problem, include:

1. the command you ran, with the token removed
2. the full output with `--verbose`
3. the expected and actual behaviour
4. the token type and scopes (never the token itself)
5. the pull request or organization, if public
