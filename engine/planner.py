
import json, os
from .state import ensure_skill, mastered
from . import templates

ROOT = os.path.dirname(__file__)

def load_skills():
    """Load skills from JSON file (called fresh each time for hot-reload support)"""
    with open(os.path.join(ROOT,"skills.json")) as f:
        return json.load(f)["skills"]

def load_misconceptions():
    with open(os.path.join(ROOT,"misconceptions.json")) as f:
        data = json.load(f)
        return {t["id"]: t for t in data["tags"]}

# Module-level cache (can be reloaded)
SKILL_LIST = load_skills()
SKILL_BY_ID = {s["id"]: s for s in SKILL_LIST}
MIS_BY_ID = load_misconceptions()

def reload_skills():
    """Force reload skills from disk (for Streamlit hot-reload)"""
    global SKILL_LIST, SKILL_BY_ID, MIS_BY_ID
    SKILL_LIST = load_skills()
    SKILL_BY_ID = {s["id"]: s for s in SKILL_LIST}
    MIS_BY_ID = load_misconceptions()
    return SKILL_LIST

def _remediation_for_tags(tag_counts:dict):
    # If any tag count >=2, route to its remedy_skill
    if not tag_counts:
        return None
    max_tag = max(tag_counts, key=lambda k: tag_counts[k])
    if tag_counts[max_tag] >= 2:
        return MIS_BY_ID.get(max_tag, {}).get("remedy_skill")
    return None

def next_skill(state:dict):
    """
    Pick the next skill based on:
    1) remediation need (tag repeated)
    2) otherwise, skill with p_mastery closest to 0.5 (entropy-based selection)
    3) respect prerequisites
    4) randomize when multiple candidates are equally good
    """
    import random
    
    # remediation check across recent skill
    # find the skill with any tag >=2 that is not yet mastered
    for s in SKILL_LIST:
        sid = s["id"]
        st = state.get("skills", {}).get(sid, None)
        if st:
            remed = _remediation_for_tags(st.get("tag_counts", {}))
            if remed and not mastered(state, remed):
                return remed

    # Check which skills have their prerequisites met
    def prereqs_met(skill_id):
        skill = SKILL_BY_ID.get(skill_id)
        if not skill:
            return False
        for prereq in skill.get("prereqs", []):
            if not mastered(state, prereq):
                return False
        return True

    # entropy pick: find skills closest to 0.5 mastery
    candidates = []
    best_gap = 999
    
    for s in SKILL_LIST:
        sid = s["id"]
        
        # Skip mastered skills
        if mastered(state, sid):
            continue
        
        # Skip skills without prerequisites met
        if not prereqs_met(sid):
            continue
        
        st = state.get("skills", {}).get(sid, {"p_mastery": 0.6})
        gap = abs(st["p_mastery"] - 0.5)
        
        if gap < best_gap:
            best_gap = gap
            candidates = [sid]  # New best, reset candidates
        elif gap == best_gap:
            candidates.append(sid)  # Tie, add to candidates
    
    # If we found candidates, pick one randomly
    if candidates:
        return random.choice(candidates)
    
    # Fallback to first skill
    return SKILL_LIST[0]["id"]

def select_difficulty(p_mastery: float, streak: int = 0) -> str:
    """
    Adaptively select question difficulty based on learner's mastery level.
    
    Rules:
    - p_mastery < 0.5: "easy" (confidence building)
    - 0.5 ≤ p_mastery < 0.7: "medium" (challenge zone)
    - 0.7 ≤ p_mastery < 0.85: "hard" (stretch)
    - p_mastery ≥ 0.85: "hard" (advanced)
    
    With 15% random variation to keep it engaging.
    """
    import random
    
    # Add randomness 15% of the time
    if random.random() < 0.15:
        return random.choice(["easy", "medium", "hard"])
    
    # Deterministic rules based on mastery
    if p_mastery < 0.5:
        return "easy"
    elif p_mastery < 0.7:
        return "medium"
    elif p_mastery < 0.85:
        return "hard"
    else:
        return "hard"  # Already advanced, keep stretching

def generate_adaptive_item(skill_id: str, state: dict):
    """
    Generate a question with adaptive difficulty selection.
    
    1. Get learner's current mastery for the skill
    2. Select appropriate difficulty
    3. Generate and return the item
    """
    # Get current mastery (default to 0.6 for new skills)
    skill_state = state.get("skills", {}).get(skill_id, {})
    p_mastery = skill_state.get("p_mastery", 0.6)
    streak = skill_state.get("streak", 0)
    
    # Select difficulty adaptively
    difficulty = select_difficulty(p_mastery, streak)
    
    # Generate item with selected difficulty
    item = templates.generate_item(skill_id, difficulty)
    
    # Store the difficulty in item metadata for logging
    item["adaptive_difficulty"] = difficulty
    item["learner_mastery"] = p_mastery
    
    return item

def generate_item_for_skill(skill_id:str, difficulty="med"):
    return templates.generate_item(skill_id, difficulty)

def lesson_for_tags(tags:list):
    lessons = []
    for t in tags or []:
        info = MIS_BY_ID.get(t)
        if info and "lesson" in info:
            lessons.append((t, info["lesson"]))
    return lessons
