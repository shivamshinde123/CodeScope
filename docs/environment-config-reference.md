# Environment and Configuration Reference

## Action inputs

| Name | Default | Guidance |
|---|---|---|
| `github-token` | `${{ github.token }}` | Grant `contents: read` and `pull-requests: write` only |
| `config-path` | `.codescope.toml` | Must be a repository-relative path without `..` |

## Environment variables

| Name | Set by | Description |
|---|---|---|
| `GITHUB_TOKEN` | Action | GitHub REST authentication |
| `GITHUB_REPOSITORY` | GitHub context | Repository full name |
| `PR_NUMBER` | Pull-request event | Pull-request number |
| `GITHUB_WORKSPACE` | GitHub runner | Checked-out target repository |
| `GITHUB_BASE_SHA` | Pull-request event | Trusted base revision |
| `CODESCOPE_CONFIG` | Action input | Policy path |

No Anthropic or other AI-provider secret is required in v2.

## Workflow permissions

```yaml
permissions:
  contents: read
  pull-requests: write
```

Fork pull requests receive restricted tokens. Comment publication may fail even when analysis succeeds. Do not add secrets to untrusted fork workflows or execute fork code with `pull_request_target`.

## Policy defaults

- `analysis.max_depth`: `2`, constrained to 1 through 5.
- `analysis.ignore`: empty, in addition to built-in ignores for Git metadata, environments, dependencies, build output, and caches.
- `architecture.forbid_cycles`: `false` unless explicitly enabled.
- `architecture.forbid`, `architecture.exceptions`, and `tests.map`: empty.

Secrets must never appear in policy, logs, comments, fixtures, or documentation.
