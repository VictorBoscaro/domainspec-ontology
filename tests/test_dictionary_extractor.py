"""Tests for dictionary_extractor.py"""

import tempfile
import textwrap
from pathlib import Path

from tools.ontology.extractors.dictionary_extractor import extract_terms


def _write_dict(content: str, name: str = "dictionary-business.md") -> Path:
    d = Path(tempfile.mkdtemp())
    f = d / name
    f.write_text(textwrap.dedent(content))
    return f


def test_extract_basic_term():
    f = _write_dict("""\
        ## Core
        ### MyTerm
        A description of my term.
        - **Code equivalent:** `MyModel`
    """)
    terms = extract_terms(f)
    assert len(terms) == 1
    t = terms[0]
    assert t.term == "MyTerm"
    assert t.prefix == "biz"
    assert t.category == "Core"
    assert "description of my term" in t.description
    assert t.code_equivalent == "MyModel"


def test_extract_edges_forward():
    f = _write_dict("""\
        ## Core
        ### MyTerm
        Description.
        - **Code equivalent:** `MyModel`
        - **Edges:** `enforces` → Remessa, `produces` → FilterResult
    """)
    terms = extract_terms(f)
    assert len(terms[0].edges) == 2
    assert terms[0].edges[0].type == "enforces"
    assert terms[0].edges[0].target == "Remessa"
    assert terms[0].edges[1].type == "produces"
    assert terms[0].edges[1].target == "FilterResult"


def test_extract_edges_reverse():
    f = _write_dict("""\
        ## Core
        ### MyTerm
        Description.
        - **Edges:** `contained-by` ← Remessa (grouped into a batch). `enforced-by` ← EligibilityFilter (filter results stored).
    """)
    terms = extract_terms(f)
    assert len(terms[0].edges) == 2
    assert terms[0].edges[0].type == "contained-by"
    assert terms[0].edges[0].target == "Remessa"
    assert terms[0].edges[1].type == "enforced-by"
    assert terms[0].edges[1].target == "EligibilityFilter"


def test_extract_edges_mixed_directions():
    f = _write_dict("""\
        ## Core
        ### MyTerm
        Description.
        - **Edges:** `contains` → Child (forward edge). `contained-by` ← Parent (reverse edge). `produces` → Output (another forward).
    """)
    terms = extract_terms(f)
    assert len(terms[0].edges) == 3
    assert terms[0].edges[0].type == "contains"
    assert terms[0].edges[0].target == "Child"
    assert terms[0].edges[1].type == "contained-by"
    assert terms[0].edges[1].target == "Parent"
    assert terms[0].edges[2].type == "produces"
    assert terms[0].edges[2].target == "Output"


def test_extract_aliases():
    f = _write_dict("""\
        ## Core
        ### MyTerm
        Description.
        - **Code equivalent:** `MyModel`
        - **Aliases in codebase:** `alias_one`, `alias_two`
        - **Aliases in conversation:** `conversational alias`
    """)
    terms = extract_terms(f)
    assert terms[0].aliases_code == ["alias_one", "alias_two"]
    assert terms[0].aliases_conversation == ["conversational alias"]


def test_extract_unanchorable_true():
    f = _write_dict("""\
        ## Core
        ### AbstractConcept
        An abstract financial concept.
        - **Unanchorable:** `true`
    """)
    terms = extract_terms(f)
    assert terms[0].unanchorable is True


def test_extract_unanchorable_defaults_false():
    f = _write_dict("""\
        ## Core
        ### ConcreteTerm
        A concrete term.
        - **Code equivalent:** `ConcreteModel`
    """)
    terms = extract_terms(f)
    assert terms[0].unanchorable is False


def test_extract_prefix_detection():
    biz = _write_dict("## Core\n### Term1\nDesc.\n", name="dictionary-business.md")
    sys = _write_dict("## Core\n### Term2\nDesc.\n", name="dictionary-sys.md")
    assert extract_terms(biz)[0].prefix == "biz"
    assert extract_terms(sys)[0].prefix == "sys"


def test_extract_multiple_terms():
    f = _write_dict("""\
        ## Category A
        ### Term1
        Description one.
        - **Code equivalent:** `Model1`

        ### Term2
        Description two.
        - **Code equivalent:** `Model2`

        ## Category B
        ### Term3
        Description three.
        - **Code equivalent:** `Model3`
    """)
    terms = extract_terms(f)
    assert len(terms) == 3
    assert terms[0].category == "Category A"
    assert terms[2].category == "Category B"


def test_extract_distinct_from():
    f = _write_dict("""\
        ## Core
        ### MyTerm
        Description.
        - **Code equivalent:** `MyModel`
        - **Distinct from:** `OtherTerm`, `AnotherTerm`
    """)
    terms = extract_terms(f)
    assert terms[0].distinct_from == ["OtherTerm", "AnotherTerm"]


def test_extract_no_code_equivalent():
    f = _write_dict("""\
        ## Core
        ### MyTerm
        Description.
    """)
    terms = extract_terms(f)
    assert terms[0].code_equivalent is None


def test_extract_source_line():
    f = _write_dict("""\
        ## Core

        ### FirstTerm
        Desc.

        ### SecondTerm
        Desc.
    """)
    terms = extract_terms(f)
    assert terms[0].source_line == 3
    assert terms[1].source_line == 6


def test_taxonomy_type_bullet_is_ignored():
    """Taxonomy type was removed from dictionary (v0.3.0 decision).
    If a dictionary still has the bullet, it should not affect the output."""
    f = _write_dict("""\
        ## Core
        ### MyTerm
        Description.
        - **Code equivalent:** `MyModel`
        - **Taxonomy type:** `entity`
    """)
    terms = extract_terms(f)
    assert len(terms) == 1
    # DictionaryTerm has no taxonomy_type field — it should not error
    assert not hasattr(terms[0], "taxonomy_type")
    assert terms[0].term == "MyTerm"
