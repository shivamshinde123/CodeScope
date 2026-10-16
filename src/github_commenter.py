"""Publish one stable, evidence-backed CodeScope pull-request comment."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import requests

GITHUB_API_BASE = "https://api.github.com"
COMMENT_MARKER = "<!-- codescope-merge-readiness -->"
LEGACY_COMMENT_MARKER = "<!-- codescope-diagram -->"
MAX_COMMENT_LENGTH = 65_536
_MAX_COMMENT_PAGES = 10


class CommentPostError(Exception):
    """Raised when creating or updating a PR comment fails."""


def _github_headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _raise_for_status(response: requests.Response, action: str) -> None:
    if response.ok:
        return
    try:
        detail = response.json().get("message", response.text)
    except (ValueError, KeyError):
        detail = response.text
    raise CommentPostError(f"Failed to {action} (HTTP {response.status_code}): {detail}")


def find_existing_comment(repo: str, pr_number: int, token: str) -> int | None:
    """Find the current or legacy CodeScope comment, raising on API failure."""
    url = f"{GITHUB_API_BASE}/repos/{repo}/issues/{pr_number}/comments"
    for page in range(1, _MAX_COMMENT_PAGES + 1):
        response = requests.get(
            url,
            headers=_github_headers(token),
            params={"per_page": 100, "page": page},
            timeout=30,
        )
        _raise_for_status(response, f"list comments on PR #{pr_number}")
        comments: list[dict[str, Any]] = response.json()
        for comment in comments:
            body = comment.get("body", "")
            if COMMENT_MARKER in body or LEGACY_COMMENT_MARKER in body:
                return int(comment["id"])
        if len(comments) < 100:
            break
    return None


def _escape_cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _file(path: str) -> str:
    return f"`{_escape_cell(path)}`"


def format_comment(
    report: dict[str, Any],
    change_summary: dict[str, Any],
    mermaid_code: str | None = None,
) -> str:
    """Format deterministic findings into a concise reviewer decision brief."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    state = report.get("state", "Analysis incomplete")
    parts = [COMMENT_MARKER, "", "## CodeScope merge readiness", "", f"### {state}", ""]
    parts.append(
        f"**{change_summary.get('total_files', 0)}** files changed · "
        f"**+{change_summary.get('total_additions', 0)}** / "
        f"**-{change_summary.get('total_deletions', 0)}** lines"
    )
    incomplete = report.get("incomplete_reasons", [])
    if incomplete:
        parts.extend(["", "> **Analysis limits:** " + " ".join(_escape_cell(item) for item in incomplete)])

    impacts = report.get("impacts", [])
    production_impacts = [item for item in impacts if item.get("kind") == "production"]
    parts.extend(["", "### Blast radius", ""])
    if production_impacts:
        parts.extend(["| Impacted component | Evidence path |", "|---|---|"])
        for item in production_impacts[:20]:
            path = " → ".join(_file(node) for node in item["dependency_path"])
            parts.append(f"| {_file(item['path'])} | {path} |")
    else:
        parts.append("No indirectly affected production component was found by supported import analysis.")

    parts.extend(["", "### Test evidence", "", "| Changed component | Status | Evidence |", "|---|---|---|"])
    evidence = report.get("test_evidence", [])
    if evidence:
        for item in evidence[:30]:
            tests = ", ".join(_file(path) for path in item["tests"]) or "No mapped test"
            parts.append(f"| {_file(item['target'])} | {item['status']} | {tests} |")
    else:
        parts.append("| — | not applicable | No supported production source file changed |")

    violations = report.get("architecture_violations", [])
    parts.extend(["", "### Architecture rules", ""])
    if violations:
        parts.extend(["| Rule | New violation | Why it matters |", "|---|---|---|"])
        for item in violations[:20]:
            parts.append(
                f"| `{_escape_cell(item['rule_id'])}` | {_escape_cell(item['evidence'])} "
                f"| {_escape_cell(item['reason'])} |"
            )
    else:
        parts.append("No new violation of a base-branch `.codescope.toml` rule was found.")

    actions: list[str] = []
    actions.extend(item["recommendation"] for item in report.get("missing_tests", []))
    actions.extend(
        f"Remove or approve an exception for `{item['source']}` → `{item['target']}` ({item['rule_id']})."
        for item in violations
    )
    if production_impacts:
        actions.append("Review the listed indirect dependents before approval.")
    parts.extend(["", "### Recommended actions", ""])
    if actions:
        parts.extend(f"- [ ] {action}" for action in actions[:25])
    else:
        parts.append("No high-confidence action was identified. This does not prove the change is safe.")

    if mermaid_code:
        parts.extend([
            "", "<details>", "<summary>Impact diagram</summary>", "", "```mermaid",
            mermaid_code, "```", "",
            "Blue nodes are directly changed; arrows show dependent-to-dependency evidence.",
            "</details>",
        ])

    meta = report.get("analysis", {})
    parts.extend([
        "", "<details>", "<summary>Analysis details</summary>", "",
        f"Scanned {meta.get('source_files_scanned', 0)} supported source files and "
        f"{meta.get('dependency_edges', 0)} dependency edges to depth {meta.get('max_depth', 2)}. "
        f"Architecture policy source: {meta.get('policy_source', 'none')}.",
        "",
        "CodeScope reads repository text and Git history; it does not execute pull-request code. "
        "Findings are advisory and evidence-backed.",
        "</details>", "", "---", f"*Updated by CodeScope at {timestamp}*",
    ])
    body = "\n".join(parts)
    if len(body) > MAX_COMMENT_LENGTH:
        notice = "\n\n---\n*Comment truncated at GitHub's size limit.*"
        body = body[: MAX_COMMENT_LENGTH - len(notice)] + notice
    return body


def post_comment(repo: str, pr_number: int, token: str, body: str) -> int:
    response = requests.post(
        f"{GITHUB_API_BASE}/repos/{repo}/issues/{pr_number}/comments",
        headers=_github_headers(token), json={"body": body}, timeout=30,
    )
    _raise_for_status(response, f"create comment on PR #{pr_number}")
    return int(response.json()["id"])


def update_comment(repo: str, comment_id: int, token: str, body: str) -> None:
    response = requests.patch(
        f"{GITHUB_API_BASE}/repos/{repo}/issues/comments/{comment_id}",
        headers=_github_headers(token), json={"body": body}, timeout=30,
    )
    _raise_for_status(response, f"update comment {comment_id}")


def post_or_update_comment(repo: str, pr_number: int, token: str, body: str) -> int:
    existing_id = find_existing_comment(repo, pr_number, token)
    if existing_id is not None:
        update_comment(repo, existing_id, token, body)
        return existing_id
    return post_comment(repo, pr_number, token, body)
