"""
mcp_server.py — Semantic Index MCP Server.

Exposes the semantic index as MCP tools for Claude Code.
Run via: python -m semantic_index.mcp_server

Tools:
  list_domains()              — list all domains with anchor counts
  domain_context(domain)      — full domain slice grouped by type, with edges
  semantic_query(question)    — vector similarity search across all embeddings
"""

from pathlib import Path
from dotenv import load_dotenv

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env")
load_dotenv(_PROJECT_ROOT / ".env.local", override=True)

from semantic_index.query.domain_slice import (
    load_domain_slice,
    list_domains as _list_domains,
    format_domain_context,
    DEFAULT_SPEC_PATH,
)
from semantic_index.query.vector_search import (
    semantic_search,
    format_search_results,
)

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("semantic-index")


@mcp.tool()
def list_domains() -> str:
    """
    List all domains in the semantic index with anchor counts.
    Call this first when you don't know which domain to query.
    """
    domains = _list_domains(DEFAULT_SPEC_PATH)
    if not domains:
        return "No domains found in spec.yaml."
    lines = ["DOMAINS IN SEMANTIC INDEX\n"]
    for domain, count in sorted(domains.items()):
        lines.append(f"  {domain}: {count} concepts")
    return "\n".join(lines)


@mcp.tool()
def domain_context(domain: str) -> str:
    """
    Return all tagged code concepts for a domain, grouped by type.
    Includes symbol names, file locations, descriptions, and edges.

    Use when:
    - Editing files in domains/<domain>/
    - Need to understand what business concepts a domain contains
    - Need to see relationships (edges) between operations and events/states

    Args:
        domain: Domain name (e.g. "aquisicao", "estoque", "liquidacao").
                Call list_domains() first if unsure.
    """
    anchors = load_domain_slice(domain, DEFAULT_SPEC_PATH)
    return format_domain_context(domain, anchors)


@mcp.tool()
def semantic_query(
    question: str,
    top_k: int = 10,
    types: list[str] | None = None,
) -> str:
    """
    Search the semantic index by meaning, not keywords.
    Embeds the question and returns the most semantically similar concepts.

    Use when:
    - Asking a business question ("what rule governs contract validation?")
    - You don't know which domain is relevant
    - Keyword search wouldn't find what you're looking for

    Requires GEMINI_API_KEY and DB credentials in environment.

    Args:
        question: Natural language question or concept description.
        top_k: Number of results to return (default 10).
        types: Optional list of taxonomy types to restrict results to
            (e.g. ["rule"], ["operation", "query"]). When set, dictionary
            terms are excluded and only matching code anchors are ranked.
            Common values: rule, entity, value-object, operation, query,
            workflow, calculation, interface, mapping.
            Leave unset on the first call; re-query with a filter if the
            initial results are cluttered with the wrong category.
    """
    results = semantic_search(question, top_k=top_k, types=types)
    return format_search_results(question, results)


if __name__ == "__main__":
    mcp.run()
