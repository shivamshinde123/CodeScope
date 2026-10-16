"""CodeScope deterministic pull-request decision pipeline."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from src.diff_parser import DiffParseError, build_change_summary, fetch_pr_diff, parse_diff
from src.github_commenter import CommentPostError, format_comment, post_or_update_comment
from src.repository_analyzer import analyze_repository, build_mermaid

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("codescope")


def get_env_vars() -> dict[str, str]:
    """Read required GitHub context and optional analysis settings."""
    required = {
        "GITHUB_TOKEN": os.getenv("GITHUB_TOKEN"),
        "GITHUB_REPOSITORY": os.getenv("GITHUB_REPOSITORY"),
        "PR_NUMBER": os.getenv("PR_NUMBER"),
    }
    missing = [key for key, value in required.items() if not value]
    if missing:
        logger.error("Missing required environment variables: %s", ", ".join(missing))
        raise SystemExit(1)
    return {
        **{key: str(value) for key, value in required.items()},
        "GITHUB_BASE_SHA": os.getenv("GITHUB_BASE_SHA", ""),
        "CODESCOPE_CONFIG": os.getenv("CODESCOPE_CONFIG", ".codescope.toml"),
        "GITHUB_WORKSPACE": os.getenv("GITHUB_WORKSPACE", os.getcwd()),
    }


def run_pipeline(config: dict[str, str]) -> str:
    """Run analysis and return the comment body (separable for testing)."""
    repo = config["GITHUB_REPOSITORY"]
    pr_number = int(config["PR_NUMBER"])
    token = config["GITHUB_TOKEN"]
    raw_diff = fetch_pr_diff(repo, pr_number, token)
    parsed_files = parse_diff(raw_diff)
    change_summary = build_change_summary(parsed_files)
    report = analyze_repository(
        Path(config["GITHUB_WORKSPACE"]),
        change_summary["files"],
        base_sha=config.get("GITHUB_BASE_SHA", ""),
        config_path=config.get("CODESCOPE_CONFIG", ".codescope.toml"),
    )
    if change_summary.get("is_truncated"):
        report["incomplete_reasons"].append(change_summary["truncation_note"])
        report["state"] = "Analysis incomplete"
    return format_comment(report, change_summary, build_mermaid(report))


def main() -> None:
    """Analyze a pull request and update CodeScope's stable comment."""
    logger.info("Starting CodeScope merge-readiness analysis")
    config = get_env_vars()
    try:
        comment_body = run_pipeline(config)
        post_or_update_comment(
            config["GITHUB_REPOSITORY"],
            int(config["PR_NUMBER"]),
            config["GITHUB_TOKEN"],
            comment_body,
        )
    except (DiffParseError, CommentPostError, ValueError) as exc:
        logger.error("CodeScope failed: %s", exc)
        raise SystemExit(1) from exc
    except Exception as exc:
        logger.exception("Unexpected CodeScope failure: %s", exc)
        raise SystemExit(1) from exc
    logger.info("CodeScope analysis completed successfully")


if __name__ == "__main__":
    main()
