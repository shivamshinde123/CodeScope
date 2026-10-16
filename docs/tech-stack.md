# Technology Stack

## Public website

- Semantic HTML5 for a durable, crawlable document.
- Hand-authored CSS for the visual system, responsive behavior, focus states, and reduced motion.
- Small dependency-free JavaScript for progressive enhancement.
- GitHub Pages and official SHA-pinned deployment actions for hosting.

No frontend framework is needed because the site has one page, no application state, and no server interaction.

## Runtime

- Python 3.12 or later.
- `uv` for dependency resolution and execution.
- GitHub composite Action for distribution.
- Ubuntu GitHub-hosted runner in documented examples.

## Libraries

| Dependency | Purpose | Rationale |
|---|---|---|
| Python `ast` | Python import extraction | Standard library, deterministic, no code execution |
| `tomllib` | Base-branch policy parsing | Standard library in Python 3.11 and later |
| `unidiff` | Unified diff parsing | Small focused parser already used by the project |
| `requests` | GitHub REST calls | Existing dependency with explicit timeout support |
| `pytest` | Behavioral tests | Existing development dependency |

The Anthropic SDK is removed from v2 because deterministic analysis is the product foundation and must not require a user secret.

## GitHub dependencies

- `actions/checkout` supplies the target repository and base history.
- `actions/setup-python` supplies Python 3.12.
- `astral-sh/setup-uv` supplies a fixed uv version.

Release hardening should pin third-party Actions to reviewed commit SHAs. Exact SHA policy is TBD.

## Rejected for v2

- Tree-sitter or language servers: broader parsing but added packaging and complexity.
- Neo4j or another graph database: unnecessary without persistence or cross-repository analysis.
- Hosted API and queue: unnecessary for the Action MVP.
- LLM-required analysis: nondeterministic, secret-dependent, and weaker as the source of enforceable findings.
