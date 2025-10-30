# Neo4j Quadratics Skill Graph

## Overview

This directory contains the Neo4j database schema and loader for the Quadratics learning skill graph.

**Files:**
- `data/quadratics_skill_graph.json` — Machine-readable skill definitions and relationships (22 skills)
- `data/load_quadratics_skill_graph.cypher` — Cypher script to import into Neo4j

## 📊 Graph Structure

### Nodes: `:Skill`

Each skill is a node with properties:
- `id` (unique) — e.g., `quad.form.identify.standard`
- `name` — Human-friendly name
- `description` — What the skill teaches
- `domain` — Always `"Quadratics"`

Example:
```cypher
(s:Skill {
  id: "quad.form.identify.standard",
  name: "Identify standard form",
  description: "Recognize y = ax² + bx + c and identify coefficients.",
  domain: "Quadratics"
})
```

### Edges

**`[:LEADS_TO]`** — Successor relationship (skill A enables skill B)
```
(A)-[:LEADS_TO]->(B)  means: master A → unlock B
```

**`[:PRECEDES]`** — Prerequisite relationship (skill A required for skill B)
```
(A)-[:PRECEDES]->(B)  means: master A → required for B
```

## 📈 Skill Map

**22 total skills organized in 5 layers:**

### Layer 0: Foundation (Entry Point)
```
quad.form.identify.standard
  ↓
  ├→ quad.form.identify.vertex
  ├→ quad.form.identify.factored
  ├→ quad.convert.factor.simple
  └→ quad.solve.by_formula
```

### Layer 1: Conversions
```
quad.convert.factor.simple
  ├→ quad.convert.factor.complex
  └→ quad.convert.vertex_to_standard (NEW)

quad.form.identify.factored
  └→ quad.convert.expand

quad.convert.expand
  └→ quad.convert.complete_square
```

### Layer 2: Graphing
```
quad.form.identify.vertex
  └→ quad.graph.vertex
    ├→ quad.graph.axis
    ├→ quad.graph.direction
    └→ quad.model.optimize

quad.convert.factor.simple
  └→ quad.graph.intercepts
    └→ quad.graph.sketch
```

### Layer 3: Solving
```
quad.convert.factor.simple
  └→ quad.solve.by_factoring
    └→ quad.solve.discriminant

quad.solve.by_completing_square (NEW)
  └→ quad.solve.discriminant

quad.graph.sketch
  └→ quad.solve.by_graphing (NEW)
```

### Layer 4: Applications (Exit Points)
```
quad.solve.by_formula
  ├→ quad.solve.discriminant
  └→ quad.model.projectile

quad.graph.vertex
  ├→ quad.model.optimize
  └→ quad.model.projectile

quad.model.projectile
  └→ quad.model.story (EXIT)
```

## 🚀 How to Load into Neo4j

### Prerequisites
- Neo4j instance running (Desktop, Aura, or Server)
- APOC plugin installed and enabled
- File access to import directory

### Steps

1. **Copy JSON to Neo4j import folder**
   ```bash
   # Neo4j Desktop (macOS)
   cp data/quadratics_skill_graph.json \
     ~/Library/Application\ Support/Neo4j\ Desktop/relate-data/dbms/*/import/
   
   # Or find your Neo4j data directory and copy to <NEO4J_HOME>/import/
   ```

2. **Open Neo4j Browser**
   - Go to http://localhost:7687 (or your Aura URL)
   - Connect to your database

3. **Copy and run the Cypher script**
   - Open `data/load_quadratics_skill_graph.cypher`
   - Copy each query section one at a time
   - Run in Neo4j Browser

4. **Verify the graph**
   ```cypher
   MATCH (s:Skill {domain:'Quadratics'})
   RETURN count(s) AS total_skills, 
          collect(s.id) AS skill_ids
   LIMIT 1;
   ```
   Should return: `total_skills: 22`

## 📊 Useful Queries

### See the full graph
```cypher
MATCH (s:Skill {domain:'Quadratics'})-[r:LEADS_TO]->(t)
RETURN s, t, r
LIMIT 100;
```

### Find prerequisites for a skill
```cypher
MATCH (s:Skill {domain:'Quadratics'})
MATCH path=(p)-[:PRECEDES*]->(s)
WHERE s.id = "quad.model.story"
RETURN path;
```

### Find what unlocks after a skill
```cypher
MATCH (s:Skill {id:"quad.form.identify.standard"})
MATCH path=(s)-[:LEADS_TO*1..3]->(t)
RETURN path;
```

### Count paths to mastery
```cypher
MATCH (start:Skill {id:"quad.form.identify.standard"})
MATCH (end:Skill {id:"quad.model.story"})
MATCH allPaths=(start)-[:LEADS_TO*]->(end)
RETURN length(allPaths) AS path_length, count(*) AS count;
```

### Find entry points
```cypher
MATCH (s:Skill {domain:'Quadratics'})
WHERE NOT (s)<-[:PRECEDES]-(:Skill)
RETURN s.id, s.name;
```

### Find exit points
```cypher
MATCH (s:Skill {domain:'Quadratics'})
WHERE NOT (s)-[:LEADS_TO]->(:Skill)
RETURN s.id, s.name;
```

## 🔄 Next Steps

### Phase 1: Extend Nodes
Add diagnostic information to skills:
```cypher
MATCH (s:Skill {id:"quad.form.identify.vertex"})
SET s.common_mistakes = [
  "vertex_sign_flip",
  "axis_wrong_direction"
],
s.learning_time_minutes = 20,
s.difficulty = "medium"
RETURN s;
```

### Phase 2: Add Resources
Link skills to lessons/videos:
```cypher
MATCH (s:Skill {id:"quad.model.projectile"})
CREATE (v:Video {title:"Projectile Motion Example", url:"https://..."})
CREATE (s)-[:HAS_RESOURCE]->(v)
RETURN s, v;
```

### Phase 3: Add User Progress
Track individual learner progress:
```cypher
MATCH (u:User {name:"Julia"})
MATCH (s:Skill {id:"quad.form.identify.standard"})
CREATE (u)-[:HAS_PROGRESS {
  p_mastery: 0.85,
  seen: 5,
  correct: 4,
  last_attempt: datetime()
}]->(s)
RETURN u, s;
```

### Phase 4: Add Personalization
Recommend next skill based on state:
```cypher
MATCH (u:User {name:"Julia"})
MATCH (u)-[p:HAS_PROGRESS]->(s:Skill)
MATCH (s)-[:LEADS_TO]->(next:Skill)
WHERE NOT (u)-[:HAS_PROGRESS]->(next)
RETURN next.id, next.name
ORDER BY p.p_mastery DESC
LIMIT 3;
```

## 📋 Statistics

| Metric | Value |
|--------|-------|
| **Total Skills** | 22 |
| **Entry Points** | 1 (standard form) |
| **Exit Points** | 2 (word problems, graphing) |
| **Total Prerequisite Edges** | 25 |
| **Total Successor Edges** | 32 |
| **Max Path Length** | ~8 skills (entry → exit) |
| **Branching Factor** | ~2.5 (average) |

## 🧪 Verification Checklist

- [ ] JSON loads without errors
- [ ] 22 Skill nodes created
- [ ] 25 PRECEDES edges created
- [ ] 32 LEADS_TO edges created
- [ ] No cycles (valid DAG)
- [ ] All skills reachable from entry point
- [ ] All paths end at exit points

## 🐛 Troubleshooting

**"Resource not found: file:///quadratics_skill_graph.json"**
- Make sure the file is in `<NEO4J_HOME>/import/`
- Check file name and extension

**"APOC not installed"**
- Install APOC plugin via Neo4j Desktop or follow [official docs](https://neo4j.com/docs/apoc/current/installation/)

**"Permission denied"**
- Ensure Neo4j has read access to the import folder
- Restart Neo4j after copying the file

## 📚 References

- [Neo4j Query Language (Cypher)](https://neo4j.com/docs/cypher-manual/current/)
- [APOC Plugin](https://neo4j.com/docs/apoc/current/)
- [Neo4j Graph Data Science](https://neo4j.com/docs/graph-data-science/current/)

---

**Last Updated:** 2025-10-30
**Version:** 1.0
**Status:** Production Ready ✅
