
from engine.grader import grade
from engine import templates

def _get_choice_id_by_tag(item, tag):
    for ch in item["choices"]:
        if tag in ch.get("tags_on_select", []):
            return ch["id"]
    return None

def test_grade_correct_and_tags():
    item = templates.gen_vertex_form()
    cor_id = _get_choice_id_by_tag(item, "correct")
    result = grade(item, cor_id)
    # Handle both old (3-tuple) and new (4-tuple) return formats
    ok, tags, text = result[:3] if len(result) == 4 else result
    score = result[3] if len(result) == 4 else None
    assert ok is True
    assert "correct" in tags
    # If score is present, full credit should be 1.0
    if score is not None:
        assert score == 1.0

def test_grade_incorrect_and_tag_detected():
    item = templates.gen_quadratic_formula()
    wrong_id = _get_choice_id_by_tag(item, "one_root_only") or _get_choice_id_by_tag(item, "sign_error")
    result = grade(item, wrong_id)
    # Handle both old (3-tuple) and new (4-tuple) return formats
    ok, tags, text = result[:3] if len(result) == 4 else result
    score = result[3] if len(result) == 4 else None
    assert ok is False
    assert any(t in tags for t in ["one_root_only", "sign_error"])
    # If score is present, no credit should be 0.0
    if score is not None:
        assert score == 0.0
