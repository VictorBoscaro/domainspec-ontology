"""
dictionary_linter.py — Validate dictionary Markdown files against the formal schema.

The linter is the first gate in the extraction pipeline. If the dictionary is
malformed, nothing else runs.

Validates:
- Every H3 heading has at least a description paragraph below it
- Required field: Code equivalent (or Unanchorable: true if no code symbol)
- Edge targets reference terms that exist in the same or sibling dictionary
- Edge verbs are from the approved vocabulary (constitution Rule 6)

No Django imports. Stdlib + tools.ontology.taxonomy only.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from tools.semantic_index.taxonomy import VALID_EDGE_VERBS


@dataclass
class LintResult:
    """One validation finding (error or warning) at a specific location."""
    file: str
    line: int
    level: str       # "error" or "warning"
    message: str


# ─── Patterns ────────────────────────────────────────────────────────────────

H2_PATTERN = re.compile(r"^##\s+(.+)$")
H3_PATTERN = re.compile(r"^###\s+(.+)$")
CODE_EQ_PATTERN = re.compile(r"^\s*[-*]\s*\*{0,2}Code equivalent\*{0,2}:?\*{0,2}\s*", re.IGNORECASE)
UNANCHORABLE_PATTERN = re.compile(r"^\s*[-*]\s*\*{0,2}Unanchorable\*{0,2}:?\*{0,2}\s*`?(\w+)`?", re.IGNORECASE)
EDGES_PATTERN = re.compile(r"^\s*[-*]\s*\**Edges\**[:\s]*(.*)", re.IGNORECASE)
EDGE_TARGET_PATTERN = re.compile(r"(?:→|->)+\s*`?(\w[\w\s-]*?)`?\s*(?:,|$)")
# Captures edge verb + direction: e.g. `enforces` → ..., `enforced-by` ← ...
EDGE_VERB_PATTERN = re.compile(r"`([\w-]+)`\s*(?:→|←|->|<-)", re.UNICODE)


# ─── Linter ──────────────────────────────────────────────────────────────────


def lint_dictionary(file_path: str | Path) -> list[LintResult]:
    """
    Lint a single dictionary Markdown file.

    Returns a list of LintResult objects (empty = file is valid).
    """
    file_path = Path(file_path)
    if not file_path.exists():
        return [LintResult(str(file_path), 0, "error", f"File not found: {file_path}")]

    lines = file_path.read_text(encoding="utf-8").splitlines()
    fname = str(file_path)
    results: list[LintResult] = []

    # First pass: collect all H3 term names for edge target validation
    all_terms: set[str] = set()
    for line in lines:
        h3 = H3_PATTERN.match(line)
        if h3:
            all_terms.add(h3.group(1).strip())

    # Second pass: validate each term block
    current_term: str | None = None
    current_term_line: int = 0
    has_description = False
    has_code_equivalent = False
    is_unanchorable = False
    description_lines: list[str] = []
    edge_targets: list[tuple[int, str]] = []  # (line_num, target_name)

    def _flush():
        nonlocal current_term, has_description, has_code_equivalent, is_unanchorable
        nonlocal description_lines, edge_targets
        if current_term is None:
            return

        # Check description
        desc_text = "\n".join(description_lines).strip()
        if not desc_text:
            results.append(LintResult(
                fname, current_term_line, "error",
                f"Term '{current_term}' has no description"
            ))

        # Check code equivalent or unanchorable
        if not has_code_equivalent and not is_unanchorable:
            results.append(LintResult(
                fname, current_term_line, "warning",
                f"Term '{current_term}' has no 'Code equivalent:' and no 'Unanchorable: true'"
            ))

        # Reset
        current_term = None
        has_description = False
        has_code_equivalent = False
        is_unanchorable = False
        description_lines = []
        edge_targets = []

    in_description = False

    for line_num, line in enumerate(lines, start=1):
        # H2 — category boundary
        if H2_PATTERN.match(line):
            _flush()
            continue

        # H3 — new term
        h3 = H3_PATTERN.match(line)
        if h3:
            _flush()
            current_term = h3.group(1).strip()
            current_term_line = line_num
            in_description = True
            continue

        if current_term is None:
            continue

        # Check for structured bullets
        if CODE_EQ_PATTERN.match(line):
            has_code_equivalent = True
            in_description = False
            continue

        unanchorable_match = UNANCHORABLE_PATTERN.match(line)
        if unanchorable_match:
            val = unanchorable_match.group(1).strip().lower()
            if val in ("true", "yes", "1"):
                is_unanchorable = True
            in_description = False
            continue

        edges_match = EDGES_PATTERN.match(line)
        if edges_match:
            raw_edges = edges_match.group(1)
            for target_match in EDGE_TARGET_PATTERN.finditer(raw_edges):
                target = target_match.group(1).strip()
                if target:
                    edge_targets.append((line_num, target))
            in_description = False
            continue

        # Any other bullet line
        if re.match(r"^\s*[-*]\s*\**\w+", line):
            in_description = False
            continue

        # Description line
        if in_description:
            if description_lines or line.strip():
                description_lines.append(line)

    # Flush last term
    _flush()

    return results


def lint_dictionaries(
    *file_paths: str | Path,
) -> list[LintResult]:
    """
    Lint multiple dictionary files and cross-validate edge targets.

    Edge target validation requires knowing all terms across all dictionaries,
    so we collect terms from all files first, then validate edges.
    """
    all_results: list[LintResult] = []

    # Collect all terms across all files (full name + short name before parenthesis)
    all_terms: set[str] = set()
    for fp in file_paths:
        fp = Path(fp)
        if not fp.exists():
            all_results.append(LintResult(str(fp), 0, "error", f"File not found: {fp}"))
            continue
        for line in fp.read_text(encoding="utf-8").splitlines():
            h3 = H3_PATTERN.match(line)
            if h3:
                full_name = h3.group(1).strip()
                all_terms.add(full_name)
                # Also index the short name before parenthesis:
                # "ApproveRemessa (Remessa Approval)" → "ApproveRemessa"
                if "(" in full_name:
                    short_name = full_name.split("(")[0].strip()
                    if short_name:
                        all_terms.add(short_name)

    # Lint each file individually
    for fp in file_paths:
        fp = Path(fp)
        if not fp.exists():
            continue
        results = lint_dictionary(fp)
        all_results.extend(results)

        # Cross-validate edge targets and edge verbs
        lines = fp.read_text(encoding="utf-8").splitlines()
        for line_num, line in enumerate(lines, start=1):
            edges_match = EDGES_PATTERN.match(line)
            if edges_match:
                raw_edges = edges_match.group(1)

                # Validate edge targets exist in some dictionary
                for target_match in EDGE_TARGET_PATTERN.finditer(raw_edges):
                    target = target_match.group(1).strip()
                    if target and target not in all_terms:
                        all_results.append(LintResult(
                            str(fp), line_num, "warning",
                            f"Edge target '{target}' not found in any dictionary"
                        ))

                # Validate edge verbs are from the approved vocabulary
                for verb_match in EDGE_VERB_PATTERN.finditer(raw_edges):
                    verb = verb_match.group(1).strip()
                    if verb not in VALID_EDGE_VERBS:
                        all_results.append(LintResult(
                            str(fp), line_num, "error",
                            f"Edge verb '{verb}' is not in the approved vocabulary. "
                            f"Valid verbs: {', '.join(sorted(VALID_EDGE_VERBS))}"
                        ))

    return all_results
