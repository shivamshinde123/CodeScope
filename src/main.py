"""
CodeScope — Main entry point.

Orchestrates the PR visualization pipeline:
1. Fetch and parse the PR diff
2. Analyze changes with Claude to generate a Mermaid diagram
3. Post the diagram as a PR comment
"""

import logging
import os
import sys

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("codescope")


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


def main() -> None:
    """Run the CodeScope pipeline."""
    logger.info("Starting CodeScope PR visualization pipeline")

    # Step 0: Load configuration
    config = get_env_vars()
    repo = config["GITHUB_REPOSITORY"]
    pr_number = int(config["PR_NUMBER"])
    token = config["GITHUB_TOKEN"]
    api_key = config["ANTHROPIC_API_KEY"]
    model = config["INPUT_MODEL"]

    logger.info("Processing PR #%d in %s (model: %s)", pr_number, repo, model)

    # Step 1: Fetch and parse the PR diff
    # (implemented in Issue #2)
    logger.info("Step 1: Fetching and parsing PR diff...")
    from src.diff_parser import fetch_pr_diff, parse_diff, build_change_summary

    raw_diff = fetch_pr_diff(repo, pr_number, token)
    parsed_files = parse_diff(raw_diff)
    change_summary = build_change_summary(parsed_files)
    logger.info(
        "Parsed %d changed files (%d additions, %d deletions)",
        change_summary["total_files"],
        change_summary["total_additions"],
        change_summary["total_deletions"],
    )

    # Step 2: Analyze with Claude and generate Mermaid diagram
    # (implemented in Issue #3)
    logger.info("Step 2: Analyzing changes with Claude...")
    try:
        from src.claude_analyzer import analyze_with_claude

        mermaid_code = analyze_with_claude(change_summary, api_key, model)
        logger.info("Mermaid diagram generated successfully")
    except Exception as e:
        logger.warning("Claude analysis failed, using fallback: %s", e)
        mermaid_code = None

    # Step 3: Post comment on PR
    # (implemented in Issue #4)
    logger.info("Step 3: Posting diagram to PR...")
    from src.github_commenter import format_comment, post_or_update_comment

    comment_body = format_comment(mermaid_code, change_summary)
    post_or_update_comment(repo, pr_number, token, comment_body)

    logger.info("CodeScope pipeline completed successfully")


if __name__ == "__main__":
    main()
