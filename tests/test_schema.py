
import os, json

def test_skills_json_schema():
    root = os.path.join(os.path.dirname(__file__), "..")
    path = os.path.join(root, "engine", "skills.json")
    with open(path,"r") as f:
        data = json.load(f)
    assert "skills" in data and isinstance(data["skills"], list)
    for s in data["skills"]:
        for key in ["id","name","prereqs"]:
            assert key in s, f"Missing {key} in skill {s}"
        assert isinstance(s["id"], str) and s["id"]
        assert isinstance(s["name"], str) and s["name"]
        assert isinstance(s["prereqs"], list)

def test_misconceptions_json_schema():
    root = os.path.join(os.path.dirname(__file__), "..")
    path = os.path.join(root, "engine", "misconceptions.json")
    with open(path,"r") as f:
        data = json.load(f)
    assert "tags" in data and isinstance(data["tags"], list)
    for t in data["tags"]:
        assert "id" in t and isinstance(t["id"], str)
        assert "remedy_skill" in t and isinstance(t["remedy_skill"], str)
        assert "lesson" in t and isinstance(t["lesson"], str)
