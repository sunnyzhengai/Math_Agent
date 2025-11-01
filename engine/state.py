
import json, os
from collections import defaultdict

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

def _user_path(username:str):
    safe = "".join(ch for ch in username if ch.isalnum() or ch in ("-","_")).strip() or "user"
    return os.path.join(DATA_DIR, f"{safe}.json")

def load_user_state(username:str):
    path = _user_path(username)
    if not os.path.exists(path):
        return {"username": username, "skills": {}, "history": []}
    with open(path,"r") as f:
        return json.load(f)

def save_user_state(username:str, state:dict):
    path = _user_path(username)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path,"w") as f:
        json.dump(state, f, indent=2)

def ensure_skill(state:dict, skill_id:str):
    skills = state.setdefault("skills", {})
    if skill_id not in skills:
        skills[skill_id] = {
            "p_mastery": 0.6,
            "seen": 0,
            "correct": 0,
            "streak": 0,
            "attempts": 0,  # Track question count for progression array
            "tag_counts": {}
        }
    return skills[skill_id]

def update_after_answer(state:dict, skill_id:str, correct:bool, tags:list, delta_win=0.08, delta_loss=0.12, difficulty_weight=1.0):
    s = ensure_skill(state, skill_id)
    s["seen"] += 1
    s["attempts"] = s.get("attempts", 0) + 1  # Increment question count
    if correct:
        s["correct"] += 1
        s["correct_streak"] = s.get("correct_streak", 0) + 1
        s["p_mastery"] = max(0.0, min(1.0, s["p_mastery"] + delta_win * difficulty_weight))
    else:
        s["correct_streak"] = 0
        s["p_mastery"] = max(0.0, min(1.0, s["p_mastery"] - delta_loss * difficulty_weight))
    # tags
    counts = s.setdefault("tag_counts", {})
    for t in tags:
        counts[t] = counts.get(t, 0) + 1

def mastered(state:dict, skill_id:str):
    s = ensure_skill(state, skill_id)
    return s["p_mastery"] >= 0.9 and s.get("correct_streak", 0) >= 3
