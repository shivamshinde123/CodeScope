# Release Compliance Review

Status: pre-release review for CodeScope v2 on 2026-10-16.

CodeScope is a free, repository-local GitHub Action. It reads pull-request metadata and supported source files from the checked-out repository, calls the GitHub API to maintain one pull-request comment, and does not operate a separate hosted service or database.

## Checklist

| Control | Status | Evidence or required follow-up |
| --- | --- | --- |
| Privacy policy and terms | Action required before Marketplace or broader public distribution | The README documents processing and storage behavior. A dedicated privacy notice, terms, and publisher contact are TBD. |
| Refund and cancellation policy | Not applicable | CodeScope v2 has no payment or subscription flow. Reassess before monetization. |
| Cookie disclosure | Not applicable | The Action has no website, browser storage, analytics, or advertising cookies. |
| Consent for data collection | Implemented for current scope | Installing and configuring the Action explicitly initiates repository analysis. No optional telemetry or external AI processing exists. |
| Data minimization | Implemented | Analysis is limited by supported file types, file-size/count bounds, repository configuration, and the GitHub metadata needed to update the PR comment. No target code is executed. |
| Dependency audit and pinning | Implemented with ongoing review required | Python dependencies are locked in `uv.lock`; workflow actions are pinned to full commit SHAs. Dependency vulnerability and license checks should be repeated before each release. |
| Dark-pattern review | Not applicable | There is no custom purchase, consent, cancellation, or account UI. |
| Marketing and safety claims | Implemented | Documentation describes limitations and does not claim that CodeScope proves a change is safe or complete. |
| Accessibility | Implemented in output design; manual verification required | Every Mermaid diagram has a text equivalent and status labels do not rely only on color. Screen-reader rendering in GitHub PR comments remains a pre-release manual check. |
| Keyboard navigation | Not applicable to custom UI | CodeScope adds Markdown to GitHub's existing interface and provides no custom interactive controls. |
| Publisher identity and support | Action required before Marketplace release | Repository ownership is visible; a dedicated security/support contact and response process are TBD. |
| Children and age gating | Not applicable | CodeScope is a developer tool, does not target children, and has no end-user account system. |
| Marketing unsubscribe | Not applicable | CodeScope sends no marketing email or promotional messages. |
| License and asset provenance | Action required before public release | The project is MIT licensed. Dependency licenses and any future visual assets must be reviewed and recorded before release. |
| Data rights and retention | Implemented for current architecture | CodeScope keeps no separate user profile or analysis database. PR comments and workflow logs remain subject to repository and GitHub retention controls. |
| Platform policy and least privilege | Implemented with documented limitation | The sample workflow requests `contents: read` and `pull-requests: write`, disables persisted checkout credentials, and avoids `pull_request_target`. Fork PRs may not permit comment writes with the read-only token. |

## Release Gates

The code change has no known compliance blocker for review or testing. Before a Marketplace or broadly promoted release, complete these non-code gates:

1. Publish publisher support, security-reporting, privacy, and terms contacts.
2. Record a dependency license and vulnerability audit for the release commit.
3. Verify the rendered PR comment with a screen reader and keyboard-only GitHub navigation.
4. Re-run this review if telemetry, hosted processing, AI providers, payments, a website, new permissions, or additional distribution regions are introduced.

Jurisdiction-dependent privacy, contract, accessibility, and marketplace obligations remain TBD pending qualified review for the intended distribution regions and business model.

This AI-assisted review is not legal advice and does not replace review by qualified counsel for the product's jurisdictions and business model.
