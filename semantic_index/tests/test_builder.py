"""Tests for registry/builder.py"""

import pytest

from semantic_index.models import DictionaryTerm, CodeAnchor, OperationalOntologyEdge
from semantic_index.extractors.tag_scanner import RawCodeAnchor
from semantic_index.registry.builder import build_registry, OrphanAnchorError


def _term(name: str, prefix: str = "biz", unanchorable: bool = False) -> DictionaryTerm:
    return DictionaryTerm(
        term=name, prefix=prefix, category="Test",
        description="Test description", code_equivalent=name,
        source_file="test.md", source_line=1,
        unanchorable=unanchorable,
    )


def _anchor(term: str, symbol: str = "fn", type_: str = "rule") -> RawCodeAnchor:
    return RawCodeAnchor(
        term=term, prefix="biz", type=type_,
        file="test.py", symbol=symbol, kind="function",
        description="Test", line=1,
    )


def test_build_empty():
    reg = build_registry([], [], strict=False)
    assert reg.meta.total_terms == 0
    assert reg.meta.total_anchors == 0


def test_build_terms_only():
    reg = build_registry([_term("Foo"), _term("Bar")], [], strict=False)
    assert reg.meta.total_terms == 2
    assert reg.meta.total_anchors == 0
    assert reg.meta.unanchored_terms == 2


def test_build_with_anchors():
    terms = [_term("Foo")]
    anchors = [_anchor("Foo", "do_foo", "rule")]
    reg = build_registry(terms, anchors, strict=False)
    assert reg.meta.total_anchors == 1
    assert len(reg.terms["Foo"].anchors) == 1
    assert reg.terms["Foo"].anchors[0].taxonomy_type == "rule"


def test_taxonomy_type_from_raw_anchor():
    terms = [_term("Foo")]
    anchors = [_anchor("Foo", "fn", "operation")]
    reg = build_registry(terms, anchors, strict=False)
    assert reg.terms["Foo"].anchors[0].taxonomy_type == "operation"


def test_orphan_anchor_strict():
    terms = [_term("Foo")]
    anchors = [_anchor("Unknown", "fn")]
    with pytest.raises(OrphanAnchorError) as exc_info:
        build_registry(terms, anchors, strict=True)
    assert len(exc_info.value.orphans) == 1


def test_orphan_anchor_non_strict():
    terms = [_term("Foo")]
    anchors = [_anchor("Unknown", "fn")]
    reg = build_registry(terms, anchors, strict=False)
    assert reg.meta.orphan_anchors == 1


def test_unanchored_by_design():
    terms = [_term("Abstract", unanchorable=True), _term("Concrete")]
    reg = build_registry(terms, [], strict=False)
    assert reg.meta.unanchored_by_design == 1
    assert reg.meta.unanchored_missing_tags == 1


def test_short_name_matching():
    """Tags using 'FIDC' should match 'FIDC (Full Name)'."""
    terms = [_term("FIDC (Full Name)")]
    anchors = [_anchor("FIDC", "fidc_fn")]
    reg = build_registry(terms, anchors, strict=False)
    assert reg.meta.orphan_anchors == 0
    assert len(reg.terms["FIDC (Full Name)"].anchors) == 1
