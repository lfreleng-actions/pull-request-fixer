# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""Custom exceptions for pull-request-fixer."""

from __future__ import annotations


class PullRequestFixerError(Exception):
    """Base exception for pull-request-fixer."""

    pass


# Former name, kept so existing imports and handlers keep working.
PRTitleFixerError = PullRequestFixerError


class FileAccessError(PullRequestFixerError):
    """Error accessing or reading a file."""

    pass


class ResourceNotFoundError(PullRequestFixerError):
    """Resource not found (404 error)."""

    pass


class GitHubAPIError(PullRequestFixerError):
    """Error communicating with GitHub API."""

    pass


class AuthenticationError(GitHubAPIError):
    """GitHub authentication failed."""

    pass


class RateLimitError(GitHubAPIError):
    """GitHub API rate limit exceeded."""

    def __init__(
        self,
        message: str = "GitHub API rate limit exceeded",
        reset_time: int | None = None,
    ):
        """Initialize rate limit error.

        Args:
            message: Error message
            reset_time: Unix timestamp when rate limit resets
        """
        super().__init__(message)
        self.reset_time = reset_time


class NetworkError(PullRequestFixerError):
    """Network communication error."""

    pass


class GitOperationError(PullRequestFixerError):
    """Error performing git operation."""

    pass


class ConfigurationError(PullRequestFixerError):
    """Configuration error."""

    pass
