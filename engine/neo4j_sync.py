"""
Neo4j Sync Module - Updates Julia's learning graph in real-time

This module syncs quiz results with her Neo4j knowledge graph,
automatically updating mastery scores and triggering remediation.
"""

from neo4j import GraphDatabase
from typing import Optional, List
import os


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
    
    def update_progress(self, 
                       user: str,
                       skill_id: str, 
                       correct: bool, 
                       tags: List[str],
                       delta_win: float = 0.08,
                       delta_loss: float = 0.12) -> dict:
        """
        Update user's progress on a skill after answering a question.
        
        Args:
            user: Username (e.g., "Julia")
            skill_id: Skill ID (e.g., "quad.form.identify.vertex")
            correct: Whether the answer was correct
            tags: List of misconception tags detected
            delta_win: Points to add if correct (0-1)
            delta_loss: Points to subtract if wrong (0-1)
        
        Returns:
            dict with updated progress and any triggered remediation
        """
        
        with self.driver.session() as session:
            # Update progress node
            result = session.run("""
                MATCH (user:User {name: $user})-[prog:HAS_PROGRESS]->(skill:Skill {id: $skill_id})
                SET prog.seen = prog.seen + 1,
                    prog.correct = CASE WHEN $correct THEN prog.correct + 1 ELSE prog.correct END,
                    prog.streak = CASE WHEN $correct THEN prog.streak + 1 ELSE 0 END,
                    prog.last_attempt = datetime(),
                    prog.p_mastery = CASE 
                        WHEN $correct THEN min(1.0, prog.p_mastery + $delta_win)
                        ELSE max(0.0, prog.p_mastery - $delta_loss)
                    END
                RETURN {
                  skill_id: skill.id,
                  skill_name: skill.name,
                  p_mastery: prog.p_mastery,
                  seen: prog.seen,
                  correct: prog.correct,
                  streak: prog.streak,
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
