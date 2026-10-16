"""Contract tests for the dependency-free GitHub Pages website."""

import re
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).parents[1]
SITE = ROOT / "site"


class DocumentProbe(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tags: list[tuple[str, dict[str, str]]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.tags.append((tag, {key: value or "" for key, value in attrs}))


def _document() -> tuple[str, DocumentProbe]:
    source = (SITE / "index.html").read_text(encoding="utf-8")
    parser = DocumentProbe()
    parser.feed(source)
    parser.close()
    return source, parser


def test_site_has_accessible_document_landmarks() -> None:
    source, parser = _document()
    tags = [tag for tag, _ in parser.tags]
    assert '<html lang="en">' in source
    assert "main" in tags
    assert "h1" in tags
    assert any(tag == "a" and attrs.get("href") == "#main" for tag, attrs in parser.tags)
    assert any(
        tag == "meta" and attrs.get("name") == "viewport"
        for tag, attrs in parser.tags
    )


def test_site_has_no_external_runtime_resources_or_collection_forms() -> None:
    source, parser = _document()
    assert "<form" not in source.lower()
    assert "analytics" not in source.lower()
    for tag, attrs in parser.tags:
        if tag == "script" and attrs.get("src"):
            assert attrs["src"].startswith("./")
        if tag == "link" and attrs.get("rel") == "stylesheet":
            assert attrs["href"].startswith("./")


def test_content_remains_visible_without_javascript() -> None:
    css = (SITE / "styles.css").read_text(encoding="utf-8")
    assert ".js .reveal" in css
    assert "prefers-reduced-motion:reduce" in css


def test_how_to_use_section_covers_install_configure_and_review() -> None:
    source, parser = _document()
    ids = {attrs.get("id") for _, attrs in parser.tags if attrs.get("id")}
    assert {"install", "install-code", "policy-code"} <= ids
    assert "Add the workflow" in source
    assert "Declare your boundaries" in source
    assert "Open a pull request" in source
    assert "Missing required evidence" in source
    assert source.count('class="copy-button"') == 2


def test_pages_workflow_is_scoped_and_sha_pinned() -> None:
    workflow = (ROOT / ".github" / "workflows" / "pages.yml").read_text(encoding="utf-8")
    assert "branches: [master]" in workflow
    assert "path: site" in workflow
    uses = re.findall(r"uses:\s+([^\s]+)", workflow)
    assert len(uses) == 4
    assert all(re.fullmatch(r"[^@]+@[0-9a-f]{40}", action) for action in uses)
