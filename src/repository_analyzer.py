"""Deterministic repository analysis for CodeScope.

The analyzer reads source text and Git objects, but never imports or executes
repository code. Findings are derived from reproducible paths and explicit
repository policy.
"""

from __future__ import annotations

import ast
import fnmatch
import hashlib
import logging
import re
import subprocess
import tomllib
from collections import deque
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

logger = logging.getLogger("codescope.repository_analyzer")

SOURCE_EXTENSIONS = {".py", ".js", ".jsx", ".ts", ".tsx"}
IGNORED_PARTS = {
    ".git", ".venv", "venv", "node_modules", "vendor", "dist", "build",
    ".next", ".pytest_cache", "__pycache__",
}
MAX_SOURCE_FILES = 5_000
MAX_FILE_BYTES = 1_000_000
MAX_IMPACT_DEPTH = 5
_JS_IMPORT_RE = re.compile(
    r"(?:import\s+(?:[^;]*?\s+from\s+)?|export\s+[^;]*?\s+from\s+|require\s*\()"
    r"['\"]([^'\"]+)['\"]"
)


class AnalysisError(Exception):
    """Raised when deterministic analysis cannot safely continue."""


def _posix(path: str | Path) -> str:
    normalized = PurePosixPath(str(path).replace("\\", "/")).as_posix()
    return normalized[2:] if normalized.startswith("./") else normalized


def _finding_id(kind: str, evidence: Iterable[str]) -> str:
    material = f"{kind}|{'|'.join(sorted(evidence))}".encode()
    return hashlib.sha256(material).hexdigest()[:12]


def is_test_file(path: str) -> bool:
    """Return whether a path follows common test naming conventions."""
    p = PurePosixPath(path)
    name = p.name.lower()
    parts = {part.lower() for part in p.parts}
    return (
        "tests" in parts
        or "test" in parts
        or "__tests__" in parts
        or name.startswith("test_")
        or name.endswith("_test.py")
        or any(token in name for token in (".test.", ".spec."))
    )


def discover_source_files(root: Path, ignore_patterns: Iterable[str] = ()) -> list[str]:
    """Discover bounded, supported source files under *root*."""
    result: list[str] = []
    for path in root.rglob("*"):
        if path.is_symlink() or not path.is_file() or path.suffix.lower() not in SOURCE_EXTENSIONS:
            continue
        relative = path.relative_to(root)
        if any(part in IGNORED_PARTS for part in relative.parts):
            continue
        try:
            if path.stat().st_size > MAX_FILE_BYTES:
                continue
        except OSError:
            continue
        normalized = _posix(relative)
        if any(_matches(normalized, pattern) for pattern in ignore_patterns):
            continue
        result.append(normalized)
        if len(result) >= MAX_SOURCE_FILES:
            logger.warning("Source discovery reached the %d file limit", MAX_SOURCE_FILES)
            break
    return sorted(result)


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        logger.warning("Could not read %s: %s", path, exc)
        return None


def _python_module_map(files: Iterable[str]) -> dict[str, str]:
    modules: dict[str, str] = {}
    for path in files:
        if not path.endswith(".py"):
            continue
        p = PurePosixPath(path)
        parts = list(p.with_suffix("").parts)
        if parts[-1] == "__init__":
            parts = parts[:-1]
        if parts:
            modules[".".join(parts)] = path
            if parts[0] in {"src", "lib", "python"} and len(parts) > 1:
                modules[".".join(parts[1:])] = path
    return modules


def _resolve_python_import(
    source: str,
    module: str | None,
    level: int,
    module_map: dict[str, str],
) -> str | None:
    source_parts = list(PurePosixPath(source).with_suffix("").parts[:-1])
    prefix = source_parts[: max(0, len(source_parts) - max(0, level - 1))] if level else []
    requested = prefix + (module.split(".") if module else [])
    for length in range(len(requested), 0, -1):
        candidate = ".".join(requested[:length])
        if candidate in module_map:
            return module_map[candidate]
    return None


def _python_dependencies(
    source: str,
    content: str,
    module_map: dict[str, str],
) -> set[str]:
    try:
        tree = ast.parse(content)
    except (SyntaxError, ValueError):
        return set()
    dependencies: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                target = _resolve_python_import(source, alias.name, 0, module_map)
                if target:
                    dependencies.add(target)
        elif isinstance(node, ast.ImportFrom):
            target = _resolve_python_import(source, node.module, node.level, module_map)
            if target:
                dependencies.add(target)
            for alias in node.names:
                child = ".".join(filter(None, (node.module, alias.name)))
                target = _resolve_python_import(source, child, node.level, module_map)
                if target:
                    dependencies.add(target)
    return dependencies


def _resolve_js_import(source: str, specifier: str, files: set[str]) -> str | None:
    if not specifier.startswith("."):
        return None
    base = PurePosixPath(source).parent.joinpath(specifier)
    candidates = [base]
    candidates.extend(PurePosixPath(f"{base}{ext}") for ext in (".ts", ".tsx", ".js", ".jsx"))
    candidates.extend(base / f"index{ext}" for ext in (".ts", ".tsx", ".js", ".jsx"))
    for candidate in candidates:
        normalized = _posix(candidate)
        while "/../" in normalized or normalized.startswith("../"):
            parts: list[str] = []
            for part in PurePosixPath(normalized).parts:
                if part == ".." and parts:
                    parts.pop()
                elif part != ".":
                    parts.append(part)
            normalized = "/".join(parts)
        if normalized in files:
            return normalized
    return None


def extract_dependencies(
    source: str,
    content: str,
    files: Iterable[str],
) -> set[str]:
    """Extract repository-local dependencies from supported source text."""
    file_set = set(files)
    suffix = PurePosixPath(source).suffix.lower()
    if suffix == ".py":
        return _python_dependencies(source, content, _python_module_map(file_set))
    dependencies: set[str] = set()
    for specifier in _JS_IMPORT_RE.findall(content):
        target = _resolve_js_import(source, specifier, file_set)
        if target:
            dependencies.add(target)
    return dependencies


def build_dependency_graph(root: Path, files: list[str]) -> dict[str, set[str]]:
    """Build an adjacency map where source files point to imported files."""
    graph = {path: set() for path in files}
    for path in files:
        content = _read_text(root / Path(path))
        if content is not None:
            graph[path] = extract_dependencies(path, content, files)
    return graph


def _git_file(root: Path, revision: str, path: str) -> str | None:
    if not revision or not re.fullmatch(r"[0-9a-fA-F]{7,64}", revision):
        return None
    try:
        completed = subprocess.run(
            ["git", "show", f"{revision}:{path}"],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    return completed.stdout if completed.returncode == 0 else None


def _base_edges(
    root: Path,
    base_sha: str,
    changed_sources: set[str],
    files: list[str],
) -> set[tuple[str, str]]:
    edges: set[tuple[str, str]] = set()
    for source in changed_sources:
        content = _git_file(root, base_sha, source)
        if content is not None:
            edges.update((source, target) for target in extract_dependencies(source, content, files))
    return edges


def _reverse_graph(graph: dict[str, set[str]]) -> dict[str, set[str]]:
    reverse = {node: set() for node in graph}
    for source, targets in graph.items():
        for target in targets:
            reverse.setdefault(target, set()).add(source)
    return reverse


def _impact_paths(
    changed: set[str],
    graph: dict[str, set[str]],
    max_depth: int,
) -> dict[str, list[str]]:
    reverse = _reverse_graph(graph)
    found: dict[str, list[str]] = {}
    queue: deque[tuple[str, list[str]]] = deque((path, [path]) for path in sorted(changed))
    visited = set(changed)
    while queue:
        node, path = queue.popleft()
        if len(path) - 1 >= max_depth:
            continue
        for dependent in sorted(reverse.get(node, set())):
            if dependent in visited:
                continue
            visited.add(dependent)
            next_path = [dependent, *path]
            found[dependent] = next_path
            queue.append((dependent, next_path))
    return found


def _tests_for(target: str, graph: dict[str, set[str]], max_depth: int = 3) -> list[str]:
    matches: list[str] = []
    for candidate in graph:
        if not is_test_file(candidate):
            continue
        queue: deque[tuple[str, int]] = deque([(candidate, 0)])
        visited = {candidate}
        while queue:
            node, depth = queue.popleft()
            if target in graph.get(node, set()):
                matches.append(candidate)
                break
            if depth >= max_depth:
                continue
            for dependency in graph.get(node, set()):
                if dependency not in visited:
                    visited.add(dependency)
                    queue.append((dependency, depth + 1))
    return sorted(set(matches))


def _configured_tests_for(
    target: str,
    files: Iterable[str],
    policy: dict[str, Any],
) -> list[str]:
    """Return tests declared by base-branch ``[[tests.map]]`` rules."""
    matches: set[str] = set()
    rules = policy.get("tests", {}).get("map", [])
    if not isinstance(rules, list):
        return []
    for rule in rules:
        if not isinstance(rule, dict) or not _matches(target, str(rule.get("source", ""))):
            continue
        patterns = rule.get("tests", [])
        if isinstance(patterns, str):
            patterns = [patterns]
        if not isinstance(patterns, list):
            continue
        for candidate in files:
            if is_test_file(candidate) and any(
                _matches(candidate, str(pattern)) for pattern in patterns
            ):
                matches.add(candidate)
    return sorted(matches)


def load_policy(root: Path, base_sha: str, config_path: str) -> dict[str, Any]:
    """Load trusted architecture policy from the pull request base revision."""
    normalized = _posix(config_path)
    if PurePosixPath(normalized).is_absolute() or ".." in PurePosixPath(normalized).parts:
        return {
            "analysis": {},
            "architecture": {"forbid": []},
            "source": "invalid",
            "error": "The CodeScope configuration path must stay inside the repository.",
        }
    raw = _git_file(root, base_sha, normalized)
    if raw is None:
        return {"analysis": {}, "architecture": {"forbid": []}, "source": "none"}
    try:
        config = tomllib.loads(raw)
    except tomllib.TOMLDecodeError as exc:
        return {
            "analysis": {},
            "architecture": {"forbid": []},
            "source": "invalid",
            "error": f"Invalid {normalized} on the base revision: {exc}",
        }
    config["source"] = "base"
    return config


def _matches(path: str, pattern: str) -> bool:
    return fnmatch.fnmatch(path, pattern) or PurePosixPath(path).match(pattern)


def _architecture_findings(
    new_edges: set[tuple[str, str]],
    policy: dict[str, Any],
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    architecture = policy.get("architecture", {})
    rules = architecture.get("forbid", [])
    exceptions = architecture.get("exceptions", [])
    if not isinstance(rules, list):
        return findings
    for index, rule in enumerate(rules):
        if not isinstance(rule, dict):
            continue
        source_pattern = str(rule.get("from", ""))
        target_pattern = str(rule.get("to", ""))
        if not source_pattern or not target_pattern:
            continue
        rule_id = str(rule.get("id", f"rule-{index + 1}"))
        for source, target in sorted(new_edges):
            if _matches(source, source_pattern) and _matches(target, target_pattern):
                exempt = False
                if isinstance(exceptions, list):
                    for exception in exceptions:
                        if not isinstance(exception, dict):
                            continue
                        if str(exception.get("rule", "")) not in {"", rule_id}:
                            continue
                        if _matches(source, str(exception.get("from", ""))) and _matches(
                            target, str(exception.get("to", ""))
                        ):
                            exempt = True
                            break
                if exempt:
                    continue
                evidence = [rule_id, source, target]
                findings.append({
                    "id": _finding_id("architecture", evidence),
                    "rule_id": rule_id,
                    "source": source,
                    "target": target,
                    "reason": str(rule.get("reason", "Forbidden dependency")),
                    "evidence": f"`{source}` imports `{target}`",
                })
    return findings


def _find_path(
    graph: dict[str, set[str]],
    start: str,
    target: str,
    max_depth: int = 20,
) -> list[str] | None:
    queue: deque[list[str]] = deque([[start]])
    visited = {start}
    while queue:
        path = queue.popleft()
        if len(path) - 1 >= max_depth:
            continue
        for neighbor in sorted(graph.get(path[-1], set())):
            if neighbor == target:
                return [*path, neighbor]
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append([*path, neighbor])
    return None


def _cycle_findings(
    graph: dict[str, set[str]],
    new_edges: set[tuple[str, str]],
    policy: dict[str, Any],
) -> list[dict[str, Any]]:
    architecture = policy.get("architecture", {})
    if not isinstance(architecture, dict) or not architecture.get("forbid_cycles", False):
        return []
    exceptions = architecture.get("exceptions", [])
    findings: list[dict[str, Any]] = []
    for source, target in sorted(new_edges):
        exempt = False
        if isinstance(exceptions, list):
            for exception in exceptions:
                if not isinstance(exception, dict):
                    continue
                if str(exception.get("rule", "")) not in {"", "no-new-cycles"}:
                    continue
                if _matches(source, str(exception.get("from", ""))) and _matches(
                    target, str(exception.get("to", ""))
                ):
                    exempt = True
                    break
        if exempt:
            continue
        graph_without_edge = {node: set(neighbors) for node, neighbors in graph.items()}
        graph_without_edge.get(source, set()).discard(target)
        return_path = _find_path(graph_without_edge, target, source)
        if not return_path:
            continue
        cycle = [source, *return_path]
        findings.append({
            "id": _finding_id("architecture-cycle", cycle),
            "rule_id": "no-new-cycles",
            "source": source,
            "target": target,
            "reason": "The new dependency closes a cycle between repository modules.",
            "evidence": " -> ".join(f"`{node}`" for node in cycle),
        })
    return findings


def analyze_repository(
    root: Path,
    changed_files: list[dict[str, Any]],
    base_sha: str = "",
    config_path: str = ".codescope.toml",
) -> dict[str, Any]:
    """Return a deterministic, evidence-backed merge-readiness report."""
    root = root.resolve()
    policy = load_policy(root, base_sha, config_path)
    ignore_patterns = policy.get("analysis", {}).get("ignore", [])
    if isinstance(ignore_patterns, str):
        ignore_patterns = [ignore_patterns]
    if not isinstance(ignore_patterns, list):
        ignore_patterns = []
    files = discover_source_files(root, (str(pattern) for pattern in ignore_patterns))
    graph = build_dependency_graph(root, files)
    changed_paths = {_posix(item["path"]) for item in changed_files}
    changed_sources = changed_paths & set(files)
    changed_production = {path for path in changed_sources if not is_test_file(path)}
    changed_tests = {path for path in changed_sources if is_test_file(path)}

    requested_depth = policy.get("analysis", {}).get("max_depth", 2)
    max_depth = max(1, min(MAX_IMPACT_DEPTH, requested_depth if isinstance(requested_depth, int) else 2))

    impact_paths = _impact_paths(changed_production, graph, max_depth)
    impacts = [
        {
            "path": path,
            "kind": "test" if is_test_file(path) else "production",
            "dependency_path": dependency_path,
            "confidence": "high",
        }
        for path, dependency_path in sorted(impact_paths.items())
    ]

    test_evidence: list[dict[str, Any]] = []
    missing_tests: list[dict[str, Any]] = []
    for target in sorted(changed_production):
        mapped = sorted(set(_tests_for(target, graph)) | set(_configured_tests_for(target, files, policy)))
        record = {
            "target": target,
            "tests": mapped,
            "changed_tests": sorted(set(mapped) & changed_tests),
            "status": "changed" if set(mapped) & changed_tests else ("existing" if mapped else "missing"),
        }
        test_evidence.append(record)
        if not mapped:
            evidence = [target, "no-mapped-test"]
            missing_tests.append({
                "id": _finding_id("missing-test", evidence),
                "target": target,
                "evidence": "No supported test file imports this changed source file.",
                "recommendation": f"Add or map a test for `{target}`.",
            })

    head_edges = {(source, target) for source, targets in graph.items() for target in targets}
    base_edges = _base_edges(root, base_sha, changed_sources, files)
    new_edges = {edge for edge in head_edges if edge[0] in changed_sources and edge not in base_edges}
    architecture = [
        *_architecture_findings(new_edges, policy),
        *_cycle_findings(graph, new_edges, policy),
    ]

    incomplete_reasons: list[str] = []
    if len(files) >= MAX_SOURCE_FILES:
        incomplete_reasons.append(f"Source scan reached the {MAX_SOURCE_FILES}-file limit.")
    if policy.get("source") == "invalid":
        incomplete_reasons.append(str(policy.get("error")))
    if not base_sha:
        incomplete_reasons.append("Base revision was unavailable; new-edge checks may be incomplete.")
    deleted_sources = sorted(
        _posix(item["path"])
        for item in changed_files
        if item.get("modification_type") == "deleted"
        and PurePosixPath(str(item.get("path", ""))).suffix.lower() in SOURCE_EXTENSIONS
    )
    if deleted_sources:
        incomplete_reasons.append(
            "Deleted source files are not present in the head checkout; dependent impact may be incomplete: "
            + ", ".join(deleted_sources[:10])
        )

    indirect_production = [item for item in impacts if item["kind"] == "production"]
    if incomplete_reasons:
        state = "Analysis incomplete"
    elif architecture or missing_tests:
        state = "Missing required evidence"
    elif indirect_production:
        state = "Needs targeted review"
    else:
        state = "Ready for review"

    return {
        "state": state,
        "changed_source_files": sorted(changed_sources),
        "changed_production_files": sorted(changed_production),
        "impacts": impacts,
        "test_evidence": test_evidence,
        "missing_tests": missing_tests,
        "architecture_violations": architecture,
        "incomplete_reasons": incomplete_reasons,
        "analysis": {
            "source_files_scanned": len(files),
            "dependency_edges": len(head_edges),
            "max_depth": max_depth,
            "policy_source": policy.get("source", "none"),
            "config_path": _posix(config_path),
        },
        "graph": graph,
    }


def build_mermaid(report: dict[str, Any], limit: int = 18) -> str | None:
    """Render a small deterministic impact diagram from evidence paths."""
    changed = list(report.get("changed_production_files", []))
    paths = [item["dependency_path"] for item in report.get("impacts", [])]
    if not paths and not changed:
        return None
    nodes: list[str] = []
    edges: set[tuple[str, str]] = set()
    for node in changed:
        if node not in nodes and len(nodes) < limit:
            nodes.append(node)
    for path in paths:
        for node in path:
            if node not in nodes and len(nodes) < limit:
                nodes.append(node)
        for source, target in zip(path, path[1:]):
            if source in nodes and target in nodes:
                edges.add((source, target))
    identifiers = {node: f"n{index}" for index, node in enumerate(nodes)}
    lines = ["flowchart LR"]
    changed_set = set(changed)
    for node in nodes:
        label = node.replace('"', "'")
        lines.append(f'  {identifiers[node]}["{label}"]')
    for source, target in sorted(edges):
        lines.append(f"  {identifiers[source]} --> {identifiers[target]}")
    for node in changed_set & set(nodes):
        lines.append(f"  style {identifiers[node]} fill:#dbeafe,stroke:#2563eb,color:#111827")
    return "\n".join(lines)
