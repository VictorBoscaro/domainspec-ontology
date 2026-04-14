"""
Semantic Index — Domain extraction and embedding engine.

Public API for runtime consumption.
"""

__version__ = "2.0.0"

# Core classes
from semantic_index.models import CodeAnchor, DictionaryTerm, OperationalOntologyRegistry
from semantic_index.registry.builder import build_registry
from semantic_index.query.domain_slice import load_domain_slice, list_domains, format_domain_context
from semantic_index.query.vector_search import semantic_search, format_search_results

__all__ = [
    "CodeAnchor",
    "DictionaryTerm",
    "OperationalOntologyRegistry",
    "build_registry",
    "load_domain_slice",
    "list_domains",
    "format_domain_context",
    "semantic_search",
    "format_search_results",
]
