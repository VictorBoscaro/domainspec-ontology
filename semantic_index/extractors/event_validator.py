"""
event_validator.py — Validate dictionary-events.md against EventLog.EventType

Validates that every event referenced in dictionary-events.md:
1. Exists in EventLog.EventType (database source of truth)
2. Is referenced with correct enum name (case-sensitive)

Authority: EventLog.EventType enum in infrastructure/database/models.py

Note: Events are immutable. Even if an event is no longer emitted, it exists
as a historical record and should be referenced in the dictionary with status
annotations (e.g., "deprecated").
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Set


@dataclass
class EventValidationResult:
    """Result of event validation check."""
    file: str
    line: int
    level: str  # "error"
    event_name: str  # The event enum name (e.g., "ACQUISITION_UPLOAD_STARTED")
    message: str


def get_valid_events() -> Set[str]:
    """
    Get all valid event type names from EventLog.EventType enum.

    Returns a set of enum names (e.g., {"ACQUISITION_UPLOAD_STARTED", "TASK_ENQUEUED", ...})

    Authority: infrastructure/database/models.py :: EventLog.EventType

    Raises:
        ImportError: If Django models cannot be imported
    """
    try:
        # Import the enum from Django models
        from infrastructure.database.models import EventLog
        return {event.name for event in EventLog.EventType}
    except ImportError as e:
        raise ImportError(
            "Could not import EventLog.EventType. Ensure Django is configured and "
            "infrastructure/database/models.py is accessible."
        ) from e


# Pattern: - **event_catalog:** `E.SOMETHING` or similar variations
# Matches the Python enum constant name (not the stored string value)
# Flexible pattern to handle markdown variations
EVENT_REFERENCE_PATTERN = re.compile(
    r'event_catalog.*?`E\.([A-Z_0-9]+)`',
    re.IGNORECASE | re.DOTALL
)


def validate_event_dictionary(
    dictionary_events_path: str | Path,
    valid_events: Set[str] | None = None,
) -> list[EventValidationResult]:
    """
    Validate that all event references in dictionary-events.md exist in EventLog.EventType.

    Args:
        dictionary_events_path: Path to dictionary-events.md
        valid_events: Set of valid event enum names. If None, loads from EventLog.EventType

    Returns:
        List of EventValidationResult objects (errors only, empty if all valid)

    Raises:
        ImportError: If EventLog.EventType cannot be imported and valid_events is None
    """
    dictionary_events_path = Path(dictionary_events_path)
    results: list[EventValidationResult] = []

    if not dictionary_events_path.exists():
        return [EventValidationResult(
            str(dictionary_events_path), 0, "error",
            "N/A",
            f"File not found: {dictionary_events_path}"
        )]

    # Load valid events from database
    if valid_events is None:
        try:
            valid_events = get_valid_events()
        except ImportError as e:
            return [EventValidationResult(
                str(dictionary_events_path), 0, "error",
                "N/A",
                str(e)
            )]

    if not valid_events:
        return [EventValidationResult(
            str(dictionary_events_path), 0, "error",
            "N/A",
            "No events found in EventLog.EventType"
        )]

    # Parse dictionary and validate event references
    lines = dictionary_events_path.read_text(encoding="utf-8").splitlines()

    for line_num, line in enumerate(lines, start=1):
        # Look for "- **event_catalog:** `E.XXX_YYY`" patterns
        match = EVENT_REFERENCE_PATTERN.search(line)
        if match:
            event_name = match.group(1).strip()

            # Check if event exists in enum
            if event_name not in valid_events:
                # Show first 5 available events for debugging
                sample_events = sorted(list(valid_events))[:5]
                sample_str = ", ".join(sample_events)
                results.append(EventValidationResult(
                    str(dictionary_events_path),
                    line_num,
                    "error",
                    event_name,
                    f"Event '{event_name}' referenced in dictionary but NOT found in EventLog.EventType\n"
                    f"       Sample available events: {sample_str}...\n"
                    f"       (Total: {len(valid_events)} events in catalog)"
                ))

    return results


def format_validation_error(result: EventValidationResult) -> str:
    """Format an event validation error for display to user."""
    return f"{result.file}:{result.line}\n  {result.level.upper()}: {result.message}"
