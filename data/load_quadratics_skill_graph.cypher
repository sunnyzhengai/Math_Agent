// ============================================================================
// Load Quadratics Skill Graph into Neo4j
// ============================================================================
// Prerequisites:
// - Copy quadratics_skill_graph.json to your Neo4j import/ folder
// - Ensure APOC plugin is installed and enabled
// - Run this script in Neo4j Browser
// ============================================================================

// ============================================================================
// Step 1: Clear old Quadratics skills (optional in dev)
// ============================================================================
MATCH (n:Skill {domain:'Quadratics'}) DETACH DELETE n;

// ============================================================================
// Step 2: Load all Skill nodes from JSON
// ============================================================================
CALL apoc.load.json("file:///quadratics_skill_graph.json") YIELD value
UNWIND value.skills AS s
MERGE (k:Skill {id:s.id})
SET k.name = s.name,
    k.description = s.description,
    k.domain = value.domain
RETURN count(k) AS skills_created;

// ============================================================================
// Step 3: Create LEADS_TO edges (successor relationships)
// ============================================================================
CALL apoc.load.json("file:///quadratics_skill_graph.json") YIELD value
UNWIND value.skills AS s
UNWIND s.successors AS succ
MATCH (a:Skill {id:s.id}), (b:Skill {id:succ})
MERGE (a)-[:LEADS_TO]->(b)
RETURN count(*) AS leads_to_edges_created;

// ============================================================================
// Step 4: Create PRECEDES edges (prerequisite relationships)
// ============================================================================
CALL apoc.load.json("file:///quadratics_skill_graph.json") YIELD value
UNWIND value.skills AS s
UNWIND s.prereqs AS pre
MATCH (p:Skill {id:pre}), (a:Skill {id:s.id})
MERGE (p)-[:PRECEDES]->(a)
RETURN count(*) AS precedes_edges_created;

// ============================================================================
// Step 5: Verify the graph structure
// ============================================================================
MATCH (s:Skill {domain:'Quadratics'})
RETURN count(s) AS total_skills,
       collect(s.id) AS skill_ids;

MATCH (s:Skill {domain:'Quadratics'})-[r]->(t:Skill {domain:'Quadratics'})
RETURN type(r) AS relationship_type,
       count(r) AS count;

// ============================================================================
// Step 6: Visualize the graph (run this separately)
// ============================================================================
// MATCH (s:Skill {domain:'Quadratics'})-[r:LEADS_TO]->(t)
// RETURN s, t, r
// LIMIT 100;

// ============================================================================
// Step 7: Find entry points (skills with no prerequisites)
// ============================================================================
MATCH (s:Skill {domain:'Quadratics'})
WHERE NOT (s)<-[:PRECEDES]-(:Skill)
RETURN s.id, s.name, s.description
ORDER BY s.id;

// ============================================================================
// Step 8: Find exit points (skills with no successors)
// ============================================================================
MATCH (s:Skill {domain:'Quadratics'})
WHERE NOT (s)-[:LEADS_TO]->(:Skill)
RETURN s.id, s.name, s.description
ORDER BY s.id;

// ============================================================================
// Step 9: Check for cycles (should be empty for a DAG)
// ============================================================================
MATCH (s:Skill {domain:'Quadratics'})
MATCH path=(s)-[:LEADS_TO|PRECEDES*]->(s)
RETURN s.id, length(path) AS cycle_length
LIMIT 10;
