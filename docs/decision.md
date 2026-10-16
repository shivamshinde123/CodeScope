# Decision Record

## 2026-10-16 — Publish a static GitHub Pages product site

**Decision:** Ship a dependency-free site from `site/` through GitHub's official Pages workflow after changes reach `master`.

**Why:** The site explains the reviewer problem and v2 evidence model without introducing a hosted application, database, analytics, cookies, forms, or another vendor. GitHub Pages fits the existing open-source distribution channel.

**Tradeoff:** Pull requests do not receive automatic site previews, and the public URL updates only after merge. This is preferred to granting broader deployment permissions or adding another hosting service.

## 2026 10 16 Keep CodeScope as a GitHub Action

CodeScope v2 will remain a composite GitHub Action. A GitHub App, hosted backend, organization dashboard, and cross-repository intelligence are deferred. The Action is sufficient to validate reviewer value with lower operational and security complexity.

## 2026 10 16 Optimize for reviewer decisions

The product will prioritize blast radius, missing-test evidence, architecture drift, and a concise merge-readiness conclusion. Mermaid remains optional supporting evidence rather than the primary output.

## 2026 10 16 Use deterministic evidence for v2

V2 removes the required Anthropic API call. Python and JavaScript or TypeScript imports, Git history, and explicit repository policy produce reproducible findings. An optional AI explanation may be reconsidered later, but it must never invent findings or be required for useful output.

## 2026 10 16 Analyze files and modules first

The initial graph is file or module level. Symbol-level analysis is deferred because reliable multi-language symbol resolution would expand scope and false-positive risk.

## 2026 10 16 Bound blast radius to two hops by default

Two hops balances useful downstream context with review noise. Repositories may configure one to five hops.

## 2026 10 16 Trust policy from the base branch

Architecture rules, exceptions, ignored paths, and test maps come from the pull-request base revision. A pull request cannot weaken its own review rules. Policy changes take effect after merging.

## 2026 10 16 Keep merge readiness advisory

V2 comments do not approve, reject, or merge pull requests. Repositories may later make the workflow required after measuring precision and reviewer trust.

## 2026 10 16 Do not execute inspected repository code

CodeScope reads text and Git objects only. It does not install target-repository dependencies, import modules, run tests, or invoke builds. This reduces fork and supply-chain risk.

## 2026 10 16 Defer persistent storage

The Action uses no database. Historical learning, cross-repository graphs, reviewer workload models, and organization analytics require a later product decision.
