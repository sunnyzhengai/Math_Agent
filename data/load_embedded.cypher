// ============================================================================
// EMBEDDED CYPHER SCRIPT - No import folder needed!
// ============================================================================
// Copy and paste this ENTIRE query into Neo4j Browser
// No apoc.load.json needed - all data is embedded
// ============================================================================

MATCH (n:Skill {domain:'Quadratics'}) DETACH DELETE n;

WITH [
  {id: "quad.form.identify.standard", name: "Identify standard form", desc: "Recognize y = ax² + bx + c and identify coefficients.", succ: ['quad.form.identify.vertex', 'quad.form.identify.factored'], pre: []},
  {id: "quad.form.identify.vertex", name: "Identify vertex form", desc: "Recognize y = a(x–h)² + k and identify parameters.", succ: ['quad.graph.vertex', 'quad.convert.vertex_to_standard'], pre: ['quad.form.identify.standard']},
  {id: "quad.form.identify.factored", name: "Identify factored form", desc: "Recognize y = a(x–r₁)(x–r₂) and relate to roots.", succ: ['quad.convert.expand', 'quad.solve.by_factoring'], pre: ['quad.form.identify.standard']},
  {id: "quad.convert.expand", name: "Expand to standard form", desc: "Multiply to get ax²+bx+c.", succ: ['quad.convert.complete_square'], pre: ['quad.form.identify.factored']},
  {id: "quad.convert.factor.simple", name: "Factor when a=1", desc: "Find integer factors of c that sum to b.", succ: ['quad.convert.factor.complex', 'quad.solve.by_factoring'], pre: ['quad.form.identify.standard']},
  {id: "quad.convert.factor.complex", name: "Factor when a≠1", desc: "Use grouping or decomposition.", succ: ['quad.solve.by_factoring'], pre: ['quad.convert.factor.simple']},
  {id: "quad.convert.complete_square", name: "Complete the square", desc: "Rewrite as a(x–h)² + k.", succ: ['quad.convert.standard_to_vertex', 'quad.solve.by_completing_square'], pre: ['quad.convert.expand']},
  {id: "quad.convert.standard_to_vertex", name: "Convert standard→vertex", desc: "Use h = –b/2a, k = c – b²/4a.", succ: ['quad.graph.vertex', 'quad.model.optimize'], pre: ['quad.convert.complete_square']},
  {id: "quad.convert.vertex_to_standard", name: "Convert vertex→standard", desc: "Expand a(x–h)² + k to ax²+bx+c.", succ: ['quad.convert.complete_square'], pre: ['quad.form.identify.vertex']},
  {id: "quad.graph.vertex", name: "Find vertex", desc: "Identify (h,k) accurately.", succ: ['quad.graph.axis', 'quad.graph.direction', 'quad.model.optimize'], pre: ['quad.form.identify.vertex']},
  {id: "quad.graph.axis", name: "Axis of symmetry", desc: "x = h.", succ: ['quad.graph.sketch'], pre: ['quad.graph.vertex']},
  {id: "quad.graph.direction", name: "Opening direction", desc: "Determine up/down from sign of a.", succ: ['quad.graph.sketch'], pre: ['quad.form.identify.vertex']},
  {id: "quad.graph.intercepts", name: "Find intercepts", desc: "Find x and y intercepts.", succ: ['quad.graph.sketch', 'quad.solve.by_factoring'], pre: ['quad.convert.factor.simple']},
  {id: "quad.graph.sketch", name: "Sketch parabola", desc: "Plot vertex, axis, intercepts.", succ: ['quad.solve.by_graphing'], pre: ['quad.graph.vertex', 'quad.graph.axis', 'quad.graph.direction']},
  {id: "quad.solve.by_factoring", name: "Solve by factoring", desc: "Set each factor=0 to find roots.", succ: ['quad.solve.discriminant', 'quad.solve.by_formula'], pre: ['quad.convert.factor.simple']},
  {id: "quad.solve.by_formula", name: "Quadratic formula", desc: "Compute x = (-b ± √(b²−4ac))/2a.", succ: ['quad.solve.discriminant', 'quad.model.projectile'], pre: ['quad.form.identify.standard']},
  {id: "quad.solve.discriminant", name: "Discriminant reasoning", desc: "Predict number/type of roots.", succ: ['quad.model.projectile'], pre: ['quad.form.identify.standard']},
  {id: "quad.solve.by_completing_square", name: "Solve by completing the square", desc: "Rewrite as (x–h)²=k and solve.", succ: ['quad.solve.discriminant'], pre: ['quad.convert.complete_square']},
  {id: "quad.solve.by_graphing", name: "Solve by graphing", desc: "Find x-intercepts from the graph.", succ: [], pre: ['quad.graph.sketch']},
  {id: "quad.model.optimize", name: "Optimize with vertex", desc: "Use vertex as max/min point.", succ: ['quad.model.projectile', 'quad.model.story'], pre: ['quad.graph.vertex']},
  {id: "quad.model.projectile", name: "Projectile motion", desc: "Model motion with quadratic.", succ: ['quad.model.story'], pre: ['quad.solve.by_formula', 'quad.graph.vertex']},
  {id: "quad.model.story", name: "Word problem mastery", desc: "Translate real-world situations to quadratic models.", succ: [], pre: ['quad.model.optimize', 'quad.model.projectile']}
] AS skills_data

UNWIND skills_data AS s
MERGE (k:Skill {id: s.id})
SET k.name = s.name, k.description = s.desc, k.domain = "Quadratics"
WITH k, s
UNWIND s.succ AS succ_id
MATCH (successor:Skill {id: succ_id})
MERGE (k)-[:LEADS_TO]->(successor)
WITH k, s
UNWIND s.pre AS pre_id
MATCH (prereq:Skill {id: pre_id})
MERGE (prereq)-[:PRECEDES]->(k)

RETURN count(DISTINCT k) AS skills_created;
