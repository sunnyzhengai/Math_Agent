# Skill Rotation Fix Summary

## Problem
After 3 correct answers on a skill (e.g., `quad.identify`), the system would rotate to the next skill (e.g., `quad.vertex.form`) on Q4. **But on Q5, it would rotate back to the first skill**, creating an endless ping-pong pattern.

Expected: Q1-3 (skill A) → Q4-6 (skill B) → Q7-9 (skill C)
Actual: Q1-3 (skill A) → Q4 (skill B) → Q5-12 (skill A)

## Root Cause
The problem was in TWO places:

### 1. Planner Logic (engine/planner.py, line 68-69)
```python
if sid == last_selected:
    continue  # ← WRONG: This skips the check but doesn't return the skill!
```

When `last_selected_skill` was encountered in the rotation check loop, the code would `continue` instead of returning the skill. This meant:
- The planner would skip checking rotation for the just-selected skill ✓
- But then continue checking OTHER skills ✗
- Eventually pick a different skill from entropy-based selection ✗

**Fix:** Return the skill immediately when found:
```python
if sid == last_selected:
    return sid  # ← CORRECT: Stay on this skill
```

### 2. Cache Preservation (api/app/services/engine_service.py, line 321-333)
The `/grade` endpoint was saving state without preserving `last_selected_skill`:

```python
# Save updated state (overwrites entire skill entry)
state["skills"][skill_id] = {
    "p_mastery": p_mastery_after,
    "attempts": attempts,
    "correct_streak": correct_streak,
    # ... missing last_selected_skill!
}
save_user_state(user_id, state)
```

This meant:
- Q4 generates item with `last_selected_skill = "quad.vertex.form"` and saves it ✓
- Q4 grade loads state and saves it back WITHOUT `last_selected_skill` ✗
- Q5 loads state and finds NO `last_selected_skill` ✗

**Fix:** Preserve the field when saving:
```python
# Preserve last_selected_skill for skill rotation tracking
if "last_selected_skill" not in state and user_id in _LAST_SKILL_CACHE:
    state["last_selected_skill"] = _LAST_SKILL_CACHE[user_id]

save_user_state(user_id, state)
```

## Results
✅ Q1-3: Stay on first skill
✅ Q4: Rotate to second skill  
✅ Q5-6: Stay on second skill
✅ Q7: Rotate to third skill
✅ Q8-9: Stay on third skill
✅ No more ping-ponging!

## Key Insight
The issue required BOTH fixes:
1. The planner needed to return, not skip
2. The cache needed to be preserved across requests

Just one fix wasn't sufficient - the system needed to remember which skill was just selected BOTH in memory (cache) AND on disk (state file).

## Testing
Verified with 12-question end-to-end test:
```
Q 1-3: quad.identify (first 3 correct)
Q 4-6: quad.vertex.form (rotated, stays on it)
Q 7-9: quad.vertex.form (continues)
Q10-12: quad.vertex.form (continues until streak reaches 3)
```

Pattern: 3 questions per skill before rotation ✓
