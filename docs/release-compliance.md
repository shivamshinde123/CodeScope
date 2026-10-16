# Release Compliance Review

Status: pre-release review for CodeScope v2 and its GitHub Pages website on 2026-10-16.

CodeScope is a free, repository-local GitHub Action. It reads pull-request metadata and supported source files from the checked-out repository, calls the GitHub API to maintain one pull-request comment, and does not operate a separate hosted service or database.

The public website is a static GitHub Pages site. It has no analytics, cookies, forms, account system, advertising, external fonts, third-party runtime scripts, or separate data storage.

## Checklist

| Control | Status | Evidence or required follow-up |
| --- | --- | --- |
| Privacy policy and terms | Action required before Marketplace or broader public distribution | The README documents processing and storage behavior. A dedicated privacy notice, terms, and publisher contact are TBD. |
| Refund and cancellation policy | Not applicable | CodeScope v2 has no payment or subscription flow. Reassess before monetization. |
| Cookie disclosure | Not applicable | The Action and website set no cookies and use no browser storage, analytics, advertising, or embedded third-party media. |
| Consent for data collection | Implemented for current scope | Installing and configuring the Action explicitly initiates repository analysis. No optional telemetry or external AI processing exists. |
| Data minimization | Implemented | Analysis is limited by supported file types, file-size/count bounds, repository configuration, and the GitHub metadata needed to update the PR comment. No target code is executed. |
| Dependency audit and pinning | Implemented with ongoing review required | Python dependencies are locked in `uv.lock`; workflow actions are pinned to full commit SHAs. Dependency vulnerability and license checks should be repeated before each release. |
| Dark-pattern review | Implemented | The website has no purchase, consent, cancellation, or account flow; its calls to action link directly to the open-source repository. |
| Marketing and safety claims | Implemented | Documentation describes limitations and does not claim that CodeScope proves a change is safe or complete. |
| Accessibility | Implemented in source; manual verification required | PR findings have text equivalents. The site has semantic landmarks, a skip link, visible focus states, responsive content, reduced-motion support, and non-color labels. Screen-reader, zoom, and contrast checks remain release gates. |
| Keyboard navigation | Implemented in source; manual verification required | Native links and buttons cover all interactions, graph nodes are buttons, and the copy action is non-essential. Complete keyboard testing remains a release gate. |
| Publisher identity and support | Action required before Marketplace release | Repository ownership is visible; a dedicated security/support contact and response process are TBD. |
| Children and age gating | Not applicable | CodeScope is a developer tool, does not target children, and has no end-user account system. |
| Marketing unsubscribe | Not applicable | CodeScope sends no marketing email or promotional messages. |
| License and asset provenance | Action required before public release | The project is MIT licensed. The website uses no external fonts, images, icons, or JavaScript packages. Python and workflow dependency licenses still require a recorded release audit. |
| Data rights and retention | Implemented for current architecture | CodeScope keeps no separate user profile or analysis database, and the website collects no visitor submissions. PR comments, workflow logs, and standard Pages hosting logs remain subject to GitHub controls. |
| Platform policy and least privilege | Implemented with documented limitation | The sample workflow requests `contents: read` and `pull-requests: write`, disables persisted checkout credentials, and avoids `pull_request_target`. Fork PRs may not permit comment writes with the read-only token. |

## Release Gates

The code change has no known compliance blocker for review or testing. Before a Marketplace or broadly promoted release, complete these non-code gates:

1. Publish publisher support, security-reporting, privacy, and terms contacts.
2. Record a dependency license and vulnerability audit for the release commit.
3. Verify the rendered PR comment with a screen reader and keyboard-only GitHub navigation.
4. Re-run this review if telemetry, hosted processing, AI providers, payments, a website, new permissions, or additional distribution regions are introduced.

Jurisdiction-dependent privacy, contract, accessibility, and marketplace obligations remain TBD pending qualified review for the intended distribution regions and business model.

This AI-assisted review is not legal advice and does not replace review by qualified counsel for the product's jurisdictions and business model.
