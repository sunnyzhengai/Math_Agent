# Root Cause Analysis: Skill Rotation Bug

## The Problem
After answering 3 questions correctly on `quad.identify`, the system rotates to `quad.vertex.form` for question 4. **But then questions 5-12 stay on `quad.identify` instead of continuing on `quad.vertex.form`.**

This is **"ping-ponging"** between skills.

## Expected Behavior
```
Q1-3: quad.identify   (3 questions, all correct, streak → 3)
Q4-6: quad.vertex.form (3 questions, all correct, streak → 3)
Q7-9: quad.factor.a1   (3 questions, all correct, streak → 3)
Q10-12: quad.discriminant (next skill in prereq chain)
```

## Actual Behavior
```
Q1-3: quad.identify      ✓
Q4:   quad.vertex.form   ✓ (rotation worked!)
Q5-12: quad.identify     ✗ (ping-pongs back!)
```

## Root Cause

When we inspect the state file (`simple_test.json`), we find:
```json
{
  "quad.identify": {
    "correct_streak": 3,  // ← STILL 3! NEVER RESET!
    ...
  },
  "quad.vertex.form": {
    "correct_streak": 1   // ← Only has 1
    ...
  },
  "last_selected_skill": "quad.vertex.form"  // ← This WAS set
}
```

**Key observation:** `last_selected_skill` IS being set and saved. But `quad.identify.correct_streak` is NOT being reset from 3 to 0.

### Why This Causes Ping-Ponging

The planner's `next_skill()` logic (in `planner.py`):

```python
for s in SKILL_LIST:
    sid = s["id"]
    
    # Skip if it's the last selected skill
    if sid == last_selected:
        continue
    
    # Check if streak >= 3
    if state["skills"][sid].get("correct_streak", 0) >= 3:
        # Rotate away from this skill
        return next_prereq_skill
```

**What happens:**

1. **Q4 request:** `last_selected_skill` is None (first time)
   - Checks `quad.identify`: streak = 3 → Rotates! ✓
   - Sets `last_selected_skill = quad.vertex.form` in memory
   - **ATTEMPTS to reset `quad.identify.correct_streak = 0`**
   - Saves state

2. **Q5 request:** `last_selected_skill = quad.vertex.form` in memory cache
   - But loads fresh state from disk
   - State has `quad.identify.streak = 3` (because reset never persisted!)
   - Planner checks: `sid != last_selected_skill`? → `quad.identify != quad.vertex.form` → YES, check it
   - `quad.identify.streak = 3`? → YES
   - Rotates away... but to where? Back to `quad.identify`! (or another skill)

## Why The Reset Didn't Persist

In `generate_next_item()` (in `engine_service.py`):

```python
skill_id = next_skill(state)  # ← Rotates, resets streak in memory

# Save state changes made by planner
save_user_state(user_id, state)  # ← Should save reset streak

# Cache the selected skill
_LAST_SKILL_CACHE[user_id] = skill_id
```

The code LOOKS correct... but the streak reset happens INSIDE `next_skill()` on the `state` object:

```python
# Inside next_skill() in planner.py:
state["skills"][sid]["correct_streak"] = 0  # Reset in memory object
```

**Hypothesis:** This reset might not be hitting the saved state because:
1. The state object loaded from disk might not have the skill entry initialized properly
2. Or there's a race condition where we're saving an older version of state

## The Simplest Fix

Instead of trying to reset the streak (which isn't persisting), we should:

**Just don't rotate from a skill we just selected.**

```python
# In planner.py next_skill():

last_selected = state.get("last_selected_skill")

for s in SKILL_LIST:
    sid = s["id"]
    
    # DON'T check for rotation on the skill we just rotated TO
    if sid == last_selected:
        continue
    
    # Only check older skills for rotation
    ...
```

Since we're setting `_LAST_SKILL_CACHE` to track the selected skill, and passing it via state, this should prevent:
- Q4 rotates from `quad.identify` to `quad.vertex.form` → sets `last_selected_skill = quad.vertex.form`
- Q5 loads state with `last_selected_skill = quad.vertex.form` → skips it, checks other skills → `quad.identify` has streak=3, but... wait, it should still rotate!

## The ACTUAL Root Cause (Revised)

The problem is **the cache isn't being used to PREVENT rotation on new selections, it's just being set.**

When Q5 runs:
- Load state: `last_selected_skill = quad.vertex.form`
- Check `quad.identify`: streak = 3, and it's NOT `last_selected_skill` → ROTATE
- But we've already rotated to this! We should stay on it!

**The fix is:** When we return a skill from `next_skill()`, remember it and don't rotate FROM it on the NEXT call. The cache is doing this, but the streak reset isn't happening, so old skills keep triggering rotations.

## Solution

**Option A (What we tried):** Reset streak when rotating - FIX the persistence issue
**Option B (Simpler):** Once rotated to a skill, don't rotate FROM it again until it naturally gets rotated away

The simplest is **Option B**: Don't check rotation on the `last_selected_skill`. This is already in code, but the condition `if sid == last_selected: continue` isn't preventing the rotation because the cache isn't being preserved correctly between requests.

**The REAL fix:** Make sure the memory cache `_LAST_SKILL_CACHE` persists the selected skill, and ensure the planner sees it on EVERY subsequent request.

Currently, we're setting `_LAST_SKILL_CACHE[user_id] = skill_id` AFTER calling next_skill(), but the planner has already run by then. We need to ensure the cache is passed TO the planner BEFORE it checks for rotations.
