"""Tests for deterministic repository analysis."""

from pathlib import Path

import src.repository_analyzer as analyzer


def _write(root: Path, path: str, content: str) -> None:
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def _change(path: str, modification_type: str = "modified") -> dict:
    return {"path": path, "modification_type": modification_type}


def test_analyze_repository_reports_blast_radius_and_test_evidence(tmp_path, monkeypatch):
    _write(tmp_path, "src/__init__.py", "")
    _write(tmp_path, "src/core.py", "def run(): return 1\n")
    _write(tmp_path, "src/service.py", "from src.core import run\n")
    _write(tmp_path, "tests/test_core.py", "from src.core import run\n")
    monkeypatch.setattr(analyzer, "load_policy", lambda *_: {
        "analysis": {"max_depth": 2}, "architecture": {"forbid": []}, "source": "base"
    })
    monkeypatch.setattr(analyzer, "_base_edges", lambda *_: set())

    report = analyzer.analyze_repository(tmp_path, [_change("src/core.py")], "abcdef1")

    assert report["state"] == "Needs targeted review"
    assert any(item["path"] == "src/service.py" for item in report["impacts"])
    evidence = report["test_evidence"][0]
    assert evidence["tests"] == ["tests/test_core.py"]
    assert evidence["status"] == "existing"
    assert report["missing_tests"] == []


def test_missing_test_is_actionable(tmp_path, monkeypatch):
    _write(tmp_path, "src/orphan.py", "VALUE = 1\n")
    monkeypatch.setattr(analyzer, "load_policy", lambda *_: {
        "analysis": {}, "architecture": {"forbid": []}, "source": "base"
    })
    monkeypatch.setattr(analyzer, "_base_edges", lambda *_: set())
    report = analyzer.analyze_repository(tmp_path, [_change("src/orphan.py")], "abcdef1")
    assert report["state"] == "Missing required evidence"
    assert report["missing_tests"][0]["target"] == "src/orphan.py"


def test_configured_test_mapping_augments_import_mapping(tmp_path, monkeypatch):
    _write(tmp_path, "src/core.py", "VALUE = 1\n")
    _write(tmp_path, "tests/integration/test_core_flow.py", "def test_flow(): pass\n")
    monkeypatch.setattr(analyzer, "load_policy", lambda *_: {
        "analysis": {},
        "architecture": {"forbid": []},
        "tests": {"map": [{"source": "src/**", "tests": ["tests/integration/**"]}]},
        "source": "base",
    })
    monkeypatch.setattr(analyzer, "_base_edges", lambda *_: set())
    report = analyzer.analyze_repository(tmp_path, [_change("src/core.py")], "abcdef1")
    assert report["test_evidence"][0]["tests"] == ["tests/integration/test_core_flow.py"]


def test_architecture_rule_reports_only_new_edge(tmp_path, monkeypatch):
    _write(tmp_path, "src/ui.py", "from src.data import load\n")
    _write(tmp_path, "src/data.py", "def load(): pass\n")
    monkeypatch.setattr(analyzer, "load_policy", lambda *_: {
        "analysis": {},
        "architecture": {
            "forbid": [{"id": "layers", "from": "src/ui.py", "to": "src/data.py", "reason": "Use a service."}]
        },
        "source": "base",
    })
    monkeypatch.setattr(analyzer, "_base_edges", lambda *_: set())
    report = analyzer.analyze_repository(tmp_path, [_change("src/ui.py")], "abcdef1")
    assert report["architecture_violations"][0]["rule_id"] == "layers"

    monkeypatch.setattr(analyzer, "_base_edges", lambda *_: {("src/ui.py", "src/data.py")})
    report = analyzer.analyze_repository(tmp_path, [_change("src/ui.py")], "abcdef1")
    assert report["architecture_violations"] == []


def test_explicit_exception_suppresses_architecture_finding(tmp_path, monkeypatch):
    _write(tmp_path, "src/ui.py", "from src.data import load\n")
    _write(tmp_path, "src/data.py", "def load(): pass\n")
    monkeypatch.setattr(analyzer, "load_policy", lambda *_: {
        "analysis": {},
        "architecture": {
            "forbid": [{"id": "layers", "from": "src/**", "to": "src/data.py"}],
            "exceptions": [{"rule": "layers", "from": "src/ui.py", "to": "src/data.py", "reason": "Migration"}],
        },
        "source": "base",
    })
    monkeypatch.setattr(analyzer, "_base_edges", lambda *_: set())
    report = analyzer.analyze_repository(tmp_path, [_change("src/ui.py")], "abcdef1")
    assert report["architecture_violations"] == []


def test_new_cycle_is_reported_when_policy_enables_it(tmp_path, monkeypatch):
    _write(tmp_path, "src/a.py", "from src.b import value\n")
    _write(tmp_path, "src/b.py", "from src.a import value\n")
    monkeypatch.setattr(analyzer, "load_policy", lambda *_: {
        "analysis": {},
        "architecture": {"forbid": [], "forbid_cycles": True},
        "source": "base",
    })
    monkeypatch.setattr(analyzer, "_base_edges", lambda *_: {("src/b.py", "src/a.py")})
    report = analyzer.analyze_repository(tmp_path, [_change("src/a.py")], "abcdef1")
    assert any(item["rule_id"] == "no-new-cycles" for item in report["architecture_violations"])


def test_deleted_source_marks_analysis_incomplete(tmp_path, monkeypatch):
    monkeypatch.setattr(analyzer, "load_policy", lambda *_: {
        "analysis": {}, "architecture": {"forbid": []}, "source": "base"
    })
    report = analyzer.analyze_repository(tmp_path, [_change("src/deleted.py", "deleted")], "abcdef1")
    assert report["state"] == "Analysis incomplete"
    assert "Deleted source files" in report["incomplete_reasons"][0]


def test_mermaid_includes_changed_node_even_without_indirect_impact():
    diagram = analyzer.build_mermaid({"changed_production_files": ["src/core.py"], "impacts": []})
    assert diagram is not None
    assert "src/core.py" in diagram
    assert "flowchart LR" in diagram
