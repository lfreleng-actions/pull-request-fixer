#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

# Integration tests for the pull-request-fixer CLI.
#
# These tests exercise the installed command's help, version and argument
# validation. Every case exits before the tool contacts GitHub, so the
# script needs no token or network access and runs the same locally and
# in CI. GITHUB_TOKEN is unset for each invocation to guarantee this.

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

# Test results array
declare -a FAILED_TESTS=()

# Output and exit code of the most recent run_cli call
CLI_OUTPUT=""
CLI_EXIT=0

# Print test header
print_test() {
    TESTS_RUN=$((TESTS_RUN + 1))
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}Test $TESTS_RUN: $1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

record_pass() {
    echo -e "${GREEN}✅ PASS: $1${NC}\n"
    TESTS_PASSED=$((TESTS_PASSED + 1))
}

record_fail() {
    echo -e "${RED}❌ FAIL: $1${NC}"
    echo -e "${RED}   $2${NC}"
    echo -e "${RED}   Output: '$CLI_OUTPUT'${NC}\n"
    TESTS_FAILED=$((TESTS_FAILED + 1))
    FAILED_TESTS+=("$1")
}

# Run the CLI without a token, capturing combined output and exit code
run_cli() {
    set +e
    CLI_OUTPUT=$(env -u GITHUB_TOKEN COLUMNS=200 pull-request-fixer "$@" 2>&1)
    CLI_EXIT=$?
    set -e
}

# Assert the last run_cli call exited with a code and printed some text
assert_result() {
    local expected_exit="$1"
    local expected_text="$2"
    local description="$3"

    if [ "$CLI_EXIT" -ne "$expected_exit" ]; then
        record_fail "$description" \
            "Expected exit code $expected_exit, got $CLI_EXIT"
    elif ! grep -qF -- "$expected_text" <<< "$CLI_OUTPUT"; then
        record_fail "$description" "Expected to find: '$expected_text'"
    else
        record_pass "$description"
    fi
}

# Test functions

test_version_flag() {
    print_test "Version flag (--version)"
    run_cli --version
    assert_result 0 "pull-request-fixer version" \
        "Version output contains tool name and version"
}

test_help_shows_version() {
    print_test "Help output shows version (--help)"
    run_cli --help
    assert_result 0 "pull-request-fixer version" "Version shown in help output"
}

test_short_help_flag() {
    print_test "Short help flag (-h)"
    run_cli -h
    assert_result 0 "Usage:" "Short help flag prints usage"
}

test_help_documents_options() {
    print_test "Help output documents the fix and filter options"
    run_cli --help
    local option
    local missing=""
    for option in --fix-title --fix-body --fix-files --file-pattern \
        --search-pattern --replacement --remove-lines --context-start \
        --context-end --pr-content-only --show-diff --update-method \
        --disable-signing --bot-identity --include-drafts \
        --no-blocked-only --dry-run --workers; do
        if ! grep -qF -- "$option" <<< "$CLI_OUTPUT"; then
            missing="$missing $option"
        fi
    done
    if [ "$CLI_EXIT" -eq 0 ] && [ -z "$missing" ]; then
        record_pass "Help lists every documented option"
    else
        record_fail "Help lists every documented option" \
            "Exit code $CLI_EXIT; missing:$missing"
    fi
}

test_missing_target() {
    print_test "Missing TARGET argument"
    run_cli
    assert_result 1 "Missing required argument 'TARGET'" \
        "Missing target exits with an error"
}

test_no_fix_options() {
    print_test "No fix options specified"
    run_cli myorg
    assert_result 1 "No fix options specified" \
        "Running without --fix-* options exits with a warning"
}

test_fix_files_requires_file_pattern() {
    print_test "--fix-files requires --file-pattern"
    run_cli myorg --fix-files --search-pattern 'foo' --replacement 'bar'
    assert_result 1 "--file-pattern is required" \
        "--fix-files without --file-pattern is rejected"
}

test_fix_files_requires_search_pattern() {
    print_test "--fix-files requires --search-pattern"
    run_cli myorg --fix-files --file-pattern 'README' --replacement 'bar'
    assert_result 1 "--search-pattern is required" \
        "--fix-files without --search-pattern is rejected"
}

test_fix_files_requires_action() {
    print_test "--fix-files requires --replacement or --remove-lines"
    run_cli myorg --fix-files --file-pattern 'README' --search-pattern 'foo'
    assert_result 1 "Either --replacement or --remove-lines is required" \
        "--fix-files without a replacement action is rejected"
}

test_invalid_update_method() {
    print_test "Invalid --update-method value"
    run_cli myorg --fix-title --update-method ftp
    assert_result 1 "Invalid update method" \
        "Unknown update method is rejected"
}

test_conflicting_identity_flags() {
    print_test "--bot-identity conflicts with --disable-signing"
    run_cli myorg --fix-title --bot-identity --disable-signing
    assert_result 1 "Cannot use both --bot-identity and --disable-signing" \
        "Conflicting git identity flags are rejected"
}

test_missing_token() {
    print_test "Missing GitHub token"
    run_cli myorg --fix-title
    assert_result 1 "GitHub token required" \
        "Missing token is reported before contacting GitHub"
}

test_workers_out_of_range() {
    print_test "--workers outside the 1-32 range"
    run_cli myorg --fix-title --workers 33
    if [ "$CLI_EXIT" -ne 0 ]; then
        record_pass "Out-of-range worker count is rejected"
    else
        record_fail "Out-of-range worker count is rejected" \
            "Expected a non-zero exit code"
    fi
}

# Print summary
print_summary() {
    echo -e "\n${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}📊 Test Summary${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}Tests run:    ${NC}$TESTS_RUN"
    echo -e "${GREEN}Tests passed: ${NC}$TESTS_PASSED"
    echo -e "${RED}Tests failed: ${NC}$TESTS_FAILED"

    if [ ${#FAILED_TESTS[@]} -gt 0 ]; then
        echo -e "\n${RED}Failed tests:${NC}"
        for test in "${FAILED_TESTS[@]}"; do
            echo -e "${RED}  ❌ $test${NC}"
        done
    fi

    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

    if [ $TESTS_FAILED -eq 0 ]; then
        echo -e "${GREEN}✅ All tests passed!${NC}\n"
        return 0
    else
        echo -e "${RED}❌ Some tests failed!${NC}\n"
        return 1
    fi
}

# Main execution
main() {
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}🧪 pull-request-fixer Integration Tests${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"

    if ! command -v pull-request-fixer > /dev/null 2>&1; then
        echo -e "${RED}❌ pull-request-fixer is not on PATH${NC}"
        echo "   Run with: uv run bash scripts/integration-test.sh"
        exit 1
    fi

    test_version_flag
    test_help_shows_version
    test_short_help_flag
    test_help_documents_options
    test_missing_target
    test_no_fix_options
    test_fix_files_requires_file_pattern
    test_fix_files_requires_search_pattern
    test_fix_files_requires_action
    test_invalid_update_method
    test_conflicting_identity_flags
    test_missing_token
    test_workers_out_of_range

    print_summary
    exit $?
}

# Run main function
main "$@"
