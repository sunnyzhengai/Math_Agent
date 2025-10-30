# 🚀 Neo4j Integration Setup Guide

This guide walks you through integrating Julia's personalized learning graph with your Streamlit app.

---

## ⚡ Quick Start (5 minutes)

### 1️⃣ Install Dependencies

```bash
cd /Users/sunnyzheng/Agent_Math/quadratics_mvp
pip install -r requirements.txt
```

This installs:
- `streamlit` — UI framework
- `neo4j>=5.0` — Graph database driver

---

### 2️⃣ Load the Extended Schema into Neo4j

**If you have Neo4j running locally (bolt://localhost:7687):**

**Option A: Via Neo4j Browser (easiest)**
1. Open http://localhost:7474
2. Copy entire contents of: `data/extend_schema.cypher`
3. Paste into the query editor
4. Click ▶️ to run

Expected output:
```
✓ misconceptions_created: 6
✓ lessons_created: 6
✓ skill_misconception_links: 6
✓ misconception_lesson_links: 6
✓ initial_progress_created: 22
✓ schema_summary: {...}
```

**Option B: Via Python Script**
```bash
python scripts/load_neo4j_skills.py
```

---

### 3️⃣ Verify the Schema

**In Neo4j Browser**, run:

```cypher
MATCH (u:User {name: "Julia"})-[p:HAS_PROGRESS]->(s:Skill)
RETURN count(*) AS progress_links;
```

Should return: `22` (one for each quadratics skill)

```cypher
MATCH (m:Misconception)-[:HAS_RESOURCE]->(l:Lesson)
RETURN count(*) AS lesson_links;
```

Should return: `6`

---

### 4️⃣ Run Streamlit with Neo4j Sync

```bash
streamlit run app.py
```

Your app now has:
- ✅ **Real-time progress syncing** to Neo4j
- ✅ **Automatic misconception tagging**
- ✅ **Smart remediation suggestions**
- ✅ **Personalized skill recommendations**
- ✅ **Learning dashboard** (sidebar)

---

## 🎯 What Julia Sees When She Answers a Question

### Scenario 1: Correct Answer ✅
```
✅ Correct! (Full credit)

Answer: The vertex is (3, 1)
In y = a(x - h)² + k, the vertex is (h, k)

Neo4j Mastery: 52% (8 attempts, 3 streak)
```

### Scenario 2: Misconception Detected 🎓
```
❌ Not quite. (No credit)

Answer: The vertex is (-3, 1)
...misconception detected: Vertex Sign Flip

📚 Remediation Triggered: Vertex Sign Flip
  → Mini-lesson: Understanding Vertex Form Signs
     "In y = a(x - h)² + k, the vertex x-coordinate is +h, not -h..."

Neo4j Mastery: 44% (9 attempts, 0 streak)
```

### Scenario 3: Recommendation 🎯
```
🎯 Next Recommended Skill: Axis of Symmetry

You're struggling - let's build confidence with Axis of Symmetry.
```

---

## 🔧 Environment Configuration

### Default Neo4j Connection

```python
# Default: bolt://localhost:7687
sync = Neo4jSync()  # Uses defaults

# Custom connection:
sync = Neo4jSync(
    uri="bolt://localhost:7687",
    username="neo4j",
    password="your_password"
)
```

### Environment Variables (Optional)

Set these in your shell if Neo4j is on a different machine:

```bash
export NEO4J_URI="bolt://your-host:7687"
export NEO4J_USER="neo4j"
export NEO4J_PASSWORD="your_password"
```

Then in `engine/neo4j_sync.py`, update the defaults:

```python
import os

def __init__(self, 
             uri: str = os.getenv("NEO4J_URI", "bolt://localhost:7687"),
             username: str = os.getenv("NEO4J_USER", "neo4j"),
             password: str = os.getenv("NEO4J_PASSWORD", "password")):
    ...
```

---

## 🐛 Troubleshooting

### ❌ "Neo4j connection refused"
```
Connection to bolt://localhost:7687 refused
```

**Fix:**
1. Verify Neo4j is running:
   ```bash
   lsof -i :7687
   ```
   Should show a Java process. If not:
   
   ```bash
   brew services start neo4j
   # Or start manually:
   /opt/homebrew/opt/neo4j/bin/neo4j start
   ```

2. Open http://localhost:7474 to verify the UI loads

### ❌ "Authentication failed"
```
Neo4j authentication failed for user neo4j
```

**Fix:**
```bash
# Check your Neo4j password (default is "password")
# If you changed it, update app.py or set env vars:
export NEO4J_PASSWORD="your_actual_password"
```

### ❌ "Neo4j not available" (silent mode)
Your app still works! The integration is wrapped in try-except, so:
- Quiz grading works locally (Streamlit state)
- Neo4j syncing fails gracefully
- Just shows no dashboard/recommendations until Neo4j comes back online

To debug:
```python
# Add this to app.py after submit button:
neo_result = sync_to_neo4j(username.lower(), item["skill_id"], correct, tags)
print("Neo4j result:", neo_result)  # Will show actual errors
```

---

## 📊 Your Neo4j Graph Structure

### Nodes
```
(:Skill)               22 nodes  (all quadratics skills)
  ↓ HAS_TAG
(:Misconception)        6 nodes  (vertex_sign_flip, wrong_pair, etc.)
  ↓ HAS_RESOURCE
(:Lesson)               6 nodes  (mini-lessons for remediation)

(:User)                 1 node   (Julia)
  ↓ HAS_PROGRESS
(:Skill)               22 relationships (with p_mastery, seen, correct, streak)
```

### Relationships
- `Skill -[LEADS_TO]→ Skill` (32 edges from prerequisites)
- `Skill -[PRECEDES]→ Skill` (25 edges from successors)
- `Skill -[HAS_TAG]→ Misconception` (6 edges)
- `Misconception -[HAS_RESOURCE]→ Lesson` (6 edges)
- `User -[HAS_PROGRESS]→ Skill` (22 edges with mastery data)

**Total: 35 nodes + 91 relationships**

---

## 🔍 Sample Neo4j Queries

### Julia's Current Mastery Profile
```cypher
MATCH (u:User {name: "Julia"})-[p:HAS_PROGRESS]->(s:Skill)
RETURN s.name, p.p_mastery, p.seen, p.correct
ORDER BY p.p_mastery DESC
LIMIT 10;
```

### Detect Julia's Top Misconceptions
```cypher
MATCH (u:User {name: "Julia"})-[tagged:TAGGED_WITH]->(m:Misconception)
RETURN m.name, tagged.count AS times_detected
ORDER BY times_detected DESC;
```

### Get Remediation Path for a Misconception
```cypher
MATCH (m:Misconception {id: "vertex_sign_flip"})-[:HAS_RESOURCE]->(l:Lesson)
RETURN m.name, l.title, l.content;
```

### Find Skills Julia Hasn't Attempted Yet
```cypher
MATCH (s:Skill {domain: "Quadratics"})
OPTIONAL MATCH (u:User {name: "Julia"})-[p:HAS_PROGRESS]->(s)
WHERE p IS NULL
RETURN s.name, s.description;
```

### Track Julia's Learning Velocity
```cypher
MATCH (u:User {name: "Julia"})-[p:HAS_PROGRESS]->(s:Skill)
RETURN {
  skill: s.name,
  mastery: p.p_mastery,
  attempts: p.seen,
  accuracy: CASE WHEN p.seen > 0 THEN p.correct * 100 / p.seen ELSE 0 END,
  current_streak: p.streak
} AS progress;
```

---

## 🎓 Example Flow: Julia Answers a Question

1. **Julia clicks "Get Next Question"**
   - Streamlit app loads a question
   - App also runs: `get_next_skill_recommendation("julia")`
   - Neo4j returns: "You're struggling with Vertex Form"

2. **Julia reads the question and answers**
   - Example: She says "The vertex is (-3, 2)" (wrong!)
   - Grader detects tag: `"vertex_sign_flip"`

3. **Julia clicks "Submit"**
   - Local grading runs
   - App calls: `sync_to_neo4j("julia", "quad.form.identify.vertex", False, ["vertex_sign_flip"])`
   - **Neo4j updates instantly:**
     - Her p_mastery drops from 0.50 → 0.38
     - Her streak resets to 0
     - She's tagged with misconception `vertex_sign_flip`
     - Count for this misconception: 1

4. **Julia Answers Again (Gets It Right This Time)**
   - She says: "The vertex is (3, 2)" ✅
   - No tags
   - App calls: `sync_to_neo4j("julia", "quad.form.identify.vertex", True, [])`
   - **Neo4j updates:**
     - Her p_mastery rises from 0.38 → 0.46
     - Streak becomes 1
     - Progress shown: "Neo4j Mastery: 46% (2 attempts, 1 streak)"

5. **Julia Answers Again (Wrong Again)**
   - Same misconception detected: `vertex_sign_flip`
   - Neo4j count: 2
   - **Threshold reached!** Remediation triggers:
     ```
     📚 Remediation Triggered: Vertex Sign Flip
     Mini-lesson: Understanding Vertex Form Signs
     "In y = a(x - h)² + k, the vertex x-coordinate is +h, not -h..."
     ```

---

## 🚀 Next Steps

1. **Test the full flow** with Neo4j running
2. **Monitor Neo4j queries** (use Neo4j Browser to inspect updates)
3. **Add more misconceptions** to `extend_schema.cypher`
4. **Create more lessons** with detailed remediation content
5. **Build a dashboard** page showing Julia's full learning graph

---

## 📚 API Reference

### `Neo4jSync` Class

```python
from engine.neo4j_sync import Neo4jSync

sync = Neo4jSync()

# Update progress after a quiz question
result = sync.update_progress(
    user="julia",
    skill_id="quad.form.identify.vertex",
    correct=True,
    tags=[]  # detected misconceptions
)
# Returns: {"progress": {...}, "remediation": {...}, "updated": True}

# Get Julia's stats
dashboard = sync.get_dashboard("julia")
# Returns: {"stats": {...}, "top_skills_to_practice": [...]}

# Get next recommendation
rec = sync.get_next_skill_recommendation("julia")
# Returns: {"skill_id": "...", "skill_name": "...", "rationale": "..."}

sync.close()
```

### Helper Function

```python
from engine.neo4j_sync import sync_to_neo4j

# One-liner for Streamlit integration
result = sync_to_neo4j("julia", "quad.form.identify.vertex", True, [])
```

---

## 🎉 You're All Set!

Your Streamlit app now powers Julia's personalized learning graph. Every quiz answer:
- Updates her mastery score in real-time
- Tags misconceptions automatically
- Triggers smart remediation
- Informs future skill recommendations

Happy teaching! 🚀

