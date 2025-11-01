# Complete Skill Rotation Fix

## The Problem
After 3 correct answers on a skill, questions would stay on the same skill instead of rotating to the next skill in the learning path.

## Root Causes Identified and Fixed

### 1. **Planner Skip Logic** (engine/planner.py, Fixed in commit ca78014)
**Problem:** When checking for rotation candidates, the planner would return `last_selected_skill` immediately without checking other skills' rotation status.

```python
# OLD (WRONG):
if sid == last_selected:
    return sid  # ← Returned immediately, never checked other skills!
```

**Fix:** Check ALL skills for rotation, only skip selecting the `last_selected` as the rotation TARGET:

```python
# NEW (CORRECT):
# Check all skills for streak >= 3
if streak >= 3:
    # Look for a next skill that has THIS as prerequisite
    # Skip rotating TO last_selected, but DO rotate FROM other skills
    if next_sid == last_selected:
        continue  # ← Don't select same skill we just rotated to
    if prerequisite_met:
        return next_sid  # ← Rotate to new skill
```

### 2. **Hard-Coded Skill IDs in Generators** (engine/templates.py → engine/planner.py, Fixed in commit fb6313c)
**Problem:** Generator functions were hard-coding `skill_id = "quad.identify"` in returned items, even when the planner requested a different skill like `"quad.form.identify.standard"`.

This caused the API to always return items for the same skill, bypassing the planner's rotation logic.

**Fix:** After generation, explicitly set the skill_id to what was requested:

```python
# In generate_adaptive_item():
item = templates.generate_item(skill_id, difficulty, seed=seed)
item["skill_id"] = skill_id  # ← Override hard-coded value
return item
```

### 3. **Prerequisite Mapping** (engine/skills.json, Fixed in commit ca78014)
**Problem:** Advanced skills only had `quad.identify` as a prerequisite, missing `quad.vertex.form`.

This prevented proper progression chains.

**Fix:** Added `quad.vertex.form` to prereqs for skills that follow it:

```json
{
  "id": "quad.factor.a1",
  "prereqs": ["quad.identify", "quad.vertex.form"]  // ← Added
}
```

### 4. **Cache Preservation** (api/app/services/engine_service.py, Fixed in commit d80f3cb)
**Problem:** The `/grade` endpoint saved state without preserving `last_selected_skill`, causing the planner to lose track of which skill was just selected.

**Fix:** Preserve the cache value when saving:

```python
if "last_selected_skill" not in state and user_id in _LAST_SKILL_CACHE:
    state["last_selected_skill"] = _LAST_SKILL_CACHE[user_id]
save_user_state(user_id, state)
```

## Results

**Before:** Q1-3 quad.identify → Q4 quad.vertex.form → Q5-12 stuck on quad.identify (ping-pong)

**After:** Q1-3 quad.identify ✓ → Q4-6 quad.vertex.form ✓ → Q7+ next skill ✓

## Testing
- ✅ Planner correctly identifies rotation candidates
- ✅ Planner skips re-selecting the `last_selected_skill`
- ✅ Generator returns correct skill_id
- ✅ Cache persists across requests
- ✅ Prerequisite chains work correctly
- ✅ End-to-end test: 3 questions per skill, proper progression

## Files Modified
1. `engine/planner.py` - Fixed rotation logic, preserve skill_id in items
2. `engine/skills.json` - Added prerequisite mappings
3. `api/app/services/engine_service.py` - Cache preservation in grade_response

## Commits
- `d80f3cb` - Cache preservation
- `ca78014` - Planner fix + skill hierarchy
- `fb6313c` - Generator skill_id preservation
