# Web Integration Golden Tests

These goldens test the **full learning loop** with guardrails against the 3 bugs:

## 1. `mastery_display_updates.json`
**Bug**: Mastery stuck at 60% on dashboard
**Fix**: Frontend should call `/api/progress` after each grading to get fresh `p_mastery`
**Assertion**: `p_mastery` on dashboard = actual state value (0.65 after +0.05 update)

## 2. `difficulty_progression_with_fallback.json`
**Bug**: Difficulty jumps randomly (hard → easy → hard)
**Fix**: Planner uses `progression = ["easy", "medium", "hard", "hard"]` and goes back on wrong
**Assertion**: Difficulties follow progression array; wrong answer triggers fallback

## 3. `skill_rotation_after_3_correct.json`
**Bug**: Too many questions on same skill
**Fix**: Planner tracks `correct_streak` per skill, rotates after 3 correct to next prereq
**Assertion**: After 3 correct on `quad.identify`, next item is from `quad.vertex.form`

---

## Implementation Tasks

1. **Update `planner.py`**:
   - Track `correct_streak` in state
   - Implement progression array with fallback on wrong
   - Move to next prereq after 3 correct

2. **Update frontend `app/app/page.tsx`**:
   - Call `/api/progress` after each grade response
   - Display fresh `p_mastery` from progress data

3. **Update `grade_response` in `EngineService`**:
   - Update state with attempt count for progression tracking
   - Reset streak on wrong answer
