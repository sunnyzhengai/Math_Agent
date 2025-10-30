# 🚀 Quick Start Guide - Neo4j + Streamlit Integration

## TL;DR - Get It Running in 3 Steps

### Step 1: Install Dependencies
```bash
cd /Users/sunnyzheng/Agent_Math/quadratics_mvp
pip install -r requirements.txt
```

### Step 2: Load Neo4j Schema
Open http://localhost:7474 and paste this entire file:
```
data/extend_schema.cypher
```

Then click ▶️ to run.

### Step 3: Run Streamlit
```bash
streamlit run app.py
```

**Done!** Julia's learning graph is now live. 🎉

---

## 📊 What Happens When Julia Answers a Question

```
Julia answers → Grade locally → Sync to Neo4j → Update dashboard
                                ↓
                         ┌──────────────┐
                         │ p_mastery    │
                         │ streak       │
                         │ tags         │
                         │ remediation? │
                         └──────────────┘
```

---

## 🎯 The 4 Features

### 1. Real-Time Progress Syncing
```python
# After grading:
neo_result = sync_to_neo4j("julia", skill_id, correct, tags)
# Result: Julia's p_mastery instantly updates in Neo4j
```

### 2. Automatic Remediation
```
If misconception detected 2+ times:
  → Show mini-lesson
  → "Understanding Vertex Form Signs"
  → "In y = a(x-h)² + k, vertex is (h,k) not (-h,k)"
```

### 3. Personalized Dashboard
```
Sidebar shows:
✓ Mastered: 2
✓ Practicing: 8
✓ Struggling: 5
✓ Average: 48%
```

### 4. Smart Recommendations
```
🎯 Next: Axis of Symmetry
"You're struggling - let's build confidence"
```

---

## 🔍 Neo4j Queries to Verify

### Check Julia's Mastery
```cypher
MATCH (u:User {name: "Julia"})-[p:HAS_PROGRESS]->(s:Skill)
RETURN s.name, p.p_mastery, p.seen, p.streak
ORDER BY p.p_mastery DESC;
```

### Check Remediation Setup
```cypher
MATCH (m:Misconception)-[:HAS_RESOURCE]->(l:Lesson)
RETURN m.name, l.title;
```

### Check Progress Links
```cypher
MATCH (u:User {name: "Julia"})-[p:HAS_PROGRESS]->(s:Skill)
RETURN count(*) AS total;
// Should return: 22
```

---

## 🐛 Troubleshooting

| Problem | Solution |
|---------|----------|
| "Connection refused" | `brew services start neo4j` |
| "Authentication failed" | Check Neo4j password (default: "password") |
| App works but no Neo4j features | Neo4j is down - app works offline too! |
| Dashboard shows wrong stats | Verify `data/extend_schema.cypher` was loaded |

---

## 📚 Files Reference

| File | Purpose |
|------|---------|
| `app.py` | Main Streamlit app with Neo4j integration |
| `engine/neo4j_sync.py` | Neo4j driver & API |
| `data/extend_schema.cypher` | Schema: Users, Misconceptions, Lessons |
| `SETUP_NEO4J.md` | Full integration guide |
| `requirements.txt` | Dependencies (streamlit, neo4j) |

---

## 🎓 The Learning Flow

1. **Julia takes quiz** → Streamlit loads question
2. **Julia answers** → App shows recommendation from Neo4j
3. **Julia submits** → Locally graded + Neo4j synced instantly
4. **Result displayed:**
   - ✅/❌ feedback
   - Detected misconceptions
   - Updated mastery % from Neo4j
   - Remediation mini-lesson if triggered
5. **Dashboard updates** → Sidebar shows new stats

---

## 🚀 What's in Your Neo4j Graph

```
22 Skills          22 Relationships
   ↓ HAS_TAG          (User → Skill)
6 Misconceptions   
   ↓ HAS_RESOURCE   6 Relationships
6 Lessons          (Misconception → Lesson)
   
1 User (Julia)     32 + 25 Relationships
                   (Skill prerequisites & successors)
```

**Total: 35 nodes, 91 edges**

---

## 💡 Pro Tips

1. **Check real-time updates:**
   - Open Neo4j Browser in another tab
   - Run queries while Julia answers questions
   - Watch p_mastery change in real-time!

2. **Add more misconceptions:**
   - Edit `data/extend_schema.cypher`
   - Add new misconception + lesson
   - Reload schema

3. **Custom connection:**
   - Edit `engine/neo4j_sync.py` if Neo4j is on different host
   - Or use environment variables (see SETUP_NEO4J.md)

4. **Local-first design:**
   - App grades locally (no Neo4j dependency)
   - Neo4j is for analytics/recommendations
   - Works even if Neo4j is down!

---

## 🎉 Success Indicators

You'll know it's working when:

✅ Streamlit dashboard loads without errors
✅ Sidebar shows "Neo4j Dashboard" with stats
✅ "🎯 Next Recommended Skill" appears above quiz
✅ After answering: "Neo4j Mastery" metric appears
✅ Neo4j queries in browser show updated data
✅ Misconception count increases with wrong answers
✅ Remediation mini-lesson pops up on 2nd misconception

---

## 📞 Full Documentation

For detailed setup, troubleshooting, and queries:
→ See `SETUP_NEO4J.md`

For Neo4j schema details:
→ See `data/extend_schema.cypher`

For Python API:
→ See `engine/neo4j_sync.py`

---

Happy learning! 🚀

