"""
client.py — Gemini Embedding API client and pgvector upsert.

CI-only. Never runs in the pre-commit hook.

Composes rich text for each registry entry, sends to Gemini Embedding API,
and upserts 768-dim vectors into pgvector in the existing Postgres database.

No Django imports. Uses psycopg2 directly for pgvector operations.

See: specs/ontology/docs/data-foundations/discovery-extraction-pipeline.md
"""

from __future__ import annotations

from semantic_index.models import CodeAnchor, DictionaryTerm, OperationalOntologyRegistry


# ─── Text composition ────────────────────────────────────────────────────────


def compose_term_text(term: DictionaryTerm) -> str:
    """
    Compose embedding text for a dictionary term (conceptual anchor).

    No taxonomy type line — a concept has no single type. Its anchors
    carry individual types (rule, entity, etc.).

    Format:
        Term: EligibilityFilter
        Description: A stateless, side-effect-free business rule...
        Edges: enforces -> Remessa, produces -> FilterResult
        Aliases: eligibility_criteria, filter_criteria, filtro de elegibilidade
    """
    parts = [
        f"Term: {term.term}",
        f"Description: {term.description}",
    ]

    if term.edges:
        edge_strs = [f"{e.type} -> {e.target}" for e in term.edges]
        parts.append(f"Edges: {', '.join(edge_strs)}")

    all_aliases = term.aliases_code + term.aliases_conversation
    if all_aliases:
        parts.append(f"Aliases: {', '.join(all_aliases)}")

    return "\n".join(parts)


def compose_anchor_text(term_name: str, anchor: CodeAnchor) -> str:
    """
    Compose embedding text for a tagged code symbol (code anchor).

    Uses taxonomy_type (from code tag), not kind (AST symbol type).

    Format:
        Symbol: evaluate_kit_completion
        Term: KitType
        Type: rule
        File: domains/documents_validation/domain/kit_matching.py
        Description: Evaluate a folder's documents against active KitTypes...
    """
    parts = [
        f"Symbol: {anchor.symbol}",
        f"Term: {term_name}",
        f"Type: {anchor.taxonomy_type}",
        f"File: {anchor.file}",
    ]

    if anchor.description:
        parts.append(f"Description: {anchor.description}")

    return "\n".join(parts)


# ─── Embedding API ───────────────────────────────────────────────────────────


def embed_registry(registry: OperationalOntologyRegistry) -> list[dict]:
    """
    Generate embedding texts for the entire registry.

    Returns a list of dicts with keys:
        - key: unique identifier (term name or term:symbol)
        - text: composed text for embedding
        - source_type: "term" or "anchor"

    The actual API call and pgvector upsert are deferred to the CI runner.
    This function only composes the texts.
    """
    entries: list[dict] = []

    for term_name, term in registry.terms.items():
        # Dictionary term embedding
        entries.append({
            "key": f"term:{term_name}",
            "text": compose_term_text(term),
            "source_type": "term",
        })

        # Code anchor embeddings
        for anchor in term.anchors:
            entries.append({
                "key": f"anchor:{term_name}:{anchor.symbol}",
                "text": compose_anchor_text(term_name, anchor),
                "source_type": "anchor",
            })

    return entries


# ─── pgvector upsert (stub — implemented when Postgres is available) ────────


def upsert_embeddings(entries: list[dict], vectors: list[list[float]]) -> int:
    """
    Upsert embedding vectors into pgvector.

    Stub implementation. The real version will:
    1. Connect to Postgres via psycopg2
    2. CREATE TABLE IF NOT EXISTS operational_ontology_embeddings (
           key TEXT PRIMARY KEY,
           source_type TEXT,
           text TEXT,
           embedding vector(768),
           updated_at TIMESTAMPTZ DEFAULT now()
       )
    3. Upsert each (key, source_type, text, embedding) pair

    Returns the number of rows upserted.
    """
    raise NotImplementedError(
        "pgvector upsert not yet implemented. "
        "This will be implemented when the CI pipeline is set up."
    )
