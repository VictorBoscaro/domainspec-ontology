"""
vector_search.py — Vector similarity search over semantic index embeddings.

Loads stored vectors from Postgres, embeds the query via Gemini,
computes cosine similarity in Python (no pgvector needed).
Used by the MCP server's semantic_query tool.
"""

from __future__ import annotations

import os
import re
from typing import Any

import numpy as np
import psycopg2
import warnings
import google.generativeai as genai

# Configure API key at module load time
_GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if _GEMINI_API_KEY:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", FutureWarning)
        genai.configure(api_key=_GEMINI_API_KEY)


_TYPE_LINE_RE = re.compile(r"^Type:\s*(\S+)", re.MULTILINE)


def _extract_type(composed_text: str) -> str | None:
    """Pull the `Type: <type>` line out of a composed embedding text.

    Dictionary terms have no type line and return None.
    """
    m = _TYPE_LINE_RE.search(composed_text)
    return m.group(1) if m else None


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity between two vectors."""
    va = np.array(a, dtype=np.float32)
    vb = np.array(b, dtype=np.float32)
    denom = np.linalg.norm(va) * np.linalg.norm(vb)
    if denom == 0:
        return 0.0
    return float(np.dot(va, vb) / denom)


def rank_results(
    query_vector: list[float],
    rows: list[dict[str, Any]],
    top_k: int = 10,
) -> list[dict[str, Any]]:
    """Rank rows by cosine similarity to query_vector, return top_k."""
    scored = []
    for row in rows:
        score = cosine_similarity(query_vector, row["vector"])
        scored.append({**row, "score": score})
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]


def load_vectors_from_db() -> list[dict[str, Any]]:
    """
    Load all embedding rows from Postgres.

    Returns list of dicts with keys: key, composed_text, domain, vector.
    Reads DB credentials from environment (DB_* or POSTGRES_* variables).
    """
    host = os.environ.get("DB_HOST") or os.environ.get("POSTGRES_HOST", "localhost")
    port = int(os.environ.get("DB_PORT") or os.environ.get("POSTGRES_PORT", "5432"))
    dbname = os.environ.get("DB_NAME") or os.environ.get("POSTGRES_DB", "postgres")
    user = os.environ.get("DB_USER") or os.environ.get("POSTGRES_USER", "postgres")
    password = os.environ.get("DB_PASSWORD") or os.environ.get("POSTGRES_PASSWORD")

    if not password:
        raise RuntimeError("DB_PASSWORD or POSTGRES_PASSWORD is required.")

    conn = psycopg2.connect(host=host, port=port, dbname=dbname, user=user, password=password)
    try:
        rows = []
        with conn.cursor() as cur:
            cur.execute("SELECT term, prefix, domain, composed_text, vector FROM embedding_term")
            for term, prefix, domain, text, vector in cur.fetchall():
                rows.append({
                    "key": f"term:{term}",
                    "composed_text": text,
                    "domain": domain,
                    "type": None,
                    "vector": list(vector),
                })
            cur.execute("SELECT symbol, term, file, line, domain, composed_text, vector FROM embedding_anchor")
            for symbol, term, file, line, domain, text, vector in cur.fetchall():
                rows.append({
                    "key": f"anchor:{term}:{symbol}",
                    "composed_text": text,
                    "domain": domain,
                    "type": _extract_type(text),
                    "vector": list(vector),
                })
        return rows
    finally:
        conn.close()


def embed_query(question: str) -> list[float]:
    """Embed a question using Gemini embedding-2-preview (same model as stored vectors)."""
    if not _GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is required for semantic_query.")

    response = genai.embed_content(
        model="models/gemini-embedding-2-preview",
        content=question,
        task_type="RETRIEVAL_QUERY",
    )

    if hasattr(response, "embedding"):
        return list(response.embedding)
    if isinstance(response, dict) and "embedding" in response:
        return list(response["embedding"])
    raise RuntimeError(f"Unexpected Gemini embed response shape: {type(response)}")


def semantic_search(
    question: str,
    top_k: int = 10,
    types: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Full pipeline: embed question → load vectors → rank → return top_k.

    Args:
        question: natural-language query.
        top_k: max results returned.
        types: optional allow-list of taxonomy types (e.g. ["rule", "operation"]).
            When set, dictionary terms (which have no type) are excluded and
            only anchors whose taxonomy type is in the list are ranked.
    """
    query_vector = embed_query(question)
    rows = load_vectors_from_db()
    if types:
        allowed = {t.lower() for t in types}
        rows = [r for r in rows if (r.get("type") or "").lower() in allowed]
    return rank_results(query_vector, rows, top_k=top_k)


def format_search_results(question: str, results: list[dict[str, Any]]) -> str:
    """Format ranked results as agent-readable text."""
    if not results:
        return f"No results found for: {question}"

    lines = [f"SEMANTIC SEARCH: {question}\n"]
    for i, result in enumerate(results, 1):
        key = result.get("key", "")
        score = result.get("score", 0.0)
        text = result.get("composed_text", "")
        domain = result.get("domain", "")

        lines.append(f"{i}. {key} (score: {score:.3f}) [domain: {domain}]")
        lines.append(f"   {text[:150]}...")
        lines.append("")

    return "\n".join(lines)
