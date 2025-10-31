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
