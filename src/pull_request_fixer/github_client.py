# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2025 The Linux Foundation

"""GitHub API client for repository and PR operations."""

# aislop-ignore-file complexity/file-too-large -- cohesive GitHub API client

from __future__ import annotations

import base64
from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_not_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from .exceptions import FileAccessError, ResourceNotFoundError


class GitHubClient:
    """Client for GitHub API operations."""

    def __init__(self, token: str, base_url: str = "https://api.github.com"):
        """Initialize GitHub client.

        Args:
            token: GitHub personal access token
            base_url: GitHub API base URL
        """
        self.token = token
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    async def __aenter__(self) -> GitHubClient:
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:  # type: ignore[no-untyped-def]
        """Async context manager exit."""
        pass

    async def validate_token(self) -> tuple[bool, str, list[str]]:
        """Validate GitHub token and check permissions.

        Returns:
            Tuple of (is_valid, username, scopes)

        Raises:
            FileAccessError: If token validation fails
        """
        query = """
        query {
          viewer {
            login
          }
        }
        """

        try:
            result = await self._graphql_request(query)
            viewer = result.get("viewer", {})
            username = viewer.get("login", "")

            # Get token scopes from REST API
            # Note: GitHub Actions tokens may not have access to /user endpoint
            scopes: list[str] = []
            try:
                url = f"{self.base_url}/user"
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.get(url, headers=self.headers)
                    response.raise_for_status()

                    # Scopes are in the X-OAuth-Scopes header
                    scopes_header = response.headers.get("X-OAuth-Scopes", "")
                    scopes = [
                        s.strip() for s in scopes_header.split(",") if s.strip()
                    ]
            except httpx.HTTPStatusError as scope_error:
                # GitHub Actions tokens may not have user access (403)
                # This is expected and we can continue without scope info
                if scope_error.response.status_code != 403:
                    raise

            return True, username, scopes

        except Exception as e:
            msg = f"Token validation failed: {e}"
            raise FileAccessError(msg) from e

    @retry(  # type: ignore[untyped-decorator]
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_not_exception_type(ResourceNotFoundError),
    )
    async def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs: Any,
    ) -> dict[str, Any] | list[dict[str, Any]]:
        """Make an API request with retry logic.

        Args:
            method: HTTP method
            endpoint: API endpoint path
            **kwargs: Additional arguments for httpx request

        Returns:
            Response JSON data

        Raises:
            FileAccessError: If request fails
        """
        url = f"{self.base_url}{endpoint}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.request(
                    method,
                    url,
                    headers=self.headers,
                    **kwargs,
                )
                response.raise_for_status()
                result: dict[str, Any] | list[dict[str, Any]] = response.json()
                return result
            except httpx.HTTPStatusError as e:
                # Don't retry 404 errors - they won't succeed on retry
                if e.response.status_code == 404:
                    msg = f"Resource not found: {e.response.text}"
                    raise ResourceNotFoundError(msg) from e
                msg = f"GitHub API error: {e.response.status_code} - {e.response.text}"
                raise FileAccessError(msg) from e
            except httpx.RequestError as e:
                msg = f"Request failed: {e}"
                raise FileAccessError(msg) from e

    @retry(  # type: ignore[untyped-decorator]
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_not_exception_type(ResourceNotFoundError),
    )
    async def _graphql_request(
        self,
        query: str,
        variables: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make a GraphQL API request with retry logic.

        Args:
            query: GraphQL query string
            variables: Query variables

        Returns:
            Response data

        Raises:
            FileAccessError: If request fails
        """
        url = "https://api.github.com/graphql"
        payload: dict[str, Any] = {"query": query}
        if variables:
            payload["variables"] = variables

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.post(
                    url,
                    headers=self.headers,
                    json=payload,
                )
                response.raise_for_status()
                json_response: Any = response.json()
                result: dict[str, Any] = (
                    json_response if isinstance(json_response, dict) else {}
                )

                if "errors" in result:
                    errors = result["errors"]
                    msg = f"GraphQL errors: {errors}"
                    raise FileAccessError(msg)

                data: dict[str, Any] = result.get("data", {})
                return data
            except httpx.HTTPStatusError as e:
                msg = f"GitHub API error: {e.response.status_code} - {e.response.text}"
                raise FileAccessError(msg) from e
            except httpx.RequestError as e:
                msg = f"Request failed: {e}"
                raise FileAccessError(msg) from e

    async def graphql(
        self,
        query: str,
        variables: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute a GraphQL query.

        Args:
            query: GraphQL query string
            variables: Query variables

        Returns:
            Response data

        Raises:
            FileAccessError: If request fails
        """
        result: dict[str, Any] = await self._graphql_request(query, variables)
        return result

    async def get_pr_files(
        self, owner: str, repo: str, pr_number: int
    ) -> list[dict[str, Any]]:
        """Get files changed in a pull request.

        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: Pull request number

        Returns:
            List of changed files
        """
        files = await self._request(
            "GET",
            f"/repos/{owner}/{repo}/pulls/{pr_number}/files",
        )
        return files if isinstance(files, list) else []

    async def get_file_content(
        self, owner: str, repo: str, path: str, ref: str
    ) -> str:
        """Get file content from a repository.

        Args:
            owner: Repository owner
            repo: Repository name
            path: File path
            ref: Git ref (branch/commit SHA)

        Returns:
            Decoded file content

        Raises:
            FileAccessError: If file cannot be retrieved
        """
        result = await self._request(
            "GET",
            f"/repos/{owner}/{repo}/contents/{path}",
            params={"ref": ref},
        )

        if not isinstance(result, dict):
            msg = f"Unexpected response type for file content: {type(result)}"
            raise FileAccessError(msg)

        content_b64 = result.get("content", "")
        if not content_b64:
            return ""

        try:
            return base64.b64decode(content_b64).decode("utf-8")
        except (ValueError, UnicodeDecodeError) as e:
            msg = f"Failed to decode file content: {e}"
            raise FileAccessError(msg) from e

    async def create_blob(
        self,
        owner: str,
        repo: str,
        content: str,
    ) -> str:
        """Create a blob object in the repository.

        Args:
            owner: Repository owner
            repo: Repository name
            content: File content

        Returns:
            SHA of created blob

        Raises:
            FileAccessError: If blob creation fails
        """
        content_b64 = base64.b64encode(content.encode("utf-8")).decode("utf-8")

        result = await self._request(
            "POST",
            f"/repos/{owner}/{repo}/git/blobs",
            json={
                "content": content_b64,
                "encoding": "base64",
            },
        )

        if not isinstance(result, dict):
            msg = f"Unexpected response type for blob creation: {type(result)}"
            raise FileAccessError(msg)

        sha = result.get("sha", "")
        if not sha:
            msg = "No SHA returned from blob creation"
            raise FileAccessError(msg)

        return str(sha)

    async def get_reference(
        self,
        owner: str,
        repo: str,
        ref: str,
    ) -> dict[str, Any]:
        """Get a Git reference.

        Args:
            owner: Repository owner
            repo: Repository name
            ref: Reference name (e.g., 'heads/main')

        Returns:
            Reference data including commit SHA

        Raises:
            FileAccessError: If reference cannot be retrieved
        """
        result = await self._request(
            "GET",
            f"/repos/{owner}/{repo}/git/ref/{ref}",
        )

        if not isinstance(result, dict):
            msg = f"Unexpected response type for reference: {type(result)}"
            raise FileAccessError(msg)

        return result

    async def create_tree(
        self,
        owner: str,
        repo: str,
        base_tree: str,
        tree_items: list[dict[str, Any]],
    ) -> str:
        """Create a tree object in the repository.

        Args:
            owner: Repository owner
            repo: Repository name
            base_tree: SHA of base tree
            tree_items: List of tree items with path, mode, type, and sha

        Returns:
            SHA of created tree

        Raises:
            FileAccessError: If tree creation fails
        """
        result = await self._request(
            "POST",
            f"/repos/{owner}/{repo}/git/trees",
            json={
                "base_tree": base_tree,
                "tree": tree_items,
            },
        )

        if not isinstance(result, dict):
            msg = f"Unexpected response type for tree creation: {type(result)}"
            raise FileAccessError(msg)

        sha = result.get("sha", "")
        if not sha:
            msg = "No SHA returned from tree creation"
            raise FileAccessError(msg)

        return str(sha)

    async def create_commit(
        self,
        owner: str,
        repo: str,
        message: str,
        tree: str,
        parents: list[str],
    ) -> str:
        """Create a commit object in the repository.

        Args:
            owner: Repository owner
            repo: Repository name
            message: Commit message
            tree: SHA of tree
            parents: List of parent commit SHAs

        Returns:
            SHA of created commit

        Raises:
            FileAccessError: If commit creation fails
        """
        result = await self._request(
            "POST",
            f"/repos/{owner}/{repo}/git/commits",
            json={
                "message": message,
                "tree": tree,
                "parents": parents,
            },
        )

        if not isinstance(result, dict):
            msg = (
                f"Unexpected response type for commit creation: {type(result)}"
            )
            raise FileAccessError(msg)

        sha = result.get("sha", "")
        if not sha:
            msg = "No SHA returned from commit creation"
            raise FileAccessError(msg)

        return str(sha)

    async def update_reference(
        self,
        owner: str,
        repo: str,
        ref: str,
        sha: str,
        force: bool = False,
    ) -> dict[str, Any]:
        """Update a Git reference to point to a new commit.

        Args:
            owner: Repository owner
            repo: Repository name
            ref: Reference name (e.g., 'heads/main')
            sha: New commit SHA
            force: Whether to force the update

        Returns:
            Updated reference data

        Raises:
            FileAccessError: If reference update fails
        """
        result = await self._request(
            "PATCH",
            f"/repos/{owner}/{repo}/git/refs/{ref}",
            json={
                "sha": sha,
                "force": force,
            },
        )

        if not isinstance(result, dict):
            msg = (
                f"Unexpected response type for reference update: {type(result)}"
            )
            raise FileAccessError(msg)

        return result

    async def update_files_in_batch(
        self,
        owner: str,
        repo: str,
        branch: str,
        files: list[dict[str, str]],
        commit_message: str,
    ) -> str:
        """Update multiple files in a single commit using Git Data API.

        This is more efficient than updating files one by one, as it:
        1. Creates all blobs in parallel
        2. Creates a single tree with all changes
        3. Creates a single commit
        4. Updates the branch reference once

        Args:
            owner: Repository owner
            repo: Repository name
            branch: Branch name (without 'refs/heads/' prefix)
            files: List of dicts with 'path' and 'content' keys
            commit_message: Commit message for the batch update

        Returns:
            SHA of created commit

        Raises:
            FileAccessError: If batch update fails
        """
        ref_data = await self.get_reference(owner, repo, f"heads/{branch}")
        current_commit_sha = ref_data["object"]["sha"]

        commit_data = await self._request(
            "GET",
            f"/repos/{owner}/{repo}/git/commits/{current_commit_sha}",
        )
        if not isinstance(commit_data, dict):
            msg = "Failed to get commit data"
            raise FileAccessError(msg)

        base_tree_sha = commit_data["tree"]["sha"]

        # Create blobs for all files in parallel for better performance
        import asyncio

        async def create_blob_for_file(
            file_info: dict[str, str],
        ) -> dict[str, Any]:
            """Create blob and return tree item."""
            blob_sha = await self.create_blob(owner, repo, file_info["content"])
            return {
                "path": file_info["path"],
                "mode": "100644",  # Regular file
                "type": "blob",
                "sha": blob_sha,
            }

        tree_items = await asyncio.gather(
            *[create_blob_for_file(file_info) for file_info in files]
        )

        tree_sha = await self.create_tree(
            owner, repo, base_tree_sha, tree_items
        )

        commit_sha = await self.create_commit(
            owner, repo, commit_message, tree_sha, [current_commit_sha]
        )

        await self.update_reference(owner, repo, f"heads/{branch}", commit_sha)

        return commit_sha

    # aislop-ignore-next-line complexity/too-many-params -- GitHub contents API shape
    async def update_file(
        self,
        owner: str,
        repo: str,
        path: str,
        content: str,
        message: str,
        branch: str,
        sha: str,
    ) -> dict[str, Any]:
        """Update a file in a repository.

        Args:
            owner: Repository owner
            repo: Repository name
            path: File path
            content: New file content
            message: Commit message
            branch: Branch name
            sha: Current file SHA (for conflict detection)

        Returns:
            Commit data
        """
        content_b64 = base64.b64encode(content.encode("utf-8")).decode("utf-8")

        result = await self._request(
            "PUT",
            f"/repos/{owner}/{repo}/contents/{path}",
            json={
                "message": message,
                "content": content_b64,
                "branch": branch,
                "sha": sha,
            },
        )
        return result if isinstance(result, dict) else {}

    async def get_rate_limit(self) -> dict[str, Any]:
        """Get current API rate limit status.

        Returns:
            Rate limit information
        """
        result = await self._request("GET", "/rate_limit")
        return result if isinstance(result, dict) else {}

    async def create_comment(
        self, owner: str, repo: str, pr_number: int, body: str
    ) -> dict[str, Any]:
        """Create a comment on a pull request.

        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: Pull request number
            body: Comment body

        Returns:
            Comment data
        """
        result = await self._request(
            "POST",
            f"/repos/{owner}/{repo}/issues/{pr_number}/comments",
            json={"body": body},
        )
        return result if isinstance(result, dict) else {}
