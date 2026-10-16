# Data Extraction Specification

## Sources

CodeScope reads:

1. Pull-request unified diff from the GitHub API.
2. Checked-out repository files with `.py`, `.js`, `.jsx`, `.ts`, or `.tsx` extensions.
3. File content from the base Git revision for changed-source edge comparison and trusted policy.
4. `.codescope.toml` from the base revision.

It does not execute the inspected source.

## Limits

- Maximum supported source files: 5,000.
- Maximum file size: 1,000,000 bytes.
- Maximum configured impact depth: 5.
- Maximum PR files in the diff summary: 500.
- Maximum total changed lines before the diff summary is marked truncated: 10,000.
- Maximum GitHub comment size: 65,536 characters.

## Python extraction

Python files are parsed with the standard-library `ast` module. `Import` and `ImportFrom` statements are resolved to repository-local files. Common `src`, `lib`, and `python` source roots receive an additional package alias. Syntax errors yield no edges for that file rather than executing fallback logic.

## JavaScript and TypeScript extraction

Static relative `import`, re-export, and `require` specifiers are extracted. Resolution checks direct files, `.ts`, `.tsx`, `.js`, `.jsx`, and matching `index` files. Package aliases, dynamic imports, framework loaders, and workspace package graphs are not resolved in v2.

## Transformation

The head graph points from importer to imported file. CodeScope reverses this graph to find dependents of changed production files. Each impact retains a path from dependent to changed dependency. Test files are identified using common test directories and filename conventions.

New architecture edges are head edges originating in changed files that were absent from the base revision. Architecture rules and exceptions use repository-relative glob patterns.

## Incomplete states

CodeScope records an explicit incomplete reason when a scan limit is reached, policy is invalid, the base SHA is absent, the diff is truncated, or a supported source file was deleted. Unsupported language coverage is disclosed in documentation but is not currently enumerated per run. Per-run unsupported-language reporting is TBD.

## Storage and transmission

Analysis is in-memory inside the GitHub runner. CodeScope sends the diff request and comment request to GitHub. V2 has no AI-provider call, telemetry endpoint, external database, or separate backend.
