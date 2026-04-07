"""
models.py — Pydantic schemas for the Operational Ontology Registry

These models define the contract between extractors, validators, embedders,
and any downstream consumers. All pipeline stages produce and consume these
types.

No Django imports. Stdlib + Pydantic only.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


# ─── Building blocks ─────────────────────────────────────────────────────────


class OperationalOntologyEdge(BaseModel):
    """A relationship edge between two dictionary terms (operational ontology level)."""

    type: str = Field(description="Edge type: enforces, contains, produced-by, etc.")
    target: str = Field(description="Target term name in the dictionary")


class CodeAnchor(BaseModel):
    """A code symbol tagged with @biz or @sys that references a dictionary term."""

    symbol: str = Field(description="Function/class/method name")
    kind: str = Field(description="Symbol kind: function, class, method")
    taxonomy_type: str = Field(description="Tag type: rule, entity, operation, etc. (from @biz/@sys tag)")
    file: str = Field(description="Relative file path from repo root")
    line: int = Field(description="Line number in source file")
    description: str = Field(description="Docstring description (without tag lines)")


# ─── Term entry ──────────────────────────────────────────────────────────────


class DictionaryTerm(BaseModel):
    """
    A single term from the unified registry — dictionary definition + code anchors.

    Combines the dictionary extractor output (term metadata) with the tag scanner
    output (code anchors referencing this term).
    """

    term: str = Field(description="Canonical term name (H3 heading from dictionary)")
    prefix: str = Field(description="'biz' or 'sys'")
    category: str = Field(description="H2 section the term belongs to")
    description: str = Field(description="Prose description from dictionary")
    code_equivalent: Optional[str] = Field(
        default=None, description="Primary code symbol name"
    )
    aliases_code: list[str] = Field(
        default_factory=list, description="Known aliases in codebase"
    )
    aliases_conversation: list[str] = Field(
        default_factory=list, description="Known aliases in conversation/docs"
    )
    edges: list[OperationalOntologyEdge] = Field(
        default_factory=list, description="Relationship edges to other terms"
    )
    distinct_from: list[str] = Field(
        default_factory=list, description="Terms this is explicitly not"
    )
    source_file: str = Field(description="Dictionary file path")
    source_line: int = Field(description="Line number of H3 heading")
    unanchorable: bool = Field(
        default=False,
        description="True if this term is abstract/value-object with no taggable symbol",
    )

    # Populated by registry builder after cross-referencing with tag scanner
    anchors: list[CodeAnchor] = Field(
        default_factory=list,
        description="Code anchors referencing this term (from tag scanner)",
    )


# ─── Registry metadata ──────────────────────────────────────────────────────


class RegistryMeta(BaseModel):
    """Aggregate metrics for the unified registry."""

    generated_at: str = Field(description="ISO 8601 timestamp")
    dictionary_biz_version: str = Field(
        default="unknown", description="Version from biz dictionary frontmatter"
    )
    dictionary_sys_version: str = Field(
        default="unknown", description="Version from sys dictionary frontmatter"
    )
    total_terms: int = Field(default=0)
    total_anchors: int = Field(default=0)
    unanchored_terms: int = Field(
        default=0, description="Terms with zero code anchors"
    )
    unanchored_by_design: int = Field(
        default=0, description="Abstract concepts / value-objects (unanchorable=True)"
    )
    unanchored_missing_tags: int = Field(
        default=0, description="Should be tagged but aren't yet"
    )
    orphan_anchors: int = Field(
        default=0, description="Code tags referencing unknown terms (must be 0)"
    )


# ─── Top-level registry ─────────────────────────────────────────────────────


class OperationalOntologyRegistry(BaseModel):
    """
    The operational ontology registry — pipeline output merging dictionaries + code tags.

    Generated as a CI artifact. Not committed to the repo.
    Distinct from the conceptual ontology (vault graph in ontology_nodes/ontology_edges).
    """

    meta: RegistryMeta
    terms: dict[str, DictionaryTerm] = Field(
        default_factory=dict, description="Keyed by canonical term name"
    )
