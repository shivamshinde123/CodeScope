# CodeScope

A GitHub Action that automatically generates visual Mermaid diagrams for pull requests, helping reviewers understand the scope of changes at a glance.

## How It Works

```
PR Opened/Updated
       │
       ▼
  Fetch PR diff (GitHub API)
       │
       ▼
  Parse diff (Python + unidiff)
  → file names, paths, mod types, line counts
       │
       ▼
  Analyze with Claude (Anthropic API)
  → relationships, impact zones, Mermaid diagram
       │
       ▼
  Post diagram as PR comment
  (updates existing comment on re-runs)
```

1. **Diff parsing** — Fetches the PR diff via GitHub API and parses it with `unidiff` to extract structured metadata (file paths, modification types, line counts).
2. **Claude analysis** — Sends the structured data to Claude, which analyzes file relationships and generates a color-coded Mermaid flowchart diagram.
3. **PR comment** — Posts the diagram as an automated comment on the PR. Re-runs update the existing comment instead of creating duplicates.

## Quick Start — Use CodeScope in Your Repo

### Step 1: Add the Anthropic API key as a repository secret

Go to your repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

- Name: `ANTHROPIC_API_KEY`
- Value: Your Anthropic API key (get one at [console.anthropic.com](https://console.anthropic.com))

### Step 2: Create the workflow file

Create `.github/workflows/codescope.yml` in your repository:

```yaml
name: CodeScope PR Visualizer

on:
  pull_request:
    types: [opened, synchronize, reopened]

permissions:
  contents: read
  pull-requests: write

jobs:
  visualize:
    name: Generate PR Diagram
    runs-on: ubuntu-latest
    steps:
      - name: Run CodeScope
        uses: shivamshinde123/CodeScope@master
        with:
          anthropic-api-key: ${{ secrets.ANTHROPIC_API_KEY }}
```

That's it. Open a PR and the diagram appears automatically.

### Optional: Customize the Claude model

```yaml
      - name: Run CodeScope
        uses: shivamshinde123/CodeScope@master
        with:
          anthropic-api-key: ${{ secrets.ANTHROPIC_API_KEY }}
          model: "claude-sonnet-4-20250514"
```

## How to Test It

1. Add `ANTHROPIC_API_KEY` as a secret in your repo
2. Push the workflow file above to your default branch (main/master)
3. Create a new branch, change a few files, and open a PR
4. Check the **Actions** tab to watch the workflow run
5. Once complete, a Mermaid diagram comment appears on the PR

## Configuration

| Input | Required | Default | Description |
|-------|----------|---------|-------------|
| `anthropic-api-key` | Yes | — | Anthropic API key for Claude |
| `github-token` | No | Auto-provided | GitHub token for API access |
| `model` | No | `claude-sonnet-4-20250514` | Claude model to use |

## What the Diagram Shows

- **Directory hierarchy** — Files grouped by directory using Mermaid subgraphs
- **Color-coded nodes** — Green (added), orange (modified), red (deleted), blue (renamed)
- **Line change counts** — Each node shows additions/deletions
- **File relationships** — Edges between related files (same directory, test ↔ source, etc.)

## Graceful Degradation

If the Claude API is unavailable, CodeScope posts a text-only table summary instead of failing the action. GitHub API errors are treated as critical failures.

## Development

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager

### Run tests

```bash
uv sync
uv run pytest tests/ -v
```

## Project Structure

```
CodeScope/
├── .github/workflows/codescope.yml   # GitHub Actions workflow
├── src/
│   ├── main.py                       # Pipeline orchestrator
│   ├── diff_parser.py                # Fetches & parses PR diffs
│   ├── claude_analyzer.py            # Claude API → Mermaid diagrams
│   └── github_commenter.py           # Posts/updates PR comments
├── tests/                            # Unit tests (28 tests)
├── action.yml                        # Composite action metadata
└── pyproject.toml                    # Dependencies (uv)
```

## Inspiration

Inspired by [Marlene Mhangami](https://github.com/marlenezw)'s work on visualizing PR changes using Excalidraw MCP and the GitHub Copilot SDK.

## License

MIT
