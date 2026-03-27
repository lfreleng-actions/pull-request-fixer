<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: 2025 The Linux Foundation
-->

# Pull Request Fixer - Features

This document provides a comprehensive overview of the features implemented
in the pull-request-fixer tool.

## Core Features

### 1. Organization Scanning

Efficiently scan entire GitHub organizations for pull requests:

- **GraphQL-Based Scanning**: Uses GitHub's GraphQL API for efficient bulk queries
- **Parallel Repository Processing**: Scans repositories concurrently
- **Progress Tracking**: Real-time progress updates during scanning
- **Smart Pagination**: Handles large organizations with automatic pagination
- **Repository Filtering**: Skips archived repositories automatically

### 2. PR Title Fixing

Automatically fix PR titles to match commit messages:

- **First Commit Detection**: Extracts the subject line from the first commit
- **Title Normalization**: Sets PR title to match the commit subject
- **Preview Mode**: Dry-run support to preview changes before applying
- **Batch Processing**: Fix PRs in parallel
- **Idempotent**: safe to re-run (no-op if already correct)

### 3. PR Body Fixing

Update PR descriptions from commit message bodies:

- **Body Extraction**: Gets commit message body (everything after subject)
- **Trailer Removal**: Automatically strips Git trailers (Signed-off-by, etc.)
- **Clean Formatting**: Preserves commit message formatting
- **Optional Feature**: Works independently of title fixing

Removed trailers include:

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

### 4. File Fixing (NEW)

Fix files in pull requests using regex-based search and replace:

- **Clone and Change**: Clones PR branch, applies fixes, amends commit, force-pushes
- **Regex Pattern Matching**: Find files using regex patterns
- **Content Search/Replace**: Apply regex-based transformations to file content
- **Line Removal**: Remove lines matching patterns, optionally within context markers
- **Context-Aware**: Limit changes to content between start/end markers
- **Safe Force Push**: Uses `--force-with-lease` to prevent overwriting
  concurrent changes
- **Git Integration**: Full Git workflow (clone, commit, push) handled automatically

#### File Fixing Use Cases

**Remove invalid type definitions from GitHub Actions:**

```bash
pull-request-fixer PR_URL \
  --fix-files \
  --file-pattern './action.yaml' \
  --search-pattern 'type:' \
  --remove-lines \
  --context-start 'inputs:' \
  --context-end 'runs:'
```

**Replace function names:**

```bash
pull-request-fixer PR_URL \
  --fix-files \
  --file-pattern '.*\.py$' \
  --search-pattern 'old_function' \
  --replacement 'new_function'
```

**Update configuration values:**

```bash
pull-request-fixer PR_URL \
  --fix-files \
  --file-pattern 'config\.yaml' \
  --search-pattern 'version: \d+\.\d+\.\d+' \
  --replacement 'version: 2.0.0'
```

### 5. Blocked PR Filtering

Process PRs that fail to merge:

- **Status Check Detection**: Identifies failing CI/CD checks
- **Merge Conflict Detection**: Finds PRs with merge conflicts
- **Branch Protection**: Detects PRs blocked by branch protection rules
- **Behind Base Branch**: Identifies PRs that need updating
- **Optional Filtering**: Use `--blocked-only` flag to enable

Blocking conditions detected:

- Failing status checks (CheckRun or StatusContext)
- Merge conflicts (`mergeable: CONFLICTING`)
- Branch protection blocks (`mergeStateStatus: BLOCKED`)
- Behind base branch (`mergeStateStatus: BEHIND`)

### 6. Single PR Processing

Process a specific PR directly by URL:

- **Direct URL Support**: Pass PR URL instead of organization name
- **Quick Fixes**: Fix individual PRs without scanning entire organization
- **All Fix Types**: Supports title, body, and file fixing
- **Same Options**: All flags work with both organization and PR URLs

Example:

```bash
pull-request-fixer https://github.com/owner/repo/pull/123 --fix-title
```

### 7. Parallel Processing

Efficient concurrent processing for performance:

- **Worker Pool**: Configurable number of parallel workers (1-32)
- **Semaphore-Based**: Proper concurrency control with asyncio semaphores
- **Repository Level**: Process repositories in parallel
- **PR Level**: Process PRs within a repository in parallel
- **Bounded Concurrency**: Respects GitHub API rate limits

Performance characteristics:

- Default: 4 workers
- Recommended for large orgs: 8-16 workers
- Limit: 32 workers
- Typical speed: 2-5 seconds per repository

### 8. Dry Run Mode

Preview changes without applying them:

- **Risk-Free**: See what would change without making actual changes
- **Detailed Output**: Shows before/after previews
- **All Features**: Works with title, body, and file fixing
- **CI Integration**: Perfect for validation in CI pipelines

Output shows:

- What would change
- Previous and new values
- Files that would change
- Number of PRs that would change

### 9. PR Comments

Automatic documentation of changes:

- **Transparency**: Adds comment explaining what changed
- **Attribution**: Links to pull-request-fixer project
- **Change Details**: Lists specific modifications made
- **Conditional**: Added when changes are actually applied (not in dry-run)

Example comment:

```markdown
🛠️ **Pull Request Fixer**

Fixed 1 file(s): action.yaml

The commit now includes the fixes.

---
*Automatically fixed by [pull-request-fixer](https://github.com/lfit/pull-request-fixer)*
```

### 10. Authentication

Flexible token handling:

- **Environment Variable**: Reads from `GITHUB_TOKEN` by default
- **Command Line**: Override with `--token` flag
- **Token Validation**: Validates token before processing
- **Scope Detection**: Warns if required scopes are missing
- **Error Messages**: Clear guidance on authentication issues

Required scopes:

- `repo` or `public_repo`: For reading/writing PRs
- `read:org`: For scanning organizations (optional but recommended)

## Technical Features

### Architecture

- **Modular Design**: Separate modules for scanning, fixing, file operations,
  and Git
- **Type Safety**: Full type hints throughout the codebase
- **Modern Python**: Uses Python 3.10+ features (match statements, type unions)
- **Async/Await**: Fully asynchronous for optimal performance
- **Error Handling**: Comprehensive exception handling with graceful degradation

### Code Organization

```text
src/pull_request_fixer/
├── cli.py              # Command-line interface
├── pr_scanner.py       # Organization/PR scanning
├── pr_fixer.py         # Title/body fixing (GraphQL)
├── pr_file_fixer.py    # File fixing (Git operations)
├── file_fixer.py       # Regex-based file modifications
├── github_client.py    # GitHub API client
├── graphql_queries.py  # GraphQL query definitions
├── models.py           # Data models
├── progress_tracker.py # Progress visualization
└── exceptions.py       # Custom exceptions
```

### Code Quality

- **Linting**: Ruff for code quality and formatting
- **Type Checking**: MyPy with strict mode enabled
- **Testing**: Pytest with 25%+ code coverage
- **Pre-commit Hooks**: Automated quality checks
- **Documentation**: Comprehensive docstrings and comments

### Dependencies

Well-maintained, modern dependencies:

- `typer`: Modern CLI framework with type hints
- `rich`: Beautiful terminal output and progress bars
- `httpx[http2]`: HTTP/2-enabled async HTTP client
- `pydantic`: Data validation and serialization
- `aiolimiter`: Async rate limiting
- `tenacity`: Retry logic for API calls

### Git Integration

For file fixing operations:

- **Temporary Clones**: Uses temporary directories for safety
- **Authentication**: Token-based Git authentication via HTTPS
- **Force-with-Lease**: Safe force pushing to prevent overwriting changes
- **Commit Amending**: Modifies existing commits rather than creating new ones
- **Branch Tracking**: Maintains proper branch references
- **Error Sanitization**: Strips tokens from error messages

## Command-Line Interface

### Global Options

| Option        | Short | Default         | Description                      |
| ------------- | ----- | --------------- | -------------------------------- |
| `--token`     | `-t`  | `$GITHUB_TOKEN` | GitHub personal access token     |
| `--dry-run`   |       | `false`         | Preview changes without applying |
| `--workers`   | `-j`  | `4`             | Parallel workers (1-32)          |
| `--verbose`   | `-v`  | `false`         | Detailed output                  |
| `--quiet`     | `-q`  | `false`         | Minimal output                   |
| `--log-level` |       | `INFO`          | Logging level                    |

### Fix Options

| Option        | Description                      |
| ------------- | -------------------------------- |
| `--fix-title` | Fix PR title from commit subject |
| `--fix-body`  | Fix PR body from commit message  |
| `--fix-files` | Fix files using regex            |

### File Fixing Options

| Option             | Description               |
| ------------------ | ------------------------- |
| `--file-pattern`   | Regex to match file paths |
| `--search-pattern` | Regex to find in files    |
| `--replacement`    | Replacement text          |
| `--remove-lines`   | Remove matching lines     |
| `--context-start`  | Start marker for context  |
| `--context-end`    | End marker for context    |

### Filtering Options

| Option             | Description          |
| ------------------ | -------------------- |
| `--include-drafts` | Include draft PRs    |
| `--blocked-only`   | Limit to blocked PRs |

## Performance

### Benchmarks

Typical performance on a 100-repository organization:

- **Scanning**: 30-60 seconds (depends on number of open PRs)
- **Title/Body Fixing**: 20-30 seconds for 50 PRs
- **File Fixing**: 2-5 seconds per PR (includes clone/push)
- **Total**: 1-2 minutes for complete processing

### Optimization Strategies

1. **Parallel Processing**: Use more workers for large organizations
2. **Blocked PR Filter**: Skip PRs that don't need fixing
3. **Selective Fixing**: Enable needed fix types
4. **GraphQL Batching**: Efficient queries reduce API calls
5. **Async Operations**: Non-blocking I/O throughout

### Rate Limiting

Respects GitHub API rate limits:

- **GraphQL**: 5,000 points per hour
- **REST API**: 5,000 requests per hour
- **Automatic Retry**: Built-in retry logic with exponential backoff
- **Rate Limit Detection**: Warns when approaching limits

## Error Handling

### Graceful Degradation

- **Partial Failures**: Continues processing even if some PRs fail
- **Detailed Errors**: Provides specific error messages
- **Exception Tracking**: Logs detailed error information
- **Recovery**: Safe to re-run after failures

### Error Types

- **Authentication Errors**: Invalid or expired tokens
- **Permission Errors**: Insufficient access to repositories
- **Network Errors**: Timeout or connection issues
- **Git Errors**: Clone, commit, or push failures
- **Validation Errors**: Invalid regex patterns or parameters

### Token Sanitization

All error messages automatically strip:

- GitHub personal access tokens (`ghp_*`)
- GitHub server tokens (`ghs_*`)
- Fine-grained tokens (`github_pat_*`)
- Git authentication URLs (`x-access-token:*`)

## Testing

### Test Coverage

- Unit tests for core functionality
- Integration tests for GitHub API
- Mocking for external dependencies
- Test fixtures for common scenarios

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=pull_request_fixer

# Run specific test file
pytest tests/test_file_fixer.py
```

## Future Enhancements

Planned features for future releases:

1. **Configuration Files**: Support for `.pull-request-fixer.yml`
2. **Label Filtering**: Process PRs with specific labels
3. **Author Filtering**: Process PRs by specific authors
4. **Template Support**: Custom PR comment templates
5. **Diff Previews**: Show file diffs in dry-run mode
6. **Rollback Support**: Undo previous changes
7. **Webhook Integration**: Trigger fixes automatically
8. **GitHub App**: Alternative authentication method

## Compatibility

- **Python**: 3.10, 3.11, 3.12, 3.13
- **GitHub**: GitHub.com and GitHub Enterprise Server
- **Platforms**: Linux, macOS, Windows
- **CI/CD**: GitHub Actions, GitLab CI, Jenkins, etc.

## Related Projects

This project builds on patterns from:

- **dependamerge**: Efficient organization scanning approach
- **markdown-table-fixer**: Git-based PR modification workflow

## Support

- **Issues**: <https://github.com/lfit/pull-request-fixer/issues>
- **Documentation**: <https://github.com/lfit/pull-request-fixer>
- **Changelog**: CHANGELOG.md
- **Implementation**: IMPLEMENTATION.md
