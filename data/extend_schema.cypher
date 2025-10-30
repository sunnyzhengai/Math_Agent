// ============================================================================
// EXTEND NEO4J SCHEMA - Add User Progress, Misconceptions, and Lessons
// ============================================================================
// This script adds the user tracking and remediation layer to the skill graph
// ============================================================================

// ============================================================================
// PART 1: Create Misconception nodes from misconceptions.json
// ============================================================================

WITH [
  {id: "vertex_sign_flip", name: "Vertex Sign Flip", desc: "Uses (-h, k) instead of (h, k)", category: "quad.form.identify.vertex"},
  {id: "axis_wrong_direction", name: "Axis Direction Error", desc: "Says opens up when a<0, or down when a>0", category: "quad.form.identify.vertex"},
  {id: "sign_error", name: "Sign Error", desc: "Incorrect sign handling in factoring", category: "quad.convert.factor.simple"},
  {id: "under_root_error", name: "Under Root Calculation Error", desc: "Wrong discriminant calculation", category: "quad.solve.discriminant"},
  {id: "wrong_pair", name: "Wrong Factor Pair", desc: "Chosen p,q multiply to c but don't add to b", category: "quad.convert.factor.simple"},
  {id: "one_root_only", name: "One Root Only", desc: "Forgot ± in quadratic formula", category: "quad.solve.by_formula"}
] AS misconceptions_data

UNWIND misconceptions_data AS m
MERGE (mis:Misconception {id: m.id})
SET mis.name = m.name, mis.description = m.desc, mis.category = m.category

RETURN count(DISTINCT mis) AS misconceptions_created;

// ============================================================================
// PART 2: Link Misconceptions to Skills via HAS_TAG
// ============================================================================

MATCH (mis:Misconception), (skill:Skill)
WHERE (mis.id = "vertex_sign_flip" AND skill.id = "quad.graph.vertex")
   OR (mis.id = "axis_wrong_direction" AND skill.id = "quad.graph.direction")
   OR (mis.id = "sign_error" AND skill.id IN ["quad.convert.factor.simple", "quad.solve.by_factoring"])
   OR (mis.id = "under_root_error" AND skill.id = "quad.solve.discriminant")
   OR (mis.id = "wrong_pair" AND skill.id = "quad.convert.factor.simple")
   OR (mis.id = "one_root_only" AND skill.id = "quad.solve.by_formula")
MERGE (skill)-[:HAS_TAG]->(mis)

RETURN count(*) AS skill_misconception_links;

// ============================================================================
// PART 3: Create Lesson nodes (mini-lessons for each misconception)
// ============================================================================

WITH [
  {id: "lesson_vertex_sign_flip", misconception: "vertex_sign_flip", title: "Understanding Vertex Form Signs", content: "In y = a(x - h)² + k, the vertex x-coordinate is +h, not -h. Example: y = (x-3)² + 1 → vertex is (3,1)"},
  {id: "lesson_axis_direction", misconception: "axis_wrong_direction", title: "Opening Direction from 'a'", content: "The coefficient 'a' determines opening: a > 0 opens UP, a < 0 opens DOWN. Sketch two examples to see the U-shape."},
  {id: "lesson_sign_error", misconception: "sign_error", title: "Sign Handling in Factoring", content: "If c < 0, the factors have opposite signs. If c > 0, both factors share the sign of b. Example: x² + 5x - 6 = (x+6)(x-1)"},
  {id: "lesson_under_root", misconception: "under_root_error", title: "Discriminant Calculation", content: "D = b² - 4ac. Compute b² and 4ac separately, then subtract with correct signs. D > 0: two roots, D = 0: one root, D < 0: no real roots."},
  {id: "lesson_wrong_pair", misconception: "wrong_pair", title: "Factor Pair Validation", content: "Check BOTH conditions: sum to b AND product to c. Test with quick expand to verify. Example: x² + 5x + 6 → factors are 2,3 (2+3=5, 2*3=6)"},
  {id: "lesson_one_root_only", misconception: "one_root_only", title: "Quadratic Formula: Don't Forget ±", content: "x = (-b ± √D) / 2a. The ± means TWO roots: (-b + √D)/2a and (-b - √D)/2a. Both are solutions!"}
] AS lessons_data

UNWIND lessons_data AS l
MERGE (lesson:Lesson {id: l.id})
SET lesson.title = l.title, lesson.content = l.content, lesson.misconception_id = l.misconception

RETURN count(DISTINCT lesson) AS lessons_created;

// ============================================================================
// PART 4: Link Lessons to Misconceptions via HAS_RESOURCE
// ============================================================================

MATCH (mis:Misconception), (lesson:Lesson)
WHERE lesson.misconception_id = mis.id
MERGE (mis)-[:HAS_RESOURCE]->(lesson)

RETURN count(*) AS misconception_lesson_links;

// ============================================================================
// PART 5: Create Julia user node (or update if exists)
// ============================================================================

MERGE (user:User {name: "Julia"})
SET user.created_at = datetime(),
    user.email = "julia@example.com"

RETURN user AS julia_user;

// ============================================================================
// PART 6: Initialize Julia's progress on all skills (p_mastery = 0.5)
// ============================================================================

MATCH (user:User {name: "Julia"}), (skill:Skill {domain: "Quadratics"})
WHERE NOT (user)-[:HAS_PROGRESS]->(skill)
CREATE (user)-[:HAS_PROGRESS {
  p_mastery: 0.5,
  seen: 0,
  correct: 0,
  streak: 0,
  last_attempt: null
}]->(skill)

RETURN count(*) AS initial_progress_created;

// ============================================================================
// PART 7: Verify the extended schema
// ============================================================================

WITH 
  (MATCH (m:Misconception) RETURN count(m) AS mcount) AS misconceptions,
  (MATCH (l:Lesson) RETURN count(l) AS lcount) AS lessons,
  (MATCH (u:User) RETURN count(u) AS ucount) AS users,
  (MATCH (s:Skill)-[:HAS_TAG]->(m:Misconception) RETURN count(*) AS tcount) AS tags,
  (MATCH (m:Misconception)-[:HAS_RESOURCE]->(l:Lesson) RETURN count(*) AS rcount) AS resources,
  (MATCH (u:User)-[:HAS_PROGRESS]->(s:Skill) RETURN count(*) AS pcount) AS progress

RETURN {
  misconceptions: misconceptions.mcount,
  lessons: lessons.lcount,
  users: users.ucount,
  skill_misconception_tags: tags.tcount,
  misconception_lesson_resources: resources.rcount,
  user_skill_progress: progress.pcount
} AS schema_summary;

// ============================================================================
// PART 8: Show Julia's learning dashboard (example query)
// ============================================================================

MATCH (user:User {name: "Julia"})-[prog:HAS_PROGRESS]->(skill:Skill)
WHERE skill.domain = "Quadratics"
OPTIONAL MATCH (skill)-[:HAS_TAG]->(mis:Misconception)-[:HAS_RESOURCE]->(lesson:Lesson)
RETURN {
  skill_id: skill.id,
  skill_name: skill.name,
  p_mastery: prog.p_mastery,
  seen: prog.seen,
  correct: prog.correct,
  streak: prog.streak,
  misconceptions: collect(DISTINCT mis.name),
  lessons: collect(DISTINCT lesson.title)
} AS julia_dashboard
ORDER BY prog.p_mastery ASC
LIMIT 5;

