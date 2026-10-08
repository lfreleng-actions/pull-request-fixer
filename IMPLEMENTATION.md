<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: 2025 The Linux Foundation
-->

# Implementation Guide

This document describes how `pull-request-fixer` works internally. See the
[README](README.md) for usage.

## Module map

<!-- markdownlint-disable MD013 -->

| Module                  | Responsibility                                                                                          |
| ----------------------- | ------------------------------------------------------------------------------------------------------- |
| `cli.py`                | Typer entry point, argument validation, single-PR and organization flows, title/body fixes, PR comments |
| `blocked_pr_scanner.py` | Wraps dependamerge's `GitHubService` to find blocked PRs across an organization                         |
| `pr_scanner.py`         | GraphQL organization scanner used with `--no-blocked-only`                                              |
| `graphql_queries.py`    | GraphQL queries for the scanner                                                                         |
| `github_client.py`      | Async `httpx` client for the GitHub REST, GraphQL and Git Data APIs, with retries                       |
| `pr_file_fixer.py`      | `--fix-files` orchestration for the `git` and `api` update methods                                      |
| `file_fixer.py`         | Finds files by regex and applies search/replace or line removal                                         |
| `git_config.py`         | Configures Git identity and signing in temporary clones                                                 |
| `progress_tracker.py`   | Rich live progress display for organization scans                                                       |
| `models.py`             | Dataclasses: `PRInfo`, `FileModification`, `FileFixSpec`, `FixOptions`, `GitHubFixResult`               |
| `exceptions.py`         | `PullRequestFixerError` and its subclasses                                                              |

<!-- markdownlint-enable MD013 -->

## Entry point and dispatch

The `pull-request-fixer` console script calls `cli.cli()`, which runs
`main()` through `typer.run`. `main()`:

1. Validates options: a target, a valid `--update-method`, compatible
   identity flags, at least one `--fix-*` option, the `--fix-files`
   requirements, then a token.
2. Maps the identity flags to a `GitConfigMode` (`USER_INHERIT`,
   `USER_NO_SIGN` or `BOT_IDENTITY`).
3. Bundles the settings into a `FixOptions` dataclass.
4. Calls `parse_target()`, which classifies the target. Anything
   containing `/pull/` or `/pulls/` is a pull request URL. A URL whose
   host is `github.com` yields the first path segment as the organization.
   Anything else counts as an organization name.
5. Runs `process_single_pr()` or `scan_and_fix_organization()` with
   `asyncio.run`.

## Single pull request flow

`process_single_pr()`:

1. Without `--no-blocked-only`, fetches the pull request's state,
   mergeability and status check rollup over GraphQL. It exits `0` for a
   closed or merged pull request. It asks `BlockedPRScanner` whether the
   pull request counts as blocked and exits `1` if not.
2. With `--fix-files`, hands off to `PRFileFixer.fix_pr_by_url()`, prints
   the result, posts a summary comment and returns.
3. Otherwise fetches the pull request over REST and calls `process_pr()`.

## Organization flow

`scan_and_fix_organization()`:

1. Validates the token with `GET /user` and inspects the
   `X-OAuth-Scopes` header for `repo`/`public_repo` and `read:org`.
2. Collects pull requests with `_collect_org_prs()`:
   - blocked-only (default): `BlockedPRScanner` calls dependamerge's
     `GitHubService.scan_organization()` and yields each unmergeable pull
     request;
   - `--no-blocked-only`: `PRScanner` pages through repositories and their
     open pull requests over GraphQL, skipping drafts unless you pass
     `--include-drafts`.
3. Processes the collected pull requests concurrently, bounded by an
   `asyncio.Semaphore(workers)`. Each task runs `_process_pr_files()` for
   `--fix-files`, or `process_pr()` otherwise.
4. Gathers results with `return_exceptions=True`, so one failure does not
   stop the others, and prints a summary through `_report_org_results()`.

If scanning fails part-way, the tool processes the pull requests found
before the error.

## Blocked pull request detection

`BlockedPRScanner` delegates to dependamerge so both tools agree on what
"blocked" means. dependamerge reports a pull request as blocked when:

- `mergeable` is `CONFLICTING` or `mergeStateStatus` is `dirty`
- `mergeStateStatus` is `behind`
- the head commit's status check rollup contains failing checks

Draft status counts only with `--include-drafts`.

## Title and description fixes

`process_pr()`:

1. `get_first_commit_info()` lists the pull request's commits
   (`GET /repos/{owner}/{repo}/pulls/{number}/commits`) and takes the
   first entry.
2. `parse_commit_message()` splits the message into a subject (first line)
   and a body. Walking back from the end of the body, it drops blank lines
   and lines matching a known trailer prefix, stopping at the first other
   line.
3. When a field differs, `update_pr_title()` or `update_pr_body()` sends
   `PATCH /repos/{owner}/{repo}/pulls/{number}`.
4. After a successful update, `rerun_failed_checks()` finds the head
   commit's completed check runs with conclusion `failure`, `cancelled`,
   `timed_out` or `action_required` and re-requests each one.
5. `create_pr_comment()` posts a summary comment.

## File fixes

`PRFileFixer.fix_pr_by_url()` fetches the pull request over REST, rejects
closed pull requests, builds a `FileFixSpec` and routes to an update
method.

### `git` method (`_fix_pr_with_git`)

1. Clones the head repository's pull request branch into a temporary
   directory, authenticating with the token in the HTTPS URL.
2. Finds matching files with `FileFixer.find_files()`; with
   `--pr-content-only`, keeps only the pull request's changed files.
3. Applies `FileFixer.remove_lines_matching()` or `FileFixer.apply_fix()`
   to each file.
4. In dry-run mode, returns the would-be modifications.
5. Otherwise configures identity and signing through
   `configure_git_identity()`, stages the files, runs
   `git commit --amend --no-edit` and
   `git push --force-with-lease origin <branch>`.

`_sanitize_message()` strips tokens and credentialed URLs from any Git
error before the tool logs or returns it.

### `api` method (`_fix_pr_with_api`)

1. Lists candidate files: the pull request's changed files with
   `--pr-content-only`, otherwise every file from a shallow clone of the
   branch.
2. Fetches each file's content through the Contents API from the base
   repository at the head branch, and applies the fix to a temporary
   copy.
3. Writes all changed files in one commit through the Git Data API (blobs,
   tree, commit, then a reference update). If that fails, it falls back to
   one Contents API commit per file.

### File matching and editing

- `find_files()` walks the clone and tests the compiled `--file-pattern`
  with `re.search` against each relative path, with and without a `./`
  prefix.
- `apply_fix()` runs `re.sub` over the whole file with `re.MULTILINE`.
- `remove_lines_matching()` processes the file line by line. A
  `--context-start` match turns removal on, a `--context-end` match turns
  it off, and the tool keeps both marker lines. With no start pattern,
  removal starts on.

## Git identity and signing

`configure_git_identity()` writes repository-local Git configuration in
the temporary clone:

- `USER_INHERIT`: copies the global `user.name` and `user.email`; when
  `commit.gpgsign` is `true`, also copies `gpg.format`, `user.signingkey`,
  and the SSH (`gpg.ssh.*`) or GPG (`gpg.program`) settings.
- `USER_NO_SIGN`: copies the identity and sets `commit.gpgsign=false`.
- `BOT_IDENTITY`: uses `pull-request-fixer <noreply@linuxfoundation.org>`
  and sets `commit.gpgsign=false`, so a global signing setting cannot
  make the bot try to sign.

Without a global `user.name` and `user.email`, both user modes fall back
to the bot identity, also unsigned.

## GitHub API client

`GitHubClient` makes requests with `httpx.AsyncClient`. `_request()` and
`_graphql_request()` retry up to three times with exponential backoff
through `tenacity`, except on `ResourceNotFoundError` (HTTP 404).

## Error handling

- Expected failures (`ResourceNotFoundError`, `FileAccessError`,
  `GitHubAPIError`) print a short message and exit `1`.
- Per-pull-request failures in organization mode count as failed updates
  and do not stop the run.
- Comments and check re-runs are best-effort; the tool ignores their
  failures.

## Testing

Unit tests live in `tests/` and run with `uv run pytest`.
`scripts/integration-test.sh` checks the installed CLI offline.
[TESTING.md](TESTING.md) describes manual testing against live pull
requests.
