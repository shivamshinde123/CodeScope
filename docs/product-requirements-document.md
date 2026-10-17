# Product Requirements Document

## Product objective

CodeScope helps a pull-request reviewer identify the consequences of merging without reconstructing the repository manually. The v2 MVP must answer what could be affected, what test evidence exists, whether a declared boundary was crossed, and what deserves attention before approval.

## Users

- Pull-request authors who want missing evidence before human review.
- Reviewers who need to orient quickly in a multi-file change.
- Maintainers who want version-controlled architecture boundaries.
- Engineering leads evaluating whether a pull request has sufficient review evidence.

## Functional requirements

### Blast radius

- Build a repository-local file dependency graph for supported languages.
- Report direct and bounded transitive dependents of changed production files.
- Preserve a reproducible dependency path for every impact.
- Distinguish production and test impacts.

### Test evidence

- Identify common test files and import-based relationships.
- Accept optional explicit source-to-test mappings.
- Report mapped tests and whether a mapped test changed.
- Recommend adding or mapping a test when none is found.
- Avoid claiming that mapped tests are sufficient.

### Architecture drift

- Load rules from the base revision.
- Report only forbidden dependency edges introduced by the pull request.
- Optionally report a new edge that closes a cycle.
- Support narrow documented exceptions.
- Explain the rule and exact edge for every finding.

### Reviewer brief

- Update one stable comment.
- Lead with one of four plain-language advisory states.
- Present text evidence before a collapsed Mermaid diagram.
- State analysis limits and avoid safety guarantees.

## Nonfunctional requirements

- Do not execute inspected repository code.
- Operate without an external AI service or secret.
- Use least-privilege GitHub permissions.
- Bound runtime, input sizes, traversal, pagination, and output.
- Produce deterministic ordering and stable findings.
- Preserve useful text output for screen readers and when Mermaid is unavailable.

## Success measures

| Metric | Meaning | Initial target |
|---|---|---|
| Actioned finding rate | Findings that cause a test, design, reviewer, or documented exception change | Establish during pilot |
| False-positive rate | Findings reviewers label incorrect or irrelevant | Establish during pilot, then reduce by type |
| Novel impact discovery | Impacted components reviewers had not initially identified | Establish through pilot survey |
| Time to useful review | Time from PR open to first substantive review | Baseline before rollout |
| Suppression rate | Findings repeatedly exempted by policy | Monitor for rules that need redesign |
| Analysis completion | Runs without an incomplete state, segmented by language and repository type | Report during pilot |

These metrics measure reviewer usefulness, not model accuracy alone. Revert and escaped-defect rates are valuable longer-term measures but require more data and careful causal interpretation.

## Non goals

GitHub App infrastructure, cross-repository graphs, reviewer assignment, line-by-line code review, automated approval, hosted analytics, and historical incident learning are outside the v2 MVP.

## Public website requirements

- Explain CodeScope with short, common words before using product terms.
- Explain blast radius as "files that use the changed code."
- Explain test evidence as "a test linked to the changed file."
- State that team rules come from `.codescope.toml` on the base branch.
- Keep the interactive dependency diagram, but explain its file links in common words.
- Link directly to installation and source documentation.
- Work without JavaScript for all essential content and navigation.
- Respect reduced-motion preferences and support keyboard navigation, zoom, and screen readers.
- Use no analytics, cookies, forms, external fonts, or third-party runtime scripts.
- Deploy only from `master` to the GitHub Pages environment.
- Provide an operational how-to covering workflow installation, optional base-branch policy, and interpretation of all four merge-readiness states.

## Acceptance criteria

- Every impact and architecture warning has inspectable evidence.
- The Action remains useful without an API key.
- Policy changes in a pull request cannot weaken analysis of that same pull request.
- No-result and incomplete states are distinct.
- Tests cover graph traversal, test mapping, rules, exceptions, cycle checks, output formatting, and GitHub failures.
- Documentation describes current behavior and limitations.
