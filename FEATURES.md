<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: 2025 The Linux Foundation
-->

# Pull Request Fixer - Features

This document summarizes what `pull-request-fixer` does. The
[README](README.md) covers usage and every option in detail.

## Targets and scope

- **Single pull request**: pass a pull request URL to fix that pull
  request.
- **Whole organization**: pass an organization name or URL to scan every
  repository in the organization and fix the matching pull requests in
  parallel.
- **Blocked pull requests by default**: both modes act only on pull
  requests with merge conflicts, a head branch behind its base, or failing
  checks. The blocking logic comes from [dependamerge][dependamerge].
  `--no-blocked-only` lifts the restriction.
- **Drafts excluded by default**: `--include-drafts` adds them.
- **GitHub.com**: the tool targets the public GitHub API.

## Title and description fixes

- **`--fix-title`** sets the title to the first commit's subject line.
- **`--fix-body`** sets the description to the first commit's body.
- **Trailer removal**: `--fix-body` strips trailing Git trailers
  (`Signed-off-by:`, `Co-authored-by:`, `Change-Id:` and others) from the
  description.
- **No-op when correct**: the tool only updates fields that differ, so
  repeat runs make no further changes.
- **Check re-runs**: after an update, the tool re-requests failed,
  cancelled, timed-out and action-required check runs, so title checks
  can pass without a new push.

## File fixes

- **Regex file selection**: `--file-pattern` selects files by path.
- **Search and replace**: `--search-pattern` with `--replacement`, with
  multi-line matching and back-references.
- **Line removal**: `--remove-lines`, optionally limited to the lines
  between `--context-start` and `--context-end` markers.
- **Scope control**: by default the tool edits every matching file in the
  repository; `--pr-content-only` limits it to files the pull request
  changes.
- **Two update methods**:
  - `git` (default): clones the pull request branch, amends its last
    commit and pushes with `--force-with-lease`. It keeps the commit
    message and sign-off, signs with your local Git signing setup, and
    supports pull requests from forks.
  - `api`: adds a new commit through the GitHub Git Data API, for pull
    requests whose branch lives in the base repository.
- **Identity control** for the `git` method: inherit your Git identity and
  signing setup, keep your identity without signing
  (`--disable-signing`), or commit as a bot (`--bot-identity`).
- **Diffs**: `--show-diff` prints a unified diff for each changed file.

## Safety and feedback

- **Dry run**: `--dry-run` previews every change without applying it.
- **Pull request comments**: after applying changes, the tool comments on
  the pull request to say what changed and, for file fixes, how.
- **Token checks**: organization mode validates the token and warns about
  missing `repo` or `read:org` scopes before scanning.
- **Token redaction**: the tool strips GitHub tokens and credentialed URLs
  from Git error output.
- **Retries**: GitHub API calls retry with exponential backoff.
- **Isolated clones**: file fixes clone into temporary directories that
  the tool deletes afterwards.

## Output and performance

- **Progress display**: a live progress display during organization
  scans.
- **Parallel processing**: `--workers` (1-32) sets repository-scan and
  pull-request concurrency; it defaults to the machine's performance core
  count.
- **Logging control**: `--verbose`, `--quiet` and `--log-level`.

## Limitations

- `--fix-files` and the title and description fixes cannot run in the
  same invocation; with `--fix-files` set, the tool ignores the others.
- The `api` update method does not support pull requests from forks,
  writes files with mode `100644`, and creates commits without a DCO
  sign-off.
- The tool has no configuration file; pass every setting on the command
  line.

[dependamerge]: https://github.com/lfreleng-actions/dependamerge
