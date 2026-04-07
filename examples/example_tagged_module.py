"""
example-tagged-module.py

A realistic module from the documents_validation domain, showing proper tagging
in practice. This demonstrates how the @biz tag system works end-to-end.

Each symbol below follows the Domain Tagging Constitution rules:
- Class/function docstrings include a natural language description
- Tags appear as the last line: @biz: <Term> | type: <type>
- All terms exist in the dictionary
- All types are from the 13-type taxonomy
- Infrastructure utilities are not tagged

Run the scanner on this file:
    python tag_scanner.py scan . --include "example-tagged-module.py"

Then inspect the generated domain-registry.yaml to see the output.

File: specs/ontology/docs/domain-tagging/example-tagged-module.py
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


# ─── Enums (vocabulary constraints) ────────────────────────────────────────

class FilterResult(Enum):
    """
    The possible outcomes of evaluating a document against a kit requirement.

    Represents the result of applying an EligibilityFilter to a document in
    a folder. Used to build up aggregate match decisions for KitType evaluation.

    @biz: FilterResult | type: enum
    """
    PASS = "pass"
    FAIL = "fail"
    INCONCLUSIVE = "inconclusive"


# ─── Value Objects (immutable domain data) ──────────────────────────────────

@dataclass(frozen=True)
class KitMatchResult:
    """
    Result of evaluating a folder's documents against a single KitType.

    Contains the kit_id, whether the kit was satisfied (all required docs
    present and matched), and per-document match detail with reasons.
    Immutable — created once per kit evaluation, never modified.

    @biz: KitType | type: value-object
    """
    kit_id: int
    confirmed: bool
    matched_docs: list[str]
    unmatched_required: list[str]


@dataclass(frozen=True)
class CrossCheckOutcome:
    """
    Result of cross-checking OCR-extracted fields against database records.

    Immutable record of a type-aware field-by-field comparison with outcome
    (pass/fail), per-field match detail, and tolerance-aware numeric comparison
    results. Created once, never mutated.

    @biz: CrossCheck | type: value-object
    """
    outcome_pass: bool
    field_comparisons: dict[str, bool]
    tolerance_numeric: float = 0.01


# ─── Entities (objects with identity and lifecycle) ────────────────────────

class KitType:
    """
    A kit configuration — a named set of required document types.

    A folder must satisfy one or more active KitTypes for documents validation
    to pass. Each KitType has a unique identity (kit_id), a list of required
    document type codes, and optional template-specific refinements.

    Entities persist over time; two KitTypes with identical fields are still
    distinct objects if they have different identities.

    @biz: KitType | type: entity
    """

    def __init__(self, kit_id: int, required_doc_types: list[str]):
        self.kit_id = kit_id
        self.required_doc_types = required_doc_types
        self.template_empresa_overrides: dict[int, list[str]] = {}


class DocumentTemplate:
    """
    A registered template pattern for document identification.

    Entities that represent a named document type (invoice, contract, etc.)
    with stored signatures: extracted text, perceptual hash, file size bounds.
    Each template has a unique identity (template_id) and persists across
    document uploads. Templates are immutable after creation.

    @biz: DocumentTemplate | type: entity
    """

    def __init__(self, template_id: int, doc_type: str, text_signature: str):
        self.template_id = template_id
        self.doc_type = doc_type
        self.text_signature = text_signature
        self.phash: Optional[str] = None
        self.size_bounds: tuple[int, int] = (0, float('inf'))


# ─── Rules (constraints that must hold) ──────────────────────────────────────

def evaluate_kit_completion(
    folder_docs: list[dict],
    active_kits: list[KitType],
) -> KitMatchResult:
    """
    Evaluate a folder's documents against active KitTypes using OR logic.

    A business rule that gates the document validation pipeline. Checks whether
    the set of documents in the folder satisfies AT LEAST ONE active kit. For
    each kit, all required doc types must be classified and template-matched
    (or empresa-matched) in the folder. Template-specific requirements take
    precedence over generic doc_type requirements.

    Returns the match result for the first satisfied kit, or failure if none
    are satisfied. This rule must pass before downstream operations proceed.

    @biz: KitType | type: rule
    """
    for kit in active_kits:
        confirmed = all(
            doc_type in [d.get('type') for d in folder_docs]
            for doc_type in kit.required_doc_types
        )
        if confirmed:
            return KitMatchResult(
                kit_id=kit.kit_id,
                confirmed=True,
                matched_docs=[d.get('name', '') for d in folder_docs],
                unmatched_required=[],
            )
    return KitMatchResult(
        kit_id=-1,
        confirmed=False,
        matched_docs=[],
        unmatched_required=active_kits[0].required_doc_types if active_kits else [],
    )


def cross_check_fields(
    extracted_data: dict,
    installment_rows: list[dict],
    field_mappings: list[dict],
) -> CrossCheckOutcome:
    """
    Cross-check OCR-extracted fields against database installment records.

    A domain rule that validates extracted field values by comparing them against
    known database records. Uses type-aware comparison: numeric fields allow ±0.01
    tolerance, dates are normalized before comparison, strings are compared
    case-insensitive with whitespace collapse.

    Implements OR semantics: a field is considered matched if it passes against
    ANY installment row. This rule gates the document validation pipeline — if
    cross-check fails, the document cannot be validated.

    @biz: CrossCheck | type: rule
    """
    comparisons = {}
    for field_name, field_value in extracted_data.items():
        matched = False
        for row in installment_rows:
            if field_name in row:
                # Simplified type-aware comparison
                matched = (
                    str(field_value).strip().lower() ==
                    str(row[field_name]).strip().lower()
                )
                if matched:
                    break
        comparisons[field_name] = matched

    outcome_pass = all(comparisons.values())
    return CrossCheckOutcome(
        outcome_pass=outcome_pass,
        field_comparisons=comparisons,
        tolerance_numeric=0.01,
    )


# ─── Operations (business actions that change state) ──────────────────────

def find_matching_template(
    file_bytes: bytes,
    filename: str,
    doc_type: Optional[str] = None,
) -> DocumentTemplate:
    """
    Find the registered template that best matches the given file.

    A core operation that identifies which DocumentTemplate a newly uploaded
    file matches. Uses two-tier strategy: (1) text similarity (primary signal,
    word-set containment scoring against stored template text), (2) perceptual
    hash (fallback for image-only documents where OCR extraction is not
    possible or unreliable).

    This operation drives document classification in the pipeline. Returns the
    best-matching template, or raises TemplateNotFound if no match exceeds
    confidence threshold.

    @biz: DocumentTemplate | type: operation
    """
    # Stub implementation — real version does OCR + hash computation
    import hashlib
    file_hash = hashlib.md5(file_bytes).hexdigest()
    return DocumentTemplate(
        template_id=1,
        doc_type=doc_type or "unknown",
        text_signature=file_hash,
    )


def register_template(
    template_id: int,
    doc_type: str,
    text_signature: str,
    phash: str,
) -> DocumentTemplate:
    """
    Register a new document template in the system.

    An operation that creates a new DocumentTemplate entity. Validates doc_type
    against allowed values, computes perceptual hash fingerprint from the sample
    file, and persists the template to the registry. Once registered, the
    template is used by find_matching_template to classify incoming documents.

    This operation mutates the system state (adds a new template to the registry).

    @biz: DocumentTemplate | type: operation
    """
    template = DocumentTemplate(template_id, doc_type, text_signature)
    template.phash = phash
    return template


# ─── Queries (reads without side effects) ─────────────────────────────────

def count_kits_by_type(kits: list[KitType]) -> dict[str, int]:
    """
    Count the number of active kits grouped by their primary required doc type.

    A read-only query that analyzes the current set of active KitTypes without
    modifying anything. Returns counts keyed by doc_type. Calling this twice
    produces identical results (idempotent).

    @biz: KitType | type: query
    """
    counts = {}
    for kit in kits:
        primary_type = kit.required_doc_types[0] if kit.required_doc_types else "unknown"
        counts[primary_type] = counts.get(primary_type, 0) + 1
    return counts


def list_unmatched_templates(
    doc_type: str,
    sample_count: int = 10,
) -> list[DocumentTemplate]:
    """
    List templates of a given doc_type that have zero successful matches.

    A read-only query for operational monitoring. Returns templates that were
    registered but never successfully matched an incoming document (potential
    signal that the template is stale or incorrectly configured).

    @biz: DocumentTemplate | type: query
    """
    # Stub — real version queries the database
    return []


# ─── Utilities (not tagged — infrastructure/plumbing) ──────────────────────

def normalize_docstring(text: str) -> str:
    """Remove leading/trailing whitespace and collapse multiple spaces."""
    return ' '.join(text.split())


def safe_divide(a: float, b: float, default: float = 0.0) -> float:
    """Compute a/b safely, returning default if b is zero."""
    return a / b if b != 0 else default


def log_validation_step(step_name: str, result: bool, detail: str = "") -> None:
    """Log a validation checkpoint. Not tagged — infrastructure."""
    status = "PASS" if result else "FAIL"
    print(f"[{step_name}] {status}: {detail}")


# ─── Deliberately untagged (would need dictionary entries) ──────────────────

def process_remessa_upload(
    file_bytes: bytes,
    filename: str,
    upload_metadata: dict,
) -> dict:
    """
    Process an uploaded remessa file through the validation pipeline.

    This is a high-level orchestration function that should be tagged with
    a concept that is not yet in the dictionary. Instead of forcing it under
    an existing term, this function is intentionally left untagged, signaling
    that the vocabulary is incomplete.

    When the missing concept is added to the dictionary, this function can be
    tagged. See Rule 8 of the Domain Tagging Constitution.
    """
    return {"status": "processing"}


# ─── End of example ──────────────────────────────────────────────────────

__all__ = [
    'KitType',
    'DocumentTemplate',
    'FilterResult',
    'KitMatchResult',
    'CrossCheckOutcome',
    'evaluate_kit_completion',
    'cross_check_fields',
    'find_matching_template',
    'register_template',
    'count_kits_by_type',
    'list_unmatched_templates',
]
