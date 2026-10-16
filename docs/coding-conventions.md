# Coding Conventions

## Python

- Target Python 3.12 or later.
- Use type hints on public functions and non-obvious local structures.
- Keep side effects at boundaries. Parsing and analysis functions should return data rather than publish comments directly.
- Never import, execute, build, or install code from the repository being analyzed.
- Bound file count, file size, graph depth, API pagination, network timeouts, and rendered output size.
- Treat repository files, policy, paths, Git output, and GitHub responses as untrusted input.
- Prefer deterministic output ordering by sorting paths, edges, and findings.
- Give every actionable finding a stable ID derived from its evidence.
- Distinguish incomplete analysis from an analysis that found no issue.

## Tests

- Test behavior and evidence contracts rather than internal call ordering, except at network boundaries.
- Use temporary repositories or in-memory policy stubs for analyzer tests.
- Mock GitHub network requests.
- Cover safe failure states, pagination, truncation, deleted files, invalid policy, explicit exceptions, and stable comment updates.
- A bug fix should include a regression test when practical.

## Documentation

- Update the relevant file in `docs/` when behavior, interfaces, data flow, configuration, or product scope changes.
- Add material decisions chronologically to `decision.md`; do not rewrite history when a decision is superseded.
- Mark unknowns as `TBD` instead of inventing an answer.

## Git and releases

- Work on a descriptive branch, never directly on the default branch.
- Keep commits focused and use imperative commit subjects.
- A release pull request must include test evidence and the release-compliance result.
- Do not claim that CodeScope proves correctness, security, or legal compliance.
