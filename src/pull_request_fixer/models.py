# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""Data models for pr-title-fixer."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


# aislop-ignore-next-line ruff/UP042 -- StrEnum requires Python 3.11+, project targets 3.10
class OutputFormat(str, Enum):
    """Output format options."""

    TEXT = "text"
    JSON = "json"
    TABLE = "table"


@dataclass
class PRInfo:
    """Information about a GitHub pull request."""

    number: int
    title: str
    repository: str
    url: str
    author: str
    is_draft: bool
    head_ref: str
    head_sha: str
    base_ref: str
    mergeable: str
    merge_state_status: str


@dataclass
class BlockedPR:
    """A blocked pull request with blocking reasons."""

    pr_info: PRInfo
    blocking_reasons: list[str]
    has_title_issues: bool = False


@dataclass
class GitHubScanResult:
    """Results from scanning a GitHub organization."""

    organization: str
    repositories_scanned: int = 0
    total_prs: int = 0
    blocked_prs: list[BlockedPR] = field(default_factory=list)
    prs_fixed: int = 0
    errors: list[str] = field(default_factory=list)


@dataclass
class FileModification:
    """Information about a file modification."""

    file_path: Path
    original_content: str
    modified_content: str

    @property
    def diff(self) -> str:
        """Generate a unified diff for the modification."""
        import difflib

        original_lines = self.original_content.splitlines(keepends=False)
        modified_lines = self.modified_content.splitlines(keepends=False)

        # Use just the filename for cleaner diff output
        filename = self.file_path.name

        diff_lines = difflib.unified_diff(
            original_lines,
            modified_lines,
            fromfile=filename,
            tofile=filename,
            lineterm="",
        )

        return "\n".join(diff_lines)


@dataclass
class FileFixSpec:
    """Parameters describing how to fix files within a pull request.

    Groups the file-matching and replacement options that are threaded
    together through the file-fixing pipeline.
    """

    file_pattern: str
    search_pattern: str
    replacement: str
    remove_lines: bool = False
    context_start: str | None = None
    context_end: str | None = None
    dry_run: bool = False
    pr_content_only: bool = False


@dataclass
class FixOptions:
    """Shared options controlling how PR titles, bodies, and files are fixed.

    Groups the common configuration threaded from the CLI into the
    single-PR and organization-scan processing flows.
    """

    fix_title: bool
    fix_body: bool
    fix_files: bool
    file_pattern: str | None
    search_pattern: str | None
    replacement: str
    remove_lines: bool
    context_start: str | None
    context_end: str | None
    pr_content_only: bool
    dry_run: bool
    show_diff: bool
    quiet: bool
    git_config_mode: str
    update_method: str


@dataclass
class GitHubFixResult:
    """Result of fixing a PR."""

    pr_info: PRInfo
    success: bool
    message: str
    files_modified: list[Path] = field(default_factory=list)
    file_modifications: list[FileModification] = field(default_factory=list)
    error: str | None = None
