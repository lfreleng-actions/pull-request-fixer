<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: 2025 The Linux Foundation
-->

# 🛠️ Pull Request Fixer

A modern Python tool for automatically fixing pull request titles and bodies
across GitHub organizations. Scans for blocked PRs and updates them based on
commit messages.

## Features

- **🔍 Organization Scanning**: Scan entire GitHub organizations for blocked
  pull requests
- **✍️ Title Fixing**: Set PR titles to match the first commit's subject line
- **📝 Body Fixing**: Set PR descriptions to match commit message bodies
  (excluding trailers)
- **📄 File Fixing**: Apply regex-based search/replace to files in PRs (clones,
  modifies, amends commit, and force-pushes changes)
- **🚫 Blocked PR Filtering**: Option to process PRs that cannot merge
  (failing checks, conflicts, etc.)
- **🚀 Parallel Processing**: Process PRs concurrently for
  performance
- **🔄 Dry Run Mode**: Preview changes before applying them
- **📊 Progress Tracking**: Real-time progress updates during scanning
- **🎯 Smart Parsing**: Automatically removes Git trailers (Signed-off-by, etc.)
- **💬 PR Comments**: Automatically adds a comment to PRs explaining the
  changes made

## Installation

```bash
pip install pull-request-fixer
```

Or with uv:

```bash
uv pip install pull-request-fixer
```

## Quick Start

```bash
# Set your GitHub token
export GITHUB_TOKEN=ghp_xxxxxxxxxxxxx

# Fix PR titles in an organization
pull-request-fixer lfreleng-actions --fix-title

# Fix both titles and bodies
pull-request-fixer lfreleng-actions --fix-title --fix-body

# Show help (includes version)
pull-request-fixer --help

# Fix files in a specific PR using regex
pull-request-fixer https://github.com/owner/repo/pull/123 \
  --fix-files \
  --file-pattern './action.yaml' \
  --search-pattern '^\s+type:\s+\S' \
  --remove-lines \
  --context-start 'inputs:' \
  --context-end 'runs:' \
  --dry-run \
  --show-diff

# Preview changes without applying (dry run)
pull-request-fixer lfreleng-actions --fix-title --fix-body --dry-run
```

## Usage

### Basic Commands

**Scan and fix an organization:**

```bash
pull-request-fixer ORGANIZATION [OPTIONS]
```

**Fix a specific PR:**

```bash
pull-request-fixer PR_URL [OPTIONS]
```

You can specify the target as:

- Organization name: `myorg`
- GitHub URL: `https://github.com/myorg`
- GitHub URL with path: `https://github.com/myorg/`
- Specific PR URL: `https://github.com/owner/repo/pull/123`

### Fix Options

#### `--fix-title`

Updates the PR title to match the first line (subject) of the first commit message.

**Example:**

If the first commit message is:

```text
Fix authentication bug in login handler

This commit addresses an issue where users couldn't
log in with special characters in passwords.

Signed-off-by: John Doe <john@example.com>
```

This sets the PR title to:

```text
Fix authentication bug in login handler
```

#### `--fix-body`

Updates the PR description to match the commit message body, excluding trailers.

Using the same commit message above, this sets the PR body to:

```text
This commit addresses an issue where users couldn't
log in with special characters in passwords.
```

The `Signed-off-by:` trailer is automatically removed.

#### `--fix-files`

Fixes files in pull requests using regex-based search and replace. This feature:

1. Clones the PR branch
2. Finds files matching `--file-pattern` (regex)
3. Applies search/replace using `--search-pattern` and `--replacement`
4. Amends the last commit with the changes
5. Force-pushes the updated commit back to the PR

**Required options when using `--fix-files`:**

- `--file-pattern`: Regex to match file paths (e.g., `'./action.yaml'` or
  `'.*\.yaml$'`)
- `--search-pattern`: Regex pattern to find in matched files
- Either `--replacement` (text to replace matches) or `--remove-lines` (to
  delete matching lines)

**Optional context options (for line removal):**

- `--context-start`: Regex to define where the removal context begins (e.g., `'inputs:'`)
- `--context-end`: Regex to define where the removal context ends (e.g., `'runs:'`)

**Optional display options:**

- `--show-diff`: Show unified diff output for file changes

#### Update Methods (for `--fix-files` only)

The tool supports two methods for applying file fixes:

**API Method (default)** - Uses GitHub API to create new commits:

```bash
pull-request-fixer https://github.com/owner/repo/pull/123 \
  --fix-files \
  --file-pattern './action.yaml' \
  --search-pattern 'pattern'
```

- Creates new commits via GitHub API
- Shows as "Verified" by GitHub
- No Git operations required
- Faster and simpler
- Default method for ease of use

**Git Method** - Clones repo, amends commit, force-pushes:

```bash
pull-request-fixer https://github.com/owner/repo/pull/123 \
  --fix-files \
  --update-method git \
  --file-pattern './action.yaml' \
  --search-pattern 'pattern'
```

- Respects your local Git signing configuration
- Amends the existing commit (preserves commit history)
- Requires Git operations (clone, amend, push)
- Use when you need to amend commits or use your own signature

**Example - Remove type definitions from GitHub Actions:**

```bash
pull-request-fixer https://github.com/owner/repo/pull/123 \
  --fix-files \
  --file-pattern './action.yaml' \
  --search-pattern '^\s+type:\s+\S' \
  --remove-lines \
  --context-start 'inputs:' \
  --context-end 'runs:' \
  --dry-run \
  --show-diff
```

This will remove lines containing `type:` that appear between `inputs:` and `runs:`
sections in `action.yaml` files.

**Example - Replace text with regex:**

```bash
pull-request-fixer https://github.com/owner/repo/pull/456 \
  --fix-files \
  --file-pattern '.*\.py$' \
  --search-pattern 'old_function_name' \
  --replacement 'new_function_name'
```

### Common Usage Patterns

**Fix titles:**

```bash
pull-request-fixer myorg --fix-title
```

**Fix both titles and bodies:**

```bash
pull-request-fixer myorg --fix-title --fix-body
```

**Preview changes (dry run):**

```bash
pull-request-fixer myorg --fix-title --fix-body --dry-run
```

**Include draft PRs:**

```bash
pull-request-fixer myorg --fix-title --include-drafts
```

**Use more workers for large organizations:**

```bash
pull-request-fixer myorg --fix-title --workers 16
```

**Quiet mode for automation:**

```bash
pull-request-fixer myorg --fix-title --quiet
```

**Verbose mode for debugging:**

```bash
pull-request-fixer myorg --fix-files --file-pattern '*.yaml' \
  --search-pattern '^\s+type:\s+\S' --remove-lines \
  --verbose  # Shows detailed DEBUG logs including file operations
```

**Process blocked PRs:**

<!-- write-good-disable -->
```bash
pull-request-fixer myorg --fix-title --blocked-only
```
<!-- write-good-enable -->

**Fix files across PRs:**

<!-- write-good-disable -->
```bash
pull-request-fixer myorg \
  --fix-files \
  --file-pattern './action.yaml' \
  --search-pattern '^\s+type:\s+\S' \
  --remove-lines \
  --context-start 'inputs:' \
  --context-end 'runs:' \
  --blocked-only \
  --dry-run
```
<!-- write-good-enable -->

## PR Comments

When the tool applies fixes (not in dry-run mode), it automatically adds a
comment to the PR explaining the changes. This provides transparency and
helps PR authors understand the automated modifications.

**Example comment:**

```markdown
## 🛠️ Pull Request Fixer

Automatically fixed pull request metadata:
- **Pull request title** updated to match first commit
- **Pull request body** updated to match commit message

---
*This fix was automatically applied by [pull-request-fixer](https://github.com/lfit/pull-request-fixer)*
```

The comment includes the items that changed. For
example, if the title changed, that line will appear in the
comment.

## Options

<!-- markdownlint-disable MD013 -->
<!-- write-good-disable -->

| Flag               | Short | Default         | Description                                           |
| ------------------ | ----- | --------------- | ----------------------------------------------------- |
| `--help`           | `-h`  |                 | Show help message and exit (displays version)         |
| `--token`          | `-t`  | `$GITHUB_TOKEN` | GitHub personal access token                          |
| `--fix-title`      |       | `false`         | Fix PR title to match first commit subject            |
| `--fix-body`       |       | `false`         | Fix PR body to match commit message body              |
| `--fix-files`      |       | `false`         | Fix files in PR using regex search/replace            |
| `--file-pattern`   |       |                 | Regex to match file paths (required w/ `--fix-files`) |
| `--search-pattern` |       |                 | Regex to search in files (required w/ `--fix-files`)  |
| `--replacement`    |       |                 | Replacement string for matched patterns               |
| `--remove-lines`   |       | `false`         | Remove matching lines instead of replacing            |
| `--context-start`  |       |                 | Regex pattern for context start (for line removal)    |
| `--context-end`    |       |                 | Regex pattern for context end (for line removal)      |
| `--show-diff`      |       | `false`         | Show unified diff output for file changes             |
| `--include-drafts` |       | `false`         | Include draft PRs in scan                             |
| `--blocked-only`   |       | `false`         | Process PRs that cannot merge                         |
| `--dry-run`        |       | `false`         | Preview changes without applying them                 |
| `--workers`        | `-j`  | `4`             | Number of parallel workers (1-32)                     |
| `--verbose`        | `-v`  | `false`         | Enable verbose output (DEBUG logs)                    |
| `--quiet`          | `-q`  | `false`         | Suppress output except errors                         |
| `--log-level`      |       | `INFO`          | Set logging level                                     |
| `--version`        |       |                 | Show version and exit                                 |

<!-- write-good-enable -->
<!-- markdownlint-enable MD013 -->

## How It Works

1. **Scan Organization**: Uses GitHub's GraphQL API to efficiently find
   blocked pull requests
2. **Fetch Commits**: Retrieves the first commit from each PR using the REST
   API
3. **Parse Messages**: Extracts commit subject and body, removing trailers
4. **Apply Changes**: Updates PR titles and/or bodies in parallel
5. **Report Results**: Shows summary of changes made

### Trailers Removed

The following Git trailer patterns are automatically removed from PR bodies:

- `Signed-off-by:`
- `Co-authored-by:`
- `Reviewed-by:`
- `Tested-by:`
- `Acked-by:`
- `Cc:`
- `Reported-by:`
- `Suggested-by:`
- `Fixes:`
- `See-also:`
- `Link:`
- `Bug:`
- `Change-Id:`

## Authentication

You need a GitHub personal access token with appropriate permissions:

1. Go to GitHub Settings → Developer settings → Personal access tokens
2. Generate a new token with `repo` scope (or `public_repo` for public repos)
3. Set the token as an environment variable:

```bash
export GITHUB_TOKEN=ghp_xxxxxxxxxxxxx
```

Or pass it via the `--token` flag:

```bash
pull-request-fixer myorg --fix-title --token ghp_xxxxxxxxxxxxx
```

## Examples

### Example 1: Fix Titles in Organization

```bash
pull-request-fixer lfreleng-actions --fix-title
```

Output:

```text
🔍 Scanning organization: lfreleng-actions
🔧 Will fix: titles

📊 Found 15 blocked PRs to process

🔍 Blocked PRs:
   • lfreleng-actions/repo1#123: Update docs
   • lfreleng-actions/repo2#456: Fix bug
   ...

🔄 Processing: lfreleng-actions/repo1#123
   ✅ Updated title: docs: Add usage examples for CLI

🔄 Processing: lfreleng-actions/repo2#456
   ✅ Updated title: fix: Resolve authentication timeout issue

✅ Fixed 15 PR(s)
```

### Example 2: Dry Run with Both Fixes

```bash
pull-request-fixer myorg --fix-title --fix-body --dry-run
```

Output:

```text
🔍 Scanning organization: myorg
🔧 Will fix: titles, bodies
🏃 Dry run mode: no changes made

📊 Found 5 blocked PRs to process

🔄 Processing: myorg/repo#123
   Would update title:
     From: Update documentation
     To:   docs: Add usage examples for CLI
   Would update body
     Length: 245 chars

✅ [DRY RUN] Would fix 5 PR(s)
```

### Example 3: High Performance Mode

For large organizations, use more workers:

```bash
pull-request-fixer bigorg --fix-title --fix-body --workers 16 --verbose
```

## Performance

- **Parallel Processing**: PRs processed concurrently for speed
- **Efficient Queries**: GraphQL for scanning, REST for updates
- **Memory Efficient**: Streaming results, no need to load all PRs
- **Typical Speed**: 2-5 seconds per repository

Example timing for 100 repositories with 50 blocked PRs using 8 workers:

- Organization scan: ~30-60 seconds
- PR processing: ~20-30 seconds
- **Total: ~50-90 seconds**

### Example 4: Fix Files in a Blocked PR

This example removes invalid `type:` definitions from a GitHub composite action:

```bash
pull-request-fixer https://github.com/lfreleng-actions/make-action/pull/40 \
  --fix-files \
  --file-pattern './action.yaml' \
  --search-pattern '^\s+type:\s+\S' \
  --remove-lines \
  --context-start 'inputs:' \
  --context-end 'runs:' \
  --dry-run \
  --show-diff
```

Output:

```text
🔍 Processing PR: https://github.com/lfreleng-actions/make-action/pull/40
🔧 Will fix: files
🏃 Dry run mode: the tool will not apply changes

📝 Fixing files in PR...
```

✅ Would fix 1 file
📂 action.yaml
--- action.yaml
+++ action.yaml
@@ -10,7 +10,6 @@
   repository:
     description: 'Remote Git repository URL'
     required: false

- type: 'string'
   debug:
     description: 'Enable debug mode'
     required: false
- type: 'boolean'

Dry-run completed!

```text

Without `--dry-run`, the output would show:

```text
✅ Updated 1 file
🔀 action.yaml
--- action.yaml
+++ action.yaml
@@ -10,7 +10,6 @@
   repository:
     description: 'Remote Git repository URL'
     required: false
-    type: 'string'
   debug:
     description: 'Enable debug mode'
     required: false
-    type: 'boolean'
```

This would:

1. Clone the PR branch
2. Remove all lines containing `type:` from the `inputs:` section of `action.yaml`
3. Amend the last commit with the changes
4. Force-push the updated commit
5. Add a comment to the PR explaining the fix

## Troubleshooting

### No PRs Found

If the tool reports "No blocked PRs found", this could mean:

- The organization truly has no blocked PRs
- You may need to adjust the scanner's definition of "blocked"

### Authentication Errors

If you see authentication errors:

Make sure your `GITHUB_TOKEN` environment variable contains a valid token

- Verify the token has `repo` or `public_repo` scope
- Check that the token hasn't expired

### Rate Limiting

If you hit rate limits:

- Reduce the number of workers: `--workers 2`
- Wait for the rate limit to reset (shown in error message)
- Use a token with higher rate limits

### Permission Errors

If updates fail:

- Ensure your token has write access to the repositories
- Check that you're not trying to update PRs in archived repos
- Verify the PRs are not locked

## Development

### Setup

```bash
git clone https://github.com/lfit/pull-request-fixer.git
cd pull-request-fixer
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
```

### Running Tests

```bash
pytest
```

### Running Pre-commit Hooks

```bash
pre-commit install
pre-commit run --all-files
```

### Code Style

The project uses:

- `ruff` for linting and formatting
- `mypy` for type checking
- `pytest` for testing

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## License

Apache-2.0

## Support

- **Issues**:
  <https://github.com/lfit/pull-request-fixer/issues>
- **Documentation**:
  <https://github.com/lfit/pull-request-fixer/blob/main/IMPLEMENTATION.md>
- **Changelog**:
  <https://github.com/lfit/pull-request-fixer/blob/main/CHANGELOG.md>

## Related Projects

- [dependamerge](https://github.com/lfit/dependamerge) - Automatically merge
  automation PRs
- [markdown-table-fixer](https://github.com/lfit/markdown-table-fixer) - Fix
  markdown table formatting

## Acknowledgments

This project uses patterns from:

- [dependamerge](https://github.com/lfit/dependamerge) for efficient GitHub
  organization scanning
- [markdown-table-fixer](https://github.com/lfit/markdown-table-fixer) for
  the initial codebase structure
