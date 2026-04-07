"""
Tests for tag_scanner.py

Run with:  pytest tools/ontology/tests/test_tag_scanner.py -v
"""

import tempfile
import textwrap
from pathlib import Path

from tools.semantic_index.extractors.tag_scanner import (
    RawCodeAnchor, ScanError,
    _extract_docstring, _split_docstring,
    scan_file, scan_codebase,
    VALID_TYPES,
)


# ─── Helpers ─────────────────────────────────────────────────────────────────

def make_file(content: str) -> tuple[Path, Path]:
    """Write content to a temp .py file. Returns (file_path, root_dir)."""
    d = tempfile.mkdtemp()
    root = Path(d)
    f = root / "test_module.py"
    f.write_text(textwrap.dedent(content))
    return f, root


def scan(content: str) -> tuple[list[RawCodeAnchor], list[ScanError]]:
    f, root = make_file(content)
    return scan_file(f, root)


# ─── _split_docstring ─────────────────────────────────────────────────────────

def test_split_basic():
    raw = """Evaluate something.

    More detail here.

    @biz: KitType | type: rule
    """
    desc, tags = _split_docstring(raw)
    assert "Evaluate something" in desc
    assert "More detail here" in desc
    assert "@biz" not in desc
    assert len(tags) == 1
    assert tags[0].group(1) == "biz"
    assert tags[0].group(2).strip() == "KitType"
    assert tags[0].group(3).strip() == "rule"


def test_split_no_tag():
    raw = "Just a plain docstring."
    desc, tags = _split_docstring(raw)
    assert desc == "Just a plain docstring."
    assert tags == []


def test_split_dedents_body_indentation():
    """Body lines indented with 4 spaces should be dedented cleanly."""
    raw = """First line.

    Second line indented.
    Third line.

    @biz: Foo | type: entity
    """
    desc, tags = _split_docstring(raw)
    assert not any(line.startswith("    ") for line in desc.splitlines())
    assert len(tags) == 1


def test_split_sys_prefix():
    raw = """A system service.\n\n    @sys: RunFiltersService | type: workflow\n    """
    desc, tags = _split_docstring(raw)
    assert tags[0].group(1) == "sys"
    assert tags[0].group(2).strip() == "RunFiltersService"


def test_split_case_insensitive():
    raw = """Something.\n\n    @BIZ: KitType | TYPE: entity\n    """
    desc, tags = _split_docstring(raw)
    assert len(tags) == 1


# ─── scan_file: happy path ────────────────────────────────────────────────────

def test_scan_function():
    anchors, errors = scan("""\
        def evaluate_kit(kits):
            \"\"\"Evaluate kits against folder.

            Checks each kit in sequence.

            @biz: KitType | type: rule
            \"\"\"
            pass
    """)
    assert len(anchors) == 1
    a = anchors[0]
    assert a.term == "KitType"
    assert a.prefix == "biz"
    assert a.type == "rule"
    assert a.kind == "function"
    assert a.symbol == "evaluate_kit"
    assert "Evaluate kits" in a.description
    assert len(errors) == 0


def test_scan_class():
    anchors, errors = scan("""\
        class KitType:
            \"\"\"A kit configuration entity.

            @biz: KitType | type: entity
            \"\"\"
            pass
    """)
    assert len(anchors) == 1
    assert anchors[0].kind == "class"
    assert anchors[0].type == "entity"
    assert len(errors) == 0


def test_scan_ignores_untagged():
    anchors, errors = scan("""\
        def helper(x):
            \"\"\"Generic utility.\"\"\"
            return x

        def another():
            pass
    """)
    assert anchors == []
    assert errors == []


def test_scan_multiple_terms():
    anchors, errors = scan("""\
        class KitType:
            \"\"\"Entity.\n\n            @biz: KitType | type: entity\n            \"\"\"
            pass

        def evaluate(kits):
            \"\"\"Rule.\n\n            @biz: KitType | type: rule\n            \"\"\"
            pass

        def find_template(f):
            \"\"\"Operation.\n\n            @biz: DocumentTemplate | type: operation\n            \"\"\"
            pass
    """)
    assert len(anchors) == 3
    terms = {a.term for a in anchors}
    assert terms == {"KitType", "DocumentTemplate"}
    assert len(errors) == 0


def test_scan_biz_and_sys():
    anchors, errors = scan("""\
        def biz_fn():
            \"\"\"Business rule.\n\n            @biz: Remessa | type: rule\n            \"\"\"
            pass

        class SysService:
            \"\"\"System workflow.\n\n            @sys: RunFilters | type: workflow\n            \"\"\"
            pass
    """)
    assert len(anchors) == 2
    prefixes = {a.prefix for a in anchors}
    assert prefixes == {"biz", "sys"}


# ─── scan_file: error cases ───────────────────────────────────────────────────

def test_scan_invalid_type():
    anchors, errors = scan("""\
        def fn():
            \"\"\"Does something.\n\n            @biz: Thing | type: helper\n            \"\"\"
            pass
    """)
    assert anchors == []
    assert len(errors) == 1
    assert errors[0].severity == "error"
    assert "helper" in errors[0].error
    assert "Invalid type" in errors[0].error


def test_scan_missing_description_warns():
    anchors, errors = scan("""\
        def fn():
            \"\"\"@biz: Thing | type: query\"\"\"
            pass
    """)
    assert len(anchors) == 1          # still collected
    assert len(errors) == 1
    assert errors[0].severity == "warning"
    assert "no description" in errors[0].error.lower()


def test_scan_syntax_error():
    f, root = make_file("def broken(:\n    pass\n")
    anchors, errors = scan_file(f, root)
    assert anchors == []
    assert len(errors) == 1
    assert errors[0].severity == "warning"
    assert "Syntax error" in errors[0].error


def test_scan_duplicate_anchor():
    anchors, errors = scan("""\
        def fn():
            \"\"\"Does something.

            @biz: Thing | type: query
            @biz: Thing | type: entity
            \"\"\"
            pass
    """)
    # First tag is collected; second is a duplicate error
    assert len(anchors) == 1
    assert any("Duplicate" in e.error for e in errors)


def test_scan_no_docstring_no_tag():
    anchors, errors = scan("""\
        def fn():
            return 42
    """)
    assert anchors == []
    assert errors == []


# ─── scan_codebase ───────────────────────────────────────────────────────────

def test_scan_codebase_finds_tagged_files():
    d = tempfile.mkdtemp()
    root = Path(d)
    (root / "module_a.py").write_text(textwrap.dedent("""\
        def fn():
            \"\"\"Desc.

            @biz: Foo | type: entity
            \"\"\"
            pass
    """))
    (root / "module_b.py").write_text("def plain(): pass\n")

    anchors, errors = scan_codebase(root)
    assert len(anchors) == 1
    assert anchors[0].term == "Foo"


def test_scan_codebase_excludes_tests():
    d = tempfile.mkdtemp()
    root = Path(d)
    src = root / "src"
    src.mkdir()
    (src / "module.py").write_text(textwrap.dedent("""\
        def fn():
            \"\"\"Desc.

            @biz: Foo | type: entity
            \"\"\"
            pass
    """))
    tests_dir = root / "src" / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_mod.py").write_text(textwrap.dedent("""\
        def test_fn():
            \"\"\"Test.

            @biz: Bar | type: rule
            \"\"\"
            pass
    """))

    anchors, _ = scan_codebase(root)
    terms = {a.term for a in anchors}
    assert "Foo" in terms
    assert "Bar" not in terms


# ─── Taxonomy completeness ────────────────────────────────────────────────────

def test_valid_types_count():
    assert len(VALID_TYPES) == 13


def test_all_13_types_scannable():
    """Every valid taxonomy type should be accepted by the scanner."""
    for t in VALID_TYPES:
        safe_type = t.replace("-", "_")
        anchors, errors = scan(f"""\
            def fn_{safe_type}():
                \"\"\"Desc.\\n\\n            @biz: Term | type: {t}\\n            \"\"\"
                pass
        """)
        type_errors = [e for e in errors if e.severity == "error" and "Invalid type" in e.error]
        assert type_errors == [], f"Type '{t}' was incorrectly rejected"
