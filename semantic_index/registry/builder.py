"""
builder.py — Unified Registry Builder

Merges dictionary extractor output + tag scanner output into a single
OperationalOntologyRegistry. Performs cross-validation (orphan anchor detection) and
computes coverage metrics.

No Django imports. Stdlib + Pydantic only.

See: specs/ontology/docs/data-foundations/discovery-extraction-pipeline.md
"""

from __future__ import annotations

from datetime import datetime, timezone

from tools.semantic_index.models import (
    CodeAnchor,
    DictionaryTerm,
    RegistryMeta,
    OperationalOntologyRegistry,
)
from tools.semantic_index.extractors.tag_scanner import RawCodeAnchor


# ─── Cross-validation ───────────────────────────────────────────────────────


class OrphanAnchorError(Exception):
    """Raised when a code tag references a term not in the dictionary."""

    def __init__(self, orphans: list[RawCodeAnchor]):
        self.orphans = orphans
        terms = [o.term for o in orphans]
        super().__init__(
            f"Orphan anchors found: {len(orphans)} tags reference unknown terms: {terms}"
        )


# ─── Builder ─────────────────────────────────────────────────────────────────


def build_registry(
    dictionary_terms: list[DictionaryTerm],
    scanner_anchors: list[RawCodeAnchor],
    biz_version: str = "unknown",
    sys_version: str = "unknown",
    strict: bool = True,
) -> OperationalOntologyRegistry:
    """
    Build the unified registry from dictionary terms and scanner anchors.

    Args:
        dictionary_terms: Output from dictionary_extractor.extract_terms()
        scanner_anchors: Output from tag_scanner.scan_codebase() — list of RawCodeAnchor
        biz_version: Version string from business dictionary frontmatter
        sys_version: Version string from system dictionary frontmatter
        strict: If True, raise OrphanAnchorError on orphan anchors. If False, log only.

    Returns:
        OperationalOntologyRegistry with all terms and their matched code anchors.

    Raises:
        OrphanAnchorError: If strict=True and any anchor references an unknown term.
    """
    # Index terms by name for fast lookup
    # Also index by short name (before parenthesis) for matching tags that use
    # the short form, e.g., tag "FIDC" matches term "FIDC (Fundo de Investimento...)"
    terms_by_name: dict[str, DictionaryTerm] = {}
    short_name_index: dict[str, str] = {}  # short_name -> full_name
    for t in dictionary_terms:
        terms_by_name[t.term] = t.model_copy()
        if "(" in t.term:
            short = t.term.split("(")[0].strip()
            short_name_index[short] = t.term

    def _resolve_term(tag_term: str) -> str | None:
        """Resolve a tag's term name to a dictionary term name."""
        if tag_term in terms_by_name:
            return tag_term
        if tag_term in short_name_index:
            return short_name_index[tag_term]
        return None

    # Cross-reference: attach scanner anchors to their dictionary terms
    orphans: list[RawCodeAnchor] = []

    for raw in scanner_anchors:
        resolved = _resolve_term(raw.term)
        if resolved is None:
            orphans.append(raw)
            continue

        anchor = CodeAnchor(
            symbol=raw.symbol,
            kind=raw.kind,
            taxonomy_type=raw.type,
            file=raw.file,
            line=raw.line,
            description=raw.description,
        )
        terms_by_name[resolved].anchors.append(anchor)

    # Fail on orphans if strict
    if orphans and strict:
        raise OrphanAnchorError(orphans)

    # Enrich edges with target_prefix (auto-derived from which dictionary the target lives in)
    for term in terms_by_name.values():
        for edge in term.edges:
            resolved_target = _resolve_term(edge.target)
            if resolved_target and resolved_target in terms_by_name:
                edge.target_prefix = terms_by_name[resolved_target].prefix

    # Compute metrics
    total_anchors = sum(len(t.anchors) for t in terms_by_name.values())
    unanchored = [t for t in terms_by_name.values() if len(t.anchors) == 0]
    unanchored_by_design = [t for t in unanchored if t.unanchorable]
    unanchored_missing = [t for t in unanchored if not t.unanchorable]

    meta = RegistryMeta(
        generated_at=datetime.now(timezone.utc).isoformat(),
        dictionary_biz_version=biz_version,
        dictionary_sys_version=sys_version,
        total_terms=len(terms_by_name),
        total_anchors=total_anchors,
        unanchored_terms=len(unanchored),
        unanchored_by_design=len(unanchored_by_design),
        unanchored_missing_tags=len(unanchored_missing),
        orphan_anchors=len(orphans),
    )

    return OperationalOntologyRegistry(meta=meta, terms=terms_by_name)
