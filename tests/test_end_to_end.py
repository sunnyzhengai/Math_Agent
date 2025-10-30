
from engine import templates
from engine.grader import grade
from engine.state import update_after_answer
from engine.planner import next_skill

def test_end_to_end_session():
    state = {"username":"julia", "skills":{}, "history":[]}
    sid = next_skill(state)
    assert isinstance(sid, str) and sid
    item = templates.generate_item(sid)
    wrong_choice = next(c["id"] for c in item["choices"] if "correct" not in c.get("tags_on_select",[]))
    result = grade(item, wrong_choice)
    # Handle both old (3-tuple) and new (4-tuple) return formats
    ok, tags, text = result[:3] if len(result) == 4 else result
    update_after_answer(state, sid, ok, tags)
    sid2 = next_skill(state)
    assert isinstance(sid2, str) and sid2
