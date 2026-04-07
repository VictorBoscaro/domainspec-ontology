"""Integration tests for the CLI pipeline."""

import json
import tempfile
import textwrap
from pathlib import Path

from tools.semantic_index.extractors.dictionary_extractor import extract_terms
from tools.semantic_index.extractors.tag_scanner import scan_codebase, RawCodeAnchor
from tools.semantic_index.registry.builder import build_registry
from tools.semantic_index.models import OperationalOntologyRegistry


def _setup_mini_project():
    """Create a minimal project with dictionary + tagged code for integration testing."""
    root = Path(tempfile.mkdtemp())

    # Dictionary
    dict_file = root / "dictionary-business.md"
    dict_file.write_text(textwrap.dedent("""\
        ## Core
        ### MyEntity
        A core business entity.
        - **Code equivalent:** `MyEntity`
        - **Edges:** `contains` → MyField

        ### MyField
        A field inside MyEntity.
        - **Unanchorable:** `true`
    """))

    # Tagged code
    code_file = root / "my_module.py"
    code_file.write_text(textwrap.dedent("""\
        class MyEntity:
            \"\"\"The core entity model.

            @biz: MyEntity | type: entity
            \"\"\"
            pass

        def process_entity(data):
            \"\"\"Process the entity.

            @biz: MyEntity | type: operation
            \"\"\"
            pass
    """))

    return root, dict_file


def test_end_to_end_pipeline():
    """Extract terms, scan code, build registry — verify it all connects."""
    root, dict_file = _setup_mini_project()

    # Step 1: Extract dictionary terms
    terms = extract_terms(dict_file)
    assert len(terms) == 2

    # Step 2: Scan codebase
    anchors, errors = scan_codebase(root)
    assert len(anchors) == 2
    assert all(a.term == "MyEntity" for a in anchors)

    # Step 3: Build registry
    registry = build_registry(terms, anchors, strict=True)
    assert registry.meta.total_terms == 2
    assert registry.meta.total_anchors == 2
    assert registry.meta.orphan_anchors == 0
    assert registry.meta.unanchored_by_design == 1  # MyField is unanchorable
    assert registry.meta.unanchored_missing_tags == 0

    # Step 4: Verify the registry can be serialized/deserialized
    json_data = json.dumps(registry.model_dump(), indent=2)
    loaded = OperationalOntologyRegistry(**json.loads(json_data))
    assert loaded.meta.total_terms == 2


def test_lint_gate_blocks_on_bad_dictionary():
    """Verify the lint gate catches errors."""
    from tools.semantic_index.extractors.dictionary_linter import lint_dictionary

    root = Path(tempfile.mkdtemp())
    bad_dict = root / "dictionary-business.md"
    bad_dict.write_text(textwrap.dedent("""\
        ## Core
        ### EmptyTerm
        ### AnotherTerm
        Has a description.
        - **Code equivalent:** `Model`
    """))

    results = lint_dictionary(str(bad_dict))
    errors = [r for r in results if r.level == "error"]
    assert len(errors) > 0  # EmptyTerm has no description
