"""
CodeScope — Claude Analyzer module.

Sends structured PR diff data to the Anthropic Claude API and receives
a Mermaid diagram that visualizes the changes for quick reviewer comprehension.
"""

import logging
import re
import time

import anthropic

logger = logging.getLogger("codescope.claude_analyzer")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
MAX_RETRIES: int = 3
DEFAULT_MODEL: str = "claude-sonnet-4-20250514"
MAX_TOKENS: int = 4096

# System prompt that frames Claude's role for every request.
_SYSTEM_PROMPT: str = (
    "You are a code review visualization expert. Your task is to analyze "
    "pull request changes and generate clear, informative Mermaid diagrams "
    "that help reviewers quickly understand the scope and impact of changes. "
    "Always output valid Mermaid syntax."
)

# Valid top-level Mermaid diagram directives used during validation.
_VALID_MERMAID_DIRECTIVES: tuple[str, ...] = (
    "graph",
    "flowchart",
    "sequenceDiagram",
    "classDiagram",
    "mindmap",
    "stateDiagram",
    "erDiagram",
    "gantt",
    "pie",
    "gitgraph",
)


# ---------------------------------------------------------------------------
# Custom Exceptions
# ---------------------------------------------------------------------------
class ClaudeAnalysisError(Exception):
    """Raised when the Claude API analysis fails irrecoverably."""


class MermaidValidationError(Exception):
    """Raised when generated Mermaid code fails structural validation."""


# ---------------------------------------------------------------------------
# Prompt Construction
# ---------------------------------------------------------------------------
def build_prompt(change_summary: dict) -> str:
    """Build a detailed user prompt from structured PR change data.

    The prompt presents the change summary in a readable format and instructs
    Claude to produce a colour-coded Mermaid ``flowchart`` diagram grouped by
    directory, with line-change counts on every node.

    Args:
        change_summary: Dictionary produced by ``diff_parser.build_change_summary``.
            Expected keys: ``total_files``, ``total_additions``, ``total_deletions``,
            ``files``, ``by_directory``, ``by_modification_type``, ``by_extension``,
            ``is_truncated``.

    Returns:
        A string prompt ready to be sent as the user message to Claude.
    """

    lines: list[str] = []

    # -- Truncation warning (placed first so Claude sees the caveat early) --
    if change_summary.get("is_truncated"):
        lines.append(
            "NOTE: The data below represents a SUBSET of the total changes. "
            "Some files have been omitted due to size limits. Visualize only "
            "the files listed here and add a note in the diagram indicating "
            "that additional files were changed but are not shown.\n"
        )

    # -- High-level statistics --
    lines.append("## Pull Request Change Summary\n")
    lines.append(f"- **Total files changed:** {change_summary['total_files']}")
    lines.append(f"- **Total additions:** +{change_summary['total_additions']}")
    lines.append(f"- **Total deletions:** -{change_summary['total_deletions']}\n")

    # -- Per-file breakdown --
    lines.append("## Changed Files\n")
    lines.append(
        "| # | Path | Modification | Additions | Deletions |"
    )
    lines.append(
        "|---|------|--------------|-----------|-----------|"
    )
    for idx, f in enumerate(change_summary["files"], start=1):
        lines.append(
            f"| {idx} | `{f['path']}` | {f['modification_type']} "
            f"| +{f['additions']} | -{f['deletions']} |"
        )
    lines.append("")

    # -- Breakdown by directory --
    lines.append("## Files Grouped by Directory\n")
    for directory, dir_files in change_summary["by_directory"].items():
        display_dir = directory if directory else "(root)"
        lines.append(f"### `{display_dir}`")
        for f in dir_files:
            lines.append(
                f"- `{f['filename']}` ({f['modification_type']}, "
                f"+{f['additions']}/-{f['deletions']})"
            )
        lines.append("")

    # -- Breakdown by modification type --
    lines.append("## Files Grouped by Modification Type\n")
    for mod_type, mod_files in change_summary["by_modification_type"].items():
        lines.append(f"### {mod_type.capitalize()}")
        for f in mod_files:
            lines.append(f"- `{f['path']}`")
        lines.append("")

    # -- Breakdown by extension --
    lines.append("## Files Grouped by Extension\n")
    for ext, ext_files in change_summary["by_extension"].items():
        display_ext = ext if ext else "(no extension)"
        lines.append(f"### `{display_ext}`")
        for f in ext_files:
            lines.append(f"- `{f['path']}`")
        lines.append("")

    # -- Instructions for the diagram --
    lines.append("## Instructions\n")
    lines.append(
        "Analyze the relationships between the changed files above and "
        "generate a Mermaid `flowchart` diagram with the following rules:\n"
    )
    lines.append(
        "1. **Directory hierarchy** — Show the directory structure of the "
        "changed files. Use Mermaid `subgraph` blocks to group files that "
        "share the same directory.\n"
    )
    lines.append(
        "2. **Color-coded nodes** — Apply styles based on modification type:\n"
        "   - **Added** files: green (`style ... fill:#2ea44f,color:#fff`)\n"
        "   - **Modified** files: orange (`style ... fill:#e36209,color:#fff`)\n"
        "   - **Deleted** files: red (`style ... fill:#cb2431,color:#fff`)\n"
        "   - **Renamed** files: blue (`style ... fill:#0366d6,color:#fff`)\n"
    )
    lines.append(
        "3. **Line change counts** — Each node label must include the "
        "filename and its change counts in the format "
        '`filename (+additions/-deletions)`.\n'
    )
    lines.append(
        "4. **Connections** — Draw edges between files that are likely "
        "related (same directory, similar names, import/export pairs, "
        "test ↔ source, etc.).\n"
    )
    lines.append(
        "5. **Output format** — Return ONLY the raw Mermaid code. "
        "Do NOT wrap it in markdown code fences. Do NOT include any "
        "explanation, commentary, or text outside the Mermaid code.\n"
    )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Mermaid Extraction & Validation
# ---------------------------------------------------------------------------
def _extract_mermaid(raw_response: str) -> str:
    """Extract Mermaid code from a Claude response, stripping any fences.

    If the response contains a markdown code fence — either
    ````mermaid ... ``` `` or plain ```` ... ``` `` — only the content
    inside the fence is returned.  Otherwise the entire response is
    treated as raw Mermaid code.

    Args:
        raw_response: The raw text returned by Claude.

    Returns:
        Cleaned Mermaid code string.
    """

    # Pattern matches ```mermaid ... ``` or ``` ... ``` (with optional language tag).
    # re.DOTALL lets '.' match newlines so we capture multi-line diagrams.
    fence_pattern = re.compile(r"```(?:mermaid)?\s*\n(.*?)```", re.DOTALL)

    match = fence_pattern.search(raw_response)
    if match:
        return match.group(1).strip()

    # No fences found — assume the whole response is Mermaid code.
    return raw_response.strip()


def validate_mermaid(mermaid_code: str) -> str:
    """Validate that *mermaid_code* looks structurally correct.

    Performs two lightweight checks:

    1. The code must begin with a recognised Mermaid directive (e.g.
       ``flowchart``, ``graph``, ``sequenceDiagram``).
    2. Opening and closing brackets must be roughly balanced.

    Args:
        mermaid_code: The Mermaid source to validate.

    Returns:
        The unchanged *mermaid_code* if validation passes.

    Raises:
        MermaidValidationError: If any validation check fails.
    """

    if not mermaid_code:
        raise MermaidValidationError("Mermaid code is empty.")

    # -- Check 1: Valid opening directive ------------------------------------
    # Strip any leading %%{ ... }%% Mermaid configuration blocks before
    # checking the directive, since those can legally precede the diagram type.
    stripped = re.sub(r"%%\{.*?%%\}", "", mermaid_code, flags=re.DOTALL).strip()

    first_token = stripped.split()[0] if stripped.split() else ""
    # stateDiagram-v2 is a valid variant — match the base keyword.
    base_token = first_token.split("-")[0]

    if base_token not in _VALID_MERMAID_DIRECTIVES:
        raise MermaidValidationError(
            f"Mermaid code does not start with a valid directive. "
            f"Found '{first_token}'; expected one of: "
            f"{', '.join(_VALID_MERMAID_DIRECTIVES)}"
        )

    # -- Check 2: Balanced brackets ------------------------------------------
    bracket_pairs = {"[": "]", "{": "}", "(": ")"}
    for open_char, close_char in bracket_pairs.items():
        open_count = mermaid_code.count(open_char)
        close_count = mermaid_code.count(close_char)
        if open_count != close_count:
            raise MermaidValidationError(
                f"Unbalanced brackets: '{open_char}' appears {open_count} "
                f"time(s) but '{close_char}' appears {close_count} time(s)."
            )

    return mermaid_code


# ---------------------------------------------------------------------------
# Claude API Integration
# ---------------------------------------------------------------------------
def analyze_with_claude(
    change_summary: dict,
    api_key: str,
    model: str = DEFAULT_MODEL,
) -> str:
    """Send the change summary to Claude and return a validated Mermaid diagram.

    Implements automatic retry with exponential back-off on rate-limit errors.

    Args:
        change_summary: Structured change data produced by the diff parser.
        api_key: Anthropic API key.
        model: Claude model identifier to use for the request.

    Returns:
        A validated Mermaid diagram string.

    Raises:
        ClaudeAnalysisError: Wraps non-retryable API errors.
        MermaidValidationError: If the generated Mermaid code is invalid.
        anthropic.AuthenticationError: If the API key is invalid.
        anthropic.APIError: On unexpected API failures after logging.
    """

    client = anthropic.Anthropic(api_key=api_key)
    user_prompt = build_prompt(change_summary)

    # Retry loop — only rate-limit errors trigger retries.
    last_exception: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info(
                "Sending analysis request to Claude (model=%s, attempt=%d/%d)",
                model,
                attempt,
                MAX_RETRIES,
            )

            response = client.messages.create(
                model=model,
                max_tokens=MAX_TOKENS,
                system=_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
            )

            raw_text: str = response.content[0].text
            logger.debug("Raw Claude response length: %d characters", len(raw_text))

            # Clean and validate the response.
            mermaid_code = _extract_mermaid(raw_text)
            mermaid_code = validate_mermaid(mermaid_code)

            logger.info("Mermaid diagram validated (%d characters)", len(mermaid_code))
            return mermaid_code

        except anthropic.RateLimitError as exc:
            # Exponential back-off: 2s, 4s, 8s …
            backoff_seconds = 2 ** attempt
            logger.warning(
                "Rate limited by Anthropic API (attempt %d/%d). "
                "Retrying in %ds …",
                attempt,
                MAX_RETRIES,
                backoff_seconds,
            )
            last_exception = exc
            if attempt < MAX_RETRIES:
                time.sleep(backoff_seconds)
            # If this was the last attempt, fall through to the raise below.

        except anthropic.AuthenticationError as exc:
            logger.error(
                "Authentication failed — verify that ANTHROPIC_API_KEY is "
                "valid: %s",
                exc,
            )
            raise

        except anthropic.APIError as exc:
            logger.error("Anthropic API error: %s", exc)
            raise

    # All retry attempts exhausted due to rate limiting.
    raise ClaudeAnalysisError(
        f"Claude API rate limit exceeded after {MAX_RETRIES} attempts."
    ) from last_exception
