"""
taxonomy.py — Operational Ontology: canonical tables for types and edges.

Single source of truth for valid taxonomy types and approved edge vocabulary
in the operational ontology layer. Derived from domainspec's 13-type taxonomy
and 12-edge relationship graph, extended with project-specific edges approved
through practice.

Source of authority: docs/vault/constitution/domain-tagging-constitution.md
(Rules 5–6).

Scope: operational ontology only. The conceptual ontology (vault graph in
ontology_nodes/ontology_edges) uses its own edge vocabulary. This module
governs @biz/@sys tags in code and dictionary entries.

Both the tag scanner and the dictionary linter import from here.
No Django imports. Stdlib only.
"""

from __future__ import annotations

# ─── Taxonomy types (Rule 5) ─────────────────────────────────────────────────
# 13 meta-types from domainspec, organized into 4 categories.
# Every @biz/@sys tag must use one of these as its `type:` field.

VALID_TYPES: dict[str, list[str]] = {
    # Structural — What things exist
    "structural": ["entity", "value-object", "enum"],
    # Behavioral — What happens
    "behavioral": ["operation", "query", "calculation", "rule", "policy", "workflow"],
    # Connective — How things communicate
    "connective": ["interface", "event", "mapping"],
    # Lifecycle — How things evolve
    "lifecycle": ["state-machine"],
}

# Flat set for fast lookup
VALID_TYPES_FLAT: frozenset[str] = frozenset(
    t for types in VALID_TYPES.values() for t in types
)


# ─── Edge vocabulary (Rule 6) ────────────────────────────────────────────────
# 12 base forward edges from domainspec + their inverses, plus additional
# project-specific edges approved through practice.
#
# Dictionary entries must use verbs from this vocabulary. The linter blocks
# unapproved verbs at error level.

# Base edges (from domainspec): Forward → Inverse pairs
BASE_EDGES: dict[str, str] = {
    "performs": "performed-by",
    "produces": "produced-by",
    "enforces": "enforced-by",
    "calculates": "calculated-by",
    "transitions": "transitioned-by",
    "exposes": "exposed-by",
    "orchestrates": "orchestrated-by",
    "applies": "applied-by",
    "maps": "mapped-by",
    "contains": "contained-in",
    "queries": "queried-by",
    "emits": "emitted-by",
}

# Additional edges (project-specific, formally approved)
# These 4 edges extend domainspec's 12 base edges for relationships the base set
# cannot express. Each has documented meaning and usage.
#
# Approved additional edges:
# - governs / governed-by: state or status controls behavior of another entity
# - matches / matched-by: term identifies or matches against another
# - implements / implemented-by: concrete entity is realization of abstract concept
# - derives / derived-from: template/definition from which another is generated
ADDITIONAL_EDGES: dict[str, str] = {
    "governs": "governed-by",
    "matches": "matched-by",
    "implements": "implemented-by",
    "derives": "derived-from",
}

# All approved edges: forward + inverse
ALL_EDGES: dict[str, str] = {**BASE_EDGES, **ADDITIONAL_EDGES}

# Flat set of all valid edge verbs (both forward and inverse forms)
VALID_EDGE_VERBS: frozenset[str] = frozenset(
    verb for pair in ALL_EDGES.items() for verb in pair
)
