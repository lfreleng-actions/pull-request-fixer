# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""File content modification using regex patterns.

This module provides functionality for finding files matching patterns and
performing regex-based search/replace operations on their content.
"""

from __future__ import annotations

import logging
from pathlib import Path  # noqa: TC003
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable


class FileFixer:
    """Handles regex-based file content modifications."""

    def __init__(self) -> None:
        """Initialize the file fixer."""
        self.logger = logging.getLogger("pull_request_fixer.file_fixer")

    def find_files(self, root_dir: Path, file_pattern: str) -> list[Path]:
        """Find files matching a regex pattern.

        Args:
            root_dir: Root directory to search from
            file_pattern: Regex pattern to match file paths (relative to root)

        Returns:
            List of matching file paths
        """
        try:
            pattern = re.compile(file_pattern)
        except re.error as e:
            self.logger.error(f"Invalid file pattern regex: {e}")
            return []

        matching_files: list[Path] = []

        # Walk the directory tree
        for path in root_dir.rglob("*"):
            if not path.is_file():
                continue

            try:
                rel_path = path.relative_to(root_dir)
                rel_path_str = str(rel_path)

                # Try both with ./ prefix and without
                if pattern.search(rel_path_str) or pattern.search(
                    f"./{rel_path_str}"
                ):
                    matching_files.append(path)
                    self.logger.debug(f"Matched file: {rel_path_str}")
            except ValueError:
                # Path is not relative to root_dir
                continue

        self.logger.debug(
            f"Found {len(matching_files)} files matching pattern '{file_pattern}'"
        )
        return matching_files

    def apply_fix(
        self,
        file_path: Path,
        search_pattern: str,
        replacement: str | Callable[[re.Match[str]], str],
        *,
        dry_run: bool = False,
    ) -> tuple[bool, str, str]:
        """Apply regex search/replace to a file.

        Args:
            file_path: Path to file to modify
            search_pattern: Regex pattern to search for
            replacement: Replacement string or function
            dry_run: If True, don't write changes

        Returns:
            Tuple of (was_modified, original_content, new_content)
        """
        try:
            # Read original content
            original_content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            self.logger.error(f"Error reading {file_path}: {e}")
            return False, "", ""

        try:
            # Compile pattern
            pattern = re.compile(search_pattern, re.MULTILINE)
        except re.error as e:
            self.logger.error(f"Invalid search pattern regex: {e}")
            return False, original_content, original_content

        # Apply replacement
        try:
            if callable(replacement):
                new_content = pattern.sub(replacement, original_content)
            else:
                new_content = pattern.sub(replacement, original_content)
        except Exception as e:
            self.logger.error(f"Error applying replacement: {e}")
            return False, original_content, original_content

        # Check if content changed
        if new_content == original_content:
            self.logger.debug(f"No changes needed for {file_path}")
            return False, original_content, new_content

        # Write changes if not dry run
        if not dry_run:
            try:
                file_path.write_text(new_content, encoding="utf-8")
                self.logger.debug(f"Modified {file_path}")
            except Exception as e:
                self.logger.error(f"Error writing {file_path}: {e}")
                return False, original_content, original_content

        return True, original_content, new_content

    def remove_lines_matching(
        self,
        file_path: Path,
        line_pattern: str,
        *,
        context_start: str | None = None,
        context_end: str | None = None,
        dry_run: bool = False,
    ) -> tuple[bool, str, str]:
        """Remove lines matching a pattern, optionally within a context.

        This is a specialized method for the common case of removing lines,
        particularly useful for removing lines between section markers.

        Args:
            file_path: Path to file to modify
            line_pattern: Regex pattern to match lines to remove
            context_start: Optional regex to define context start (e.g., "inputs:")
            context_end: Optional regex to define context end (e.g., "runs:")
            dry_run: If True, don't write changes

        Returns:
            Tuple of (was_modified, original_content, new_content)
        """
        try:
            original_content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            self.logger.error(f"Error reading {file_path}: {e}")
            return False, "", ""

        lines = original_content.splitlines(keepends=True)
        new_lines: list[str] = []

        try:
            line_regex = re.compile(line_pattern)
            context_start_regex = (
                re.compile(context_start) if context_start else None
            )
            context_end_regex = re.compile(context_end) if context_end else None
        except re.error as e:
            self.logger.error(f"Invalid regex pattern: {e}")
            return False, original_content, original_content

        in_context = context_start_regex is None  # If no context, always active
        removed_count = 0

        for line in lines:
            if context_start_regex and context_start_regex.search(line):
                in_context = True
                new_lines.append(line)
                continue

            if context_end_regex and context_end_regex.search(line):
                in_context = False
                new_lines.append(line)
                continue

            # Check if line should be removed
            if in_context and line_regex.search(line):
                removed_count += 1
                self.logger.debug(f"Removing line: {line.rstrip()}")
                continue

            new_lines.append(line)

        if removed_count == 0:
            self.logger.debug(f"No lines removed from {file_path}")
            return False, original_content, original_content

        new_content = "".join(new_lines)

        # Write changes if not dry run
        if not dry_run:
            try:
                file_path.write_text(new_content, encoding="utf-8")
                self.logger.debug(
                    f"Modified {file_path}: removed {removed_count} line(s)"
                )
            except Exception as e:
                self.logger.error(f"Error writing {file_path}: {e}")
                return False, original_content, original_content

        return True, original_content, new_content


def create_line_removal_pattern(
    line_content: str,
    *,
    context_start: str | None = None,
    context_end: str | None = None,
) -> str:
    """Create a regex pattern for removing lines between context markers.

    This is a helper function for building complex removal patterns.

    Args:
        line_content: Content that lines must contain to be removed
        context_start: Optional start context marker
        context_end: Optional end context marker

    Returns:
        Regex pattern string
    """
    # Escape special regex characters in the line content
    escaped_content = re.escape(line_content)

    if context_start and context_end:
        # Build pattern that matches content between markers
        # This is a simplified version - for complex cases, use remove_lines_matching
        escaped_start = re.escape(context_start)
        escaped_end = re.escape(context_end)
        return rf"(?<=^{escaped_start}\n).*{escaped_content}.*\n(?=.*{escaped_end})"

    # Simple pattern for line containing content
    return rf"^.*{escaped_content}.*\n"
