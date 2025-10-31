"""
Snapshot normalization utilities for golden tests.

These helpers strip volatile fields and sort/normalize data structures
so that golden comparisons are stable and deterministic.
"""

import copy
import json
import os


def normalize_item_for_snapshot(item: dict) -> dict:
    """
    Strip volatile fields from a generated item and sort for stable comparison.
    
    Removes:
    - item_id (UUID, changes each run)
    - ts, created_at, timestamp (time-dependent)
    - explanation (optional, may vary)
    
    Normalizes:
    - Sorts choices by text for order-independence
    - Removes choice IDs (volatile)
    - Sorts tags_on_select in each choice
    """
    x = copy.deepcopy(item)
    
    # Remove volatile fields
    for k in ["item_id", "ts", "created_at", "timestamp", "explanation"]:
        x.pop(k, None)
    
    # Normalize choices: sort by text, remove volatile IDs, sort tags
    choices = x.get("choices", [])
    for c in choices:
        c.pop("id", None)
        c.pop("created_at", None)
        if isinstance(c.get("tags_on_select"), list):
            c["tags_on_select"] = sorted(c["tags_on_select"])
    
    # Sort choices by text for deterministic comparison
    x["choices"] = sorted(choices, key=lambda c: c.get("text", ""))
    
    return x


def normalize_decision_for_snapshot(decision: dict) -> dict:
    """
    Strip volatile fields from a planner decision.
    
    Removes:
    - ts, created_at (time-dependent)
    - trace_id, request_id (session-specific)
    
    Normalizes:
    - Sorts sources list if present
    """
    x = copy.deepcopy(decision)
    
    # Remove volatile fields
    for k in ["ts", "created_at", "timestamp", "trace_id", "request_id"]:
        x.pop(k, None)
    
    # Sort sources if present
    if isinstance(x.get("sources"), list):
        x["sources"] = sorted(x["sources"])
    
    return x


def normalize_mastery_update_for_snapshot(update: dict) -> dict:
    """
    Normalize a mastery state update.
    
    Removes:
    - ts, updated_at (time-dependent)
    - trace_id
    """
    x = copy.deepcopy(update)
    for k in ["ts", "updated_at", "timestamp", "trace_id"]:
        x.pop(k, None)
    return x


def load_json(path: str) -> dict:
    """Load a JSON file from disk."""
    with open(path, "r") as f:
        return json.load(f)


def save_json(path: str, data: dict, indent: int = 2) -> None:
    """Save a JSON file to disk, creating directories as needed."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=indent)


def compare_snapshots(got: dict, want: dict) -> tuple[bool, str]:
    """
    Compare two snapshots and return (matches, reason).
    
    If they don't match, includes a helpful diff message.
    """
    if got == want:
        return True, ""
    
    # Build a helpful diff message
    reason = "\nSnapshot mismatch:\n"
    reason += f"GOT:\n{json.dumps(got, indent=2)}\n\n"
    reason += f"WANT:\n{json.dumps(want, indent=2)}"
    
    return False, reason
