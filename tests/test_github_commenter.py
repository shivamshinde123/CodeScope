"""Tests for src.github_commenter module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.github_commenter import (
    COMMENT_MARKER,
    MAX_COMMENT_LENGTH,
    CommentPostError,
    find_existing_comment,
    format_comment,
    post_comment,
    post_or_update_comment,
    update_comment,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_change_summary(**overrides) -> dict:
    """Build a minimal change summary dict for formatting tests."""
    summary = {
        "total_files": 2,
        "total_additions": 30,
        "total_deletions": 5,
        "is_truncated": False,
        "truncation_note": None,
        "files": [
            {
                "path": "src/app.py",
                "directory": "src",
                "filename": "app.py",
                "extension": ".py",
                "modification_type": "modified",
                "additions": 20,
                "deletions": 3,
            },
            {
                "path": "src/utils.py",
                "directory": "src",
                "filename": "utils.py",
                "extension": ".py",
                "modification_type": "added",
                "additions": 10,
                "deletions": 2,
            },
        ],
    }
    summary.update(overrides)
    return summary


# ===================================================================
# format_comment tests
# ===================================================================


class TestFormatComment:
    """Tests for the format_comment function."""

    def test_format_comment_with_mermaid(self):
        """Output should contain the marker, a mermaid code fence, and stats."""
        mermaid = "flowchart TD\n  A[app.py] --> B[utils.py]"
        summary = _make_change_summary()

        body = format_comment(mermaid, summary)

        assert COMMENT_MARKER in body
        assert "```mermaid" in body
        assert mermaid in body
        # Stats
        assert "2" in body  # total_files
        assert "+30" in body  # total_additions
        assert "-5" in body  # total_deletions

    def test_format_comment_fallback(self):
        """When mermaid_code is None, a text table fallback is produced."""
        summary = _make_change_summary()

        body = format_comment(None, summary)

        assert COMMENT_MARKER in body
        # Should NOT contain a mermaid fence
        assert "```mermaid" not in body
        # Should contain fallback table
        assert "Changed Files" in body
        assert "src/app.py" in body
        assert "Mermaid diagram generation was unavailable" in body

    def test_format_comment_truncation(self):
        """Very long mermaid code (>65536 chars) gets truncated."""
        # Create mermaid content exceeding the limit
        long_mermaid = "flowchart TD\n" + "  A[Node] --> B[Node]\n" * 5000
        summary = _make_change_summary()

        body = format_comment(long_mermaid, summary)

        assert len(body) <= MAX_COMMENT_LENGTH
        assert "truncated" in body.lower()


# ===================================================================
# find_existing_comment tests
# ===================================================================


class TestFindExistingComment:
    """Tests for the find_existing_comment function."""

    @patch("src.github_commenter.requests.get")
    def test_find_existing_comment_found(self, mock_get):
        """When one comment contains the marker, return its ID."""
        comments = [
            {"id": 100, "body": "Some other comment"},
            {"id": 200, "body": f"Update\n{COMMENT_MARKER}\nDiagram here"},
            {"id": 300, "body": "Another comment"},
        ]

        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = comments
        mock_get.return_value = mock_response

        result = find_existing_comment("owner/repo", 42, "fake-token")

        assert result == 200

    @patch("src.github_commenter.requests.get")
    def test_find_existing_comment_not_found(self, mock_get):
        """When no comment contains the marker, return None."""
        comments = [
            {"id": 100, "body": "Some other comment"},
            {"id": 300, "body": "Another comment"},
        ]

        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.json.return_value = comments
        mock_get.return_value = mock_response

        result = find_existing_comment("owner/repo", 42, "fake-token")

        assert result is None


# ===================================================================
# post_comment tests
# ===================================================================


class TestPostComment:
    """Tests for the post_comment function."""

    @patch("src.github_commenter.requests.post")
    def test_post_comment_success(self, mock_post):
        """Mock requests.post returning 201 with an id."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.status_code = 201
        mock_response.json.return_value = {"id": 555}
        mock_post.return_value = mock_response

        result = post_comment("owner/repo", 42, "fake-token", "Hello!")

        assert result == 555
        mock_post.assert_called_once()

    @patch("src.github_commenter.requests.post")
    def test_post_comment_failure(self, mock_post):
        """Mock requests.post returning 403. Should raise CommentPostError."""
        mock_response = MagicMock()
        mock_response.ok = False
        mock_response.status_code = 403
        mock_response.json.return_value = {"message": "Forbidden"}
        mock_response.text = "Forbidden"
        mock_post.return_value = mock_response

        with pytest.raises(CommentPostError):
            post_comment("owner/repo", 42, "fake-token", "Hello!")


# ===================================================================
# post_or_update_comment tests
# ===================================================================


class TestPostOrUpdateComment:
    """Tests for the post_or_update_comment function."""

    @patch("src.github_commenter.post_comment")
    @patch("src.github_commenter.find_existing_comment", return_value=None)
    def test_post_or_update_creates_new(self, mock_find, mock_post):
        """When no existing comment is found, post_comment is called."""
        mock_post.return_value = 999

        result = post_or_update_comment("owner/repo", 42, "fake-token", "body")

        assert result == 999
        mock_find.assert_called_once_with("owner/repo", 42, "fake-token")
        mock_post.assert_called_once_with("owner/repo", 42, "fake-token", "body")

    @patch("src.github_commenter.update_comment")
    @patch("src.github_commenter.find_existing_comment", return_value=200)
    def test_post_or_update_updates_existing(self, mock_find, mock_update):
        """When an existing comment is found, update_comment is called."""
        result = post_or_update_comment("owner/repo", 42, "fake-token", "body")

        assert result == 200
        mock_find.assert_called_once_with("owner/repo", 42, "fake-token")
        mock_update.assert_called_once_with("owner/repo", 200, "fake-token", "body")
