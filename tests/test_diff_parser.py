"""Tests for src.diff_parser module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from src.diff_parser import (
    DiffParseError,
    MAX_FILES,
    build_change_summary,
    fetch_changed_files,
    fetch_pr_diff,
    parse_diff,
)

# ---------------------------------------------------------------------------
# Sample unified diff used across several tests
# ---------------------------------------------------------------------------

SAMPLE_DIFF = (
    "diff --git a/src/app.py b/src/app.py\n"
    "index 1234567..abcdefg 100644\n"
    "--- a/src/app.py\n"
    "+++ b/src/app.py\n"
    "@@ -1,4 +1,6 @@\n"
    " import os\n"
    "+import sys\n"
    " \n"
    " def main():\n"
    "-    print(\"hello\")\n"
    "+    print(\"hello world\")\n"
    "+    return 0\n"
)


# ===================================================================
# parse_diff tests
# ===================================================================


class TestParseDiff:
    """Tests for the parse_diff function."""

    def test_parse_diff_basic(self):
        """Parse a sample unified diff with one modified file and verify output structure."""
        result = parse_diff(SAMPLE_DIFF)

        assert isinstance(result, list)
        assert len(result) == 1

        entry = result[0]
        assert entry["path"] == "src/app.py"
        assert entry["directory"] == "src"
        assert entry["filename"] == "app.py"
        assert entry["extension"] == ".py"
        assert entry["modification_type"] == "modified"
        assert entry["additions"] == 3  # +import sys, +print("hello world"), +return 0
        assert entry["deletions"] == 1  # -print("hello")

    def test_parse_diff_empty(self):
        """Parsing an empty string should return an empty list."""
        assert parse_diff("") == []

    def test_parse_diff_malformed(self):
        """Parsing a malformed string returns an empty list (does not raise)."""
        result = parse_diff("this is not a valid diff at all")
        assert result == []


# ===================================================================
# build_change_summary tests
# ===================================================================


class TestBuildChangeSummary:
    """Tests for the build_change_summary function."""

    def test_build_change_summary_basic(self):
        """Build a summary from 3 parsed files and verify totals and groupings."""
        parsed_files = [
            {
                "path": "src/app.py",
                "directory": "src",
                "filename": "app.py",
                "extension": ".py",
                "modification_type": "modified",
                "additions": 10,
                "deletions": 3,
            },
            {
                "path": "src/utils.py",
                "directory": "src",
                "filename": "utils.py",
                "extension": ".py",
                "modification_type": "added",
                "additions": 25,
                "deletions": 0,
            },
            {
                "path": "tests/test_app.py",
                "directory": "tests",
                "filename": "test_app.py",
                "extension": ".py",
                "modification_type": "modified",
                "additions": 15,
                "deletions": 5,
            },
        ]

        summary = build_change_summary(parsed_files)

        # Totals
        assert summary["total_files"] == 3
        assert summary["total_additions"] == 50
        assert summary["total_deletions"] == 8

        # File list preserved
        assert len(summary["files"]) == 3

        # Grouped by directory
        assert "src" in summary["by_directory"]
        assert len(summary["by_directory"]["src"]) == 2
        assert "tests" in summary["by_directory"]
        assert len(summary["by_directory"]["tests"]) == 1

        # Grouped by modification type
        assert "modified" in summary["by_modification_type"]
        assert len(summary["by_modification_type"]["modified"]) == 2
        assert "added" in summary["by_modification_type"]
        assert len(summary["by_modification_type"]["added"]) == 1

        # Grouped by extension
        assert ".py" in summary["by_extension"]
        assert len(summary["by_extension"][".py"]) == 3

        # Not truncated
        assert summary["is_truncated"] is False
        assert summary["truncation_note"] is None

    def test_build_change_summary_empty(self):
        """Empty list produces zero totals and no truncation."""
        summary = build_change_summary([])

        assert summary["total_files"] == 0
        assert summary["total_additions"] == 0
        assert summary["total_deletions"] == 0
        assert summary["files"] == []
        assert summary["by_directory"] == {}
        assert summary["by_modification_type"] == {}
        assert summary["by_extension"] == {}
        assert summary["is_truncated"] is False
        assert summary["truncation_note"] is None

    def test_build_change_summary_truncation(self):
        """When file count exceeds MAX_FILES, is_truncated should be True."""
        # Create 501 mock files (exceeds MAX_FILES=500)
        parsed_files = [
            {
                "path": f"src/file_{i}.py",
                "directory": "src",
                "filename": f"file_{i}.py",
                "extension": ".py",
                "modification_type": "modified",
                "additions": 1,
                "deletions": 0,
            }
            for i in range(501)
        ]

        summary = build_change_summary(parsed_files)

        assert summary["is_truncated"] is True
        assert summary["truncation_note"] is not None
        assert "501 files" in summary["truncation_note"]
        # Files list is capped at MAX_FILES
        assert summary["total_files"] == MAX_FILES


# ===================================================================
# fetch_pr_diff tests
# ===================================================================


class TestFetchPrDiff:
    """Tests for the fetch_pr_diff function."""

    @patch("src.diff_parser.requests.get")
    def test_fetch_pr_diff_success(self, mock_get):
        """Mock requests.get to return 200 with diff text."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.text = SAMPLE_DIFF
        mock_get.return_value = mock_response

        result = fetch_pr_diff("owner/repo", 42, "fake-token")

        assert result == SAMPLE_DIFF
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert "/repos/owner/repo/pulls/42" in call_args[0][0]

    @patch("src.diff_parser.requests.get")
    def test_fetch_pr_diff_404(self, mock_get):
        """Mock requests.get to return 404. Should raise DiffParseError."""
        mock_response = MagicMock()
        mock_response.ok = False
        mock_response.status_code = 404
        mock_response.json.return_value = {"message": "Not Found"}
        mock_get.return_value = mock_response

        with pytest.raises(DiffParseError, match="not found"):
            fetch_pr_diff("owner/repo", 9999, "fake-token")


# ===================================================================
# fetch_changed_files tests
# ===================================================================


class TestFetchChangedFiles:
    """Tests for the fetch_changed_files function."""

    @patch("src.diff_parser.requests.get")
    def test_fetch_changed_files_pagination(self, mock_get):
        """Mock two pages: 100 items on page 1, 50 items on page 2."""
        page1_files = [
            {
                "filename": f"file_{i}.py",
                "status": "modified",
                "additions": 1,
                "deletions": 0,
                "changes": 1,
                "patch": "@@ ...",
            }
            for i in range(100)
        ]
        page2_files = [
            {
                "filename": f"file_{100 + i}.py",
                "status": "added",
                "additions": 5,
                "deletions": 0,
                "changes": 5,
                "patch": "@@ ...",
            }
            for i in range(50)
        ]

        mock_response_page1 = MagicMock()
        mock_response_page1.ok = True
        mock_response_page1.status_code = 200
        mock_response_page1.json.return_value = page1_files

        mock_response_page2 = MagicMock()
        mock_response_page2.ok = True
        mock_response_page2.status_code = 200
        mock_response_page2.json.return_value = page2_files

        mock_get.side_effect = [mock_response_page1, mock_response_page2]

        result = fetch_changed_files("owner/repo", 42, "fake-token")

        assert len(result) == 150
        assert mock_get.call_count == 2

        # Verify first-page items are present
        assert result[0]["filename"] == "file_0.py"
        assert result[0]["status"] == "modified"

        # Verify second-page items are present
        assert result[100]["filename"] == "file_100.py"
        assert result[100]["status"] == "added"
