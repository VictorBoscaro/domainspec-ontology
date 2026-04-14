"""Tests for extractors/dictionary_linter.py"""

import tempfile
import textwrap
from pathlib import Path

from semantic_index.extractors.dictionary_linter import lint_dictionary, lint_dictionaries


def _write(content: str, name: str = "dictionary-business.md") -> str:
    d = Path(tempfile.mkdtemp())
    f = d / name
    f.write_text(textwrap.dedent(content))
    return str(f)


def test_valid_dictionary():
    f = _write("""\
        ## Core
        ### MyTerm
        A valid description.
        - **Code equivalent:** `MyModel`
    """)
    results = lint_dictionary(f)
    assert len(results) == 0


def test_missing_description():
    f = _write("""\
        ## Core
        ### EmptyTerm
        ### NextTerm
        Has a description.
        - **Code equivalent:** `Model`
    """)
    results = lint_dictionary(f)
    errors = [r for r in results if r.level == "error"]
    assert any("no description" in r.message for r in errors)


def test_missing_code_equivalent_warns():
    f = _write("""\
        ## Core
        ### MissingCode
        Has description but no code equivalent.
    """)
    results = lint_dictionary(f)
    warnings = [r for r in results if r.level == "warning"]
    assert any("Code equivalent" in r.message for r in warnings)


def test_unanchorable_suppresses_code_warning():
    f = _write("""\
        ## Core
        ### AbstractTerm
        An abstract concept.
        - **Unanchorable:** `true`
    """)
    results = lint_dictionary(f)
    warnings = [r for r in results if r.level == "warning" and "Code equivalent" in r.message]
    assert len(warnings) == 0


def test_lint_file_not_found():
    results = lint_dictionary("/nonexistent/file.md")
    assert len(results) == 1
    assert results[0].level == "error"
    assert "not found" in results[0].message


def test_lint_dictionaries_cross_validates_edges():
    biz = _write("""\
        ## Core
        ### TermA
        Description.
        - **Code equivalent:** `ModelA`
        - **Edges:** `enforces` → UnknownTerm
    """, name="dictionary-business.md")
    sys = _write("""\
        ## Core
        ### TermB
        Description.
        - **Code equivalent:** `ModelB`
    """, name="dictionary-sys.md")

    results = lint_dictionaries(biz, sys)
    edge_warnings = [r for r in results if "UnknownTerm" in r.message]
    assert len(edge_warnings) > 0


def test_lint_dictionaries_known_edge_target_ok():
    biz = _write("""\
        ## Core
        ### TermA
        Description.
        - **Code equivalent:** `ModelA`
        - **Edges:** `enforces` → TermB
    """, name="dictionary-business.md")
    sys = _write("""\
        ## Core
        ### TermB
        Description.
        - **Code equivalent:** `ModelB`
    """, name="dictionary-sys.md")

    results = lint_dictionaries(biz, sys)
    edge_warnings = [r for r in results if "not found" in r.message]
    assert len(edge_warnings) == 0
