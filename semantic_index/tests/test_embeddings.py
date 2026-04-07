"""Tests for embeddings/client.py"""

from tools.semantic_index.models import CodeAnchor, DictionaryTerm, OperationalOntologyEdge
from tools.semantic_index.embeddings.client import compose_term_text, compose_anchor_text


def _term(**kwargs) -> DictionaryTerm:
    defaults = dict(
        term="TestTerm", prefix="biz", category="Core",
        description="A test description.", code_equivalent="TestModel",
        source_file="test.md", source_line=1,
    )
    defaults.update(kwargs)
    return DictionaryTerm(**defaults)


def _anchor(**kwargs) -> CodeAnchor:
    defaults = dict(
        symbol="test_fn", kind="function",
        taxonomy_type="rule", file="test.py",
        line=10, description="Does something.",
    )
    defaults.update(kwargs)
    return CodeAnchor(**defaults)


def test_compose_term_text_basic():
    text = compose_term_text(_term())
    assert "Term: TestTerm" in text
    assert "Description: A test description." in text


def test_compose_term_text_no_type_line():
    """Term text should NOT include a Type: line — type belongs on anchors only."""
    text = compose_term_text(_term())
    assert "Type:" not in text


def test_compose_term_text_with_edges():
    term = _term(edges=[
        OperationalOntologyEdge(type="enforces", target="Remessa"),
    ])
    text = compose_term_text(term)
    assert "Edges: enforces -> Remessa" in text


def test_compose_term_text_with_aliases():
    term = _term(aliases_code=["alias1"], aliases_conversation=["alias2"])
    text = compose_term_text(term)
    assert "Aliases: alias1, alias2" in text


def test_compose_anchor_text_uses_taxonomy_type():
    """Anchor text should use taxonomy_type (rule), not kind (function)."""
    anchor = _anchor(taxonomy_type="rule", kind="function")
    text = compose_anchor_text("TestTerm", anchor)
    assert "Type: rule" in text
    assert "Type: function" not in text


def test_compose_anchor_text_fields():
    anchor = _anchor(symbol="my_fn", taxonomy_type="entity", file="path/to/file.py")
    text = compose_anchor_text("MyTerm", anchor)
    assert "Symbol: my_fn" in text
    assert "Term: MyTerm" in text
    assert "Type: entity" in text
    assert "File: path/to/file.py" in text


def test_compose_anchor_text_accepts_code_anchor_not_dict():
    """compose_anchor_text must accept CodeAnchor, not dict."""
    anchor = _anchor()
    # Should not raise — accepts CodeAnchor directly
    text = compose_anchor_text("Term", anchor)
    assert isinstance(text, str)
