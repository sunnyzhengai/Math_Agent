#!/usr/bin/env python3
"""
Load Quadratics Skill Graph into Neo4j

Usage:
    python3 scripts/load_neo4j_skills.py \
      --uri bolt://localhost:7687 \
      --username neo4j \
      --password password \
      --json data/quadratics_skill_graph.json
"""

import json
import argparse
from pathlib import Path

try:
    from neo4j import GraphDatabase
    DRIVER_AVAILABLE = True
except ImportError:
    DRIVER_AVAILABLE = False


def load_skill_graph(
    uri: str,
    username: str,
    password: str,
    json_path: str,
    clear_first: bool = False
):
    """Load skill graph from JSON into Neo4j."""
    
    if not DRIVER_AVAILABLE:
        print("❌ neo4j-driver not installed. Install with:")
        print("   pip install neo4j")
        return False
    
    # Load JSON
    json_file = Path(json_path)
    if not json_file.exists():
        print(f"❌ JSON file not found: {json_path}")
        return False
    
    with open(json_file) as f:
        data = json.load(f)
    
    skills = data.get('skills', [])
    domain = data.get('domain', 'Quadratics')
    
    print(f"\n📋 Loading {len(skills)} skills from {domain}...")
    print(f"   Connecting to: {uri}")
    
    # Connect to Neo4j
    try:
        driver = GraphDatabase.driver(uri, auth=(username, password))
        driver.verify_connectivity()
        print("   ✅ Connected to Neo4j")
    except Exception as e:
        print(f"   ❌ Connection failed: {e}")
        return False
    
    try:
        with driver.session() as session:
            # Optional: Clear old data
            if clear_first:
                print("\n🗑️  Clearing old Quadratics skills...")
                result = session.run(
                    "MATCH (n:Skill {domain:$domain}) DETACH DELETE n RETURN count(n) AS deleted",
                    domain=domain
                )
                deleted = result.single()['deleted']
                print(f"   Deleted {deleted} old skills")
            
            # Create Skill nodes
            print(f"\n📍 Creating {len(skills)} Skill nodes...")
            for skill in skills:
                session.run(
                    """
                    MERGE (k:Skill {id:$id})
                    SET k.name = $name,
                        k.description = $description,
                        k.domain = $domain
                    """,
                    id=skill['id'],
                    name=skill['name'],
                    description=skill['description'],
                    domain=domain
                )
            print("   ✅ Created Skill nodes")
            
            # Create LEADS_TO edges
            print(f"\n🔗 Creating LEADS_TO edges...")
            leads_to_count = 0
            for skill in skills:
                for successor_id in skill.get('successors', []):
                    session.run(
                        """
                        MATCH (a:Skill {id:$id}), (b:Skill {id:$successor})
                        MERGE (a)-[:LEADS_TO]->(b)
                        """,
                        id=skill['id'],
                        successor=successor_id
                    )
                    leads_to_count += 1
            print(f"   ✅ Created {leads_to_count} LEADS_TO edges")
            
            # Create PRECEDES edges
            print(f"\n📚 Creating PRECEDES edges...")
            precedes_count = 0
            for skill in skills:
                for prereq_id in skill.get('prereqs', []):
                    session.run(
                        """
                        MATCH (p:Skill {id:$prereq}), (a:Skill {id:$id})
                        MERGE (p)-[:PRECEDES]->(a)
                        """,
                        prereq=prereq_id,
                        id=skill['id']
                    )
                    precedes_count += 1
            print(f"   ✅ Created {precedes_count} PRECEDES edges")
            
            # Verify
            print(f"\n✅ Verification:")
            result = session.run(
                "MATCH (s:Skill {domain:$domain}) RETURN count(s) AS count",
                domain=domain
            )
            skill_count = result.single()['count']
            print(f"   Total skills: {skill_count}")
            
            result = session.run(
                "MATCH (s:Skill {domain:$domain})-[r:LEADS_TO]->(t) RETURN count(r) AS count",
                domain=domain
            )
            leads_to_edges = result.single()['count']
            print(f"   LEADS_TO edges: {leads_to_edges}")
            
            result = session.run(
                "MATCH (s:Skill {domain:$domain})-[r:PRECEDES]->(t) RETURN count(r) AS count",
                domain=domain
            )
            precedes_edges = result.single()['count']
            print(f"   PRECEDES edges: {precedes_edges}")
            
            # Find entry and exit points
            result = session.run(
                "MATCH (s:Skill {domain:$domain}) WHERE NOT (s)<-[:PRECEDES]-(:Skill) RETURN collect(s.id) AS entry",
                domain=domain
            )
            entry_points = result.single()['entry']
            print(f"   Entry points: {entry_points}")
            
            result = session.run(
                "MATCH (s:Skill {domain:$domain}) WHERE NOT (s)-[:LEADS_TO]->(:Skill) RETURN collect(s.id) AS exit",
                domain=domain
            )
            exit_points = result.single()['exit']
            print(f"   Exit points: {exit_points}")
        
        print("\n🎉 Successfully loaded Quadratics skill graph!")
        return True
        
    except Exception as e:
        print(f"\n❌ Error during load: {e}")
        return False
    finally:
        driver.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Load Quadratics Skill Graph into Neo4j"
    )
    parser.add_argument(
        "--uri",
        default="bolt://localhost:7687",
        help="Neo4j connection URI (default: bolt://localhost:7687)"
    )
    parser.add_argument(
        "--username",
        default="neo4j",
        help="Neo4j username (default: neo4j)"
    )
    parser.add_argument(
        "--password",
        default="password",
        help="Neo4j password (default: password)"
    )
    parser.add_argument(
        "--json",
        default="data/quadratics_skill_graph.json",
        help="Path to JSON skill graph"
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear old Quadratics skills before loading"
    )
    
    args = parser.parse_args()
    
    success = load_skill_graph(
        uri=args.uri,
        username=args.username,
        password=args.password,
        json_path=args.json,
        clear_first=args.clear
    )
    
    exit(0 if success else 1)
