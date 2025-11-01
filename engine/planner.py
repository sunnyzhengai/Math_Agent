
import json, os
from typing import Optional
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
    # Exclude 'correct' tag (which is always high) and only look at misconception tags
    if not tag_counts:
        return None
    
    # Filter out 'correct' tag
    error_tags = {tag: count for tag, count in tag_counts.items() if tag != "correct"}
    
    if not error_tags:
        return None
    
    max_tag = max(error_tags, key=lambda k: error_tags[k])
    if error_tags[max_tag] >= 2:
        return MIS_BY_ID.get(max_tag, {}).get("remedy_skill")
    return None

def next_skill(state:dict):
    """
    Pick the next skill based on:
    1) Check if current skill has 3+ correct streak → move to next skill in prerequisites
    2) remediation need (tag repeated)
    3) otherwise, skill with p_mastery closest to 0.5 (entropy-based selection)
    4) respect prerequisites
    5) randomize when multiple candidates are equally good
    """
    import random
    
    # Check if any skill has 3+ correct streak → rotate to next skill in prerequisites
    last_selected = state.get("last_selected_skill")  # Track previous selection to prevent ping-ponging
    
    for s in SKILL_LIST:
        sid = s["id"]
        
        # If this is the skill we just rotated to, keep practicing it!
        if sid == last_selected:
            return sid  # ← RETURN IT, don't skip!
        
        st = state.get("skills", {}).get(sid, {})
        streak = st.get("correct_streak", 0)
        
        if streak >= 3:
            # This skill has 3 correct answers! Find a skill that has this as a prerequisite
            for next_skill_candidate in SKILL_LIST:
                next_sid = next_skill_candidate["id"]
                # Skip if already mastered
                if mastered(state, next_sid):
                    continue
                # Check if current skill is a prerequisite for next skill
                if sid in next_skill_candidate.get("prereqs", []):
                    # Reset streak on this skill so we don't keep rotating
                    if sid not in state.get("skills", {}):
                        state["skills"][sid] = {}
                    state["skills"][sid]["correct_streak"] = 0
                    state["last_selected_skill"] = next_sid  # Track that we selected this
                    return next_sid
    
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

def generate_adaptive_item(skill_id: str, state: dict, seed: Optional[int] = None, difficulty_hint: Optional[str] = None):
    """
    Generate a question with adaptive difficulty selection.
    
    1. Check skill's progression array (if available)
       - Use question count within the skill to index into progression
    2. Fallback to adaptive mastery-based selection
    3. Get learner's current mastery for the skill
    4. Generate and return the item
    
    Progression arrays ensure natural cadence:
      Q1-2: easy (confidence)
      Q3-4: medium (challenge)
      Q5-6: hard (stretch)
      Q7+: hard/applied (deep mastery)
    """
    # Get current mastery (default to 0.6 for new skills)
    skill_state = state.get("skills", {}).get(skill_id, {})
    p_mastery = skill_state.get("p_mastery", 0.6)
    streak = skill_state.get("streak", 0)
    attempts = skill_state.get("attempts", 0)  # How many questions for this skill
    
    # Get the skill definition to check for progression array
    skill_def = SKILL_BY_ID.get(skill_id, {})
    progression = skill_def.get("progression")
    
    # Determine difficulty (allow override for testing)
    if difficulty_hint:
        difficulty = difficulty_hint
        difficulty_source = "hint"
    elif progression and attempts < len(progression):
        # Use progression array to ensure natural cadence
        difficulty = progression[attempts]
        difficulty_source = "progression"
    else:
        # Fallback to adaptive mastery-based selection
        difficulty = select_difficulty(p_mastery, streak)
        difficulty_source = "adaptive"
    
    # Generate item with selected difficulty (pass seed for reproducibility)
    item = templates.generate_item(skill_id, difficulty, seed=seed)
    
    # Store the difficulty in item metadata for logging
    item["adaptive_difficulty"] = difficulty
    item["learner_mastery"] = p_mastery
    item["difficulty_source"] = difficulty_source
    item["progression_index"] = attempts if progression else None
    
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
