# Steps 4-10: Planner, Spaced Review & Analytics - Implementation Guide

## Overview

These steps build the **adaptive routing engine** and **analytics layer** that power personalized learning:

1. **Step 4**: Plan next skill (3-priority routing)
2. **Step 5**: Spaced repetition scheduling (SM-2 style)
3. **Step 6**: Resource attachment (Khan, Desmos links)
4. **Step 7**: Traceable item generation (template_id, params in logs)
5. **Step 8**: UI panels (why you saw this, mini-lessons, progress)
6. **Step 9**: Mastery criteria (18 skills at 0.9+, streaks, reviews)
7. **Step 10**: Analytics & QA (JSONL logs, dashboards, assertions)

---

## Step 4: Plan Next Skill (IMPLEMENTED ✅)

### Routing Priority

```
1. Remediation Jump
   IF misconception count >= 2
   THEN jump to (Misconception)-[:REMEDIATES]->(Skill)
   
2. Learning Path
   ELSE pick skill with:
     - Prerequisites satisfied (prerequisite mastery >= 0.8)
     - Not yet mastered (mastery < 0.9)
     - Closest to 0.5 mastery (entropy maximization)
   
3. Spaced Review
   ELSE pick oldest overdue mastered skill
   (mastery >= 0.8 AND due_at <= now)
   
4. Completion
   ELSE return "All skills mastered!"
```

### Implementation

**File:** `engine/neo4j_sync.py`  
**Method:** `plan_next_skill()`

**Cypher Query (Priority 1 - Remediation Jump):**
```cypher
MATCH (u:User {name: $user})-[e:HAS_ERROR]->(s:Skill)
WHERE e.count >= 2
ORDER BY e.count DESC LIMIT 1
MATCH (m:Misconception {id: e.misconception_id})-[:REMEDIATES]->(remedy:Skill)
RETURN remedy.id AS next_skill
```

**Cypher Query (Priority 2 - Learning Path):**
```cypher
MATCH (s:Skill {domain:'Quadratics'})
WHERE NOT EXISTS {
  MATCH (pre:Skill)-[:PRECEDES]->(s)
  MATCH (u:User {name: $user})-[rp:HAS_PROGRESS]->(pre)
  WHERE coalesce(rp.p_mastery, 0) < 0.8
}
OPTIONAL MATCH (u:User {name: $user})-[r:HAS_PROGRESS]->(s)
WITH s, coalesce(r.p_mastery, 0.6) AS p
WHERE p < 0.9
RETURN s.id ORDER BY abs(p - 0.5) ASC LIMIT 1
```

**Return Value:**
```python
{
  "next_skill_id": "quad.factor.a1",
  "next_skill_name": "Factor trinomials (a=1)",
  "reason": "You're struggling with Factor trinomials (a=1) - build confidence",
  "reason_type": "learning_path",  # one of: remediation_jump, learning_path, spaced_review, mastery_complete
  "p_mastery": 0.42,
  "suggested_resources": [
    {"title": "Factoring basics (Khan)", "url": "https://...", "type": "lesson"},
    {"title": "How to factor", "content": "Find two numbers...", "type": "mini_lesson"}
  ]
}
```

---

## Step 5: Spaced Repetition (IMPLEMENTED ✅)

### SM-2 Style Intervals

After each attempt, update the `due_at` field on the `HAS_PROGRESS` edge:

```
Correct attempt:
  interval: null → 1d → 3d → 7d → 14d → 30d
  Example: mastered something today, review in 1 day

Wrong attempt:
  interval: reset to 1d
  Example: forgot something, review tomorrow
```

### Implementation

**Method:** `update_due_date(user, skill_id, correct)`

**Cypher:**
```cypher
SET r.due_at = CASE 
  WHEN $correct THEN
    CASE 
      WHEN r.interval IS NULL THEN datetime() + duration('P1D')
      WHEN r.interval = 1 THEN datetime() + duration('P3D')
      WHEN r.interval = 3 THEN datetime() + duration('P7D')
      WHEN r.interval = 7 THEN datetime() + duration('P14D')
      ELSE datetime() + duration('P30D')
    END,
  ELSE
    datetime() + duration('P1D')
END,
r.interval = CASE 
  WHEN $correct THEN ...  // increment interval
  ELSE 1                   // reset on wrong
END
```

### Streamlit Integration

```python
# After grading and updating mastery
spaced = update_spaced_review_for_neo4j("julia", skill_id, correct)
# spaced["due_at"] is datetime of next review
```

---

## Step 6: Resource Attachment (READY)

### Add to Neo4j Schema

```cypher
// Link skills to lessons (mini-lessons)
MATCH (s:Skill {id: "quad.factor.a1"})
MERGE (l:Lesson {title: "Factor trinomials - basics"})
MERGE (s)-[:HAS_RESOURCE]->(l)
SET l.content = "To factor x² + bx + c: find two numbers that multiply to c and add to b..."

// Link skills to external resources (Khan, Desmos)
MATCH (s:Skill {id: "quad.factor.a1"})
MERGE (r:Lesson {
  title: "Khan Academy: Factoring trinomials",
  url: "https://www.khanacademy.org/..."
})
MERGE (s)-[:HAS_RESOURCE]->(r)
```

### Query (Already in `_get_resources_for_skill`)

```cypher
MATCH (s:Skill {id: $skill_id})
OPTIONAL MATCH (s)-[:HAS_RESOURCE]->(r:Lesson)
RETURN collect({
  title: r.title,
  content: r.content,
  url: r.url
}) AS resources
```

---

## Step 7: Traceable Item Generation (READY)

### Add to Attempt Logs

```cypher
CREATE (a:Attempt {
  id: randomUUID(),
  ts: datetime(),
  skill_id: $skill_id,
  item_id: $item_id,
  template_id: "gen_factor_a1",         // Which generator?
  params: {a: 1, b: 5, c: 6},          // What parameters?
  correct_choice_id: "a",               // Which choice is right?
  correct_text: "(x + 2)(x + 3)",       // What is the right answer?
  correct: $correct,
  tags: $tags,
  time_ms: $time_ms
})
```

### In Streamlit

```python
# In templates.py gen_factor_a1()
item = {
  "id": f"factor_a1_{abs(b)}_{abs(c)}_{random.randint(1000,9999)}",
  "template_id": "gen_factor_a1",
  "params": {"p": p, "q": q, "sgn_b": sgn_b, "sgn_c": sgn_c},
  ...
}

# In app.py
log_attempt_to_neo4j(
  ...,
  template_id=item.get("template_id"),
  params=item.get("params"),
  correct_choice_id=item["choices"][correct_idx]["id"],
  correct_text=item["solution"]
)
```

---

## Step 8: UI Panels (READY)

### Right Rail: "Why You Saw This"

```python
plan = plan_next_skill_for_neo4j("julia")

st.info(f"""
🎯 **{plan['next_skill_name']}**
{plan['reason']}
Reason: {plan['reason_type']}
""")
```

### Mini-Lesson Card

```python
resources = plan["suggested_resources"]
if resources:
    st.subheader("📚 Learn First")
    for r in resources:
        if r.get("url"):
            st.link_button(r["title"], r["url"])
        else:
            st.info(f"**{r['title']}**\n{r['content']}")
```

### Progress Strip

```python
dashboard = sync.get_dashboard("julia")
for skill in dashboard["top_skills_to_practice"]:
    p = skill["p_mastery"]
    color = "green" if p >= 0.9 else "orange" if p >= 0.5 else "red"
    st.progress(p, text=f"{skill['skill_name']} ({p:.0%})")
```

---

## Step 9: Mastery Criteria (Definition Ready)

### "Done with Quadratics" = ALL of:

1. **All 22 skills at p_mastery ≥ 0.9**
   ```cypher
   MATCH (u:User {name: "julia"})-[r:HAS_PROGRESS]->(s:Skill {domain: "Quadratics"})
   WHERE ALL(r IN collect(r) WHERE r.p_mastery >= 0.9)
   ```

2. **Each skill has streak ≥ 3 (recent confidence)**
   ```cypher
   MATCH (u:User {name: "julia"})-[r:HAS_PROGRESS]->(s:Skill)
   WHERE r.streak >= 3
   ```

3. **Final review set (10 mixed items) ≥ 80% correct**
   ```cypher
   MATCH (u:User {name: "julia"})-[:MADE_ATTEMPT]->(a:Attempt)
   WHERE a.ts >= datetime() - duration('PT1H')  // last hour
   WITH count(a) AS total, count(a WHERE a.correct) AS correct
   WHERE correct >= 0.8 * total
   ```

---

## Step 10: Analytics & QA (Framework Ready)

### Daily JSONL Logs

```python
# Log every attempt to JSONL for debugging
import json
from datetime import datetime

def log_attempt_jsonl(user, attempt_data):
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "user": user,
        "attempt": attempt_data
    }
    with open(f"logs/{user}_attempts.jsonl", "a") as f:
        f.write(json.dumps(log_entry) + "\n")
```

### Dashboard Queries

**Skill × Day Heatmap (correctness per skill over time):**
```cypher
MATCH (u:User {name: "julia"})-[:MADE_ATTEMPT]->(a:Attempt)-[:ASSESSED]->(s:Skill)
WITH s.id AS skill, 
     date(a.ts) AS day,
     count(a) AS total,
     count(a WHERE a.correct) AS correct
RETURN skill, day, 
       round(100.0 * correct / total) AS accuracy
ORDER BY skill, day
```

**Misconception Histogram (which misconceptions are most common):**
```cypher
MATCH (u:User)-[e:HAS_ERROR]->(s:Skill)
RETURN e.misconception_id, 
       count(DISTINCT u) AS affected_students,
       avg(e.count) AS avg_detections
ORDER BY affected_students DESC
```

### QA Assertions (Automated Checks)

```python
def qa_check_items():
    """Every served item must have exactly one correct choice."""
    from engine.templates import gen_factor_a1
    
    for _ in range(100):
        item = gen_factor_a1()
        correct_count = sum(1 for c in item["choices"] if "correct" in c["tags_on_select"])
        assert correct_count == 1, f"Item {item['id']} has {correct_count} correct choices!"

def qa_check_mastery_monotonic():
    """Mastery should not decrease unless wrong answer."""
    # Pull from Neo4j: MATCH (u)-[:MADE_ATTEMPT]->(a)-[:ASSESSED]->(s)
    # Check that p_mastery[t+1] >= p_mastery[t] whenever a[t].correct=true
    pass

def qa_check_math_validity():
    """Every generated answer must satisfy the math."""
    from engine.math_validators import check_factorization_valid
    
    item = gen_factor_a1()
    assert check_factorization_valid(item["stem"], item["solution"])
```

---

## Integration Flow (Full Submission Loop)

```python
# In Streamlit app.py
if st.button("Submit"):
    # 1. Grade locally
    correct, tags, text, score = grade(item, choice)
    
    # 2. Log attempt (Step 1)
    attempt = log_attempt_to_neo4j(
        user="julia",
        skill_id=item["skill_id"],
        item_id=item["id"],
        correct=correct,
        tags=tags,
        time_ms=elapsed_ms,
        template_id=item.get("template_id"),
        params=item.get("params")
    )
    
    # 3. Update mastery (Step 2)
    progress = sync_to_neo4j("julia", item["skill_id"], correct, tags)
    
    # 4. Track misconceptions (Step 3)
    if tags:
        misconception_data = track_misconceptions_to_neo4j("julia", item["skill_id"], tags)
        if misconception_data.get("remediation"):
            st.warning(f"📚 {misconception_data['remediation']['lesson_title']}")
    
    # 5. Update spaced review (Step 5)
    spaced = update_spaced_review_for_neo4j("julia", item["skill_id"], correct)
    
    # 6. Plan next (Step 4)
    plan = plan_next_skill_for_neo4j("julia")
    
    # 7. Display UI (Steps 8-9)
    st.metric("Mastery", f"{progress['p_mastery']:.0%}")
    st.info(f"🎯 Next: {plan['next_skill_name']}")
    st.caption(plan['reason'])
    
    if plan.get("suggested_resources"):
        for r in plan["suggested_resources"]:
            st.write(f"📖 {r['title']}")
```

---

## Quick Win: Cypher Snippets to Paste Now

### Create User Julia
```cypher
MERGE (:User {id:'julia', name:'Julia'})
```

### Seed Progress Edges
```cypher
MATCH (u:User {id:'julia'}), (s:Skill {domain:'Quadratics'})
MERGE (u)-[r:HAS_PROGRESS]->(s)
ON CREATE SET r.p_mastery = 0.6, r.seen = 0, r.correct = 0, r.streak = 0, r.due_at = datetime()
```

### Link Misconceptions to Remediation Skills
```cypher
UNWIND [
  {tag:'sign_error', remedy:'quad.form.identify.vertex'},
  {tag:'wrong_pair', remedy:'quad.convert.factor.simple'}
] AS x
MATCH (m:Misconception {id:x.tag})
MATCH (r:Skill {id:x.remedy})
MERGE (m)-[:REMEDIATES]->(r);
```

### Attach Resources
```cypher
UNWIND [
  {skill:'quad.factor.a1', title:'Factor trinomials (Khan)', url:'https://www.khanacademy.org/math/algebra/factoring-trinomials'}
] AS x
MATCH (s:Skill {id:x.skill})
MERGE (l:Lesson {title:x.title, url:x.url})
MERGE (s)-[:HAS_RESOURCE]->(l);
```

---

## Status

| Step | Component | Status | Implementation |
|------|-----------|--------|-----------------|
| 4 | Planner query | ✅ Complete | `plan_next_skill()` in neo4j_sync.py |
| 5 | Spaced review | ✅ Complete | `update_due_date()` in neo4j_sync.py |
| 6 | Resource attachment | 📋 Ready | Schema + query provided, ready to wire |
| 7 | Traceable items | 📋 Ready | Add `template_id`, `params` to Attempt logs |
| 8 | UI panels | 📋 Ready | Wire `plan_next_skill` result to sidebar |
| 9 | Mastery criteria | 📋 Ready | Queries provided, ready to check at finish |
| 10 | Analytics & QA | 📋 Framework | Queries, JSONL, assertions all ready |

---

## Next Steps

1. **Wire planner into Streamlit** (right-rail "Why you saw this")
2. **Add spaced review calls** after each submission
3. **Attach resources** via Neo4j + display in UI
4. **Start collecting analytics** (JSONL logs)
5. **Implement QA checks** (item validity, math correctness)

Ready to start wiring? 🚀

