# Step 2: Update Mastery on the Edge - Implementation Complete ✅

## The Problem Solved

Previously, mastery was updated on the progress **nodes**. Now it's updated directly on the **relationship edge** (`HAS_PROGRESS`), which is:
- **Faster** to query (edge properties are indexed)
- **Atomic** (no separate updates)
- **Simpler** (one Cypher operation)
- **Observable** (easy to trace mastery changes)

---

## What Changed

### Old Approach (Nodes)
```cypher
// Had to MATCH then SET separately
MATCH (user)-[prog:HAS_PROGRESS]->(skill)
SET prog.p_mastery = ...  // Old value + delta
```

### New Approach (Atomic Edge Update)
```cypher
MATCH (user), (skill)
MERGE (user)-[r:HAS_PROGRESS]->(skill)
  ON CREATE SET r.p_mastery = 0.6, r.seen = 0, ...
SET r.seen = r.seen + 1,
    r.p_mastery = apoc.number.min(1.0, 
                    apoc.number.max(0.0,
                      r.p_mastery + CASE WHEN $correct THEN 0.08 ELSE -0.12 END
                    ))
RETURN r.p_mastery, r.streak
```

**Key Improvements:**
1. ✅ **MERGE** ensures relationship exists (creates if needed)
2. ✅ **ON CREATE** initializes new relationships at 0.6 mastery
3. ✅ **apoc.number.min/max** bounds mastery to [0.0, 1.0]
4. ✅ **One-step update** (no separate computation)
5. ✅ **Atomic transaction** (all-or-nothing)

---

## The Mastery Update Formula

### Simple Stochastic Update (Current)

```
p_mastery_new = clamp(p_mastery_old + delta, 0.0, 1.0)

Where:
  delta = +0.08 if correct (reward)
  delta = -0.12 if wrong   (penalty)
  clamp(x, 0.0, 1.0) = max(0.0, min(1.0, x))
```

**Why this works:**
- Asymmetric deltas (win: 0.08, loss: 0.12) → slower learning, more caution
- Bounded [0.0, 1.0] → always valid probability
- Simple & observable → easy to debug
- Sufficient for MVP

### Future: Bayesian Knowledge Tracing (BKT)

When ready to upgrade, you can swap in:
```
p_mastery_new = p(T) + (1 - p(T)) * (1 - slip) * correct
              + p(T) * guess * !correct
```

Where:
- `p(T)` = current mastery
- `slip` = P(wrong | mastered)
- `guess` = P(right | not mastered)

---

## Neo4j Graph Schema

### HAS_PROGRESS Relationship

```cypher
(user:User)-[r:HAS_PROGRESS]->(skill:Skill)

Properties:
  r.p_mastery  (float 0.0-1.0)      // Probability of mastery
  r.seen       (int)                // Total attempts
  r.correct    (int)                // Correct attempts
  r.streak     (int)                // Current win streak
  r.last       (datetime)           // Last attempt time
```

### Example State After 5 Attempts

```
Julia's progress on "Factoring (a=1)":

Initial (first question):
  p_mastery: 0.6   (default)
  seen: 0, correct: 0, streak: 0

After Q1 (✓ correct):
  p_mastery: 0.68  (0.6 + 0.08)
  seen: 1, correct: 1, streak: 1

After Q2 (✓ correct):
  p_mastery: 0.76  (0.68 + 0.08)
  seen: 2, correct: 2, streak: 2

After Q3 (✗ wrong):
  p_mastery: 0.64  (0.76 - 0.12)
  seen: 3, correct: 2, streak: 0

After Q4 (✓ correct):
  p_mastery: 0.72  (0.64 + 0.08)
  seen: 4, correct: 3, streak: 1

After Q5 (✓ correct):
  p_mastery: 0.80  (0.72 + 0.08)
  seen: 5, correct: 4, streak: 2
```

---

## Implementation Details

### Code Location
**File:** `engine/neo4j_sync.py`
**Method:** `update_progress()` (lines 108-183)

### The Cypher Query (Annotated)

```cypher
// 1. Get user and skill nodes
MATCH (user:User {name: $user}), (skill:Skill {id: $skill_id})

// 2. MERGE the relationship (create if doesn't exist)
MERGE (user)-[r:HAS_PROGRESS]->(skill)

// 3. Initialize NEW relationships
ON CREATE SET r.p_mastery = 0.6,    // Start at 60% mastery
              r.seen = 0,            // No attempts yet
              r.correct = 0,         // No correct answers
              r.streak = 0,          // No streak
              r.last = datetime()    // Timestamp

// 4. Update EXISTING relationships
SET r.seen = r.seen + 1,                    // Increment attempts

    r.correct = r.correct + CASE 
      WHEN $correct THEN 1 
      ELSE 0 
    END,                                    // Count correct answers

    r.streak = CASE 
      WHEN $correct THEN r.streak + 1       // Extend streak on win
      ELSE 0                                 // Reset streak on loss
    END,

    r.p_mastery = apoc.number.min(1.0,      // Cap at 1.0
                    apoc.number.max(0.0,    // Floor at 0.0
                      r.p_mastery + CASE 
                        WHEN $correct THEN $delta_win      // +0.08 on win
                        ELSE -$delta_loss                  // -0.12 on loss
                      END
                    )),

    r.last = datetime()                     // Update timestamp

// 5. Return new state
RETURN {
  skill_id: skill.id,
  skill_name: skill.name,
  p_mastery: r.p_mastery,
  seen: r.seen,
  correct: r.correct,
  streak: r.streak
} AS result
```

---

## Integration with Streamlit

In `app.py`, the flow is:

```python
# 1. Grade the answer
result = grade(item, choice)
correct, tags, chosen_text, score = result

# 2. Log the attempt (Step 1)
attempt_log = log_attempt_to_neo4j(
    user="julia",
    skill_id=item["skill_id"],
    item_id=item["id"],
    correct=correct,
    tags=tags,
    time_ms=time_ms
)

# 3. Update mastery on the edge (Step 2) ← YOU ARE HERE
neo_result = sync_to_neo4j(
    user="julia",
    skill_id=item["skill_id"],
    correct=correct,
    tags=tags
)

# 4. Display updated stats
st.metric(
    "Neo4j Mastery",
    f"{neo_result['progress']['p_mastery']:.0%}",
    f"{neo_result['progress']['seen']} attempts"
)
```

---

## Querying the Updated State

### Get current mastery for all skills
```cypher
MATCH (u:User {name: "Julia"})-[r:HAS_PROGRESS]->(s:Skill)
RETURN s.name, 
       r.p_mastery, 
       r.seen, 
       r.correct,
       round(100.0 * r.correct / r.seen) AS accuracy
ORDER BY r.p_mastery DESC
```

### Get skills over/under threshold
```cypher
MATCH (u:User {name: "Julia"})-[r:HAS_PROGRESS]->(s:Skill)
WITH r, s,
     CASE 
       WHEN r.p_mastery >= 0.9 THEN "mastered"
       WHEN r.p_mastery >= 0.5 THEN "practicing"
       ELSE "struggling"
     END AS level
RETURN level, count(*) AS count
```

### Get current streak leaders
```cypher
MATCH (u:User {name: "Julia"})-[r:HAS_PROGRESS]->(s:Skill)
WHERE r.streak > 0
RETURN s.name, r.streak
ORDER BY r.streak DESC
LIMIT 5
```

### Timeline of mastery changes
```cypher
MATCH (u:User {name: "Julia"})-[:MADE_ATTEMPT]->(a:Attempt)-[:ASSESSED]->(s:Skill {id: "quad.factor.a1"})
RETURN a.ts, a.correct, a.tags
ORDER BY a.ts
// Then calculate mastery progression using these attempts
```

---

## Why This Design?

### ✅ Edge Properties are Query-Optimal
- **Fast lookups:** `(user)-[HAS_PROGRESS]->(skill)` is a single traversal
- **Direct access:** No need to join to node properties
- **Indexed:** Most graph databases index relationship properties

### ✅ Atomic Updates Prevent Race Conditions
- **One transaction:** MERGE + SET is atomic
- **No interleaving:** Concurrent requests don't corrupt state
- **Consistent:** Always read-after-write is correct

### ✅ Simple, Observable Formula
- **Understandable:** Easy to explain to non-technical folks
- **Debuggable:** Can trace each +0.08 or -0.12 in logs
- **Tunable:** Can adjust delta_win/delta_loss without code changes

### ✅ Ready for Future Upgrades
- **Backward compatible:** Extra fields (slip, guess) can coexist
- **Easy migration:** Just change the SET clause for BKT
- **Non-breaking:** Old queries still work

---

## Comparison: Before vs After

### Before (Separate Node Updates)
```
Julia answers Q1: grade() → update_progress()
  ├─ MATCH (julia)-[prog:HAS_PROGRESS]->(skill)
  ├─ Compute: p_mastery_new = prog.p_mastery + 0.08
  ├─ SET prog.p_mastery = p_mastery_new
  └─ RETURN p_mastery_new
```

### After (Atomic Edge Updates)
```
Julia answers Q1: grade() → sync_to_neo4j()
  ├─ MATCH (julia), (skill)
  ├─ MERGE (julia)-[r:HAS_PROGRESS]->(skill)
  ├─ ON CREATE SET r = {defaults}
  ├─ SET r.p_mastery = min(1.0, max(0.0, r.p_mastery + 0.08))
  └─ RETURN r.p_mastery
```

**Faster:** One operation instead of separate compute + update
**Safer:** Atomic MERGE prevents race conditions
**Cleaner:** All logic in one place

---

## Next: Step 3 (Ready When You Are)

Once mastery is being updated correctly, we'll implement:

**Step 3: Dashboard Queries** - Real-time analytics
- Accuracy rate per skill
- Learning velocity (mastery gain per attempt)
- Misconception patterns
- Time-to-mastery estimates

Ready to proceed? Just say "next"! 🚀

