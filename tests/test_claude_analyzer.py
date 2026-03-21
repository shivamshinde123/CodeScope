"""Tests for src.claude_analyzer module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import anthropic
import pytest

from src.claude_analyzer import (
    ClaudeAnalysisError,
    MermaidValidationError,
    _extract_mermaid,
    analyze_with_claude,
    build_prompt,
    validate_mermaid,
)

# ---------------------------------------------------------------------------
# Helpers — reusable change summary fixtures
# ---------------------------------------------------------------------------


def _make_change_summary(
    *,
    total_files: int = 3,
    total_additions: int = 50,
    total_deletions: int = 10,
    is_truncated: bool = False,
    truncation_note: str | None = None,
) -> dict:
    """Build a minimal change summary dict for prompt-building tests."""
    files = [
        {
            "path": f"src/file_{i}.py",
            "directory": "src",
            "filename": f"file_{i}.py",
            "extension": ".py",
            "modification_type": "modified",
            "additions": total_additions // max(total_files, 1),
            "deletions": total_deletions // max(total_files, 1),
        }
        for i in range(total_files)
    ]

    by_directory: dict[str, list] = {}
    by_modification_type: dict[str, list] = {}
    by_extension: dict[str, list] = {}
    for f in files:
        by_directory.setdefault(f["directory"], []).append(f)
        by_modification_type.setdefault(f["modification_type"], []).append(f)
        by_extension.setdefault(f["extension"], []).append(f)

    return {
        "total_files": total_files,
        "total_additions": total_additions,
        "total_deletions": total_deletions,
        "files": files,
        "by_directory": by_directory,
        "by_modification_type": by_modification_type,
        "by_extension": by_extension,
        "is_truncated": is_truncated,
        "truncation_note": truncation_note,
    }


# ===================================================================
# build_prompt tests
# ===================================================================


class TestBuildPrompt:
    """Tests for the build_prompt function."""

    def test_build_prompt_contains_key_sections(self):
        """The prompt should include stats, file table, and instructions."""
        summary = _make_change_summary()
        prompt = build_prompt(summary)

        # High-level stats
        assert "Total files changed" in prompt
        assert "Total additions" in prompt
        assert "Total deletions" in prompt

        # File table header
        assert "Path" in prompt
        assert "Modification" in prompt

        # Instructions section
        assert "Instructions" in prompt
        assert "flowchart" in prompt

    def test_build_prompt_truncation_note(self):
        """When is_truncated=True, the prompt should contain a truncation warning."""
        summary = _make_change_summary(
            is_truncated=True,
            truncation_note="PR is too large; showing subset.",
        )
        prompt = build_prompt(summary)

        assert "SUBSET" in prompt
        assert "omitted" in prompt.lower() or "size limits" in prompt.lower()


# ===================================================================
# _extract_mermaid tests
# ===================================================================


class TestExtractMermaid:
    """Tests for the _extract_mermaid helper."""

    def test_extract_mermaid_with_fences(self):
        """Input with ```mermaid ... ``` fences extracts inner content."""
        raw = "Some text\n```mermaid\nflowchart TD\n  A --> B\n```\nMore text"
        result = _extract_mermaid(raw)
        assert result == "flowchart TD\n  A --> B"

    def test_extract_mermaid_without_fences(self):
        """Plain mermaid code without fences is returned as-is (stripped)."""
        raw = "flowchart TD\n  A --> B"
        result = _extract_mermaid(raw)
        assert result == "flowchart TD\n  A --> B"


# ===================================================================
# validate_mermaid tests
# ===================================================================


class TestValidateMermaid:
    """Tests for the validate_mermaid function."""

    def test_validate_mermaid_valid_flowchart(self):
        """A valid flowchart passes validation and is returned unchanged."""
        code = "flowchart TD\n  A[File] --> B[File]"
        result = validate_mermaid(code)
        assert result == code

    def test_validate_mermaid_invalid_directive(self):
        """Code starting with an unrecognised word raises MermaidValidationError."""
        with pytest.raises(MermaidValidationError, match="valid directive"):
            validate_mermaid("hello world")

    def test_validate_mermaid_unbalanced_brackets(self):
        """Unbalanced brackets raise MermaidValidationError."""
        with pytest.raises(MermaidValidationError, match="Unbalanced"):
            validate_mermaid("flowchart TD\n  A[File")

    def test_validate_mermaid_empty(self):
        """Empty string raises MermaidValidationError."""
        with pytest.raises(MermaidValidationError, match="empty"):
            validate_mermaid("")


# ===================================================================
# analyze_with_claude tests
# ===================================================================


class TestAnalyzeWithClaude:
    """Tests for the analyze_with_claude function."""

    @patch("src.claude_analyzer.anthropic.Anthropic")
    def test_analyze_with_claude_success(self, mock_anthropic_cls):
        """Mock the Anthropic client to return a valid mermaid response."""
        valid_mermaid = "flowchart TD\n  A[app.py] --> B[utils.py]"

        # Set up the mock chain: Anthropic() -> client -> client.messages.create()
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client

        mock_content_block = MagicMock()
        mock_content_block.text = valid_mermaid

        mock_response = MagicMock()
        mock_response.content = [mock_content_block]
        mock_client.messages.create.return_value = mock_response

        summary = _make_change_summary()
        result = analyze_with_claude(summary, api_key="fake-key")

        assert result == valid_mermaid
        mock_client.messages.create.assert_called_once()

    @patch("src.claude_analyzer.anthropic.Anthropic")
    def test_analyze_with_claude_auth_error(self, mock_anthropic_cls):
        """AuthenticationError from the Anthropic client should propagate."""
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client

        # anthropic.AuthenticationError requires specific constructor args
        mock_client.messages.create.side_effect = anthropic.AuthenticationError(
            message="Invalid API key",
            response=MagicMock(status_code=401),
            body={"error": {"message": "Invalid API key"}},
        )

        summary = _make_change_summary()

        with pytest.raises(anthropic.AuthenticationError):
            analyze_with_claude(summary, api_key="bad-key")
