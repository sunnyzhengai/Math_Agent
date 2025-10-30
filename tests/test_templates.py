
from engine import templates

def _has_one_correct(choices):
    return sum(1 for c in choices if "correct" in c.get("tags_on_select",[])) == 1

def test_generate_factor_a1_shape():
    item = templates.gen_factor_a1()
    assert item["skill_id"] == "quad.factor.a1"
    assert "stem" in item and "choices" in item
    assert len(item["choices"]) >= 3
    assert _has_one_correct(item["choices"])

def test_generate_factor_an1_shape():
    item = templates.gen_factor_an1()
    assert item["skill_id"] == "quad.factor.an1"
    assert _has_one_correct(item["choices"])

def test_generate_vertex_form_shape():
    item = templates.gen_vertex_form()
    assert item["skill_id"] == "quad.vertex.form"
    assert _has_one_correct(item["choices"])

def test_generate_discriminant_shape():
    item = templates.gen_discriminant()
    assert item["skill_id"] == "quad.discriminant"
    assert _has_one_correct(item["choices"])

def test_generate_quadratic_formula_shape():
    item = templates.gen_quadratic_formula()
    assert item["skill_id"] == "quad.formula"
    assert _has_one_correct(item["choices"])

def test_registry_dispatch():
    item = templates.generate_item("quad.factor.a1")
    assert item["skill_id"] == "quad.factor.a1"
