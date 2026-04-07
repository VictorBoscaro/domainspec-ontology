#!/usr/bin/env python3
"""
tag_scanner.py — Domain Registry Scanner

Scans a Python codebase for @biz and @sys docstring tags and produces
structured RawCodeAnchor records. No external dependencies — stdlib only.

This module provides the core extraction logic. CLI entry points are in cli.py.
The registry builder (registry/builder.py) consumes RawCodeAnchor objects.

See: specs/ontology/docs/data-foundations/discovery-extraction-pipeline.md
"""

import ast
import re
import inspect
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

# ─── Constants ───────────────────────────────────────────────────────────────

TAG_PATTERN = re.compile(
    r"@(biz|sys):\s*([\w][\w\s\-]*?)\s*\|\s*type:\s*([\w][\w\-]*)",
    re.IGNORECASE,
)

VALID_TYPES = {
    # Structural — what things exist
    "entity", "value-object", "enum",
    # Behavioral — what happens
    "operation", "query", "calculation", "rule", "policy", "workflow",
    # Connective — how things communicate
    "interface", "event", "mapping",
    # Lifecycle — how things evolve
    "state-machine",
}


# ─── Data model ──────────────────────────────────────────────────────────────

@dataclass
class RawCodeAnchor:
    """Raw output from the tag scanner — one record per tagged symbol.

    Carries term and prefix because the scanner doesn't know which
    DictionaryTerm this anchor belongs to. The registry builder groups
    these by term and normalizes them into CodeAnchor objects.
    """
    term: str
    prefix: str       # 'biz' or 'sys'
    type: str         # becomes CodeAnchor.taxonomy_type after builder normalization
    file: str         # relative to scan root
    symbol: str
    kind: str         # 'class', 'function', 'method'
    description: str
    line: int


@dataclass
class ScanError:
    file: str
    symbol: str
    line: int
    error: str
    severity: str     # 'error' or 'warning'


# ─── AST extraction ──────────────────────────────────────────────────────────

def _extract_docstring(node) -> Optional[str]:
    """Return the docstring of a class/function AST node, or None."""
    if not node.body:
        return None
    first = node.body[0]
    if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
        val = first.value.value
        if isinstance(val, str):
            return val
    return None


def _split_docstring(raw: str) -> tuple[str, list[re.Match]]:
    """
    Separate description lines from @biz/@sys tag lines.
    Applies textwrap.dedent so indentation artifacts from Python's docstring
    storage don't bleed into the description text.
    Returns (description_text, list_of_tag_matches).
    """
    cleaned = inspect.cleandoc(raw)
    desc_lines = []
    tag_matches = []
    for line in cleaned.splitlines():
        m = TAG_PATTERN.search(line.strip())
        if m:
            tag_matches.append(m)
        else:
            desc_lines.append(line)
    description = "\n".join(desc_lines).strip()
    return description, tag_matches


def scan_file(path: Path, root: Path) -> tuple[list[RawCodeAnchor], list[ScanError]]:
    """
    Parse one Python file and extract all tagged symbols.
    Returns (anchors, errors). Never raises — errors are collected, not thrown.
    """
    anchors: list[RawCodeAnchor] = []
    errors: list[ScanError] = []
    rel = str(path.relative_to(root))

    # Parse
    try:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as e:
        errors.append(ScanError(rel, "<file>", e.lineno or 0,
                                f"Syntax error: {e.msg}", "warning"))
        return anchors, errors
    except Exception as e:
        errors.append(ScanError(rel, "<file>", 0,
                                f"Parse error: {e}", "warning"))
        return anchors, errors

    # Track seen (file, symbol) pairs to detect duplicates
    seen: set[tuple[str, str]] = set()

    # Collect class context to label methods correctly
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue

        kind = "class" if isinstance(node, ast.ClassDef) else "function"
        symbol = node.name
        line = node.lineno

        raw_doc = _extract_docstring(node)
        if not raw_doc:
            continue

        description, tag_matches = _split_docstring(raw_doc)
        if not tag_matches:
            continue

        # Warn on missing description
        if not description:
            errors.append(ScanError(rel, symbol, line,
                                    "Tag present but no description in docstring",
                                    "warning"))

        for m in tag_matches:
            prefix = m.group(1).lower()       # 'biz' or 'sys'
            term   = m.group(2).strip()
            type_  = m.group(3).strip().lower()

            # Validate type
            if type_ not in VALID_TYPES:
                errors.append(ScanError(
                    rel, symbol, line,
                    f"Invalid type '{type_}'. Valid types: {', '.join(sorted(VALID_TYPES))}",
                    "error",
                ))
                continue

            # Detect duplicates
            key = (rel, symbol)
            if key in seen:
                errors.append(ScanError(rel, symbol, line,
                                        "Duplicate anchor: symbol tagged more than once",
                                        "error"))
                continue
            seen.add(key)

            anchors.append(RawCodeAnchor(
                term=term, prefix=prefix, type=type_,
                file=rel, symbol=symbol, kind=kind,
                description=description, line=line,
            ))

    return anchors, errors


# ─── Codebase scanning ──────────────────────────────────────────────────────


def scan_codebase(
    root: Path,
    include: str = "**/*.py",
    exclude_dirs: tuple[str, ...] = ("tests", "__pycache__", ".venv", "venv", "node_modules", "worktrees"),
) -> tuple[list[RawCodeAnchor], list[ScanError]]:
    """
    Scan all Python files under root for @biz/@sys tags.

    Args:
        root: Root directory to scan
        include: Glob pattern for files to include
        exclude_dirs: Directory names to exclude from scanning

    Returns:
        (all_anchors, all_errors) across all scanned files.
    """
    root = Path(root).resolve()
    files = list(root.glob(include))
    if exclude_dirs:
        files = [f for f in files if not any(d in f.parts for d in exclude_dirs)]
    files = sorted(f for f in files if f.is_file())

    all_anchors: list[RawCodeAnchor] = []
    all_errors: list[ScanError] = []

    for f in files:
        anchors, errors = scan_file(f, root)
        all_anchors.extend(anchors)
        all_errors.extend(errors)

    return all_anchors, all_errors
