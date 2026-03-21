"""
CodeScope — GitHub Commenter module.

Posts or updates a Mermaid diagram comment on a pull request.  Uses a hidden
HTML marker (``<!-- codescope-diagram -->``) to identify its own comments so
that re-runs update the existing comment instead of creating duplicates.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import requests

logger = logging.getLogger("codescope.github_commenter")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
GITHUB_API_BASE: str = "https://api.github.com"

# Hidden marker embedded in every CodeScope comment.  Used to locate an
# existing comment on subsequent runs.
COMMENT_MARKER: str = "<!-- codescope-diagram -->"

# GitHub enforces a hard limit on comment body size (bytes).
MAX_COMMENT_LENGTH: int = 65_536

# Maximum number of comment pages to fetch when searching for an existing one.
_MAX_COMMENT_PAGES: int = 10


# ---------------------------------------------------------------------------
# Custom exception
# ---------------------------------------------------------------------------
class CommentPostError(Exception):
    """Raised when creating or updating a PR comment fails."""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _github_headers(token: str) -> dict[str, str]:
    """Build standard headers for GitHub API requests.

    Args:
        token: GitHub authentication token.

    Returns:
        Headers dict with Authorization and Accept fields.
    """
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }


def _raise_for_status(response: requests.Response, action: str) -> None:
    """Inspect a GitHub API response and raise on failure.

    Args:
        response: The HTTP response object.
        action: Human-readable description of the operation (for error messages).

    Raises:
        CommentPostError: On any non-2xx response.
    """
    if response.ok:
        return

    status = response.status_code
    try:
        detail = response.json().get("message", response.text)
    except (ValueError, KeyError):
        detail = response.text

    msg = f"Failed to {action} (HTTP {status}): {detail}"
    logger.error(msg)
    raise CommentPostError(msg)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def find_existing_comment(
    repo: str,
    pr_number: int,
    token: str,
) -> int | None:
    """Search PR comments for an existing CodeScope comment.

    Iterates through comment pages looking for a comment that contains the
    ``COMMENT_MARKER``.  Returns as soon as the first match is found.

    Args:
        repo: Repository in ``owner/name`` format.
        pr_number: The pull-request number.
        token: GitHub authentication token.

    Returns:
        The comment ID if found, otherwise ``None``.
    """
    url = f"{GITHUB_API_BASE}/repos/{repo}/issues/{pr_number}/comments"
    headers = _github_headers(token)

    logger.info("Searching for existing CodeScope comment on PR #%d", pr_number)

    for page in range(1, _MAX_COMMENT_PAGES + 1):
        params = {"per_page": 100, "page": page}
        response = requests.get(url, headers=headers, params=params, timeout=30)

        if not response.ok:
            logger.warning(
                "Could not fetch comments page %d (HTTP %d) — stopping search",
                page,
                response.status_code,
            )
            break

        comments: list[dict[str, Any]] = response.json()
        if not comments:
            break

        for comment in comments:
            body: str = comment.get("body", "")
            if COMMENT_MARKER in body:
                comment_id: int = comment["id"]
                logger.info("Found existing CodeScope comment (id=%d)", comment_id)
                return comment_id

        # Fewer results than requested means we're on the last page.
        if len(comments) < 100:
            break

    logger.info("No existing CodeScope comment found")
    return None


def format_comment(
    mermaid_code: str | None,
    change_summary: dict[str, Any],
) -> str:
    """Format the PR comment body with stats and the Mermaid diagram.

    If *mermaid_code* is ``None`` (e.g. Claude analysis failed), a text-only
    fallback summary is generated instead.

    Args:
        mermaid_code: The Mermaid diagram source, or ``None`` for fallback.
        change_summary: Structured summary from ``diff_parser.build_change_summary``.

    Returns:
        The full comment body string, ready to post.
    """
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    # Start with the hidden marker so we can find this comment later.
    parts: list[str] = [COMMENT_MARKER, ""]

    # Header
    parts.append("## CodeScope: PR Change Visualization")
    parts.append("")

    # Stats summary
    total_files = change_summary.get("total_files", 0)
    total_additions = change_summary.get("total_additions", 0)
    total_deletions = change_summary.get("total_deletions", 0)
    is_truncated = change_summary.get("is_truncated", False)

    parts.append(
        f"**{total_files}** file(s) changed | "
        f"**+{total_additions}** additions | "
        f"**-{total_deletions}** deletions"
    )
    parts.append("")

    if is_truncated:
        truncation_note = change_summary.get(
            "truncation_note",
            "Some files were omitted due to the large size of this PR.",
        )
        parts.append(f"> **Note:** {truncation_note}")
        parts.append("")

    # Diagram or fallback
    if mermaid_code:
        parts.append("```mermaid")
        parts.append(mermaid_code)
        parts.append("```")
    else:
        # Text-only fallback when diagram generation fails.
        parts.append("### Changed Files")
        parts.append("")
        parts.append("| File | Type | +/- |")
        parts.append("|------|------|-----|")
        for f in change_summary.get("files", []):
            parts.append(
                f"| `{f['path']}` | {f['modification_type']} "
                f"| +{f['additions']}/-{f['deletions']} |"
            )
        parts.append("")
        parts.append(
            "*Mermaid diagram generation was unavailable. "
            "Showing a text summary instead.*"
        )

    parts.append("")

    # Footer
    parts.append("---")
    parts.append(f"*Generated by **CodeScope** at {timestamp}*")

    body = "\n".join(parts)

    # Guard against GitHub's comment size limit.
    if len(body) > MAX_COMMENT_LENGTH:
        logger.warning(
            "Comment body exceeds %d chars (%d). Truncating.",
            MAX_COMMENT_LENGTH,
            len(body),
        )
        # Trim the body and append a truncation notice.
        truncated_notice = (
            "\n\n---\n*Comment truncated due to GitHub's size limit.*"
        )
        body = body[: MAX_COMMENT_LENGTH - len(truncated_notice)] + truncated_notice

    return body


def post_comment(
    repo: str,
    pr_number: int,
    token: str,
    body: str,
) -> int:
    """Create a new comment on a pull request.

    Args:
        repo: Repository in ``owner/name`` format.
        pr_number: The pull-request number.
        token: GitHub authentication token.
        body: The comment body (Markdown).

    Returns:
        The ID of the newly created comment.

    Raises:
        CommentPostError: If the GitHub API returns an error.
    """
    url = f"{GITHUB_API_BASE}/repos/{repo}/issues/{pr_number}/comments"
    headers = _github_headers(token)

    logger.info("Creating new comment on PR #%d", pr_number)
    response = requests.post(
        url, headers=headers, json={"body": body}, timeout=30,
    )
    _raise_for_status(response, f"create comment on PR #{pr_number}")

    comment_id: int = response.json()["id"]
    logger.info("Comment created (id=%d)", comment_id)
    return comment_id


def update_comment(
    repo: str,
    comment_id: int,
    token: str,
    body: str,
) -> None:
    """Update an existing PR comment.

    Args:
        repo: Repository in ``owner/name`` format.
        comment_id: The ID of the comment to update.
        token: GitHub authentication token.
        body: The new comment body (Markdown).

    Raises:
        CommentPostError: If the GitHub API returns an error.
    """
    url = f"{GITHUB_API_BASE}/repos/{repo}/issues/comments/{comment_id}"
    headers = _github_headers(token)

    logger.info("Updating existing comment (id=%d)", comment_id)
    response = requests.patch(
        url, headers=headers, json={"body": body}, timeout=30,
    )
    _raise_for_status(response, f"update comment {comment_id}")

    logger.info("Comment updated successfully (id=%d)", comment_id)


def post_or_update_comment(
    repo: str,
    pr_number: int,
    token: str,
    body: str,
) -> int:
    """Post a new comment or update the existing CodeScope comment.

    Checks for an existing comment with the CodeScope marker.  If one is
    found, it is updated in place; otherwise a new comment is created.

    Args:
        repo: Repository in ``owner/name`` format.
        pr_number: The pull-request number.
        token: GitHub authentication token.
        body: The comment body (Markdown).

    Returns:
        The comment ID (existing or newly created).

    Raises:
        CommentPostError: If creating or updating the comment fails.
    """
    existing_id = find_existing_comment(repo, pr_number, token)

    if existing_id is not None:
        update_comment(repo, existing_id, token, body)
        return existing_id

    return post_comment(repo, pr_number, token, body)
