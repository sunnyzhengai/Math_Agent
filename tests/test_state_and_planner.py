
from engine.state import load_user_state, save_user_state, ensure_skill, update_after_answer, mastered
from engine.planner import next_skill, generate_item_for_skill, lesson_for_tags, MIS_BY_ID

def test_state_lifecycle(tmp_path, monkeypatch):
    import engine.state as st
    old = st.DATA_DIR
    st.DATA_DIR = str(tmp_path)
    try:
        s = load_user_state("alice")
        assert s["username"] == "alice"
        ensure_skill(s, "quad.vertex.form")
        save_user_state("alice", s)
        s2 = load_user_state("alice")
        assert "quad.vertex.form" in s2["skills"]
    finally:
        st.DATA_DIR = old

def test_mastery_update_and_rule():
    s = {"username":"bob", "skills":{}}
    sid = "quad.vertex.form"
    for _ in range(12):
        update_after_answer(s, sid, True, ["correct"])
    assert mastered(s, sid) is True

def test_planner_remediation_trigger():
    s = {"username":"eve", "skills":{}}
    sid = "quad.vertex.form"
    update_after_answer(s, sid, False, ["axis_wrong_direction"])
    update_after_answer(s, sid, False, ["axis_wrong_direction"])
    remedy = MIS_BY_ID["axis_wrong_direction"]["remedy_skill"]
    picked = next_skill(s)
    assert picked == remedy
