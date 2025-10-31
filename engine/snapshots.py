"""
Snapshot helpers for golden test artifacts.
Converts runtime objects to deterministic, serializable snapshots.
"""

def to_snapshot_item(item: dict) -> dict:
    """
    Convert an item to snapshot form:
    - Remove volatile IDs (shuffle them for reproducibility)
    - Sort choices deterministically
    - Include skill, difficulty, and validation info
    """
    choices_sorted = sorted(
        item.get("choices", []),
        key=lambda c: (c.get("text", ""), c.get("id", ""))
    )
    
    return {
        "skill_id": item.get("skill_id"),
        "stem": item.get("stem"),
        "difficulty": item.get("adaptive_difficulty", item.get("difficulty", "med")),
        "solution": item.get("solution"),
        "rationale": item.get("rationale"),
        "choices": [
            {
                "text": c.get("text"),
                "tags_on_select": c.get("tags_on_select", [])
            }
            for c in choices_sorted
        ],
        "validation": {
            "has_correct": any(t[0] == "correct" for c in choices_sorted for t in [c.get("tags_on_select", [])]),
            "num_choices": len(choices_sorted),
            "no_duplicates": len(set(c.get("text") for c in choices_sorted)) == len(choices_sorted)
        }
    }

def to_snapshot_decision(decision: dict) -> dict:
    """
    Convert a planner decision to snapshot form.
    """
    return {
        "next_skill_id": decision.get("next_skill_id"),
        "next_skill_name": decision.get("next_skill_name"),
        "reason": decision.get("reason"),
        "reason_type": decision.get("reason_type"),
        "difficulty_source": decision.get("difficulty_source"),
        "progression_index": decision.get("progression_index")
    }

def to_snapshot_mastery_update(before: dict, after: dict, correct: bool, tags: list) -> dict:
    """
    Snapshot a mastery edge update.
    """
    return {
        "input": {
            "p_mastery_before": before.get("p_mastery", 0.6),
            "streak_before": before.get("streak", 0),
            "attempts_before": before.get("attempts", 0),
            "correct": correct,
            "tags": tags
        },
        "output": {
            "p_mastery_after": after.get("p_mastery", 0.6),
            "streak_after": after.get("streak", 0),
            "attempts_after": after.get("attempts", 0)
        },
        "deltas": {
            "mastery_delta": after.get("p_mastery", 0.6) - before.get("p_mastery", 0.6),
            "streak_delta": after.get("streak", 0) - before.get("streak", 0)
        }
    }

def to_snapshot_session_transcript(steps: list) -> dict:
    """
    Snapshot a full session transcript (10 steps).
    """
    return {
        "num_steps": len(steps),
        "steps": [
            {
                "step": i + 1,
                "skill_id": step.get("skill_id"),
                "difficulty": step.get("difficulty"),
                "correct": step.get("correct"),
                "mastery_after": step.get("mastery_after"),
                "tags": step.get("tags", [])
            }
            for i, step in enumerate(steps)
        ]
    }
