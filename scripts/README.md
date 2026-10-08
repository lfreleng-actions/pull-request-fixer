<!--
SPDX-License-Identifier: Apache-2.0
SPDX-FileCopyrightText: 2025 The Linux Foundation
-->

# Scripts

This directory holds developer scripts for `pull-request-fixer`. None of
them ship in the published package.

| Script                   | Purpose                                  | Token |
| ------------------------ | ---------------------------------------- | ----- |
| `integration-test.sh`    | Tests the CLI's help and argument checks | No    |
| `debug_graphql.py`       | Runs the scanner's GraphQL queries       | Yes   |
| `diagnose_org_access.py` | Explains why an org scan finds nothing   | Yes   |

## `integration-test.sh`

Runs the installed `pull-request-fixer` command and checks its help
output, version output and argument validation:

- `--version`, `--help` and `-h`
- every documented option appears in `--help`
- a missing `TARGET`, missing `--fix-*` options and a missing token
- `--fix-files` without `--file-pattern`, `--search-pattern`, or a
  `--replacement`/`--remove-lines` action
- an invalid `--update-method`
- `--bot-identity` combined with `--disable-signing`
- an out-of-range `--workers` value

Each case exits before the tool contacts GitHub. The script unsets
`GITHUB_TOKEN` for every invocation, so it needs no credentials or
network access.

Run it from the repository root through `uv`, which puts the
development install of the command on `PATH`:

```bash
uv sync --extra dev
uv run bash scripts/integration-test.sh
```

The script exits `0` when all tests pass and `1` otherwise.

### Adding a test

1. Write a `test_*` function that calls `print_test` with a description.
2. Invoke the CLI through `run_cli`, which captures the combined output in
   `CLI_OUTPUT` and the exit code in `CLI_EXIT`.
3. Check the result with `assert_result EXIT_CODE 'expected text'
   'description'`, or call `record_pass`/`record_fail` directly.
4. Call the new function from `main()`.

```bash
test_new_validation() {
    print_test "Description of the behaviour under test"
    run_cli myorg --fix-title --some-flag
    assert_result 1 "expected error text" "CLI rejects the flag"
}
```

Keep new cases offline: any invocation that passes validation with a
token would contact GitHub.

## `debug_graphql.py`

Runs the GraphQL queries the organization scanner uses and prints the raw
responses, to diagnose query or permission problems:

```bash
export GITHUB_TOKEN=ghp_xxxxxxxxxxxxx
uv run python scripts/debug_graphql.py --org myorg
uv run python scripts/debug_graphql.py --org myorg --repo myrepo --pr 123
```

The integration test workflow (`.github/workflows/testing.yaml`) runs this
script against the repository owner's organization.

## `diagnose_org_access.py`

Checks token validity and scopes, organization access, and the repository
and pull request queries, to explain why a scan returns no repositories:

```bash
export GITHUB_TOKEN=ghp_xxxxxxxxxxxxx
uv run python scripts/diagnose_org_access.py myorg
```
