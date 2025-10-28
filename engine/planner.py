
import json, os
from .state import ensure_skill, mastered
from . import templates
from math import fabs

ROOT = os.path.dirname(__file__)

def load_skills():
    with open(os.path.join(ROOT,"skills.json")) as f:
        return json.load(f)["skills"]

def load_misconceptions():
    with open(os.path.join(ROOT,"misconceptions.json")) as f:
        data = json.load(f)
        return {t["id"]: t for t in data["tags"]}

SKILL_LIST = load_skills()
SKILL_BY_ID = {s["id"]: s for s in SKILL_LIST}
MIS_BY_ID = load_misconceptions()

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
    2) otherwise, skill with p_mastery closest to 0.5
    Exclude mastered skills.
    """
    # remediation check across recent skill
    # find the skill with any tag >=2 that is not yet mastered
    candidates = []
    for s in SKILL_LIST:
        sid = s["id"]
        st = state.get("skills", {}).get(sid, None)
        if st:
            remed = _remediation_for_tags(st.get("tag_counts", {}))
            if remed and not mastered(state, remed):
                return remed

    # entropy pick
    best_sid = None
    best_gap = 999
    for s in SKILL_LIST:
        sid = s["id"]
        if mastered(state, sid):
            continue
        st = state.get("skills", {}).get(sid, {"p_mastery":0.6})
        gap = abs(st["p_mastery"] - 0.5)
        if gap < best_gap:
            best_gap = gap
            best_sid = sid
    return best_sid or SKILL_LIST[0]["id"]

def generate_item_for_skill(skill_id:str, difficulty="med"):
    return templates.generate_item(skill_id, difficulty)

def lesson_for_tags(tags:list):
    lessons = []
    for t in tags or []:
        info = MIS_BY_ID.get(t)
        if info and "lesson" in info:
            lessons.append((t, info["lesson"]))
    return lessons
