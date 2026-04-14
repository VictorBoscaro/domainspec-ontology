"""
dictionary_extractor.py — Parse dictionary Markdown files into structured DictionaryTerm objects.

Reads dictionary-business.md and dictionary-sys.md, extracts each H3 term
with its metadata (description, code equivalent, aliases, edges),
and returns a list of DictionaryTerm objects.

No Django imports. Stdlib + Pydantic only.

Usage (standalone):
    python -m semantic_index.extractors.dictionary_extractor docs/vault/dictionary-business.md

See: specs/ontology/docs/data-foundations/discovery-extraction-pipeline.md
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from semantic_index.models import DictionaryTerm, OperationalOntologyEdge


# ─── Constants ───────────────────────────────────────────────────────────────

H2_PATTERN = re.compile(r"^##\s+(.+)$")
H3_PATTERN = re.compile(r"^###\s+(.+)$")

# Bullet patterns for structured metadata lines
BULLET_PATTERNS = {
    "code_equivalent": re.compile(
        r"^\s*[-*]\s*\*{0,2}Code equivalent\*{0,2}:?\*{0,2}\s*`?([^`]+)`?", re.IGNORECASE
    ),
    "aliases_code": re.compile(
        r"^\s*[-*]\s*\*{0,2}Aliases in codebase\*{0,2}:?\*{0,2}\s*(.*)", re.IGNORECASE
    ),
    "aliases_conversation": re.compile(
        r"^\s*[-*]\s*\*{0,2}Aliases in conversation\*{0,2}:?\*{0,2}\s*(.*)", re.IGNORECASE
    ),
    "distinct_from": re.compile(
        r"^\s*[-*]\s*\*{0,2}Distinct from\*{0,2}:?\*{0,2}\s*(.*)", re.IGNORECASE
    ),
    "unanchorable": re.compile(
        r"^\s*[-*]\s*\*{0,2}Unanchorable\*{0,2}:?\*{0,2}\s*`?(\w+)`?", re.IGNORECASE
    ),
}

# Edge format: "`type` → Target (desc)." or "`type` ← Target (desc)."
# Each edge segment is separated by ". " on a single line.
# Direction ← means the *target* performs the action on the *source* term.
EDGE_PATTERN = re.compile(
    r"`([\w\s-]+?)`\s*(?:(→|←|->|<-))\s*(\w[\w\s-]*?)(?:\s*\(|`|,|\.|\s*$)"
)


# ─── Parsing helpers ─────────────────────────────────────────────────────────


def _parse_comma_list(raw: str) -> list[str]:
    """Parse a comma-separated list, stripping backticks and whitespace."""
    if not raw or raw.strip() in ("—", "-", "none", "n/a", ""):
        return []
    items = []
    for item in raw.split(","):
        cleaned = item.strip().strip("`").strip()
        if cleaned and cleaned not in ("—", "-", "none"):
            items.append(cleaned)
    return items


def _parse_edges(raw: str) -> list[OperationalOntologyEdge]:
    """Parse edge definitions from a single line or multi-line bullet.

    Handles both → (forward) and ← (reverse) directions.
    For ←, the edge type and target are swapped so the edge always reads
    as "this term --type--> target".
    """
    edges = []
    for match in EDGE_PATTERN.finditer(raw):
        edge_type = match.group(1).strip()
        direction = match.group(2)
        target = match.group(3).strip()
        if not edge_type or not target:
            continue
        if direction in ("←", "<-"):
            # Reverse: "contained-by ← Remessa" means Remessa --contained-by--> this term
            # Store as: this term --contained-by--> Remessa (keep the semantic as-is)
            edges.append(OperationalOntologyEdge(type=edge_type, target=target))
        else:
            edges.append(OperationalOntologyEdge(type=edge_type, target=target))
    return edges


def _detect_prefix(file_path: str) -> str:
    """Detect prefix (biz/sys) from dictionary filename."""
    name = Path(file_path).name.lower()
    if "business" in name or "biz" in name:
        return "biz"
    if "sys" in name or "system" in name:
        return "sys"
    return "unknown"


# ─── Main extractor ─────────────────────────────────────────────────────────


def extract_terms(file_path: str | Path) -> list[DictionaryTerm]:
    """
    Parse a dictionary Markdown file and extract all terms as DictionaryTerm objects.

    Args:
        file_path: Path to dictionary-business.md or dictionary-sys.md

    Returns:
        List of DictionaryTerm objects, one per H3 heading in the dictionary.
    """
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"Dictionary file not found: {file_path}")

    lines = file_path.read_text(encoding="utf-8").splitlines()
    prefix = _detect_prefix(str(file_path))
    source_file = str(file_path)

    terms: list[DictionaryTerm] = []
    current_category: str = ""
    current_term: Optional[dict] = None
    description_lines: list[str] = []
    in_description = False

    def _flush_term():
        """Save the current term being parsed."""
        nonlocal current_term, description_lines, in_description
        if current_term is not None:
            current_term["description"] = "\n".join(description_lines).strip()
            terms.append(DictionaryTerm(**current_term))
        current_term = None
        description_lines = []
        in_description = False

    for line_num, line in enumerate(lines, start=1):
        # H2 = category
        h2_match = H2_PATTERN.match(line)
        if h2_match:
            _flush_term()
            current_category = h2_match.group(1).strip()
            continue

        # H3 = new term
        h3_match = H3_PATTERN.match(line)
        if h3_match:
            _flush_term()
            term_name = h3_match.group(1).strip()
            current_term = {
                "term": term_name,
                "prefix": prefix,
                "category": current_category,
                "description": "",
                "code_equivalent": None,
                "aliases_code": [],
                "aliases_conversation": [],
                "edges": [],
                "distinct_from": [],
                "source_file": source_file,
                "source_line": line_num,
                "unanchorable": False,
            }
            in_description = True
            continue

        # Inside a term block
        if current_term is not None:
            # Try to match structured bullet lines
            matched_bullet = False
            for field_name, pattern in BULLET_PATTERNS.items():
                m = pattern.match(line)
                if m:
                    matched_bullet = True
                    in_description = False
                    value = m.group(1).strip()

                    if field_name == "code_equivalent":
                        current_term["code_equivalent"] = value if value not in ("—", "-", "none") else None
                    elif field_name == "aliases_code":
                        current_term["aliases_code"] = _parse_comma_list(value)
                    elif field_name == "aliases_conversation":
                        current_term["aliases_conversation"] = _parse_comma_list(value)
                    elif field_name == "distinct_from":
                        current_term["distinct_from"] = _parse_comma_list(value)
                    elif field_name == "unanchorable":
                        current_term["unanchorable"] = value.strip().lower() in ("true", "yes", "1")
                    break

            if not matched_bullet and in_description:
                # Skip empty lines at the start of description
                if description_lines or line.strip():
                    description_lines.append(line)

    # Flush last term
    _flush_term()

    return terms


# ─── Entry point for standalone testing ──────────────────────────────────────

if __name__ == "__main__":
    import json
    import sys

    if len(sys.argv) < 2:
        print("Usage: python dictionary_extractor.py <dictionary_file.md>")
        sys.exit(1)

    path = sys.argv[1]
    results = extract_terms(path)
    print(f"Extracted {len(results)} terms from {path}\n")
    for t in results:
        anchored = "unanchorable" if t.unanchorable else f"{len(t.anchors)} anchors"
        print(f"  [{t.prefix}] {t.term} — {anchored}, {len(t.edges)} edges")
    print(f"\nFull JSON:\n{json.dumps([t.model_dump() for t in results], indent=2)}")
