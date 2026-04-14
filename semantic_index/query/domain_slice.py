"""
domain_slice.py — Load and format a domain slice from spec.yaml.

No DB. No API. Reads domains/spec.yaml directly.
Used by the MCP server's domain_context tool.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_SPEC_PATH = _REPO_ROOT / "domains" / "spec.yaml"

_TYPE_LABELS: dict[str, str] = {
    "operation": "OPERATIONS",
    "query": "QUERIES",
    "entity": "ENTITIES",
    "rule": "RULES",
    "policy": "POLICIES",
    "event": "EVENTS",
    "calculation": "CALCULATIONS",
    "state-machine": "STATE MACHINES",
    "workflow": "WORKFLOWS",
    "value-object": "VALUE OBJECTS",
    "enum": "ENUMS",
    "interface": "INTERFACES",
    "mapping": "MAPPINGS",
}


def load_domain_slice(
    domain: str,
    spec_path: Path = DEFAULT_SPEC_PATH,
) -> list[dict[str, Any]]:
    """Return all concepts for a domain from spec.yaml."""
    raw = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
    concepts = raw.get("concepts", [])
    return [c for c in concepts if c.get("domain") == domain]


def list_domains(
    spec_path: Path = DEFAULT_SPEC_PATH,
) -> dict[str, int]:
    """Return all domains and their anchor counts."""
    raw = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
    counts: dict[str, int] = {}
    for concept in raw.get("concepts", []):
        domain = concept.get("domain", "unknown")
        counts[domain] = counts.get(domain, 0) + 1
    return counts


def format_domain_context(domain: str, anchors: list[dict[str, Any]]) -> str:
    """Format a domain slice as compact, agent-readable text."""
    if not anchors:
        return f"DOMAIN: {domain}\n\nNo concepts found."

    by_type: dict[str, list[dict]] = {}
    for anchor in anchors:
        t = anchor.get("type", "unknown")
        by_type.setdefault(t, []).append(anchor)

    lines = [f"DOMAIN: {domain} ({len(anchors)} concepts)\n"]

    for type_key, label in _TYPE_LABELS.items():
        group = by_type.pop(type_key, [])
        if not group:
            continue
        lines.append(f"{label} ({len(group)})")
        for a in group:
            symbol = a.get("symbol", "")
            file_path = a.get("file", "")
            line_no = a.get("line", "")
            term = a.get("term", "")
            description = a.get("description", "")
            edges = a.get("edges", [])

            lines.append(f"  {symbol}  {file_path}:{line_no}  → {term}")
            if description:
                lines.append(f"    {description}")
            if edges:
                edge_strs = [f"{e['edge_type']}→{e['target']}" for e in edges]
                lines.append(f"    edges: {', '.join(edge_strs)}")
        lines.append("")

    # Catch any types not in _TYPE_LABELS
    for type_key, group in by_type.items():
        lines.append(f"{type_key.upper()} ({len(group)})")
        for a in group:
            symbol = a.get("symbol", "")
            file_path = a.get("file", "")
            line_no = a.get("line", "")
            term = a.get("term", "")
            lines.append(f"  {symbol}  {file_path}:{line_no}  → {term}")
        lines.append("")

    return "\n".join(lines)
