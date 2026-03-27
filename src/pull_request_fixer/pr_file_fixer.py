# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""Fix files in pull requests by cloning, modifying, and pushing changes.

This module provides functionality for fixing files in GitHub pull requests
by cloning the PR branch, applying regex-based modifications, amending the
commit, and force-pushing the changes back.
"""

from __future__ import annotations

from contextlib import suppress
import logging
from pathlib import Path
import re
import subprocess
import tempfile
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .github_client import GitHubClient
    from .models import PRInfo

from .exceptions import ResourceNotFoundError
from .git_config import GitConfigMode, configure_git_identity
from .models import GitHubFixResult


class PRFileFixer:
    """Fixes files in pull requests using Git operations."""

    def __init__(
        self,
        client: GitHubClient,
        git_config_mode: str = GitConfigMode.USER_INHERIT,
    ) -> None:
        """Initialize PR file fixer.

        Args:
            client: GitHub API client for authentication and API calls
            git_config_mode: Git configuration mode (USER_INHERIT, USER_NO_SIGN, or BOT_IDENTITY)
        """
        self.client = client
        self.git_config_mode = git_config_mode
        self.logger = logging.getLogger("pull_request_fixer.pr_file_fixer")

    def _sanitize_message(self, message: str) -> str:
        """Remove sensitive information from messages.

        Args:
            message: Message that may contain tokens

        Returns:
            Sanitized message with tokens removed
        """
        # Remove common token patterns
        patterns = [
            r"ghp_[a-zA-Z0-9]{36}",  # GitHub personal access tokens
            r"ghs_[a-zA-Z0-9]{36}",  # GitHub server tokens
            r"github_pat_[a-zA-Z0-9_]{82}",  # GitHub fine-grained tokens
            r"https://[^:]+:[^@]+@",  # URLs with credentials
            r"x-access-token:[^@]+@",  # Git auth tokens
        ]

        sanitized = message
        for pattern in patterns:
            sanitized = re.sub(pattern, "[REDACTED]", sanitized)

        return sanitized

    async def fix_pr_by_url(  # noqa: PLR0911
        self,
        pr_url: str,
        file_pattern: str,
        search_pattern: str,
        replacement: str,
        *,
        remove_lines: bool = False,
        context_start: str | None = None,
        context_end: str | None = None,
        dry_run: bool = False,
        update_method: str = "api",
        pr_content_only: bool = False,
    ) -> GitHubFixResult:
        """Fix files in a PR by URL.

        Args:
            pr_url: GitHub PR URL (e.g., https://github.com/owner/repo/pull/123)
            file_pattern: Regex pattern to match file paths
            search_pattern: Regex pattern to search for in files
            replacement: Replacement string (or empty for line removal)
            remove_lines: If True, remove matching lines entirely
            context_start: Optional regex to define context start for line removal
            context_end: Optional regex to define context end for line removal
            dry_run: If True, don't actually push changes
            update_method: Method to apply fixes: 'git' (clone, amend, push) or 'api' (GitHub API)
            pr_content_only: If True, only fix files already modified in the PR

        Returns:
            GitHubFixResult with operation details
        """
        from .models import GitHubFixResult, PRInfo

        # Parse PR URL
        match = re.match(
            r"https?://github\.com/([^/]+)/([^/]+)/pull/(\d+)", pr_url
        )
        if not match:
            return GitHubFixResult(
                pr_info=PRInfo(
                    number=0,
                    title="",
                    repository="",
                    url=pr_url,
                    author="",
                    is_draft=False,
                    head_ref="",
                    head_sha="",
                    base_ref="",
                    mergeable="",
                    merge_state_status="",
                ),
                success=False,
                message=f"Invalid PR URL format: {pr_url}",
            )

        owner, repo, pr_number_str = match.groups()
        pr_number = int(pr_number_str)

        self.logger.debug(f"Processing PR: {owner}/{repo}#{pr_number}")

        try:
            # Get PR details
            error_message = None
            pr_data: dict[str, Any] | list[dict[str, Any]] | None = None
            try:
                pr_data = await self.client._request(
                    "GET", f"/repos/{owner}/{repo}/pulls/{pr_number}"
                )
            except ResourceNotFoundError:
                # PR not found (404) - provide friendly message
                error_message = f"Pull request #{pr_number} not found. It may have been closed, merged, or deleted."

            if error_message or not isinstance(pr_data, dict):
                return GitHubFixResult(
                    pr_info=PRInfo(
                        number=pr_number,
                        title="",
                        repository=f"{owner}/{repo}",
                        url=pr_url,
                        author="",
                        is_draft=False,
                        head_ref="",
                        head_sha="",
                        base_ref="",
                        mergeable="",
                        merge_state_status="",
                    ),
                    success=False,
                    message=error_message or "Failed to fetch PR data",
                )

            head = pr_data.get("head", {})
            head_sha = head.get("sha", "")
            head_ref = head.get("ref", "")
            head_repo = head.get("repo", {})
            clone_url = head_repo.get("clone_url", "")

            pr_info = PRInfo(
                number=pr_number,
                title=pr_data.get("title", ""),
                repository=f"{owner}/{repo}",
                url=pr_url,
                author=pr_data.get("user", {}).get("login", ""),
                is_draft=pr_data.get("draft", False),
                head_ref=head_ref,
                head_sha=head_sha,
                base_ref=pr_data.get("base", {}).get("ref", ""),
                mergeable=pr_data.get("mergeable", "unknown"),
                merge_state_status=pr_data.get("mergeable_state", "unknown"),
            )

            # Check if PR is closed
            pr_state = pr_data.get("state", "").lower()
            if pr_state != "open":
                # Check if it was merged
                is_merged = pr_data.get("merged", False)
                state_display = (
                    "merged"
                    if is_merged
                    else (pr_state if pr_state else "closed")
                )
                return GitHubFixResult(
                    pr_info=pr_info,
                    success=False,
                    message=f"Pull request #{pr_number} is {state_display} and cannot be processed",
                    file_modifications=[],
                )

            if not clone_url and update_method == "git":
                return GitHubFixResult(
                    pr_info=pr_info,
                    success=False,
                    message="PR head repository not accessible",
                    file_modifications=[],
                )

            # Route to appropriate update method
            if update_method == "api":
                # Use GitHub API to update files
                return await self._fix_pr_with_api(
                    pr_info,
                    owner,
                    repo,
                    pr_data,
                    file_pattern,
                    search_pattern,
                    replacement,
                    remove_lines=remove_lines,
                    context_start=context_start,
                    context_end=context_end,
                    dry_run=dry_run,
                    pr_content_only=pr_content_only,
                )
            else:
                # Clone and fix using Git operations
                return await self._fix_pr_with_git(
                    pr_info,
                    clone_url,
                    owner,
                    repo,
                    file_pattern,
                    search_pattern,
                    replacement,
                    remove_lines=remove_lines,
                    context_start=context_start,
                    context_end=context_end,
                    dry_run=dry_run,
                    pr_content_only=pr_content_only,
                )

        except Exception as e:
            self.logger.error(f"Error fixing PR: {e}", exc_info=True)
            return GitHubFixResult(
                pr_info=PRInfo(
                    number=pr_number,
                    title="",
                    repository=f"{owner}/{repo}",
                    url=pr_url,
                    author="",
                    is_draft=False,
                    head_ref="",
                    head_sha="",
                    base_ref="",
                    mergeable="",
                    merge_state_status="",
                ),
                success=False,
                message=str(e),
                error=str(e),
            )

    async def _fix_pr_with_git(  # noqa: PLR0911
        self,
        pr_info: PRInfo,
        clone_url: str,
        owner: str,
        repo: str,
        file_pattern: str,
        search_pattern: str,
        replacement: str,
        *,
        remove_lines: bool = False,
        context_start: str | None = None,
        context_end: str | None = None,
        dry_run: bool = False,
        git_config_mode: str | None = None,
        pr_content_only: bool = False,
    ) -> GitHubFixResult:
        """Fix PR using Git operations (clone, fix, amend, push).

        Args:
            pr_info: PR information
            clone_url: Repository clone URL
            owner: Repository owner
            repo: Repository name
            file_pattern: Regex pattern to match file paths
            search_pattern: Regex pattern to search for
            replacement: Replacement string
            remove_lines: If True, remove matching lines entirely
            context_start: Optional context start for line removal
            context_end: Optional context end for line removal
            dry_run: If True, don't push changes
            git_config_mode: Override git config mode for this operation
            pr_content_only: If True, only fix files already modified in the PR

        Returns:
            GitHubFixResult with operation details
        """
        # Use provided mode or fall back to instance default
        config_mode = git_config_mode or self.git_config_mode
        from .file_fixer import FileFixer
        from .models import GitHubFixResult

        with tempfile.TemporaryDirectory() as tmpdir:
            repo_dir = Path(tmpdir) / "repo"
            self.logger.debug(f"Cloning {clone_url} to {repo_dir}")

            try:
                # Clone the repository with authentication
                # Note: The token is embedded in the URL for git operations.
                # While this is the standard approach for HTTPS git authentication,
                # we ensure all error messages are sanitized via _sanitize_message()
                # to prevent token exposure in logs or error output.
                auth_url = clone_url.replace(
                    "https://", f"https://x-access-token:{self.client.token}@"
                )
                subprocess.run(
                    [
                        "git",
                        "clone",
                        "--branch",
                        pr_info.head_ref,
                        auth_url,
                        str(repo_dir),
                    ],
                    check=True,
                    capture_output=True,
                    text=True,
                )

                # Find and fix files
                fixer = FileFixer()
                all_matching_files = fixer.find_files(repo_dir, file_pattern)

                # Filter to PR files only if pr_content_only is True
                if pr_content_only:
                    # Get the list of files changed in this PR
                    pr_files = await self.client.get_pr_files(
                        owner, repo, pr_info.number
                    )
                    pr_file_paths = {f.get("filename", "") for f in pr_files}

                    matching_files = [
                        f
                        for f in all_matching_files
                        if str(f.relative_to(repo_dir)) in pr_file_paths
                    ]
                    self.logger.debug(
                        f"Found {len(all_matching_files)} files matching pattern, "
                        f"{len(matching_files)} are in PR"
                    )
                else:
                    matching_files = all_matching_files
                    self.logger.debug(
                        f"Found {len(matching_files)} files matching pattern"
                    )

                files_modified: list[Path] = []
                file_modifications: list[FileModification] = []
                total_changes = 0

                for file_path in matching_files:
                    self.logger.debug(f"Processing {file_path}")

                    if remove_lines:
                        # Use line removal mode
                        was_modified, original, modified = (
                            fixer.remove_lines_matching(
                                file_path,
                                search_pattern,
                                context_start=context_start,
                                context_end=context_end,
                                dry_run=False,  # Always apply to temp dir
                            )
                        )
                    else:
                        # Use regex replacement mode
                        was_modified, original, modified = fixer.apply_fix(
                            file_path,
                            search_pattern,
                            replacement,
                            dry_run=False,  # Always apply to temp dir
                        )

                    if was_modified:
                        from .models import FileModification

                        files_modified.append(file_path)
                        file_modifications.append(
                            FileModification(
                                file_path=file_path,
                                original_content=original,
                                modified_content=modified,
                            )
                        )
                        total_changes += 1
                        self.logger.debug(f"Modified {file_path.name}")

                # Handle no files modified or dry-run mode
                if not files_modified:
                    message = "No files required changes"
                    return GitHubFixResult(
                        pr_info=pr_info,
                        success=True,
                        message=message,
                        files_modified=[],
                        file_modifications=[],
                    )

                if dry_run:
                    count = len(files_modified)
                    message = (
                        f"Would fix {count} file{'s' if count != 1 else ''}"
                    )
                    return GitHubFixResult(
                        pr_info=pr_info,
                        success=True,
                        message=message,
                        files_modified=files_modified,
                        file_modifications=file_modifications,
                    )

                # Configure git identity and signing
                git_config = configure_git_identity(
                    repo_dir,
                    mode=config_mode,
                    bot_name="pull-request-fixer",
                    bot_email="noreply@linuxfoundation.org",
                )
                self.logger.debug(f"Git config applied: {git_config}")

                # Stage the changes
                for file_path in files_modified:
                    rel_path = file_path.relative_to(repo_dir)
                    subprocess.run(
                        ["git", "add", str(rel_path)],
                        cwd=repo_dir,
                        check=True,
                        capture_output=True,
                    )

                # Check if there are actually changes to commit
                result = subprocess.run(
                    ["git", "diff", "--cached", "--quiet"],
                    check=False,
                    cwd=repo_dir,
                    capture_output=True,
                )

                if result.returncode == 0:
                    # No changes - return early with success
                    self.logger.debug("No formatting changes needed")
                    return GitHubFixResult(
                        pr_info=pr_info,
                        success=True,
                        message="⏩ Files were already properly formatted",
                        files_modified=[],
                        file_modifications=[],
                    )

                # Amend the last commit
                self.logger.debug("Amending last commit with file fixes")
                subprocess.run(
                    ["git", "commit", "--amend", "--no-edit"],
                    cwd=repo_dir,
                    check=True,
                    capture_output=True,
                    text=True,
                )

                # Force push to update the PR
                self.logger.debug(f"Force pushing to {pr_info.head_ref}")
                try:
                    subprocess.run(
                        [
                            "git",
                            "push",
                            "--force-with-lease",
                            "origin",
                            pr_info.head_ref,
                        ],
                        cwd=repo_dir,
                        check=True,
                        capture_output=True,
                        text=True,
                    )
                except subprocess.CalledProcessError as e:
                    sanitized_stderr = self._sanitize_message(e.stderr or "")
                    self.logger.warning(
                        f"Push rejected - remote branch {pr_info.head_ref} was updated: {sanitized_stderr}"
                    )
                    error_msg = "Push rejected: PR branch was updated while processing. Please retry."
                    raise RuntimeError(error_msg) from e

                # Create a comment on the PR
                file_names = [
                    str(f.relative_to(repo_dir)) for f in files_modified
                ]
                comment_body = (
                    f"🛠️ **Pull Request Fixer**\n\n"
                    f"Fixed {total_changes} file(s): {', '.join(file_names)}\n\n"
                    f"The commit has been amended with the fixes.\n\n"
                    f"---\n"
                    f"*Automatically fixed by [pull-request-fixer]"
                    f"(https://github.com/lfit/pull-request-fixer)*"
                )

                with suppress(Exception):
                    await self.client.create_comment(
                        owner, repo, pr_info.number, comment_body
                    )

                count = len(files_modified)
                message = f"Updated {count} file{'s' if count != 1 else ''}"
                return GitHubFixResult(
                    pr_info=pr_info,
                    success=True,
                    message=message,
                    files_modified=files_modified,
                    file_modifications=file_modifications,
                )

            except subprocess.CalledProcessError as e:
                # Sanitize all error output to prevent token exposure
                sanitized_stderr = self._sanitize_message(e.stderr or "")
                sanitized_stdout = self._sanitize_message(e.stdout or "")
                sanitized_error = self._sanitize_message(str(e))
                self.logger.error(
                    f"Git operation failed: {sanitized_stderr}",
                    extra={"stdout": sanitized_stdout},
                )
                return GitHubFixResult(
                    pr_info=pr_info,
                    success=False,
                    message=f"Git operation failed: {sanitized_stderr}",
                    error=sanitized_error,
                    file_modifications=[],
                )
            except RuntimeError as e:
                # Handle expected errors (push rejections)
                return GitHubFixResult(
                    pr_info=pr_info,
                    success=False,
                    message=str(e),
                    error=str(e),
                    file_modifications=[],
                )
            except Exception as e:
                # Sanitize exception messages to prevent token exposure
                sanitized_message = self._sanitize_message(str(e))
                self.logger.error(
                    f"Error during fix: {sanitized_message}", exc_info=True
                )
                return GitHubFixResult(
                    pr_info=pr_info,
                    success=False,
                    message=sanitized_message,
                    error=sanitized_message,
                    file_modifications=[],
                )

    async def _fix_pr_with_api(
        self,
        pr_info: PRInfo,
        owner: str,
        repo: str,
        pr_data: dict[str, Any],
        file_pattern: str,
        search_pattern: str,
        replacement: str,
        *,
        remove_lines: bool = False,
        context_start: str | None = None,
        context_end: str | None = None,
        dry_run: bool = False,
        pr_content_only: bool = False,
    ) -> GitHubFixResult:
        """
        Fix PR using GitHub API (updates files).

        Note:
            Changes made via the GitHub API are marked as "Verified" by GitHub
            only if performed through a GitHub App with the appropriate permissions.
            If using a personal access token, changes will not be marked as "Verified"
            unless commit signature verification is configured separately.

        Args:
            pr_info: PR information
            owner: Repository owner
            repo: Repository name
            pr_data: Full PR data from API
            file_pattern: Regex pattern to match file paths
            search_pattern: Regex pattern to search for
            replacement: Replacement string
            remove_lines: If True, remove matching lines entirely
            context_start: Optional context start for line removal
            context_end: Optional context end for line removal
            dry_run: If True, don't actually push changes
            pr_content_only: If True, only fix files already modified in the PR

        Returns:
            GitHubFixResult with operation details
        """
        from .file_fixer import FileFixer
        from .models import FileModification

        branch = pr_info.head_ref
        pr_number = pr_info.number

        try:
            pattern = re.compile(file_pattern)

            if pr_content_only:
                # Get files from the PR only
                files = await self.client.get_pr_files(owner, repo, pr_number)

                # Debug: Log all files and their status
                self.logger.debug(f"Total files from PR: {len(files)}")
                for f in files:
                    filename = f.get("filename", "")
                    status = f.get("status")
                    self.logger.debug(f"  File: {filename}, status: {status!r}")

                matching_files = [
                    f
                    for f in files
                    if (
                        pattern.search(f.get("filename", ""))
                        or pattern.search(f"./{f.get('filename', '')}")
                    )
                    and f.get("status") != "removed"
                ]
            else:
                # Get all files from the repository that match the pattern
                # We need to use the Git tree API to get all files

                # Clone the PR branch to get all files
                clone_url = (
                    pr_data.get("head", {}).get("repo", {}).get("clone_url", "")
                )
                if not clone_url:
                    return GitHubFixResult(
                        pr_info=pr_info,
                        success=False,
                        message="Cannot access repository to list all files",
                        files_modified=[],
                        file_modifications=[],
                    )

                with tempfile.TemporaryDirectory() as tmpdir:
                    repo_dir = Path(tmpdir) / "repo"
                    auth_url = clone_url.replace(
                        "https://",
                        f"https://x-access-token:{self.client.token}@",
                    )
                    subprocess.run(
                        [
                            "git",
                            "clone",
                            "--depth=1",
                            "--branch",
                            pr_info.head_ref,
                            auth_url,
                            str(repo_dir),
                        ],
                        check=True,
                        capture_output=True,
                        text=True,
                    )

                    fixer = FileFixer()
                    file_paths = fixer.find_files(repo_dir, file_pattern)

                    # Convert to format expected by rest of function
                    matching_files = [
                        {
                            "filename": str(f.relative_to(repo_dir)),
                            "sha": None,  # We'll fetch this later
                            "status": "modified",
                        }
                        for f in file_paths
                    ]

            self.logger.debug(
                f"Found {len(matching_files)} files matching pattern"
            )

            if not matching_files:
                return GitHubFixResult(
                    pr_info=pr_info,
                    success=True,
                    message="No files matched the pattern",
                    files_modified=[],
                    file_modifications=[],
                )

            files_modified: list[Path] = []
            file_modifications: list[FileModification] = []
            fixer = FileFixer()

            # First pass: Process all files and collect modifications
            # This allows us to batch the API updates
            files_to_update: list[dict[str, str]] = []

            for file_data in matching_files:
                filename = file_data.get("filename", "")
                file_sha = file_data.get("sha")

                self.logger.debug(f"Processing {filename}")

                if not filename or not file_sha:
                    continue

                try:
                    # Get current file content
                    content = await self.client.get_file_content(
                        owner, repo, filename, branch
                    )

                    with tempfile.NamedTemporaryFile(
                        mode="w", suffix=".tmp", delete=False
                    ) as tmp_file:
                        tmp_file.write(content)
                        tmp_path = Path(tmp_file.name)

                    try:
                        # Apply fixes
                        if remove_lines:
                            was_modified, original, modified = (
                                fixer.remove_lines_matching(
                                    tmp_path,
                                    search_pattern,
                                    context_start=context_start,
                                    context_end=context_end,
                                    dry_run=False,
                                )
                            )
                        else:
                            was_modified, original, modified = fixer.apply_fix(
                                tmp_path,
                                search_pattern,
                                replacement,
                                dry_run=False,
                            )

                        if was_modified and modified != content:
                            files_modified.append(Path(filename))
                            file_modifications.append(
                                FileModification(
                                    file_path=Path(filename),
                                    original_content=original,
                                    modified_content=modified,
                                )
                            )

                            # Collect for batch update
                            if not dry_run:
                                files_to_update.append(
                                    {
                                        "path": filename,
                                        "content": modified,
                                    }
                                )
                    finally:
                        # Clean up temp file
                        tmp_path.unlink(missing_ok=True)

                except Exception as e:
                    self.logger.warning(f"Failed to process {filename}: {e}")
                    continue

            # Second pass: Batch update all modified files in a single commit
            # This is much more efficient than updating files one by one:
            # - Eliminates redundant SHA re-fetches
            # - Creates a single commit instead of multiple commits
            # - Reduces API calls from 3N to ~N (where N = number of files)
            if files_to_update and not dry_run:
                try:
                    file_list = ", ".join(f["path"] for f in files_to_update)
                    commit_message = (
                        f"Fix {len(files_to_update)} file(s) in PR #{pr_number}\n\n"
                        f"Applied pattern-based fixes to:\n"
                        f"{file_list}\n\n"
                        f"Automated by pull-request-fixer"
                    )

                    await self.client.update_files_in_batch(
                        owner,
                        repo,
                        branch,
                        files_to_update,
                        commit_message,
                    )
                    self.logger.debug(
                        f"Successfully updated {len(files_to_update)} files in a single commit"
                    )
                except Exception as e:
                    # Fall back to individual file updates if batch fails
                    self.logger.warning(
                        f"Batch update failed, falling back to individual updates: {e}"
                    )
                    for file_info in files_to_update:
                        try:
                            # Re-fetch file to get current SHA for individual update
                            refetched_file_data = await self.client._request(
                                "GET",
                                f"/repos/{owner}/{repo}/contents/{file_info['path']}",
                                params={"ref": branch},
                            )
                            if isinstance(refetched_file_data, dict):
                                current_sha = refetched_file_data.get("sha", "")
                            else:
                                self.logger.warning(
                                    f"Could not get SHA for {file_info['path']}, skipping"
                                )
                                continue

                            commit_message = (
                                f"Fix {file_info['path']}\n\n"
                                f"Applied pattern-based fixes in PR #{pr_number}"
                            )

                            await self.client.update_file(
                                owner,
                                repo,
                                file_info["path"],
                                file_info["content"],
                                commit_message,
                                branch,
                                current_sha,
                            )
                            self.logger.debug(
                                f"Successfully updated {file_info['path']} (fallback)"
                            )
                        except Exception as file_error:
                            self.logger.error(
                                f"Failed to update {file_info['path']}: {file_error}"
                            )

            if not files_modified:
                return GitHubFixResult(
                    pr_info=pr_info,
                    success=True,
                    message="No files required changes",
                    files_modified=[],
                    file_modifications=[],
                )

            # Create comment
            if not dry_run:
                file_names = [str(f) for f in files_modified]
                comment_body = (
                    f"🛠️ **Pull Request Fixer**\n\n"
                    f"Fixed {len(files_modified)} file(s): {', '.join(file_names)}\n\n"
                    f"Changes applied via GitHub API.\n\n"
                    f"---\n"
                    f"*Automatically fixed by [pull-request-fixer]"
                    f"(https://github.com/lfit/pull-request-fixer)*"
                )

                try:
                    await self.client.create_comment(
                        owner, repo, pr_number, comment_body
                    )
                except Exception as e:
                    self.logger.debug(f"Failed to create PR comment: {e}")

            count = len(files_modified)
            message = (
                f"[DRY RUN] Would update {count} file{'s' if count != 1 else ''}"
                if dry_run
                else f"Updated {count} file{'s' if count != 1 else ''}"
            )

            return GitHubFixResult(
                pr_info=pr_info,
                success=True,
                message=message,
                files_modified=files_modified,
                file_modifications=file_modifications,
            )

        except Exception as e:
            sanitized_message = self._sanitize_message(str(e))
            self.logger.error(
                f"Error during API fix: {sanitized_message}", exc_info=True
            )
            return GitHubFixResult(
                pr_info=pr_info,
                success=False,
                message=f"API fix failed: {sanitized_message}",
                error=sanitized_message,
                file_modifications=[],
            )
