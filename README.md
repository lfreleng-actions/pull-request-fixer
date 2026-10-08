<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: 2025 The Linux Foundation
-->

# 🛠️ Pull Request Fixer

A Python command-line tool that repairs GitHub pull requests in place. It
can work on one pull request or scan a whole GitHub organization, and it
can:

- set a pull request's **title** to the subject line of its first commit
- set a pull request's **description** to the body of its first commit,
  minus Git trailers such as `Signed-off-by:`
- apply regex **search/replace or line removal to files** on the pull
  request's branch, then push the result back to the pull request

A common use is unblocking automated pull requests (Dependabot,
pre-commit.ci and similar) that fail a semantic title check or carry a
small, mechanical defect across a whole organization.

By default the tool only touches **blocked** pull requests: those with
merge conflicts, those behind their base branch, or those with failing
checks.

## Contents

- [Installation](#installation)
- [Quick start](#quick-start)
- [Targets](#targets)
- [Which pull requests get processed](#which-pull-requests-get-processed)
- [Fixing titles and descriptions](#fixing-titles-and-descriptions)
- [Fixing files](#fixing-files)
- [Pull request comments](#pull-request-comments)
- [Options](#options)
- [Authentication](#authentication)
- [Exit status](#exit-status)
- [Troubleshooting](#troubleshooting)
- [Development](#development)

## Installation

The tool needs Python 3.10 or newer. File fixing also needs `git` on
`PATH`, except with `--update-method api --pr-content-only`.

```bash
pip install pull-request-fixer
```

Or with uv:

```bash
uv tool install pull-request-fixer
```

## Quick start

```bash
export GITHUB_TOKEN=ghp_xxxxxxxxxxxxx

# Preview title fixes for blocked pull requests across an organization
pull-request-fixer myorg --fix-title --dry-run

# Fix titles and descriptions for real
pull-request-fixer myorg --fix-title --fix-body

# Fix the title of one pull request
pull-request-fixer https://github.com/owner/repo/pull/123 --fix-title

# Remove 'type:' lines from the inputs section of a root action.yaml
pull-request-fixer https://github.com/owner/repo/pull/123 \
  --fix-files \
  --file-pattern '^\./action\.yaml$' \
  --search-pattern '^\s+type:\s+\S' \
  --remove-lines \
  --context-start '^inputs:' \
  --context-end '^runs:' \
  --dry-run --show-diff
```

The tool needs at least one of `--fix-title`, `--fix-body` or
`--fix-files`; without one it prints a warning and exits.

## Targets

`TARGET` is the only positional argument. It can be:

| Form              | Example                                  | Mode         |
| ----------------- | ---------------------------------------- | ------------ |
| Organization name | `myorg`                                  | Organization |
| Organization URL  | `https://github.com/myorg`               | Organization |
| Pull request URL  | `https://github.com/owner/repo/pull/123` | Single PR    |

The tool works with GitHub.com; it does not support GitHub Enterprise
Server hosts.

In **organization mode** the tool validates the token, scans every
repository in the organization for open pull requests, then processes the
matching pull requests in parallel.

In **single PR mode** the tool processes the one pull request. Unless you
pass `--no-blocked-only`, it reports a closed or merged pull request and
exits without changing it; `--fix-files` always refuses closed pull
requests.

## Which pull requests get processed

Both modes process only blocked pull requests unless you pass
`--no-blocked-only`. The tool reuses the blocking logic from
[dependamerge][dependamerge], so both tools agree on which pull requests
count as blocked. A pull request counts as blocked when it has:

- merge conflicts (`mergeable: CONFLICTING` or merge state `dirty`)
- a head branch behind its base branch (merge state `behind`)
- one or more failing status checks or check runs

The organization scan skips draft pull requests unless you pass
`--include-drafts`.

In single PR mode, if the pull request is not blocked, the tool prints
`pull request is NOT in a blocked state` and exits with status 1. Add
`--no-blocked-only` to process it anyway.

## Fixing titles and descriptions

Both fixes read the **first** (oldest) commit on the pull request.

### `--fix-title`

Sets the pull request title to the first commit's subject line, when the
two differ.

### `--fix-body`

Sets the pull request description to the first commit's message body,
when the commit has a body. The tool strips trailing Git trailers from
the body. It recognizes these trailers, case-insensitively:

`Signed-off-by:`, `Co-authored-by:`, `Reviewed-by:`, `Tested-by:`,
`Acked-by:`, `Cc:`, `Reported-by:`, `Suggested-by:`, `Fixes:`,
`See-also:`, `Link:`, `Bug:`, `Change-Id:`

For example, given this first commit:

```text
Fix: Correct race condition in calendar refresh

Serialize refreshes so concurrent updates cannot interleave.

Signed-off-by: Jane Doe <jane@example.com>
```

`--fix-title` sets the title to
`Fix: Correct race condition in calendar refresh`, and `--fix-body` sets
the description to
`Serialize refreshes so concurrent updates cannot interleave.`

After updating a title or description, the tool asks GitHub to re-run any
of the pull request's check runs that ended as failed, cancelled, timed
out or action required. This lets checks such as a semantic pull request
title check pick up the change. Re-running checks is best-effort; the
tool ignores checks that GitHub refuses to re-run.

## Fixing files

`--fix-files` edits files on the pull request's head branch. When you
pass `--fix-files`, the tool **ignores** `--fix-title` and `--fix-body`;
run the tool twice to do both.

`--fix-files` needs:

- `--file-pattern`: a Python regular expression for the files to edit
- `--search-pattern`: a Python regular expression for the content to
  change
- one action: `--replacement TEXT` or `--remove-lines`

### Selecting files

The tool tests `--file-pattern` with `re.search` against each file's
repository-relative path, both as `path/to/file` and as
`./path/to/file`. The pattern can match anywhere in the path, and `.`
matches any character, so `./action.yaml` also matches
`sub/dir/action.yaml`. Anchor and escape the pattern to match one file:

<!-- markdownlint-disable MD013 -->

| Pattern                | Matches                                     |
| ---------------------- | ------------------------------------------- |
| `^\./action\.yaml$`    | `action.yaml` at the repository root only   |
| `(^\|/)action\.ya?ml$` | `action.yaml` or `action.yml` in any folder |
| `\.github/workflows/`  | every file under `.github/workflows/`       |

<!-- markdownlint-enable MD013 -->

By default the tool considers every matching file in the repository at
the pull request's head commit. Add `--pr-content-only` to restrict it to
files the pull request already changes.

### Search and replace

With `--replacement`, the tool runs `re.sub` over each file's whole
content with `re.MULTILINE` set, so `^` and `$` match at line boundaries.
The replacement supports back-references such as `\1`. An empty
replacement (`--replacement ''`) deletes the matched text.

```bash
pull-request-fixer https://github.com/owner/repo/pull/456 \
  --fix-files \
  --file-pattern '\.py$' \
  --search-pattern '\bold_function_name\b' \
  --replacement 'new_function_name'
```

### Line removal

With `--remove-lines`, the tool deletes every line that matches
`--search-pattern`. Two optional patterns limit where removal applies:

- `--context-start`: removal begins after a line matching this pattern
- `--context-end`: removal stops at a line matching this pattern

The tool always keeps the marker lines themselves. Without
`--context-start`, removal applies from the top of the file. After a
`--context-end` match, removal stays off until the next
`--context-start` match.

### Update methods

`--update-method` chooses how the tool writes file changes back:

<!-- markdownlint-disable MD013 -->

| Behaviour                | `git` (default)                         | `api`                                     |
| ------------------------ | --------------------------------------- | ----------------------------------------- |
| How                      | Clone, amend, `--force-with-lease` push | GitHub Git Data API                       |
| Commit                   | Amends the branch's **last** commit     | Adds a **new** commit                     |
| Commit message           | Unchanged                               | `Fix N file(s) in PR #N` with no sign-off |
| Signing                  | Your local Git signing setup            | No signature from your keys               |
| Pull requests from forks | Supported, with push access to the fork | Not supported                             |
| File modes               | Preserved                               | Rewritten as `100644`                     |
| Needs `git`              | Yes                                     | Unless `--pr-content-only` set            |

<!-- markdownlint-enable MD013 -->

Because the `git` method amends the existing commit, it keeps that
commit's message, author and any `Signed-off-by:` trailer, which suits
repositories that enforce DCO sign-off or signed commits.

The `api` method reads and writes the head branch in the pull request's
**base** repository, so it only works when the branch lives there, as it
does for Dependabot and pre-commit.ci pull requests. Its commits carry no
DCO sign-off. It normally writes all changes in one commit; if that
batch commit fails, it falls back to one `Fix <path>` commit per file.

### Git identity and signing

These flags apply to the `git` method only:

- default: copy `user.name`, `user.email` and the commit signing settings
  (`commit.gpgsign`, `gpg.format`, `user.signingkey` and related keys)
  from your global Git configuration
- `--disable-signing`: use your identity but turn signing off
- `--bot-identity`: commit as `pull-request-fixer
  <noreply@linuxfoundation.org>` without signing

If your global Git configuration has no `user.name` or `user.email`, the
tool falls back to the bot identity, without signing. You cannot combine
`--bot-identity` with `--disable-signing`.

### Previewing changes

`--dry-run` makes no changes. `--show-diff` prints a unified diff for each
changed file; organization dry runs always print diffs.

## Pull request comments

When the tool changes a pull request (not in dry-run mode), it posts a
comment describing the change. For title and description fixes:

```markdown
## 🛠️ Pull Request Fixer

Automatically fixed pull request metadata:
- Updated pull request title to match commit
- Updated pull request description to match commit body message

---
*This fix was automatically applied by [pull-request-fixer](https://github.com/lfreleng-actions/pull-request-fixer)*
```

For file fixes, the comment shows the command options used and the diff
for each file. When the diffs total more than 40 lines, it lists the
changed files instead.

## Options

<!-- markdownlint-disable MD013 -->

| Option              | Short | Default         | Description                                                       |
| ------------------- | ----- | --------------- | ----------------------------------------------------------------- |
| `--token`           | `-t`  | `$GITHUB_TOKEN` | GitHub token                                                      |
| `--fix-title`       |       | off             | Set the title to the first commit's subject                       |
| `--fix-body`        |       | off             | Set the description to the first commit's body, minus trailers    |
| `--fix-files`       |       | off             | Edit files with regex; overrides `--fix-title` and `--fix-body`   |
| `--file-pattern`    |       |                 | Regex for file paths (required with `--fix-files`)                |
| `--search-pattern`  |       |                 | Regex for file content (required with `--fix-files`)              |
| `--replacement`     |       |                 | Replacement text; supports back-references                        |
| `--remove-lines`    |       | off             | Delete matching lines instead of replacing                        |
| `--context-start`   |       |                 | Regex for the line after which removal begins                     |
| `--context-end`     |       |                 | Regex for the line at which removal stops                         |
| `--pr-content-only` |       | off             | Only edit files the pull request already changes                  |
| `--show-diff`       |       | off             | Print a unified diff for each changed file                        |
| `--update-method`   |       | `git`           | `git` (clone, amend, push) or `api` (new commit through the API)  |
| `--disable-signing` |       | off             | `git` method: use your identity without signing                   |
| `--bot-identity`    |       | off             | `git` method: commit as the bot identity without signing          |
| `--include-drafts`  |       | off             | Include draft pull requests                                       |
| `--no-blocked-only` |       | off             | Process pull requests regardless of blocked state                 |
| `--dry-run`         |       | off             | Preview changes without applying them                             |
| `--workers`         | `-j`  | CPU cores       | Parallel workers, 1-32; defaults to the performance core count    |
| `--verbose`         | `-v`  | off             | Debug logging                                                     |
| `--quiet`           | `-q`  | off             | Errors only                                                       |
| `--log-level`       |       | `INFO`          | Logging level                                                     |
| `--version`         |       |                 | Print the version and exit                                        |
| `--help`            | `-h`  |                 | Print the version and help, then exit                             |

<!-- markdownlint-enable MD013 -->

## Authentication

Pass a GitHub token with `--token` or the `GITHUB_TOKEN` environment
variable. The token needs:

- read access to the repositories you scan, and `read:org` to list an
  organization's repositories and read check status
- write access to pull requests to change titles, descriptions and
  comments
- push access to the pull request's head repository for `--fix-files`;
  with the `git` method on a pull request from a fork, that means the fork

With a classic personal access token, grant `repo` (or `public_repo` for
public repositories only) and `read:org`. In organization mode the tool
validates the token first and warns when it cannot see those scopes.
Tokens issued to GitHub Actions do not report scopes, so the tool skips
that check for them.

## Exit status

| Status | Meaning                                                             |
| ------ | ------------------------------------------------------------------- |
| `0`    | Run completed; also when single PR mode finds a closed or merged PR |
| `1`    | Missing target, fix option or token; API error; PR not blocked      |
| `2`    | Unknown option or out-of-range value, such as `--workers 33`        |

An organization run exits `0` even when updating some pull requests
fails. Check the `❌ Failed updates:` line in its summary.

## Troubleshooting

**`✅ No blocked PRs found!`** — the organization has no open pull
requests that count as blocked. Use `--no-blocked-only` to process all
open pull requests, or `--include-drafts` to include drafts.

**`pull request is NOT in a blocked state`** — single PR mode only
processes blocked pull requests by default. Add `--no-blocked-only`.

**Token validation failed or scope warnings** — check that the token has
not expired and has the access listed under
[Authentication](#authentication).

**`Push rejected` errors** — someone pushed to the pull request branch
while the tool worked on it; run the tool again.

**Rate limiting** — reduce `--workers`, or wait for the limit to reset.

**Unexpected files changed** — anchor `--file-pattern` as shown in
[Selecting files](#selecting-files), and preview with
`--dry-run --show-diff`.

Use `--verbose` for debug logging. The `scripts/` directory holds
diagnostic scripts for GraphQL and organization access problems; see
[scripts/README.md](scripts/README.md).

## Development

```bash
git clone https://github.com/lfreleng-actions/pull-request-fixer.git
cd pull-request-fixer
uv sync --extra dev
prek install -t pre-commit -t commit-msg
uv run pytest
uv run bash scripts/integration-test.sh
```

The test dependencies live in the `dev` extra, so plain `uv sync` leaves
`pytest` missing. See [CONTRIBUTING.md](CONTRIBUTING.md) for the
contribution workflow, [SETUP.md](SETUP.md) for installation and CI use,
[IMPLEMENTATION.md](IMPLEMENTATION.md) for the internals, and
[TESTING.md](TESTING.md) for testing against live pull requests.

## License

Apache-2.0

## Related projects

- [dependamerge][dependamerge]: bulk pull request management for GitHub
  organizations; this tool uses its blocked pull request detection
- [markdown-table-fixer][mtf]: fixes markdown table formatting; this
  project began as a fork of its codebase

[dependamerge]: https://github.com/lfreleng-actions/dependamerge
[mtf]: https://github.com/lfreleng-actions/markdown-table-fixer
