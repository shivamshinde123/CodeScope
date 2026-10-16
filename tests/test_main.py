"""Tests for the CodeScope pipeline boundary."""

from unittest.mock import patch

import pytest

from src.main import get_env_vars, run_pipeline


def test_get_env_vars_requires_github_context(monkeypatch):
    for key in ("GITHUB_TOKEN", "GITHUB_REPOSITORY", "PR_NUMBER"):
        monkeypatch.delenv(key, raising=False)
    with pytest.raises(SystemExit):
        get_env_vars()


@patch("src.main.format_comment", return_value="comment")
@patch("src.main.build_mermaid", return_value="flowchart LR")
@patch("src.main.analyze_repository")
@patch("src.main.parse_diff", return_value=[])
@patch("src.main.fetch_pr_diff", return_value="diff")
def test_run_pipeline_passes_workspace_and_base_sha(
    mock_fetch, mock_parse, mock_analyze, mock_mermaid, mock_format, tmp_path
):
    mock_analyze.return_value = {"incomplete_reasons": [], "state": "Ready for review"}
    config = {
        "GITHUB_TOKEN": "token",
        "GITHUB_REPOSITORY": "owner/repo",
        "PR_NUMBER": "7",
        "GITHUB_BASE_SHA": "abcdef1",
        "CODESCOPE_CONFIG": ".codescope.toml",
        "GITHUB_WORKSPACE": str(tmp_path),
    }
    assert run_pipeline(config) == "comment"
    mock_analyze.assert_called_once()
    assert mock_analyze.call_args.kwargs["base_sha"] == "abcdef1"
    assert mock_analyze.call_args.args[0] == tmp_path
