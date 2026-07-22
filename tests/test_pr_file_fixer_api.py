# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""Comprehensive test suite for PRFileFixer._fix_pr_with_api method.

Tests cover:
- Successful file modifications via GitHub API
- Pattern matching and filtering
- Line removal with context
- Search and replace operations
- Dry run mode
- Error handling and edge cases
- GitHub API interaction mocking
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

from pull_request_fixer.github_client import GitHubClient
from pull_request_fixer.models import FileFixSpec, PRInfo
from pull_request_fixer.pr_file_fixer import PRFileFixer


class TestFixPRWithAPI:
    """Test suite for _fix_pr_with_api method."""

    @pytest.fixture
    def mock_client(self) -> Mock:
        """Create a mocked GitHub client."""
        client = MagicMock(spec=GitHubClient)
        client.get_pr_files = AsyncMock()  # type: ignore[method-assign]
        client.get_file_content = AsyncMock()  # type: ignore[method-assign]
        client.update_file = AsyncMock()  # type: ignore[method-assign]
        client.create_comment = AsyncMock()  # type: ignore[method-assign]
        client._request = AsyncMock()  # type: ignore[method-assign]
        client.update_files_in_batch = AsyncMock()  # type: ignore[method-assign]
        return client

    @pytest.fixture
    def pr_fixer(self, mock_client: Mock) -> PRFileFixer:
        """Create a PRFileFixer instance with mocked client."""
        return PRFileFixer(client=mock_client)  # type: ignore[arg-type]

    @pytest.fixture
    def pr_info(self) -> PRInfo:
        """Create sample PR information."""
        return PRInfo(
            number=123,
            title="Test PR",
            repository="owner/repo",
            url="https://github.com/owner/repo/pull/123",
            author="test-user",
            is_draft=False,
            head_ref="feature-branch",
            head_sha="abc123",
            base_ref="main",
            mergeable="MERGEABLE",
            merge_state_status="CLEAN",
        )

    @pytest.fixture
    def pr_data(self) -> dict[str, Any]:
        """Create sample PR data."""
        return {
            "number": 123,
            "title": "Test PR",
            "head": {"ref": "feature-branch", "sha": "abc123"},
            "base": {"ref": "main"},
        }

    @pytest.mark.asyncio
    async def test_successful_pattern_replacement(
        self,
        pr_fixer: PRFileFixer,
        mock_client: Mock,
        pr_info: PRInfo,
        pr_data: dict[str, Any],
    ) -> None:
        """Test successful search and replace operation."""
        # Setup mock responses
        mock_client.get_pr_files.return_value = [
            {"filename": "test.yaml", "sha": "file123", "status": "modified"}
        ]
        mock_client.get_file_content.return_value = "old_value: test\n"
        mock_client.update_files_in_batch.return_value = None
        mock_client.create_comment.return_value = {"id": 1}

        # Execute
        result = await pr_fixer._fix_pr_with_api(
            pr_info=pr_info,
            owner="owner",
            repo="repo",
            pr_data=pr_data,
            spec=FileFixSpec(
                file_pattern=r"\.yaml$",
                search_pattern=r"old_value",
                replacement="new_value",
                dry_run=False,
                pr_content_only=True,
            ),
        )

        # Verify
        assert result.success is True
        assert result.message == "Updated 1 file"
        assert len(result.files_modified) == 1
        assert result.files_modified[0] == Path("test.yaml")
        assert len(result.file_modifications) == 1
        assert "new_value" in result.file_modifications[0].modified_content
        assert "old_value" not in result.file_modifications[0].modified_content

        # Verify API calls
        mock_client.get_pr_files.assert_called_once_with("owner", "repo", 123)
        mock_client.get_file_content.assert_called_once_with(
            "owner", "repo", "test.yaml", "feature-branch"
        )
        mock_client.update_files_in_batch.assert_called_once()
        mock_client.create_comment.assert_called_once()

    @pytest.mark.asyncio
    async def test_remove_lines_matching(
        self,
        pr_fixer: PRFileFixer,
        mock_client: Mock,
        pr_info: PRInfo,
        pr_data: dict[str, Any],
    ) -> None:
        """Test removing lines matching a pattern."""
        # Setup
        original_content = """inputs:
  param1:
    type: string
  param2:
    type: boolean
runs:
  using: composite
"""
        mock_client.get_pr_files.return_value = [
            {"filename": "action.yaml", "sha": "file456", "status": "modified"}
        ]
        mock_client.get_file_content.return_value = original_content
        mock_client._request.return_value = {"sha": "file456"}
        mock_client.update_file.return_value = {"commit": {"sha": "new_commit"}}

        # Execute
        result = await pr_fixer._fix_pr_with_api(
            pr_info=pr_info,
            owner="owner",
            repo="repo",
            pr_data=pr_data,
            spec=FileFixSpec(
                file_pattern=r"action\.yaml$",
                search_pattern=r"type:",
                replacement="",
                remove_lines=True,
                context_start=r"inputs:",
                context_end=r"runs:",
                dry_run=False,
                pr_content_only=True,
            ),
        )

        # Verify
        assert result.success is True
        assert len(result.files_modified) == 1
        assert "type:" not in result.file_modifications[0].modified_content
        assert "param1:" in result.file_modifications[0].modified_content
        assert "runs:" in result.file_modifications[0].modified_content

    @pytest.mark.asyncio
    async def test_multiple_files_modified(
        self,
        pr_fixer: PRFileFixer,
        mock_client: Mock,
        pr_info: PRInfo,
        pr_data: dict[str, Any],
    ) -> None:
        """Test modifying multiple files in a single PR."""
        # Setup
        mock_client.get_pr_files.return_value = [
            {"filename": "file1.yaml", "sha": "sha1", "status": "modified"},
            {"filename": "file2.yaml", "sha": "sha2", "status": "modified"},
            {"filename": "file3.txt", "sha": "sha3", "status": "modified"},
        ]

        async def get_content_side_effect(
            _owner: str, _repo: str, path: str, _ref: str
        ) -> str:
            if path.endswith(".yaml"):
                return "old_value: test\n"
            return "other content\n"

        mock_client.get_file_content.side_effect = get_content_side_effect
        mock_client._request.return_value = {"sha": "current_sha"}
        mock_client.update_file.return_value = {"commit": {"sha": "new"}}

        # Execute - only match .yaml files
        result = await pr_fixer._fix_pr_with_api(
            pr_info=pr_info,
            owner="owner",
            repo="repo",
            pr_data=pr_data,
            spec=FileFixSpec(
                file_pattern=r"\.yaml$",
                search_pattern=r"old_value",
                replacement="new_value",
                dry_run=False,
                pr_content_only=True,
            ),
        )

        # Verify
        assert result.success is True
        assert result.message == "Updated 2 files"
        assert len(result.files_modified) == 2
        assert Path("file1.yaml") in result.files_modified
        assert Path("file2.yaml") in result.files_modified
        assert Path("file3.txt") not in result.files_modified

    @pytest.mark.asyncio
    async def test_dry_run_mode(
        self,
        pr_fixer: PRFileFixer,
        mock_client: Mock,
        pr_info: PRInfo,
        pr_data: dict[str, Any],
    ) -> None:
        """Test dry run mode does not make actual changes."""
        # Setup
        mock_client.get_pr_files.return_value = [
            {"filename": "test.yaml", "sha": "file123", "status": "modified"}
        ]
        mock_client.get_file_content.return_value = "old_value: test\n"

        # Execute
        result = await pr_fixer._fix_pr_with_api(
            pr_info=pr_info,
            owner="owner",
            repo="repo",
            pr_data=pr_data,
            spec=FileFixSpec(
                file_pattern=r"\.yaml$",
                search_pattern=r"old_value",
                replacement="new_value",
                dry_run=True,
                pr_content_only=True,
            ),
        )

        # Verify
        assert result.success is True
        assert result.message == "[DRY RUN] Would update 1 file"
        assert len(result.files_modified) == 1
        assert len(result.file_modifications) == 1

        # Verify no actual changes were made
        mock_client.update_file.assert_not_called()
        mock_client.create_comment.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_files_matching_pattern(
        self,
        pr_fixer: PRFileFixer,
        mock_client: Mock,
        pr_info: PRInfo,
        pr_data: dict[str, Any],
    ) -> None:
        """Test when no files match the pattern."""
        # Setup
        mock_client.get_pr_files.return_value = [
            {"filename": "test.txt", "sha": "file123", "status": "modified"}
        ]

        # Execute - looking for .yaml files
        result = await pr_fixer._fix_pr_with_api(
            pr_info=pr_info,
            owner="owner",
            repo="repo",
            pr_data=pr_data,
            spec=FileFixSpec(
                file_pattern=r"\.yaml$",
                search_pattern=r"old_value",
                replacement="new_value",
                dry_run=False,
                pr_content_only=True,
            ),
        )

        # Verify
        assert result.success is True
        assert result.message == "No files matched the pattern"
        assert len(result.files_modified) == 0
        assert len(result.file_modifications) == 0
        mock_client.get_file_content.assert_not_called()

    @pytest.mark.asyncio
    async def test_file_pattern_with_dot_slash_prefix(
        self,
        pr_fixer: PRFileFixer,
        mock_client: Mock,
        pr_info: PRInfo,
        pr_data: dict[str, Any],
    ) -> None:
        """Test that file patterns with './' prefix match correctly."""
        # Setup
        mock_client.get_pr_files.return_value = [
            {"filename": "action.yaml", "sha": "file123", "status": "modified"}
        ]
        mock_client.get_file_content.return_value = "old_value: test\n"
        mock_client.update_files_in_batch.return_value = None
        mock_client.create_comment.return_value = {"id": 1}

        # Execute - using a pattern with './' prefix (should match 'action.yaml')
        result = await pr_fixer._fix_pr_with_api(
            pr_info=pr_info,
            owner="owner",
            repo="repo",
            pr_data=pr_data,
            spec=FileFixSpec(
                file_pattern=r"^\./action\.yaml$",
                search_pattern=r"old_value",
                replacement="new_value",
                dry_run=False,
                pr_content_only=True,
            ),
        )

        # Verify
        assert result.success is True
        assert result.message == "Updated 1 file"
        assert len(result.files_modified) == 1
        assert result.files_modified[0] == Path("action.yaml")
        assert len(result.file_modifications) == 1
        assert "new_value" in result.file_modifications[0].modified_content
        assert "old_value" not in result.file_modifications[0].modified_content

        # Verify API calls
        mock_client.get_pr_files.assert_called_once_with("owner", "repo", 123)
        mock_client.get_file_content.assert_called_once_with(
            "owner", "repo", "action.yaml", "feature-branch"
        )
        mock_client.update_files_in_batch.assert_called_once()
        mock_client.create_comment.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_changes_needed(
        self,
        pr_fixer: PRFileFixer,
        mock_client: Mock,
        pr_info: PRInfo,
        pr_data: dict[str, Any],
    ) -> None:
        """Test when files match pattern but no changes are needed."""
        # Setup
        mock_client.get_pr_files.return_value = [
            {"filename": "test.yaml", "sha": "file123", "status": "modified"}
        ]
        mock_client.get_file_content.return_value = "content: value\n"

        # Execute - search for pattern that doesn't exist
        result = await pr_fixer._fix_pr_with_api(
            pr_info=pr_info,
            owner="owner",
            repo="repo",
            pr_data=pr_data,
            spec=FileFixSpec(
                file_pattern=r"\.yaml$",
                search_pattern=r"nonexistent",
                replacement="new_value",
                dry_run=False,
                pr_content_only=True,
            ),
        )

        # Verify
        assert result.success is True
        assert result.message == "No files required changes"
        assert len(result.files_modified) == 0
        mock_client.update_file.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_removed_files(
        self,
        pr_fixer: PRFileFixer,
        mock_client: Mock,
        pr_info: PRInfo,
        pr_data: dict[str, Any],
    ) -> None:
        """Test that removed files are skipped."""
        # Setup
        mock_client.get_pr_files.return_value = [
            {"filename": "test.yaml", "sha": "file123", "status": "removed"},
            {"filename": "other.yaml", "sha": "file456", "status": "modified"},
        ]
        mock_client.get_file_content.return_value = "old_value: test\n"
        mock_client._request.return_value = {"sha": "file456"}
        mock_client.update_file.return_value = {"commit": {"sha": "new"}}

        # Execute
        result = await pr_fixer._fix_pr_with_api(
            pr_info=pr_info,
            owner="owner",
            repo="repo",
            pr_data=pr_data,
            spec=FileFixSpec(
                file_pattern=r"\.yaml$",
                search_pattern=r"old_value",
                replacement="new_value",
                dry_run=False,
                pr_content_only=True,
            ),
        )

        # Verify - only other.yaml should be processed
        assert result.success is True
        assert len(result.files_modified) == 1
        assert result.files_modified[0] == Path("other.yaml")

    @pytest.mark.asyncio
    async def test_skips_files_without_filename(
        self,
        pr_fixer: PRFileFixer,
        mock_client: Mock,
        pr_info: PRInfo,
        pr_data: dict[str, Any],
    ) -> None:
        """Test that files without a filename are skipped.

        The API sha in the file entry is not consumed by the fix flow
        (content is fetched by path+branch and the sha is refetched
        before pushing), so a missing sha must not skip a file. Only a
        missing filename is disqualifying.
        """
        # Setup
        mock_client.get_pr_files.return_value = [
            {"sha": "file123", "status": "modified"},  # Missing filename
            {"filename": "test2.yaml", "status": "modified"},  # Missing sha
            {"filename": "test3.yaml", "sha": "file456", "status": "modified"},
        ]
        mock_client.get_file_content.return_value = "old_value: test\n"
        mock_client._request.return_value = {"sha": "file456"}
        mock_client.update_file.return_value = {"commit": {"sha": "new"}}

        # Execute
        result = await pr_fixer._fix_pr_with_api(
            pr_info=pr_info,
            owner="owner",
            repo="repo",
            pr_data=pr_data,
            spec=FileFixSpec(
                file_pattern=r"\.yaml$",
                search_pattern=r"old_value",
                replacement="new_value",
                dry_run=False,
                pr_content_only=True,
            ),
        )

        # Verify - the entry missing a filename is skipped; both files
        # with a filename are processed regardless of the sha field.
        assert result.success is True
        assert len(result.files_modified) == 2
        assert Path("test2.yaml") in result.files_modified
        assert Path("test3.yaml") in result.files_modified

    @pytest.mark.asyncio
    async def test_file_processing_error_continues(
        self,
        pr_fixer: PRFileFixer,
        mock_client: Mock,
        pr_info: PRInfo,
        pr_data: dict[str, Any],
    ) -> None:
        """Test that errors processing individual files don't stop the entire operation."""
        # Setup
        mock_client.get_pr_files.return_value = [
            {"filename": "file1.yaml", "sha": "sha1", "status": "modified"},
            {"filename": "file2.yaml", "sha": "sha2", "status": "modified"},
        ]

        # First file raises error, second succeeds
        async def get_content_side_effect(
            _owner: str, _repo: str, path: str, _ref: str
        ) -> str:
            if path == "file1.yaml":
                raise Exception("Failed to get content")
            return "old_value: test\n"

        mock_client.get_file_content.side_effect = get_content_side_effect
        mock_client._request.return_value = {"sha": "sha2"}
        mock_client.update_file.return_value = {"commit": {"sha": "new"}}

        # Execute
        result = await pr_fixer._fix_pr_with_api(
            pr_info=pr_info,
            owner="owner",
            repo="repo",
            pr_data=pr_data,
            spec=FileFixSpec(
                file_pattern=r"\.yaml$",
                search_pattern=r"old_value",
                replacement="new_value",
                dry_run=False,
                pr_content_only=True,
            ),
        )

        # Verify - file2.yaml should still be processed
        assert result.success is True
        assert len(result.files_modified) == 1
        assert result.files_modified[0] == Path("file2.yaml")

    @pytest.mark.asyncio
    async def test_api_error_handling(
        self,
        pr_fixer: PRFileFixer,
        mock_client: Mock,
        pr_info: PRInfo,
        pr_data: dict[str, Any],
    ) -> None:
        """Test error handling when GitHub API fails."""
        # Setup - API call fails
        mock_client.get_pr_files.side_effect = Exception("API Error")

        # Execute
        result = await pr_fixer._fix_pr_with_api(
            pr_info=pr_info,
            owner="owner",
            repo="repo",
            pr_data=pr_data,
            spec=FileFixSpec(
                file_pattern=r"\.yaml$",
                search_pattern=r"old_value",
                replacement="new_value",
                dry_run=False,
                pr_content_only=True,
            ),
        )

        # Verify
        assert result.success is False
        assert "API fix failed" in result.message
        assert result.error is not None
        assert "API Error" in result.error
        assert len(result.files_modified) == 0

    @pytest.mark.asyncio
    async def test_token_sanitization_in_errors(
        self,
        pr_fixer: PRFileFixer,
        mock_client: Mock,
        pr_info: PRInfo,
        pr_data: dict[str, Any],
    ) -> None:
        """Test that tokens are sanitized in error messages."""
        # Setup - API call fails with token in message
        error_msg = "Authentication failed for https://x-access-token:ghp_1234567890123456789012345678901234@github.com/owner/repo"
        mock_client.get_pr_files.side_effect = Exception(error_msg)

        # Execute
        result = await pr_fixer._fix_pr_with_api(
            pr_info=pr_info,
            owner="owner",
            repo="repo",
            pr_data=pr_data,
            spec=FileFixSpec(
                file_pattern=r"\.yaml$",
                search_pattern=r"old_value",
                replacement="new_value",
                dry_run=False,
                pr_content_only=True,
            ),
        )

        # Verify token is redacted
        assert result.success is False
        assert result.error is not None
        assert "ghp_" not in result.error
        assert "[REDACTED]" in result.error

    @pytest.mark.asyncio
    async def test_sha_refetch_for_concurrent_changes(
        self,
        pr_fixer: PRFileFixer,
        mock_client: Mock,
        pr_info: PRInfo,
        pr_data: dict[str, Any],
    ) -> None:
        """Test that batch update handles file updates correctly."""
        # Setup
        mock_client.get_pr_files.return_value = [
            {"filename": "test.yaml", "sha": "old_sha", "status": "modified"}
        ]
        mock_client.get_file_content.return_value = "old_value: test\n"
        mock_client.update_files_in_batch.return_value = None

        # Execute
        result = await pr_fixer._fix_pr_with_api(
            pr_info=pr_info,
            owner="owner",
            repo="repo",
            pr_data=pr_data,
            spec=FileFixSpec(
                file_pattern=r"\.yaml$",
                search_pattern=r"old_value",
                replacement="new_value",
                dry_run=False,
                pr_content_only=True,
            ),
        )

        # Verify
        assert result.success is True

        # Verify update_files_in_batch was called
        mock_client.update_files_in_batch.assert_called_once()
        update_call = mock_client.update_files_in_batch.call_args
        # Check that the files to update contain the correct content
        files_to_update = update_call[0][3]
        assert len(files_to_update) == 1
        assert files_to_update[0]["path"] == "test.yaml"
        assert "new_value" in files_to_update[0]["content"]

    @pytest.mark.asyncio
    async def test_sha_fallback_when_refetch_returns_list(
        self,
        pr_fixer: PRFileFixer,
        mock_client: Mock,
        pr_info: PRInfo,
        pr_data: dict[str, Any],
    ) -> None:
        """Test fallback to individual updates when batch update fails."""
        # Setup
        mock_client.get_pr_files.return_value = [
            {
                "filename": "test.yaml",
                "sha": "original_sha",
                "status": "modified",
            }
        ]
        mock_client.get_file_content.return_value = "old_value: test\n"
        # Batch update fails, triggering fallback
        mock_client.update_files_in_batch.side_effect = Exception(
            "Batch failed"
        )
        # Refetch returns list instead of dict (edge case)
        mock_client._request.return_value = []
        mock_client.update_file.return_value = {"commit": {"sha": "commit_sha"}}

        # Execute
        result = await pr_fixer._fix_pr_with_api(
            pr_info=pr_info,
            owner="owner",
            repo="repo",
            pr_data=pr_data,
            spec=FileFixSpec(
                file_pattern=r"\.yaml$",
                search_pattern=r"old_value",
                replacement="new_value",
                dry_run=False,
                pr_content_only=True,
            ),
        )

        # Verify - fallback should skip the file when refetch returns unexpected data
        assert result.success is True
        # The file should still be in files_modified since it was processed
        assert len(result.files_modified) == 1

    @pytest.mark.asyncio
    async def test_comment_created_with_correct_format(
        self,
        pr_fixer: PRFileFixer,
        mock_client: Mock,
        pr_info: PRInfo,
        pr_data: dict[str, Any],
    ) -> None:
        """Test that PR comment is created with correct formatting."""
        # Setup
        mock_client.get_pr_files.return_value = [
            {"filename": "file1.yaml", "sha": "sha1", "status": "modified"},
            {"filename": "file2.yaml", "sha": "sha2", "status": "modified"},
        ]
        mock_client.get_file_content.return_value = "old_value: test\n"
        mock_client._request.return_value = {"sha": "sha"}
        mock_client.update_file.return_value = {"commit": {"sha": "new"}}
        mock_client.create_comment.return_value = {"id": 1}

        # Execute
        result = await pr_fixer._fix_pr_with_api(
            pr_info=pr_info,
            owner="owner",
            repo="repo",
            pr_data=pr_data,
            spec=FileFixSpec(
                file_pattern=r"\.yaml$",
                search_pattern=r"old_value",
                replacement="new_value",
                dry_run=False,
                pr_content_only=True,
            ),
        )

        # Verify
        assert result.success is True

        # Check comment content
        comment_call = mock_client.create_comment.call_args
        # create_comment is called with positional args: (owner, repo, pr_number, body)
        comment_body = comment_call[0][3]
        assert "🛠️ **Pull Request Fixer**" in comment_body
        assert "Fixed 2 file(s): file1.yaml, file2.yaml" in comment_body
        assert "Changes applied via GitHub API" in comment_body
        assert "pull-request-fixer" in comment_body

    @pytest.mark.asyncio
    async def test_comment_failure_suppressed(
        self,
        pr_fixer: PRFileFixer,
        mock_client: Mock,
        pr_info: PRInfo,
        pr_data: dict[str, Any],
    ) -> None:
        """Test that comment creation failures don't fail the entire operation."""
        # Setup
        mock_client.get_pr_files.return_value = [
            {"filename": "test.yaml", "sha": "sha1", "status": "modified"}
        ]
        mock_client.get_file_content.return_value = "old_value: test\n"
        mock_client._request.return_value = {"sha": "sha1"}
        mock_client.update_file.return_value = {"commit": {"sha": "new"}}
        # Comment creation fails
        mock_client.create_comment.side_effect = Exception("Comment failed")

        # Execute
        result = await pr_fixer._fix_pr_with_api(
            pr_info=pr_info,
            owner="owner",
            repo="repo",
            pr_data=pr_data,
            spec=FileFixSpec(
                file_pattern=r"\.yaml$",
                search_pattern=r"old_value",
                replacement="new_value",
                dry_run=False,
                pr_content_only=True,
            ),
        )

        # Verify - operation should still succeed
        assert result.success is True
        assert len(result.files_modified) == 1

    @pytest.mark.asyncio
    async def test_commit_message_format(
        self,
        pr_fixer: PRFileFixer,
        mock_client: Mock,
        pr_info: PRInfo,
        pr_data: dict[str, Any],
    ) -> None:
        """Test that commit messages are formatted correctly."""
        # Setup
        mock_client.get_pr_files.return_value = [
            {
                "filename": "config/settings.yaml",
                "sha": "sha1",
                "status": "modified",
            }
        ]
        mock_client.get_file_content.return_value = "old_value: test\n"
        mock_client.update_files_in_batch.return_value = None

        # Execute
        result = await pr_fixer._fix_pr_with_api(
            pr_info=pr_info,
            owner="owner",
            repo="repo",
            pr_data=pr_data,
            spec=FileFixSpec(
                file_pattern=r"\.yaml$",
                search_pattern=r"old_value",
                replacement="new_value",
                dry_run=False,
                pr_content_only=True,
            ),
        )

        # Verify
        assert result.success is True

        # Check commit message for batch update
        update_call = mock_client.update_files_in_batch.call_args
        # update_files_in_batch is called with positional args: (owner, repo, branch, files, message)
        commit_message = update_call[0][4]
        assert "Fix 1 file(s) in PR #123" in commit_message
        assert "config/settings.yaml" in commit_message
        assert "Automated by pull-request-fixer" in commit_message

    @pytest.mark.asyncio
    async def test_file_modifications_contain_correct_diff_info(
        self,
        pr_fixer: PRFileFixer,
        mock_client: Mock,
        pr_info: PRInfo,
        pr_data: dict[str, Any],
    ) -> None:
        """Test that FileModification objects contain correct original and modified content."""
        # Setup
        original_content = "line1: old_value\nline2: keep\nline3: old_value\n"
        expected_modified = "line1: new_value\nline2: keep\nline3: new_value\n"

        mock_client.get_pr_files.return_value = [
            {"filename": "test.yaml", "sha": "sha1", "status": "modified"}
        ]
        mock_client.get_file_content.return_value = original_content
        mock_client._request.return_value = {"sha": "sha1"}
        mock_client.update_file.return_value = {"commit": {"sha": "new"}}

        # Execute
        result = await pr_fixer._fix_pr_with_api(
            pr_info=pr_info,
            owner="owner",
            repo="repo",
            pr_data=pr_data,
            spec=FileFixSpec(
                file_pattern=r"\.yaml$",
                search_pattern=r"old_value",
                replacement="new_value",
                dry_run=False,
                pr_content_only=True,
            ),
        )

        # Verify
        assert result.success is True
        assert len(result.file_modifications) == 1

        mod = result.file_modifications[0]
        assert mod.file_path == Path("test.yaml")
        assert mod.original_content == original_content
        assert mod.modified_content == expected_modified
        assert "old_value" in mod.original_content
        assert "new_value" in mod.modified_content

    @pytest.mark.asyncio
    async def test_singular_plural_message_formatting(
        self,
        pr_fixer: PRFileFixer,
        mock_client: Mock,
        pr_info: PRInfo,
        pr_data: dict[str, Any],
    ) -> None:
        """Test that result messages correctly handle singular vs plural."""
        # Setup for single file
        mock_client.get_pr_files.return_value = [
            {"filename": "test.yaml", "sha": "sha1", "status": "modified"}
        ]
        mock_client.get_file_content.return_value = "old_value: test\n"
        mock_client._request.return_value = {"sha": "sha1"}
        mock_client.update_file.return_value = {"commit": {"sha": "new"}}

        # Execute
        result = await pr_fixer._fix_pr_with_api(
            pr_info=pr_info,
            owner="owner",
            repo="repo",
            pr_data=pr_data,
            spec=FileFixSpec(
                file_pattern=r"\.yaml$",
                search_pattern=r"old_value",
                replacement="new_value",
                dry_run=False,
                pr_content_only=True,
            ),
        )

        # Verify singular
        assert result.success is True
        assert result.message == "Updated 1 file"

        # Setup for multiple files
        mock_client.get_pr_files.return_value = [
            {"filename": "file1.yaml", "sha": "sha1", "status": "modified"},
            {"filename": "file2.yaml", "sha": "sha2", "status": "modified"},
        ]

        # Execute
        result = await pr_fixer._fix_pr_with_api(
            pr_info=pr_info,
            owner="owner",
            repo="repo",
            pr_data=pr_data,
            spec=FileFixSpec(
                file_pattern=r"\.yaml$",
                search_pattern=r"old_value",
                replacement="new_value",
                dry_run=False,
                pr_content_only=True,
            ),
        )

        # Verify plural
        assert result.success is True
        assert result.message == "Updated 2 files"
