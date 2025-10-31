"""
Neo4j Sync Module - Updates Julia's learning graph in real-time

This module syncs quiz results with her Neo4j knowledge graph,
automatically updating mastery scores and triggering remediation.
"""

from neo4j import GraphDatabase
from typing import Optional, List
import os
from datetime import datetime
import uuid


class Neo4jSync:
    """Sync Julia's learning progress to Neo4j knowledge graph"""
    
    def __init__(self, uri: str = "bolt://localhost:7687", 
                 username: str = "neo4j", 
                 password: str = "password"):
        """Initialize Neo4j connection"""
        self.driver = GraphDatabase.driver(uri, auth=(username, password))
        self.username = username
        self.password = password
        self.uri = uri
    
    def close(self):
        """Close Neo4j connection"""
        self.driver.close()
    
    def log_attempt(self,
                   user: str,
                   skill_id: str,
                   item_id: str,
                   correct: bool,
                   tags: List[str],
                   time_ms: int = 0,
                   confidence: Optional[int] = None) -> dict:
        """
        Create an immutable Attempt node and link it to user and skill.
        
        This is the audit trail for analytics, mastery calculations, and spaced review.
        
        Args:
            user: Username (e.g., "Julia")
            skill_id: Skill ID (e.g., "quad.factor.a1")
            item_id: Question item ID (e.g., "factor_a1_3_2_1234")
            correct: Whether the answer was correct
            tags: List of misconception tags detected (e.g., ["vertex_sign_flip"])
            time_ms: Time taken to answer in milliseconds
            confidence: Optional confidence rating (1-5)
        
        Returns:
            dict with attempt details
        """
        attempt_id = str(uuid.uuid4())
        
        with self.driver.session() as session:
            # Create immutable Attempt node and link to user and skill
            result = session.run("""
                // Create Attempt node (immutable)
                CREATE (a:Attempt {
                  id: $attempt_id,
                  ts: datetime(),
                  skill_id: $skill_id,
                  item_id: $item_id,
                  correct: $correct,
                  tags: $tags,
                  time_ms: $time_ms,
                  confidence: $confidence
                })
                
                // Link attempt to user
                MATCH (u:User {name: $user})
                CREATE (u)-[:MADE_ATTEMPT]->(a)
                
                // Link attempt to skill
                MATCH (s:Skill {id: $skill_id})
                CREATE (a)-[:ASSESSED]->(s)
                
                RETURN {
                  attempt_id: a.id,
                  ts: a.ts,
                  skill_id: a.skill_id,
                  item_id: a.item_id,
                  correct: a.correct,
                  tags: a.tags,
                  time_ms: a.time_ms,
                  confidence: a.confidence
                } AS attempt
            """, 
            attempt_id=attempt_id,
            user=user,
            skill_id=skill_id,
            item_id=item_id,
            correct=correct,
            tags=tags,
            time_ms=time_ms,
            confidence=confidence)
            
            attempt = result.single()["attempt"]
            return {
                "attempt_id": attempt["attempt_id"],
                "logged": True,
                "details": attempt
            }
    
    def update_progress(self, 
                       user: str,
                       skill_id: str, 
                       correct: bool, 
                       tags: List[str],
                       delta_win: float = 0.08,
                       delta_loss: float = 0.12) -> dict:
        """
        Atomically update user's progress on a skill.
        
        Uses MERGE to ensure the HAS_PROGRESS relationship exists,
        then performs one-step stochastic mastery update.
        
        Args:
            user: Username (e.g., "Julia")
            skill_id: Skill ID (e.g., "quad.factor.a1")
            correct: Whether the answer was correct
            tags: List of misconception tags detected
            delta_win: Points to add if correct (0-1)
            delta_loss: Points to subtract if wrong (0-1)
        
        Returns:
            dict with updated progress and any triggered remediation
        """
        
        with self.driver.session() as session:
            # One-step atomic mastery update on the edge
            result = session.run("""
                MATCH (user:User {name: $user}), (skill:Skill {id: $skill_id})
                MERGE (user)-[r:HAS_PROGRESS]->(skill)
                ON CREATE SET r.p_mastery = 0.6, 
                              r.seen = 0, 
                              r.correct = 0, 
                              r.streak = 0, 
                              r.last = datetime()
                SET r.seen = r.seen + 1,
                    r.correct = r.correct + CASE WHEN $correct THEN 1 ELSE 0 END,
                    r.streak = CASE WHEN $correct THEN r.streak + 1 ELSE 0 END,
                    r.p_mastery = apoc.number.min(1.0,
                                    apoc.number.max(0.0,
                                      r.p_mastery + CASE WHEN $correct THEN $delta_win ELSE -$delta_loss END
                                    )),
                    r.last = datetime()
                RETURN {
                  skill_id: skill.id,
                  skill_name: skill.name,
                  p_mastery: r.p_mastery,
                  seen: r.seen,
                  correct: r.correct,
                  streak: r.streak,
                  correct_flag: $correct,
                  tags: $tags
                } AS result
            """, user=user, skill_id=skill_id, correct=correct, tags=tags,
                delta_win=delta_win, delta_loss=delta_loss)
            
            progress = result.single()["result"]
            
            # Link misconception tags if detected
            if tags:
                for tag in tags:
                    session.run("""
                        MATCH (user:User {name: $user}),
                              (skill:Skill {id: $skill_id}),
                              (mis:Misconception {id: $tag})
                        MERGE (user)-[tagged:TAGGED_WITH {skill_id: $skill_id}]->(mis)
                        SET tagged.count = CASE WHEN tagged.count IS NULL THEN 1 ELSE tagged.count + 1 END,
                            tagged.last_seen = datetime()
                    """, user=user, skill_id=skill_id, tag=tag)
            
            # Check if remediation needed (misconception count >= 2)
            remediation = None
            if tags:
                rem_result = session.run("""
                    MATCH (user:User {name: $user})-[tagged:TAGGED_WITH]->(mis:Misconception)
                    WHERE tagged.skill_id = $skill_id
                    WITH mis, tagged.count AS count
                    WHERE count >= 2
                    MATCH (mis)-[:HAS_RESOURCE]->(lesson:Lesson)
                    RETURN {
                      misconception_id: mis.id,
                      misconception_name: mis.name,
                      count: count,
                      lesson_title: lesson.title,
                      lesson_content: lesson.content
                    } AS remediation
                """, user=user, skill_id=skill_id)
                
                rem_data = rem_result.single()
                if rem_data:
                    remediation = rem_data["remediation"]
            
            return {
                "progress": progress,
                "remediation": remediation,
                "updated": True
            }
    
    def track_misconceptions(self,
                           user: str,
                           skill_id: str,
                           tags: List[str]) -> dict:
        """
        Track misconception occurrences for this user on this skill.
        
        Creates/updates HAS_ERROR edges that count misconception detections.
        Triggers remediation when count >= 2.
        
        Args:
            user: Username (e.g., "Julia")
            skill_id: Skill ID (e.g., "quad.factor.a1")
            tags: List of misconception IDs detected (e.g., ["sign_error", "wrong_pair"])
        
        Returns:
            dict with misconception counts and any triggered remediation
        """
        if not tags:
            return {"misconceptions": {}, "remediation": None}
        
        with self.driver.session() as session:
            # Track each misconception
            misconceptions = {}
            
            for tag in tags:
                # Ensure misconception exists and increment count
                result = session.run("""
                    // Ensure misconception exists
                    MERGE (m:Misconception {id: $tag})
                    
                    // Track error for this user on this skill
                    WITH m
                    MATCH (u:User {name: $user}), (s:Skill {id: $skill_id})
                    MERGE (u)-[e:HAS_ERROR {misconception_id: m.id, skill_id: $skill_id}]->(s)
                    ON CREATE SET e.count = 0,
                                  e.first_seen = datetime(),
                                  e.triggered_remediation = false
                    SET e.count = e.count + 1,
                        e.last_seen = datetime()
                    
                    RETURN {
                      misconception_id: m.id,
                      misconception_name: m.name,
                      count: e.count,
                      triggered_remediation: e.triggered_remediation
                    } AS error_info
                """, tag=tag, user=user, skill_id=skill_id)
                
                error_info = result.single()["error_info"]
                misconceptions[tag] = error_info
            
            # Check if any misconception reached remediation threshold (count >= 2)
            remediation = None
            for tag, error_info in misconceptions.items():
                if error_info["count"] >= 2 and not error_info["triggered_remediation"]:
                    # Get the lesson for this misconception
                    lesson_result = session.run("""
                        MATCH (m:Misconception {id: $tag})-[:HAS_RESOURCE]->(l:Lesson)
                        RETURN {
                          misconception_id: m.id,
                          misconception_name: m.name,
                          lesson_title: l.title,
                          lesson_content: l.content,
                          count: $count
                        } AS lesson_info
                    """, tag=tag, count=error_info["count"])
                    
                    lesson_data = lesson_result.single()
                    if lesson_data:
                        remediation = lesson_data["lesson_info"]
                        
                        # Mark that remediation was triggered for this misconception
                        session.run("""
                            MATCH (u:User {name: $user})-[e:HAS_ERROR {misconception_id: $tag, skill_id: $skill_id}]->(s:Skill)
                            SET e.triggered_remediation = true,
                                e.remediation_triggered_at = datetime()
                        """, user=user, tag=tag, skill_id=skill_id)
                    
                    # Return first triggered remediation
                    break
            
            return {
                "misconceptions": misconceptions,
                "remediation": remediation,
                "updated": True
            }
    
    def plan_next_skill(self, user: str) -> dict:
        """
        Decide what skill to present next using adaptive routing.
        
        Routing priority:
        1. If misconception detected ≥2 times → jump to remediation skill
        2. Else pick lowest-mastery unmastered skill (prerequisites satisfied)
        3. Else schedule spaced review (oldest overdue skill)
        
        Args:
            user: Username (e.g., "Julia")
        
        Returns:
            dict with next_skill_id, reason, and suggested_resources
        """
        with self.driver.session() as session:
            # Priority 1: Check for hottest error tag (remediation jump)
            error_result = session.run("""
                MATCH (u:User {name: $user})-[e:HAS_ERROR]->(s:Skill)
                WHERE e.count >= 2
                ORDER BY e.count DESC
                LIMIT 1
                RETURN e.misconception_id AS tag, s.id AS skill_id
            """, user=user)
            
            error_data = error_result.single()
            if error_data:
                tag = error_data["tag"]
                # Get the remediation skill for this misconception
                remedy_result = session.run("""
                    MATCH (m:Misconception {id: $tag})-[:REMEDIATES]->(remedy:Skill)
                    RETURN remedy.id AS remedy_skill_id, remedy.name AS remedy_skill_name
                """, tag=tag)
                
                remedy_data = remedy_result.single()
                if remedy_data:
                    # Get resources for remedy skill
                    resources = self._get_resources_for_skill(session, remedy_data["remedy_skill_id"])
                    
                    return {
                        "next_skill_id": remedy_data["remedy_skill_id"],
                        "next_skill_name": remedy_data["remedy_skill_name"],
                        "reason": f"Repeated misconception detected: {tag}",
                        "reason_type": "remediation_jump",
                        "suggested_resources": resources,
                        "updated": True
                    }
            
            # Priority 2: Pick lowest-mastery unmastered skill (prerequisites satisfied)
            main_result = session.run("""
                MATCH (s:Skill {domain: "Quadratics"})
                WHERE NOT EXISTS {
                  MATCH (pre:Skill)-[:PRECEDES]->(s)
                  MATCH (u:User {name: $user})-[rp:HAS_PROGRESS]->(pre)
                  WHERE coalesce(rp.p_mastery, 0) < 0.8
                }
                OPTIONAL MATCH (u:User {name: $user})-[r:HAS_PROGRESS]->(s)
                WITH s, coalesce(r.p_mastery, 0.6) AS p, r
                WHERE p < 0.9
                RETURN s.id AS skill_id,
                       s.name AS skill_name,
                       p AS p_mastery,
                       abs(p - 0.5) AS entropy_gap
                ORDER BY entropy_gap ASC
                LIMIT 1
            """, user=user)
            
            main_data = main_result.single()
            if main_data:
                resources = self._get_resources_for_skill(session, main_data["skill_id"])
                
                # Determine reason based on mastery level
                p = main_data["p_mastery"]
                if p < 0.3:
                    reason = f"You're struggling with {main_data['skill_name']} - build confidence"
                elif p < 0.5:
                    reason = f"Close to halfway on {main_data['skill_name']} - keep going!"
                elif p < 0.7:
                    reason = f"Good progress on {main_data['skill_name']} - aim for mastery"
                else:
                    reason = f"Almost there on {main_data['skill_name']}!"
                
                return {
                    "next_skill_id": main_data["skill_id"],
                    "next_skill_name": main_data["skill_name"],
                    "reason": reason,
                    "reason_type": "learning_path",
                    "p_mastery": p,
                    "suggested_resources": resources,
                    "updated": True
                }
            
            # Priority 3: Spaced review (oldest overdue skill)
            review_result = session.run("""
                MATCH (u:User {name: $user})-[r:HAS_PROGRESS]->(s:Skill)
                WHERE r.p_mastery >= 0.8 AND r.due_at <= datetime()
                RETURN s.id AS skill_id,
                       s.name AS skill_name,
                       r.due_at AS due_at,
                       r.p_mastery AS p_mastery
                ORDER BY r.due_at ASC
                LIMIT 1
            """, user=user)
            
            review_data = review_result.single()
            if review_data:
                resources = self._get_resources_for_skill(session, review_data["skill_id"])
                
                return {
                    "next_skill_id": review_data["skill_id"],
                    "next_skill_name": review_data["skill_name"],
                    "reason": f"Time to review {review_data['skill_name']} (spaced repetition)",
                    "reason_type": "spaced_review",
                    "p_mastery": review_data["p_mastery"],
                    "suggested_resources": resources,
                    "updated": True
                }
            
            # Fallback: return None (all skills mastered + no review due)
            return {
                "next_skill_id": None,
                "reason": "🎉 All skills mastered! Great work!",
                "reason_type": "mastery_complete",
                "suggested_resources": [],
                "updated": False
            }
    
    def _get_resources_for_skill(self, session, skill_id: str) -> List[dict]:
        """
        Get curated resources (lessons, Khan links, etc.) for a skill.
        
        Returns list of resources with title, url, type.
        """
        result = session.run("""
            MATCH (s:Skill {id: $skill_id})
            OPTIONAL MATCH (s)-[:HAS_RESOURCE]->(r:Lesson)
            RETURN collect({
              title: r.title,
              content: r.content,
              url: r.url,
              type: 'lesson'
            }) AS resources
        """, skill_id=skill_id)
        
        data = result.single()
        resources = data["resources"] if data else []
        # Filter out nulls
        return [r for r in resources if r["title"]]
    
    def update_due_date(self, user: str, skill_id: str, correct: bool) -> dict:
        """
        Update the spaced repetition due date for a skill.
        
        SM-2 style intervals:
        - If correct: increase interval (1, 3, 7, 14 days...)
        - If wrong: reset to 1 day
        
        Args:
            user: Username
            skill_id: Skill ID
            correct: Whether the last attempt was correct
        
        Returns:
            dict with updated due_at
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (u:User {name: $user})-[r:HAS_PROGRESS]->(s:Skill {id: $skill_id})
                
                // Calculate new interval
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
                  WHEN $correct THEN 
                    CASE 
                      WHEN r.interval IS NULL THEN 1
                      WHEN r.interval = 1 THEN 3
                      WHEN r.interval = 3 THEN 7
                      WHEN r.interval = 7 THEN 14
                      ELSE 30
                    END
                  ELSE
                    1
                END
                
                RETURN {
                  skill_id: s.id,
                  due_at: r.due_at,
                  interval: r.interval
                } AS spaced_review
            """, user=user, skill_id=skill_id, correct=correct)
            
            data = result.single()
            return data["spaced_review"] if data else {}
    
    def get_dashboard(self, user: str) -> dict:
        """
        Get Julia's learning dashboard summary.
        
        Returns:
            dict with overall stats and top skills needing work
        """
        with self.driver.session() as session:
            # Get overall stats
            stats = session.run("""
                MATCH (user:User {name: $user})-[prog:HAS_PROGRESS]->(skill:Skill)
                RETURN {
                  total_skills: count(skill),
                  mastered: count(skill WHERE prog.p_mastery >= 0.9),
                  practicing: count(skill WHERE prog.p_mastery >= 0.5 AND prog.p_mastery < 0.9),
                  struggling: count(skill WHERE prog.p_mastery < 0.5),
                  avg_mastery: avg(prog.p_mastery),
                  total_seen: sum(prog.seen),
                  total_correct: sum(prog.correct)
                } AS stats
            """, user=user).single()["stats"]
            
            # Get skills needing work (lowest mastery)
            skills = session.run("""
                MATCH (user:User {name: $user})-[prog:HAS_PROGRESS]->(skill:Skill)
                WHERE skill.domain = "Quadratics"
                OPTIONAL MATCH (skill)-[:HAS_TAG]->(mis:Misconception)
                RETURN {
                  skill_id: skill.id,
                  skill_name: skill.name,
                  p_mastery: prog.p_mastery,
                  seen: prog.seen,
                  correct: prog.correct,
                  misconceptions: collect(DISTINCT mis.name)
                } AS skill
                ORDER BY prog.p_mastery ASC
                LIMIT 5
            """, user=user)
            
            top_skills = [record["skill"] for record in skills]
            
            return {
                "stats": stats,
                "top_skills_to_practice": top_skills
            }
    
    def get_next_skill_recommendation(self, user: str) -> Optional[dict]:
        """
        Recommend the next skill Julia should practice (entropy-based).
        Prioritizes skills closest to 0.5 mastery.
        
        Returns:
            dict with recommended skill and rationale, or None if all mastered
        """
        with self.driver.session() as session:
            result = session.run("""
                MATCH (user:User {name: $user})-[prog:HAS_PROGRESS]->(skill:Skill)
                WHERE skill.domain = "Quadratics" AND prog.p_mastery < 0.9
                WITH skill, prog,
                     abs(prog.p_mastery - 0.5) AS entropy_gap
                ORDER BY entropy_gap ASC
                LIMIT 1
                RETURN {
                  skill_id: skill.id,
                  skill_name: skill.name,
                  description: skill.description,
                  p_mastery: prog.p_mastery,
                  rationale: CASE 
                    WHEN prog.p_mastery < 0.3 THEN "You're struggling - let's build confidence"
                    WHEN prog.p_mastery < 0.5 THEN "You're close to half-way - keep going!"
                    WHEN prog.p_mastery < 0.7 THEN "Good progress - aim for mastery"
                    ELSE "Almost there!"
                  END
                } AS recommendation
            """, user=user)
            
            data = result.single()
            return data["recommendation"] if data else None


# Helper function for Streamlit integration
def sync_to_neo4j(user: str, 
                  skill_id: str, 
                  correct: bool, 
                  tags: List[str],
                  uri: str = "bolt://localhost:7687") -> dict:
    """
    Sync a single question result to Neo4j.
    
    Usage in Streamlit:
        result = grade(item, choice)
        correct, tags, chosen_text, score = result
        neo_result = sync_to_neo4j("Julia", item["skill_id"], correct, tags)
        if neo_result["remediation"]:
            st.warning(f"Remediation suggested: {neo_result['remediation']['lesson_title']}")
    """
    sync = Neo4jSync(uri=uri)
    try:
        return sync.update_progress(user, skill_id, correct, tags)
    finally:
        sync.close()


def log_attempt_to_neo4j(user: str,
                        skill_id: str,
                        item_id: str,
                        correct: bool,
                        tags: List[str],
                        time_ms: int = 0,
                        confidence: Optional[int] = None,
                        uri: str = "bolt://localhost:7687") -> dict:
    """
    Log an attempt as an immutable record.
    
    Usage in Streamlit (after grading):
        result = grade(item, choice)
        correct, tags, chosen_text, score = result
        attempt = log_attempt_to_neo4j(
            user="Julia",
            skill_id=item["skill_id"],
            item_id=item["id"],
            correct=correct,
            tags=tags,
            time_ms=elapsed_ms
        )
        # attempt["attempt_id"] is the unique log entry
    """
    sync = Neo4jSync(uri=uri)
    try:
        return sync.log_attempt(user, skill_id, item_id, correct, tags, time_ms, confidence)
    finally:
        sync.close()


def track_misconceptions_to_neo4j(user: str,
                                 skill_id: str,
                                 tags: List[str],
                                 uri: str = "bolt://localhost:7687") -> dict:
    """
    Track misconceptions and trigger remediation when threshold is reached.
    
    Usage in Streamlit (after grading if tags detected):
        result = grade(item, choice)
        correct, tags, chosen_text, score = result
        
        if tags:
            misconception_data = track_misconceptions_to_neo4j(
                user="Julia",
                skill_id=item["skill_id"],
                tags=tags
            )
            
            if misconception_data["remediation"]:
                # Show mini-lesson
                rem = misconception_data["remediation"]
                st.warning(f"📚 {rem['misconception_name']}")
                st.write(f"**{rem['lesson_title']}**")
                st.write(rem['lesson_content'])
    """
    sync = Neo4jSync(uri=uri)
    try:
        return sync.track_misconceptions(user, skill_id, tags)
    finally:
        sync.close()


def plan_next_skill_for_neo4j(user: str,
                             uri: str = "bolt://localhost:7687") -> dict:
    """
    Get the next skill to present using adaptive routing logic.
    
    Priority:
    1. Remediation jump (misconception detected ≥2 times)
    2. Learning path (lowest-mastery unmastered skill, prerequisites satisfied)
    3. Spaced review (oldest overdue mastered skill)
    4. Completion (all skills mastered)
    
    Usage in Streamlit:
        plan = plan_next_skill_for_neo4j("julia")
        
        if plan["next_skill_id"]:
            st.info(f"🎯 {plan['next_skill_name']}")
            st.caption(plan['reason'])
            
            if plan.get("suggested_resources"):
                st.subheader("📚 Resources")
                for resource in plan["suggested_resources"]:
                    if resource.get("url"):
                        st.link_button(resource["title"], resource["url"])
                    else:
                        st.write(f"**{resource['title']}**: {resource.get('content', '')}")
        else:
            st.success(plan['reason'])
    """
    sync = Neo4jSync(uri=uri)
    try:
        return sync.plan_next_skill(user)
    finally:
        sync.close()


def update_spaced_review_for_neo4j(user: str,
                                  skill_id: str,
                                  correct: bool,
                                  uri: str = "bolt://localhost:7687") -> dict:
    """
    Update the spaced repetition due date after an attempt.
    
    Uses SM-2 style intervals:
    - Correct: 1d → 3d → 7d → 14d → 30d
    - Wrong: always reset to 1d
    
    Usage in Streamlit:
        # After grading and updating mastery
        spaced = update_spaced_review_for_neo4j(
            user="julia",
            skill_id=item["skill_id"],
            correct=correct
        )
        # spaced["due_at"] is when to show this skill again
    """
    sync = Neo4jSync(uri=uri)
    try:
        return sync.update_due_date(user, skill_id, correct)
    finally:
        sync.close()


if __name__ == "__main__":
    # Quick test
    sync = Neo4jSync()
    
    # Simulate a few quiz results
    print("Simulating Julia's quiz results...\n")
    
    results = [
        ("quad.form.identify.vertex", True, []),
        ("quad.form.identify.vertex", True, []),
        ("quad.form.identify.vertex", False, ["vertex_sign_flip"]),
        ("quad.solve.by_factoring", True, []),
        ("quad.solve.by_factoring", False, ["wrong_pair"]),
    ]
    
    for skill_id, correct, tags in results:
        result = sync.update_progress("Julia", skill_id, correct, tags)
        print(f"✓ {skill_id}: {result['progress']['p_mastery']:.2f}")
        if result['remediation']:
            print(f"  → Remediation: {result['remediation']['lesson_title']}")
    
    # Show dashboard
    print("\n" + "="*60)
    print("JULIA'S LEARNING DASHBOARD")
    print("="*60)
    dashboard = sync.get_dashboard("Julia")
    stats = dashboard['stats']
    print(f"\nStats:")
    print(f"  Mastered: {stats['mastered']}/{stats['total_skills']}")
    print(f"  Practicing: {stats['practicing']}/{stats['total_skills']}")
    print(f"  Struggling: {stats['struggling']}/{stats['total_skills']}")
    print(f"  Avg Mastery: {stats['avg_mastery']:.2%}")
    
    print(f"\nTop Skills to Practice:")
    for skill in dashboard['top_skills_to_practice'][:3]:
        print(f"  • {skill['skill_name']} ({skill['p_mastery']:.0%})")
    
    # Get recommendation
    print(f"\nNext Recommended Skill:")
    rec = sync.get_next_skill_recommendation("Julia")
    if rec:
        print(f"  {rec['skill_name']}")
        print(f"  {rec['rationale']}")
    
    sync.close()
