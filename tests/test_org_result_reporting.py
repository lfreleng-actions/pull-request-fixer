# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 The Linux Foundation

"""Tests for organization result tallying in the CLI.

These lock in the ``(prs_with_changes, failed_count)`` accounting used to
render the summary line after an organization-wide scan, independent of the
console output.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from pull_request_fixer.cli import _report_org_results


def _fix_result(*, has_files: bool) -> SimpleNamespace:
    """Build a minimal stand-in for a GitHubFixResult."""
    return SimpleNamespace(
        success=True,
        message="done",
        file_modifications=["mod"] if has_files else [],
        error=None,
    )


def test_counts_changes_and_failures_quietly() -> None:
    results: list[Any] = [
        {
            "status": "success",
            "pr_id": "o/r#1",
            "result": _fix_result(has_files=True),
        },
        {
            "status": "success",
            "pr_id": "o/r#2",
            "title": {"previous": "a", "updated": "b"},
        },
        {
            "status": "success",
            "pr_id": "o/r#3",
            "result": _fix_result(has_files=False),
        },
        {"status": "failed", "pr_id": "o/r#4", "error": "boom"},
        RuntimeError("network"),
    ]

    prs_with_changes, failed_count = _report_org_results(
        results, quiet=True, dry_run=False, show_diff=False
    )

    assert prs_with_changes == 2
    assert failed_count == 2


def test_success_without_changes_is_not_counted() -> None:
    results: list[Any] = [
        {
            "status": "success",
            "pr_id": "o/r#1",
            "result": _fix_result(has_files=False),
        },
    ]

    prs_with_changes, failed_count = _report_org_results(
        results, quiet=True, dry_run=False, show_diff=False
    )

    assert prs_with_changes == 0
    assert failed_count == 0


def test_non_dict_non_exception_results_are_ignored() -> None:
    prs_with_changes, failed_count = _report_org_results(
        ["unexpected", None], quiet=False, dry_run=False, show_diff=False
    )

    assert prs_with_changes == 0
    assert failed_count == 0
