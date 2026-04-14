"""
Tests for event_validator.py — validate dictionary-events.md against EventLog.EventType
"""

import pytest
from pathlib import Path
from semantic_index.extractors.event_validator import (
    validate_event_dictionary,
    format_validation_error,
)


def test_valid_event_reference(tmp_path):
    """Test that valid event references pass validation."""
    dict_file = tmp_path / "dictionary-events.md"
    dict_file.write_text("""
#### ACQUISITION_UPLOAD_STARTED
Some description

- **event_catalog:** `E.ACQUISITION_UPLOAD_STARTED`
""")

    valid_events = {"ACQUISITION_UPLOAD_STARTED", "TASK_ENQUEUED"}
    results = validate_event_dictionary(dict_file, valid_events)

    assert len(results) == 0, "Valid event should not produce error"


def test_invalid_event_reference(tmp_path):
    """Test that invalid event references are caught."""
    dict_file = tmp_path / "dictionary-events.md"
    dict_file.write_text("""
#### NONEXISTENT_EVENT
Some description

- **event_catalog:** `E.NONEXISTENT_EVENT`
""")

    valid_events = {"ACQUISITION_UPLOAD_STARTED", "TASK_ENQUEUED"}
    results = validate_event_dictionary(dict_file, valid_events)

    assert len(results) == 1, "Invalid event should produce error"
    assert "NONEXISTENT_EVENT" in results[0].message
    assert results[0].level == "error"
    assert results[0].event_name == "NONEXISTENT_EVENT"


def test_multiple_events_mixed_valid_invalid(tmp_path):
    """Test validation across multiple event entries with mix of valid and invalid."""
    dict_file = tmp_path / "dictionary-events.md"
    dict_file.write_text("""
#### ACQUISITION_UPLOAD_STARTED
- **event_catalog:** `E.ACQUISITION_UPLOAD_STARTED`

#### INVALID_EVENT_ONE
- **event_catalog:** `E.INVALID_EVENT_ONE`

#### ACQUISITION_UPLOAD_COMPLETED
- **event_catalog:** `E.ACQUISITION_UPLOAD_COMPLETED`

#### INVALID_EVENT_TWO
- **event_catalog:** `E.INVALID_EVENT_TWO`
""")

    valid_events = {
        "ACQUISITION_UPLOAD_STARTED",
        "ACQUISITION_UPLOAD_COMPLETED",
        "TASK_ENQUEUED",
    }
    results = validate_event_dictionary(dict_file, valid_events)

    assert len(results) == 2, "Should catch both invalid events"
    assert all(r.level == "error" for r in results)
    invalid_names = {r.event_name for r in results}
    assert invalid_names == {"INVALID_EVENT_ONE", "INVALID_EVENT_TWO"}


def test_case_sensitive_matching(tmp_path):
    """Test that event matching is case-sensitive."""
    dict_file = tmp_path / "dictionary-events.md"
    dict_file.write_text("""
#### Wrong Case
- **event_catalog:** `E.acquisition_upload_started`
""")

    valid_events = {"ACQUISITION_UPLOAD_STARTED"}
    results = validate_event_dictionary(dict_file, valid_events)

    assert len(results) == 1, "Case-sensitive matching should fail for lowercase"
    assert results[0].event_name == "acquisition_upload_started"


def test_multiple_event_references_in_one_line(tmp_path):
    """Test that only the pattern in event_catalog field is matched."""
    dict_file = tmp_path / "dictionary-events.md"
    dict_file.write_text("""
#### ACQUISITION_UPLOAD_STARTED
This mentions E.SOME_RANDOM_EVENT but should only validate event_catalog.

- **event_catalog:** `E.ACQUISITION_UPLOAD_STARTED`
""")

    valid_events = {"ACQUISITION_UPLOAD_STARTED"}
    results = validate_event_dictionary(dict_file, valid_events)

    assert len(results) == 0, "Should only validate event_catalog field, not other mentions"


def test_missing_file(tmp_path):
    """Test handling of missing dictionary file."""
    nonexistent = tmp_path / "nonexistent.md"
    valid_events = {"ACQUISITION_UPLOAD_STARTED"}

    results = validate_event_dictionary(nonexistent, valid_events)

    assert len(results) == 1
    assert results[0].level == "error"
    assert "not found" in results[0].message.lower()


def test_empty_valid_events(tmp_path):
    """Test handling when no valid events are provided."""
    dict_file = tmp_path / "dictionary-events.md"
    dict_file.write_text("#### TEST\n- **event_catalog:** `E.TEST`")

    results = validate_event_dictionary(dict_file, set())

    assert len(results) == 1
    assert results[0].level == "error"
    assert "No events found" in results[0].message


def test_format_validation_error():
    """Test error formatting for display."""
    from semantic_index.extractors.event_validator import EventValidationResult

    result = EventValidationResult(
        file="test.md",
        line=42,
        level="error",
        event_name="TEST_EVENT",
        message="Event not found"
    )

    formatted = format_validation_error(result)
    assert "test.md:42" in formatted
    assert "ERROR" in formatted
    assert "Event not found" in formatted


def test_deprecated_event_still_valid(tmp_path):
    """Test that deprecated events (if still in enum) pass validation."""
    dict_file = tmp_path / "dictionary-events.md"
    dict_file.write_text("""
#### LEGACY_UPLOAD_STARTED
Fired by the old upload system (deprecated as of 2026-04-01).

- **event_catalog:** `E.LEGACY_UPLOAD_STARTED`
- **status:** deprecated
- **reason:** Replaced by ACQUISITION_UPLOAD_STARTED
""")

    # Event exists in enum even if deprecated
    valid_events = {"LEGACY_UPLOAD_STARTED", "ACQUISITION_UPLOAD_STARTED"}
    results = validate_event_dictionary(dict_file, valid_events)

    assert len(results) == 0, "Deprecated events still in enum should pass validation"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
