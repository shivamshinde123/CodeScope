# Technical Design Document

## Design summary

CodeScope builds a bounded file dependency graph from repository text, overlays pull-request changes, and produces evidence records. The same graph powers blast radius, test mapping, architecture checks, and Mermaid rendering.

## Graph model

Each supported source file is a node. An edge `A -> B` means file A imports file B. Blast radius traverses the reverse graph from changed production nodes so the report can show dependents. A dependency path is ordered from impacted dependent to changed dependency.

## Change comparison

Head edges come from the checkout. For each changed source file, CodeScope reads its base-revision content with `git show` and extracts base edges using the same resolver. A head edge from a changed source is new when the same pair is absent from the base edge set.

## Test mapping

Import traversal finds test files that directly or transitively import a changed source. Base policy may add glob mappings. A target is `changed` when a mapped test is also changed, `existing` when mappings exist but did not change, and `missing` when no mapping exists. These states describe evidence, not test quality.

## Architecture evaluation

Forbid rules match new edges with source and target globs. Exceptions may narrow by rule ID and edge globs. When `forbid_cycles` is enabled, CodeScope removes each new edge temporarily and searches for an existing return path; a path from target back to source means the new edge closes a cycle.

## Merge readiness

Precedence is:

1. `Analysis incomplete` when a material limit prevents a reliable result.
2. `Missing required evidence` when missing tests or architecture violations exist.
3. `Needs targeted review` when indirect production dependents exist.
4. `Ready for review` otherwise.

The state is advisory and does not map to a numerical probability.

## Stable publication

The comment contains `<!-- codescope-merge-readiness -->`. On rerun, CodeScope searches issue comments and patches the existing comment. The legacy `<!-- codescope-diagram -->` marker is recognized so v2 upgrades replace the v1 comment rather than duplicating it.

## Performance

Discovery, file size, graph depth, comment pages, Git commands, HTTP calls, and comment length are bounded. Current graph construction rebuilds per run. Profiling and incremental caching are deferred until real repositories show a need.

## Known limitations

Static regex extraction does not resolve aliases or dynamic JavaScript imports. Python namespace and generated import patterns may be incomplete. Base-edge extraction uses the head file universe, which may omit renamed or deleted targets. Deletions produce an incomplete state. More precise rename and base-graph handling is a future improvement.
