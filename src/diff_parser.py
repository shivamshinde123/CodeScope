"""
diff_parser.py - PR diff fetching and parsing for the CodeScope GitHub Action.

This module provides functions to:
  1. Fetch raw PR diffs and changed-file lists from the GitHub API.
  2. Parse unified diffs into structured per-file change records.
  3. Aggregate those records into a high-level change summary.

Typical usage:

    raw   = fetch_pr_diff("owner/repo", 42, token)
    files = parse_diff(raw)
    summary = build_change_summary(files)
"""

from __future__ import annotations

import logging
import os
from collections import defaultdict
from typing import Any

import requests
import unidiff
import unidiff.errors

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

GITHUB_API_BASE: str = "https://api.github.com"

# Safety limits -- PRs beyond these thresholds are considered truncated.
MAX_FILES: int = 500
MAX_LINE_CHANGES: int = 10_000

# GitHub's maximum supported value for the per_page query parameter.
_GITHUB_MAX_PER_PAGE: int = 100

# ---------------------------------------------------------------------------
# Logger
# ---------------------------------------------------------------------------

logger = logging.getLogger("codescope.diff_parser")

# ---------------------------------------------------------------------------
# Custom exception
# ---------------------------------------------------------------------------


class DiffParseError(Exception):
    """Raised when diff fetching or parsing fails in an unrecoverable way."""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _github_headers(token: str, accept: str) -> dict[str, str]:
    """Build a standard set of headers for GitHub API requests.

    Args:
        token: GitHub personal-access or installation token.
        accept: Value for the ``Accept`` header (controls response format).

    Returns:
        A dict suitable for passing as ``headers`` to :func:`requests.get`.
    """
    return {
        "Authorization": f"token {token}",
        "Accept": accept,
    }


def _raise_for_github_status(response: requests.Response) -> None:
    """Inspect a GitHub API response and raise a clear error on failure.

    Common status codes are translated into human-readable messages so that
    callers do not need to inspect raw HTTP codes themselves.

    Args:
        response: The :class:`requests.Response` returned by a GitHub API call.

    Raises:
        DiffParseError: If the response status code indicates an error.
    """
    if response.ok:
        return

    status = response.status_code
    # Map well-known codes to user-friendly messages.
    messages = {
        401: "Authentication failed. Check that the GitHub token is valid.",
        403: "Access denied. The token may lack the required scopes, or a rate limit was hit.",
        404: "Resource not found. Verify the repository name and PR number.",
        422: "Unprocessable entity. The request was well-formed but the server could not process it.",
    }
    detail = messages.get(status, f"GitHub API returned HTTP {status}.")

    # Append the body (often contains a machine-readable "message" field).
    try:
        body = response.json()
        server_msg = body.get("message", "")
        if server_msg:
            detail = f"{detail} Server message: {server_msg}"
    except (ValueError, KeyError):
        pass

    logger.error("GitHub API error (HTTP %d): %s", status, detail)
    raise DiffParseError(detail)


# ---------------------------------------------------------------------------
# Public API -- fetching
# ---------------------------------------------------------------------------


def fetch_pr_diff(repo: str, pr_number: int, token: str) -> str:
    """Fetch the raw unified diff for a pull request.

    Args:
        repo: Repository in ``owner/name`` format (e.g. ``"octocat/Hello-World"``).
        pr_number: The pull-request number.
        token: GitHub authentication token.

    Returns:
        The full unified-diff text as a string.

    Raises:
        DiffParseError: On any HTTP error returned by the GitHub API.
        requests.RequestException: On network-level failures (DNS, timeout, etc.).
    """
    url = f"{GITHUB_API_BASE}/repos/{repo}/pulls/{pr_number}"
    headers = _github_headers(token, accept="application/vnd.github.v3.diff")

    logger.info("Fetching PR diff: %s #%d", repo, pr_number)
    response = requests.get(url, headers=headers, timeout=30)
    _raise_for_github_status(response)

    logger.debug("Received diff (%d bytes)", len(response.text))
    return response.text


def fetch_changed_files(repo: str, pr_number: int, token: str) -> list[dict[str, Any]]:
    """Fetch the list of files changed in a pull request.

    Handles GitHub pagination automatically: pages are fetched using
    ``per_page=100`` until the API returns an empty page.

    Args:
        repo: Repository in ``owner/name`` format.
        pr_number: The pull-request number.
        token: GitHub authentication token.

    Returns:
        A list of dicts, each containing at minimum the keys ``filename``,
        ``status``, ``additions``, ``deletions``, ``changes``, and
        optionally ``patch``.

    Raises:
        DiffParseError: On any HTTP error returned by the GitHub API.
        requests.RequestException: On network-level failures.
    """
    url = f"{GITHUB_API_BASE}/repos/{repo}/pulls/{pr_number}/files"
    headers = _github_headers(token, accept="application/vnd.github.v3+json")

    all_files: list[dict[str, Any]] = []
    page = 1

    logger.info("Fetching changed files: %s #%d", repo, pr_number)

    while True:
        params = {"per_page": _GITHUB_MAX_PER_PAGE, "page": page}
        response = requests.get(url, headers=headers, params=params, timeout=30)
        _raise_for_github_status(response)

        page_files: list[dict[str, Any]] = response.json()

        # An empty page means we have retrieved everything.
        if not page_files:
            break

        # Keep only the fields we care about to minimise memory usage.
        for f in page_files:
            all_files.append({
                "filename": f.get("filename", ""),
                "status": f.get("status", "unknown"),
                "additions": f.get("additions", 0),
                "deletions": f.get("deletions", 0),
                "changes": f.get("changes", 0),
                "patch": f.get("patch"),  # may be None for binary files
            })

        # If fewer results than requested, there are no more pages.
        if len(page_files) < _GITHUB_MAX_PER_PAGE:
            break

        page += 1

    logger.info("Fetched %d changed file(s) across %d page(s)", len(all_files), page)
    return all_files


# ---------------------------------------------------------------------------
# Public API -- parsing
# ---------------------------------------------------------------------------


def parse_diff(raw_diff: str) -> list[dict[str, Any]]:
    """Parse a raw unified diff string into structured per-file records.

    Each record captures the file path, its components, the type of
    modification, and line-change counts.

    Args:
        raw_diff: A unified-diff string (as returned by :func:`fetch_pr_diff`).

    Returns:
        A list of dicts with the following keys:

        - ``path`` (str): Full file path.
        - ``directory`` (str): Parent directory of the file.
        - ``filename`` (str): Base name of the file.
        - ``extension`` (str): File extension including the dot (e.g. ``".py"``).
        - ``modification_type`` (str): One of ``"added"``, ``"modified"``,
          ``"deleted"``, ``"renamed"``.
        - ``additions`` (int): Number of added lines.
        - ``deletions`` (int): Number of removed lines.

        Returns an empty list if the diff is empty or cannot be parsed.
    """
    if not raw_diff or not raw_diff.strip():
        logger.debug("Empty diff received; returning empty list")
        return []

    try:
        patch_set = unidiff.PatchSet.from_string(raw_diff)
    except unidiff.errors.UnidiffParseError as exc:
        logger.warning("Failed to parse diff: %s", exc)
        return []

    parsed_files: list[dict[str, Any]] = []

    for patched_file in patch_set:
        file_path: str = patched_file.path

        # Determine the modification type by inspecting boolean flags on
        # the patched-file object.  Order matters: ``is_rename`` should be
        # checked before the generic "modified" fallback because a rename
        # can also look like an add+delete pair.
        if patched_file.is_added_file:
            mod_type = "added"
        elif patched_file.is_removed_file:
            mod_type = "deleted"
        elif patched_file.is_rename:
            mod_type = "renamed"
        else:
            mod_type = "modified"

        # os.path.splitext returns ("name", ".ext"); for dotfiles with no
        # extension (e.g. ".gitignore") it returns (".gitignore", "").
        _, extension = os.path.splitext(file_path)

        parsed_files.append({
            "path": file_path,
            "directory": os.path.dirname(file_path),
            "filename": os.path.basename(file_path),
            "extension": extension,
            "modification_type": mod_type,
            "additions": patched_file.added,
            "deletions": patched_file.removed,
        })

    logger.info("Parsed %d file(s) from diff", len(parsed_files))
    return parsed_files


# ---------------------------------------------------------------------------
# Public API -- summarisation
# ---------------------------------------------------------------------------


def build_change_summary(parsed_files: list[dict[str, Any]]) -> dict[str, Any]:
    """Build an aggregate summary from a list of parsed file records.

    The summary groups files by directory, modification type, and extension,
    and flags very large PRs as *truncated* so that downstream consumers can
    handle them appropriately.

    Args:
        parsed_files: The list returned by :func:`parse_diff`.

    Returns:
        A dict with the following keys:

        - ``total_files`` (int): Number of files in the PR.
        - ``total_additions`` (int): Sum of added lines across all files.
        - ``total_deletions`` (int): Sum of removed lines across all files.
        - ``files`` (list[dict]): The (possibly truncated) list of file records.
        - ``by_directory`` (dict[str, list[dict]]): Files grouped by directory.
        - ``by_modification_type`` (dict[str, list[dict]]): Files grouped by
          modification type.
        - ``by_extension`` (dict[str, list[dict]]): Files grouped by extension.
        - ``is_truncated`` (bool): ``True`` when the PR exceeds safety limits.
        - ``truncation_note`` (str | None): Human-readable note when truncated,
          otherwise ``None``.
    """
    total_additions = sum(f.get("additions", 0) for f in parsed_files)
    total_deletions = sum(f.get("deletions", 0) for f in parsed_files)
    total_line_changes = total_additions + total_deletions

    # Determine whether the diff is too large to process fully.
    is_truncated = len(parsed_files) > MAX_FILES or total_line_changes > MAX_LINE_CHANGES

    truncation_note: str | None = None
    if is_truncated:
        truncation_note = (
            f"This PR is very large ({len(parsed_files)} files, "
            f"{total_line_changes} line changes). "
            f"Only the first {MAX_FILES} files are included in the summary."
        )
        logger.warning("PR exceeds safety limits: %s", truncation_note)
        # Keep only the first MAX_FILES entries to bound memory and processing.
        parsed_files = parsed_files[:MAX_FILES]

    # Group files into lookup dicts for convenient downstream access.
    by_directory: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_modification_type: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_extension: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for f in parsed_files:
        by_directory[f["directory"]].append(f)
        by_modification_type[f["modification_type"]].append(f)
        by_extension[f["extension"]].append(f)

    return {
        "total_files": len(parsed_files),
        "total_additions": total_additions,
        "total_deletions": total_deletions,
        "files": parsed_files,
        "by_directory": dict(by_directory),
        "by_modification_type": dict(by_modification_type),
        "by_extension": dict(by_extension),
        "is_truncated": is_truncated,
        "truncation_note": truncation_note,
    }
