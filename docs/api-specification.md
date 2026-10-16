# API Specification

## Scope

CodeScope v2 is a composite GitHub Action. It has no hosted HTTP API. Its external interfaces are Action inputs, GitHub event context, `.codescope.toml`, GitHub REST calls, and the pull-request comment it publishes.

## Action inputs

| Input | Required | Default | Description |
|---|---:|---|---|
| `github-token` | Yes | `github.token` | Reads the pull-request diff and creates or updates one comment |
| `config-path` | No | `.codescope.toml` | Repository-relative path to policy on the base revision |

The caller must check out the pull request with full history before invoking the Action.

## Runtime environment

`action.yml` maps GitHub context to these process variables:

| Variable | Required | Meaning |
|---|---:|---|
| `GITHUB_TOKEN` | Yes | Token for GitHub REST requests |
| `GITHUB_REPOSITORY` | Yes | `owner/repository` |
| `PR_NUMBER` | Yes | Pull-request number |
| `GITHUB_WORKSPACE` | Yes in Actions | Checked-out repository root |
| `GITHUB_BASE_SHA` | Required for complete results | Base revision used for trusted policy and new-edge comparison |
| `CODESCOPE_CONFIG` | No | Policy path, default `.codescope.toml` |

## GitHub REST usage

### Read pull-request diff

`GET /repos/{owner}/{repo}/pulls/{pull_number}` with `Accept: application/vnd.github.v3.diff`.

### List comments

`GET /repos/{owner}/{repo}/issues/{issue_number}/comments?per_page=100&page={page}`. CodeScope inspects at most ten pages for its stable marker.

### Create comment

`POST /repos/{owner}/{repo}/issues/{issue_number}/comments`

```json
{"body": "<!-- codescope-merge-readiness -->\n..."}
```

### Update comment

`PATCH /repos/{owner}/{repo}/issues/comments/{comment_id}` using the same body shape.

## Policy schema

```toml
[analysis]
max_depth = 2
ignore = ["generated/**"]

[architecture]
forbid_cycles = true

[[architecture.forbid]]
id = "stable-rule-id"
from = "source/glob/**"
to = "target/glob/**"
reason = "Human-readable architectural intent"

[[architecture.exceptions]]
rule = "stable-rule-id"
from = "narrow/source.py"
to = "narrow/target.py"
reason = "Documented exception"

[[tests.map]]
source = "src/domain/**"
tests = ["tests/domain/**"]
```

Unknown keys are ignored in v2. Invalid TOML marks analysis incomplete. Schema versioning is TBD.

## Internal report contract

`analyze_repository` returns a dictionary with:

- `state`: one of `Ready for review`, `Needs targeted review`, `Missing required evidence`, or `Analysis incomplete`.
- `changed_source_files` and `changed_production_files`.
- `impacts`: path, kind, dependency path, and confidence.
- `test_evidence`: changed target, mapped tests, changed mapped tests, and status.
- `missing_tests`: stable finding ID, target, evidence, and recommendation.
- `architecture_violations`: stable finding ID, rule ID, source, target, evidence, and reason.
- `incomplete_reasons`.
- `analysis`: scan counts, depth, policy source, and config path.
- `graph`: repository-local adjacency map used for rendering.

This internal contract is not yet a compatibility-guaranteed public Python API.
