"""
CodeScope — Main entry point.

Orchestrates the PR visualization pipeline:
1. Fetch and parse the PR diff
2. Analyze changes with Claude to generate a Mermaid diagram
3. Post the diagram as a PR comment

Graceful degradation: if Claude API fails, a text-only summary is posted
instead of a Mermaid diagram.  GitHub API failures are treated as critical
and cause the action to exit with code 1.
"""

from __future__ import annotations

import logging
import os
import sys

from src.claude_analyzer import ClaudeAnalysisError, MermaidValidationError, analyze_with_claude
from src.diff_parser import DiffParseError, build_change_summary, fetch_pr_diff, parse_diff
from src.github_commenter import CommentPostError, format_comment, post_or_update_comment

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("codescope")


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

def get_env_vars() -> dict[str, str]:
    """Read and validate required environment variables.

    Returns:
        Dictionary with all configuration values.

    Raises:
        SystemExit: If required environment variables are missing.
    """
    required = {
        "GITHUB_TOKEN": os.getenv("GITHUB_TOKEN"),
        "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY"),
        "GITHUB_REPOSITORY": os.getenv("GITHUB_REPOSITORY"),
        "PR_NUMBER": os.getenv("PR_NUMBER"),
    }

    missing = [key for key, value in required.items() if not value]
    if missing:
        logger.error("Missing required environment variables: %s", ", ".join(missing))
        sys.exit(1)

    return {
        **{k: v for k, v in required.items() if v is not None},
        "INPUT_MODEL": os.getenv("INPUT_MODEL", "claude-sonnet-4-20250514"),
    }


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def main() -> None:
    """Run the CodeScope pipeline.

    Exit codes:
        0 — Success, or non-critical failure (Claude unavailable, diagram
            generation failed — a text fallback was posted instead).
        1 — Critical failure (missing env vars, GitHub API errors, unable
            to post the comment at all).
    """
    logger.info("Starting CodeScope PR visualization pipeline")

    # ---- Step 0: Load configuration ----------------------------------------
    config = get_env_vars()
    repo = config["GITHUB_REPOSITORY"]
    pr_number = int(config["PR_NUMBER"])
    token = config["GITHUB_TOKEN"]
    api_key = config["ANTHROPIC_API_KEY"]
    model = config["INPUT_MODEL"]

    logger.info("Processing PR #%d in %s (model: %s)", pr_number, repo, model)

    # ---- Step 1: Fetch and parse the PR diff --------------------------------
    logger.info("Step 1: Fetching and parsing PR diff...")
    try:
        raw_diff = fetch_pr_diff(repo, pr_number, token)
        parsed_files = parse_diff(raw_diff)
        change_summary = build_change_summary(parsed_files)
    except DiffParseError as exc:
        logger.error("Failed to fetch/parse PR diff: %s", exc)
        sys.exit(1)
    except Exception as exc:
        logger.error("Unexpected error during diff parsing: %s", exc)
        sys.exit(1)

    logger.info(
        "Parsed %d changed file(s) (%d additions, %d deletions)",
        change_summary["total_files"],
        change_summary["total_additions"],
        change_summary["total_deletions"],
    )

    # ---- Step 2: Analyze with Claude ----------------------------------------
    logger.info("Step 2: Analyzing changes with Claude...")
    mermaid_code: str | None = None

    try:
        mermaid_code = analyze_with_claude(change_summary, api_key, model)
        logger.info("Mermaid diagram generated successfully")
    except (ClaudeAnalysisError, MermaidValidationError) as exc:
        # Non-critical: fall back to text summary.
        logger.warning("Claude analysis failed — falling back to text summary: %s", exc)
    except Exception as exc:
        logger.warning("Unexpected error during Claude analysis — using fallback: %s", exc)

    # ---- Step 3: Post comment on PR -----------------------------------------
    logger.info("Step 3: Posting diagram to PR...")
    comment_body = format_comment(mermaid_code, change_summary)

    try:
        post_or_update_comment(repo, pr_number, token, comment_body)
    except CommentPostError as exc:
        logger.error("Failed to post comment: %s", exc)
        sys.exit(1)
    except Exception as exc:
        logger.error("Unexpected error while posting comment: %s", exc)
        sys.exit(1)

    logger.info("CodeScope pipeline completed successfully")


if __name__ == "__main__":
    main()
