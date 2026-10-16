# File and Folder Structure

## GitHub Pages website

```text
site/
├── index.html       # Product landing page and semantic content
├── styles.css       # Responsive visual design
├── script.js        # Progressive enhancement only
├── 404.html         # Project-site fallback
├── robots.txt       # Crawler policy
└── sitemap.xml      # Canonical public URL
```

The website intentionally has no package manager, build step, analytics SDK, external font request, or runtime backend.

```text
CodeScope/
├── .github/workflows/codescope.yml
├── docs/
│   ├── api-specification.md
│   ├── coding-conventions.md
│   ├── component-map.md
│   ├── data-extraction-specification.md
│   ├── decision.md
│   ├── database-schema.md
│   ├── environment-config-reference.md
│   ├── flow.md
│   ├── file-folder-structure.md
│   ├── product-requirements-document.md
│   ├── system-architecture-document.md
│   ├── tech-stack.md
│   ├── technical-design-document.md
│   └── ui-ux-wireframes.md
├── examples/                 Historical sample application and fixtures
├── src/
│   ├── diff_parser.py        Pull-request change collection
│   ├── github_commenter.py   Reviewer output and stable publication
│   ├── main.py               Pipeline entry point
│   └── repository_analyzer.py
├── tests/
├── .codescope.toml           CodeScope's own base-branch policy
├── action.yml                Public composite Action contract
├── LICENSE
├── pyproject.toml
└── README.md
```

Production logic belongs in `src/`, behavioral tests in `tests/`, user setup in `README.md`, and durable design decisions in `docs/`. Generated artifacts, credentials, caches, local environments, and repository-specific output must not be committed.
