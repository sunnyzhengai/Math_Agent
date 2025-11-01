# Bug Fixes Summary

## Overview
Fixed 3 critical bugs reported by the user:
1. ✅ Mastery % frozen at 60% on dashboard
2. ✅ Difficulty level jumps randomly (not following progression)
3. ✅ Too many questions on same skill (no skill rotation)

---

## Fix #1: Mastery Display Frozen at 60%

**Problem**: Dashboard showed mastery stuck at 60%, even though grading showed correct answers increasing it.

**Root Cause**: Frontend was displaying `learner_mastery_before` from the item (frozen at generation time), not the current `p_mastery` from state.

**Solution**: Added `refreshProgress()` in frontend to fetch live progress after each grading via `/api/progress`.

**Files Changed**:
- `web/app/app/page.tsx` (frontend)
  - Added `refreshProgress()` function to call `/api/progress`
  - Call it after grading to update `masteryPercent` from current state
  
**Result**: Dashboard now shows real-time mastery updates! ✅

---

## Fix #2: Difficulty Progression with Fallback

**Problem**: Questions jumped randomly between difficulties (easy → hard → easy), ignoring progression array.

**Root Cause**: The planner used progression array but didn't handle fallback on wrong answers. Also, attempt count just incremented without checking if answers were correct.

**Solution**: 
1. Track progression index in state (`attempts` field)
2. On **correct answer**: increment attempts (move to next progression level)
3. On **wrong answer**: decrement attempts (go back one level)

**Files Changed**:
- `api/app/services/engine_service.py` (backend)
  - In `grade_response()`: decrement `attempts` on wrong answer
  - This creates fallback behavior: progression follows [easy, easy, medium, medium, hard, hard, hard]

**Progression Array Logic**:
```
Initial state: attempts = 0 → progression[0] = "easy"

✅ Correct → attempts = 1 → progression[1] = "easy"
✅ Correct → attempts = 2 → progression[2] = "medium"
❌ Wrong → attempts = 1 (fallback!) → progression[1] = "easy"
✅ Correct → attempts = 2 → progression[2] = "medium"
```

**Result**: Natural difficulty curve with recovery on wrong answers! ✅

---

## Fix #3: Skill Rotation After 3 Correct Answers

**Problem**: Users got stuck answering too many questions on the same skill, leading to boredom and monotony.

**Root Cause**: Planner had no logic to track consecutive correct answers and move to the next skill.

**Solution**:
1. Track `correct_streak` per skill in state
2. Increment on correct, reset on wrong
3. In `next_skill()`: check if any skill has `correct_streak >= 3`
4. If so, find next skill with current skill as prerequisite and move there

**Files Changed**:
- `api/app/services/engine_service.py` (backend)
  - Track `correct_streak` in state
  - Increment on correct, reset on wrong
  
- `engine/planner.py` (backend logic)
  - In `next_skill()`: check for `streak >= 3` first
  - Find skill with current as prerequisite and return it
  
**Skill Rotation Flow**:
```
State: quad.identify with correct_streak = 3

→ Check: Does quad.identify have prereqs to other skills?
  Yes! These skills have it as prereq:
    - quad.vertex.form
    - quad.factor.a1
    - quad.discriminant

→ Pick one (first available) and move there!
```

**Result**: After 3 correct on one skill, automatically move to the next! ✅

---

## Golden Tests Created

All fixes have corresponding golden tests in `tests/goldens/web_integration/`:

1. **`mastery_display_updates.json`**
   - Verifies: mastery updates from 0.6 → 0.65 after correct answer
   - Assertion: progress.p_mastery reflects actual state

2. **`difficulty_progression_with_fallback.json`**
   - Verifies: progression [easy, medium, hard, hard] with fallback
   - Assertion: difficulties follow progression array

3. **`skill_rotation_after_3_correct.json`**
   - Verifies: after 3 correct, move to next skill
   - Assertion: next_skill returns different skill_id

---

## Testing

To verify all fixes work:

```bash
# 1. Backend running
cd quadratics_web/api && uvicorn app.main:app --port 8000

# 2. Frontend running
cd quadratics_web/web && npm run dev

# 3. Test at http://localhost:3000/app
# - Answer 3 questions correctly on same skill → should rotate to next
# - Answer a question wrong → should go back one difficulty level
# - Watch mastery % update in real-time after each submission
```

---

## Commits

- ✅ `f8dd497` - Fix 1: Refresh progress after grading
- ✅ `b108539` - Fix 2 & 3: Add progression fallback & streak tracking
- ✅ `d196f82` - Fix 3 Complete: Skill rotation in planner

---

## Next Steps

If you'd like to extend these fixes:

1. **Add spaced review**: Track `due_at` for reviewing mastered skills
2. **Add misconception routing**: When tags hit threshold, route to remediation skill
3. **Add analytics**: Log attempt details for heatmaps and dashboards
4. **Add adaptive difficulty**: Adjust progression array based on empirical difficulty

