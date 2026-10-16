"""Tests for the stable CodeScope pull-request comment publisher."""

from unittest.mock import MagicMock, patch

import pytest

from src.github_commenter import (
    COMMENT_MARKER,
    LEGACY_COMMENT_MARKER,
    CommentPostError,
    find_existing_comment,
    format_comment,
    post_comment,
    post_or_update_comment,
)


def _summary() -> dict:
    return {"total_files": 2, "total_additions": 30, "total_deletions": 5}


def _report() -> dict:
    return {
        "state": "Missing required evidence",
        "changed_production_files": ["src/core.py"],
        "impacts": [{
            "path": "src/service.py",
            "kind": "production",
            "dependency_path": ["src/service.py", "src/core.py"],
        }],
        "test_evidence": [{"target": "src/core.py", "status": "missing", "tests": []}],
        "missing_tests": [{"recommendation": "Add or map a test for `src/core.py`."}],
        "architecture_violations": [{
            "rule_id": "layers",
            "source": "src/ui.py",
            "target": "src/data.py",
            "evidence": "`src/ui.py` imports `src/data.py`",
            "reason": "UI must use the service layer.",
        }],
        "incomplete_reasons": [],
        "analysis": {
            "source_files_scanned": 6,
            "dependency_edges": 3,
            "max_depth": 2,
            "policy_source": "base",
        },
    }


def test_format_comment_is_scannable_and_evidence_backed():
    body = format_comment(_report(), _summary(), "flowchart LR\n  n0 --> n1")
    assert COMMENT_MARKER in body
    assert "Missing required evidence" in body
    assert "src/service.py" in body
    assert "src/core.py" in body
    assert "UI must use the service layer" in body
    assert "```mermaid" in body
    assert "does not execute pull-request code" in body


def test_format_comment_handles_no_findings_without_claiming_safety():
    report = _report()
    report.update({
        "state": "Ready for review",
        "impacts": [],
        "test_evidence": [],
        "missing_tests": [],
        "architecture_violations": [],
    })
    body = format_comment(report, _summary())
    assert "No high-confidence action was identified" in body
    assert "does not prove the change is safe" in body


@pytest.mark.parametrize("marker", [COMMENT_MARKER, LEGACY_COMMENT_MARKER])
@patch("src.github_commenter.requests.get")
def test_find_existing_comment_supports_current_and_legacy_markers(mock_get, marker):
    response = MagicMock(ok=True)
    response.json.return_value = [{"id": 200, "body": marker}]
    mock_get.return_value = response
    assert find_existing_comment("owner/repo", 42, "token") == 200


@patch("src.github_commenter.requests.get")
def test_find_existing_comment_raises_on_api_failure(mock_get):
    response = MagicMock(ok=False, status_code=403, text="Forbidden")
    response.json.return_value = {"message": "Forbidden"}
    mock_get.return_value = response
    with pytest.raises(CommentPostError, match="HTTP 403"):
        find_existing_comment("owner/repo", 42, "token")


@patch("src.github_commenter.requests.post")
def test_post_comment_returns_id(mock_post):
    response = MagicMock(ok=True)
    response.json.return_value = {"id": 555}
    mock_post.return_value = response
    assert post_comment("owner/repo", 42, "token", "body") == 555


@patch("src.github_commenter.post_comment", return_value=999)
@patch("src.github_commenter.find_existing_comment", return_value=None)
def test_post_or_update_creates_when_missing(mock_find, mock_post):
    assert post_or_update_comment("owner/repo", 42, "token", "body") == 999
    mock_find.assert_called_once()
    mock_post.assert_called_once()


@patch("src.github_commenter.update_comment")
@patch("src.github_commenter.find_existing_comment", return_value=200)
def test_post_or_update_updates_existing(mock_find, mock_update):
    assert post_or_update_comment("owner/repo", 42, "token", "body") == 200
    mock_update.assert_called_once_with("owner/repo", 200, "token", "body")
