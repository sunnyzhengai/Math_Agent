
import random
import copy
from math import gcd
from .math_validators import validate_item_math

def _shuffle_choices(choices):
    # Make a deep copy so we don't mutate the original
    choices_copy = copy.deepcopy(choices)
    random.shuffle(choices_copy)
    # Keep original IDs - they're already correctly set (a/b/c/d)
    return choices_copy

def _format_poly(a, b, c, var="x"):
    """Format a polynomial ax^2 + bx + c with proper superscripts and clean notation."""
    terms = []
    
    # Handle x^2 term
    if a != 0:
        if a == 1:
            terms.append(f"{var}²")
        elif a == -1:
            terms.append(f"-{var}²")
        else:
            terms.append(f"{a}{var}²")
    
    # Handle x term
    if b != 0:
        if b > 0 and terms:
            if b == 1:
                terms.append(f"+ {var}")
            else:
                terms.append(f"+ {b}{var}")
        else:
            if b == 1:
                terms.append(f"{var}")
            elif b == -1:
                terms.append(f"-{var}")
            else:
                terms.append(f"{b}{var}")
    
    # Handle constant term
    if c != 0:
        if c > 0 and terms:
            terms.append(f"+ {c}")
        else:
            terms.append(f"{c}")
    
    result = " ".join(terms)
    # Clean up any "- -" to just "-"
    result = result.replace("- -", "+ ").replace("+ -", "- ")
    return result

def _format_factored(factors):
    """Format factored form with proper notation."""
    return factors.replace("^2", "²").replace("+ -", "- ")

def _simplify_coefficients(a, b, c):
    """Simplify quadratic coefficients by dividing by their GCD.
    Returns (a, b, c) with GCD = 1, or original if GCD = 1."""
    g = gcd(gcd(abs(a), abs(b)), abs(c))
    if g > 1:
        return a // g, b // g, c // g
    return a, b, c

def _infer_difficulty(a=None, b=None, c=None, h=None, k=None, has_fractions=False, num_params=None):
    """
    Auto-infer difficulty based on parameters:
    - easy: single digit coefficients, a=1, integer params, no negatives
    - medium: a≠1, mixed signs, moderate values
    - hard: large coefficients, multiple negatives, fractions/decimals
    - applied: requires interpretation beyond simple computation
    
    Returns: "easy", "medium", "hard", or "applied"
    """
    if has_fractions:
        return "hard"
    
    # Count parameters for complexity estimate
    params = [p for p in [a, b, c, h, k] if p is not None]
    
    if not params:
        return "medium"  # default
    
    # Easy: a=1, small absolute values, all positive or simple sign pattern
    if a is not None:
        if a == 1:
            max_val = max(abs(p) for p in params if p is not None)
            if max_val <= 3:
                return "easy"
        elif abs(a) > 3:
            return "hard"  # large leading coefficient
    
    # Hard: large coefficients or many negative signs
    max_val = max(abs(p) for p in params if p is not None)
    if max_val >= 6:
        return "hard"
    
    # Medium: moderate complexity
    if a is not None and a != 1:
        return "medium"
    
    # Count negative values (sign complexity)
    neg_count = sum(1 for p in params if p is not None and p < 0)
    if neg_count >= 2:
        return "medium"
    
    return "easy"


def gen_factor_a1(difficulty="med"):
    """
    Generate x^2 + b x + c factorable with a=1
    Returns an item dict with diagnostic choices.
    """
    pairs = [(1,1),(1,2),(1,3),(2,3),(2,4),(3,4),(3,5)]
    if difficulty=="hard":
        pairs += [(4,5),(4,6),(5,6),(5,7)]
    p,q = random.choice(pairs)
    sgn_b = random.choice([1,-1])
    sgn_c = 1 if random.random()<0.5 else -1
    # ensure factorable: (x + sp)(x + sq) with signs
    sp = sgn_b * p
    sq = sgn_b * q if sgn_c>0 else -sgn_b * q
    b = sp + sq
    c = sp * sq

    stem = f"Factor: {_format_poly(1, b, c)}"
    correct = _format_factored(f"(x + {sp})(x + {sq})".replace("+ -","- "))
    # distractors
    d1 = _format_factored(f"(x + {p})(x + {q})".replace("+ -","- "))  # ignores signs
    # d2: flip the sign of one factor (not both)
    flipped_sq = -sq
    d2_str = f"(x + {sp})(x + {flipped_sq})"
    d2 = _format_factored(d2_str.replace("+ -","- "))  # sign flip on one
    d3 = _format_factored(f"(x + {sp+1})(x + {sq-1})".replace("+ -","- "))  # wrong pair summing to b
    choices = [
        {"id":"a","text":correct,"tags_on_select":["correct"]},
        {"id":"b","text":d1,"tags_on_select":["sign_error"]},
        {"id":"c","text":d2,"tags_on_select":["sign_error"]},
        {"id":"d","text":d3,"tags_on_select":["wrong_pair"]},
    ]
    # Infer difficulty from parameters
    inferred_diff = _infer_difficulty(a=1, b=b, c=c)
    return {
        "id": f"factor_a1_{abs(b)}_{abs(c)}_{random.randint(1000,9999)}",
        "skill_id":"quad.factor.a1",
        "difficulty": inferred_diff,
        "stem": stem,
        "choices": _shuffle_choices(choices),
        "solution": correct,
        "rationale": "Find integers that multiply to c and add to b; carry signs through both factors."
    }

def gen_factor_an1(difficulty="med"):
    """
    Generate ax^2 + bx + c with a ≠ 1 (factorable)
    Use AC method to ensure factorability.
    """
    a = random.choice([2,3,4,5])
    r,s = random.choice([(1,1),(1,2),(2,3),(1,3)])
    pr_sign = random.choice([1,-1])
    sq_sign = random.choice([1,-1])
    p = pr_sign * r
    q = sq_sign * s
    # Construct (ax + p)(x + q) => ax^2 + (aq + p)x + pq
    b = a*q + p
    c = p*q
    stem = f"Factor: {_format_poly(a, b, c)}"
    correct = _format_factored(f"({a}x + {p})(x + {q})".replace("+ -","- "))
    d1 = _format_factored(f"(x + {p})(x + {q})".replace("+ -","- "))  # missing a (missing_gcf-ish)
    d2 = _format_factored(f"({a}x + {q})(x + {p})".replace("+ -","- "))  # cross product mismatch
    d3 = _format_factored(f"({a}x - {p})(x - {q})".replace("+ -","- "))  # sign flip both
    choices = [
        {"id":"a","text":correct,"tags_on_select":["correct"]},
        {"id":"b","text":d1,"tags_on_select":["missing_gcf"]},
        {"id":"c","text":d2,"tags_on_select":["cross_product_mismatch"]},
        {"id":"d","text":d3,"tags_on_select":["sign_error"]},
    ]
    # Infer difficulty from parameters
    inferred_diff = _infer_difficulty(a=a, b=b, c=c)
    return {
        "id": f"factor_an1_{a}_{abs(b)}_{abs(c)}_{random.randint(1000,9999)}",
        "skill_id":"quad.factor.an1",
        "difficulty": inferred_diff,
        "stem": stem,
        "choices": _shuffle_choices(choices),
        "solution": correct,
        "rationale": "Use AC or factoring by grouping: ensure cross products sum to b and product is ac."
    }

def gen_vertex_form(difficulty="med"):
    """
    Given y = a(x - h)^2 + k ask for vertex and axis/direction.
    """
    a = random.choice([1,2,3,-1,-2])
    h = random.randint(-5,5)
    k = random.randint(-5,5)
    
    # Format the equation properly
    h_str = f"- {h}" if h > 0 else f"+ {abs(h)}"
    k_str = f"+ {k}" if k > 0 else f"- {abs(k)}"
    stem = f"For y = {a}(x {h_str})² {k_str}, what is the vertex and opening direction?"
    
    vertex = f"({h}, {k})"
    direction = "up" if a>0 else "down"
    correct = f"Vertex {vertex}, opens {direction}"
    # distractors
    d1 = f"Vertex ({-h}, {k}), opens {direction}"  # vertex_sign_flip
    d2 = f"Vertex {vertex}, opens {'down' if direction=='up' else 'up'}"  # direction wrong
    # d3 should always differ from correct; if k=0 use 1, else negate k
    wrong_k = 1 if k == 0 else -k
    d3 = f"Vertex ({h}, {wrong_k}), opens {direction}"  # sign error on k
    choices = [
        {"id":"a","text":correct,"tags_on_select":["correct"]},
        {"id":"b","text":d1,"tags_on_select":["vertex_sign_flip"]},
        {"id":"c","text":d2,"tags_on_select":["axis_wrong_direction"]},
        {"id":"d","text":d3,"tags_on_select":["sign_error"]},
    ]
    # Infer difficulty from parameters
    inferred_diff = _infer_difficulty(a=a, h=h, k=k)
    return {
        "id": f"vertex_{a}_{h}_{k}_{random.randint(1000,9999)}",
        "skill_id":"quad.vertex.form",
        "difficulty": inferred_diff,
        "stem": stem,
        "choices": _shuffle_choices(choices),
        "solution": correct,
        "rationale": "In y=a(x-h)²+k, the vertex is (h,k). If a>0 it opens up; if a<0 it opens down."
    }

def gen_discriminant(difficulty="med"):
    """
    Ask for number of real solutions using discriminant.
    """
    a = random.choice([1,2,3,4])
    b = random.choice([-8,-6,-4,-2,0,2,4,6,8])
    c = random.choice([-6,-4,-2,0,2,4,6])
    D = b*b - 4*a*c
    if difficulty=="easy":
        # bias to perfect squares
        c = (b*b)//(4*a) if random.random()<0.3 and 4*a!=0 else c
        D = b*b - 4*a*c
    # Simplify coefficients by dividing by GCD
    a, b, c = _simplify_coefficients(a, b, c)
    D = b*b - 4*a*c  # recalculate D after simplification
    if D>0:
        truth = "two real solutions"
    elif D==0:
        truth = "one real solution"
    else:
        truth = "no real solutions"
    stem = f"For the quadratic {_format_poly(a, b, c)} = 0, how many real solutions are there?"
    choices = [
        {"id":"a","text":truth,"tags_on_select":["correct"]},
        {"id":"b","text":"one real solution" if truth!="one real solution" else "two real solutions","tags_on_select":["under_root_error"]},
        {"id":"c","text":"no real solutions" if truth!="no real solutions" else "two real solutions","tags_on_select":["under_root_error"]},
        {"id":"d","text":"cannot be determined","tags_on_select":["under_root_error"]},
    ]
    # Infer difficulty from parameters
    inferred_diff = _infer_difficulty(a=a, b=b, c=c)
    return {
        "id": f"disc_{a}_{b}_{c}_{random.randint(1000,9999)}",
        "skill_id":"quad.discriminant",
        "difficulty": inferred_diff,
        "stem": stem,
        "choices": _shuffle_choices(choices),
        "solution": truth,
        "rationale": "Discriminant D=b²-4ac: D>0 two real, D=0 one real, D<0 none."
    }

def gen_quadratic_formula(difficulty="med"):
    """
    Solve using quadratic formula; provide correct pair and common errors.
    """
    a = random.choice([1,1,1,2,3])  # bias to easier
    r1 = random.choice([-5,-4,-3,-2,-1,1,2,3,4,5])
    r2 = r1 + random.choice([1,2,3,4])
    # Build from roots to ensure integer/nice solutions
    # For integer roots, construct (x - r1)(x - r2) = 0; then scale by a
    b = -a*(r1 + r2)
    c = a*(r1*r2)
    # Simplify coefficients by dividing by GCD
    a, b, c = _simplify_coefficients(a, b, c)
    # Recalculate roots from simplified coefficients using quadratic formula
    # (We keep the original logic but work with simplified coefficients)
    stem = f"Solve using the quadratic formula: {_format_poly(a, b, c)} = 0"
    correct = f"x = {r1}, {r2}"
    d1 = f"x = {-r1}, {-r2}"  # sign error
    d2 = f"x = {-(b)}/{2*a} ± √({b*b} - 4·{a}·{c})/{2*a}"  # plugged into formula but not simplified
    d3 = f"x = {-(b)}/{2*a}"  # only the midpoint / forgot ±
    choices = [
        {"id":"a","text":correct,"tags_on_select":["correct"]},
        {"id":"b","text":d1,"tags_on_select":["sign_error"]},
        {"id":"c","text":d2,"tags_on_select":["under_root_error"]},
        {"id":"d","text":d3,"tags_on_select":["one_root_only"]},
    ]
    # Infer difficulty from parameters
    inferred_diff = _infer_difficulty(a=a, b=b, c=c)
    return {
        "id": f"qf_{a}_{b}_{c}_{random.randint(1000,9999)}",
        "skill_id":"quad.formula",
        "difficulty": inferred_diff,
        "stem": stem,
        "choices": _shuffle_choices(choices),
        "solution": correct,
        "rationale": "Plug a,b,c into the formula, simplify the radical, and include both ± branches."
    }


def gen_identify_quadratic(difficulty="med"):
    """
    Generate a question asking whether an expression is a quadratic.
    Tests different aspects of quadratic identification.
    """
    import random
    
    # Different categories of quadratics and non-quadratics
    test_cases = [
        # QUADRATICS (is_quad=True)
        # 1. Standard form with all terms
        ("x² + 3x + 2", True, "standard_form_trinomial"),
        ("2x² - 5x + 1", True, "leading_coeff_trinomial"),
        ("3x² + 4x - 7", True, "leading_coeff_trinomial"),
        ("-x² + 2x - 1", True, "negative_leading_coeff"),
        
        # 2. Missing terms (b=0 or c=0)
        ("x² + 5", True, "missing_linear_term"),
        ("x² - 9", True, "missing_linear_term"),
        ("4x²", True, "only_quadratic_term"),
        ("x² + 2x", True, "missing_constant_term"),
        ("-3x²", True, "only_quadratic_term_negative"),
        
        # 3. Factored form (expands to quadratic)
        ("(x - 2)(x + 3)", True, "factored_form"),
        ("(x + 1)(x - 1)", True, "factored_form"),
        ("(2x - 1)(x + 4)", True, "factored_form_with_coeff"),
        
        # 4. Vertex form
        ("(x - 3)²", True, "vertex_form_perfect_square"),
        ("2(x + 1)² - 5", True, "vertex_form_with_coeff"),
        
        # 5. Missing some standard forms but still quadratic
        ("x² + x", True, "missing_constant_term"),  # x² + x + 0
        
        # NON-QUADRATICS (is_quad=False)
        # 6. Linear expressions
        ("x + 3", False, "linear_binomial"),
        ("2x - 5", False, "linear_with_coeff"),
        ("x", False, "linear_monomial"),
        ("5x", False, "linear_monomial_with_coeff"),
        
        # 7. Constants
        ("5", False, "constant"),
        ("0", False, "constant"),
        ("-7", False, "constant"),
        
        # 8. Cubic and higher
        ("x³ + 2x", False, "cubic"),
        ("x³ - x² + 1", False, "cubic_trinomial"),
        ("x⁴ + x²", False, "quartic"),
        ("x⁵ - 3x", False, "quintic"),
        
        # 9. Mixed degree where highest is NOT 2
        ("x² + x³", False, "mixed_cubic_dominant"),
        ("x² + x³ - x", False, "mixed_cubic_dominant"),
        
        # 10. Other confusing cases
        ("(x + 1)(x + 1)(x + 2)", False, "product_three_factors"),  # Expands to cubic
        ("x(x + 5) + 2x + 3", True, "expanded_appears_linear_terms"),  # x² + 5x + 2x + 3 = x² + 7x + 3
    ]
    
    # Pick a random test case
    expr, is_quad, category = random.choice(test_cases)
    
    # Determine correct answer and distractors based on whether it's quadratic
    if is_quad:
        correct = "Yes, this is a quadratic."
        rationale = f"The expression {expr} has degree 2 (highest power is x²), so it is quadratic."
        
        # Distractors that test common misconceptions
        if category == "only_quadratic_term" or category == "only_quadratic_term_negative":
            d1 = "No, it's linear because it only has one term."
            d2 = "No, this is a monomial, not a polynomial."
            d3 = "No, this is too simple."
        elif category in ["factored_form", "factored_form_with_coeff"]:
            d1 = "No, it's in factored form, not expanded."
            d2 = "No, factored expressions can't be quadratic."
            d3 = "No, because it has multiplication."
        elif category in ["vertex_form_perfect_square", "vertex_form_with_coeff"]:
            d1 = "No, it's a perfect square, not a quadratic."
            d2 = "No, vertex form is linear."
            d3 = "No, because it has a perfect square."
        else:
            d1 = "No, it's linear."
            d2 = "No, it's cubic."
            d3 = "No, it's a polynomial but not quadratic."
    else:
        correct = "No, this is not a quadratic."
        rationale = f"The expression {expr} does not have degree 2 as its highest power."
        
        # Distractors that test common misconceptions
        if category in ["linear_binomial", "linear_monomial", "linear_monomial_with_coeff", "linear_with_coeff"]:
            d1 = "Yes, because it has a variable."
            d2 = "Yes, because it has a linear term."
            d3 = "Yes, all polynomial expressions are quadratic."
        elif category in ["constant"]:
            d1 = "Yes, constants are special quadratics."
            d2 = "Yes, because every polynomial is quadratic."
            d3 = "Yes, if there's no variable, it's still quadratic."
        elif category in ["cubic", "cubic_trinomial", "quintic"]:
            d1 = "Yes, high-degree polynomials are quadratic."
            d2 = "Yes, any polynomial with at least one x² term is quadratic."
            d3 = "Yes, it has an x² term."
        elif category in ["quartic"]:
            d1 = "Yes, because it contains an x² term."
            d2 = "Yes, x⁴ can be written as (x²)²."
            d3 = "Yes, high powers don't matter."
        elif category in ["mixed_cubic_dominant"]:
            d1 = "Yes, it has an x² term."
            d2 = "Yes, because it's a polynomial."
            d3 = "Yes, polynomials with x² are always quadratic."
        else:
            d1 = "Yes, because it looks like a quadratic."
            d2 = "Yes, if it has polynomial terms."
            d3 = "Yes, most expressions are quadratic."
    
    stem = f"Is the following expression a quadratic? {expr}"
    choices = [
        {"id":"a","text":correct,"tags_on_select":["correct"]},
        {"id":"b","text":d1,"tags_on_select":["misconception"]},
        {"id":"c","text":d2,"tags_on_select":["misconception"]},
        {"id":"d","text":d3,"tags_on_select":["misconception"]},
    ]
    
    return {
        "id": f"identify_{category}_{random.randint(1000,9999)}",
        "skill_id":"quad.identify",
        "difficulty": "easy",  # Identification is always foundational
        "stem": stem,
        "choices": _shuffle_choices(choices),
        "solution": correct,
        "rationale": rationale
    }

# Registry
GEN_BY_SKILL = {
    # Original skill IDs
    "quad.factor.a1": gen_factor_a1,
    "quad.factor.an1": gen_factor_an1,
    "quad.vertex.form": gen_vertex_form,
    "quad.discriminant": gen_discriminant,
    "quad.formula": gen_quadratic_formula,
    "quad.identify": gen_identify_quadratic,
    
    # New skill IDs (map to existing generators)
    # Factoring skills
    "quad.convert.factor.simple": gen_factor_a1,        # a=1 factoring
    "quad.convert.factor.complex": gen_factor_an1,      # a≠1 factoring
    
    # Form identification skills
    "quad.form.identify.standard": gen_identify_quadratic,  # Identify standard form
    "quad.form.identify.vertex": gen_vertex_form,           # Identify vertex form
    "quad.form.identify.factored": gen_factor_a1,           # Identify factored form
    
    # Conversion skills (reuse existing generators)
    "quad.convert.expand": gen_factor_a1,                   # Expand factored → standard
    "quad.convert.complete_square": gen_vertex_form,        # Complete square → vertex
    "quad.convert.vertex_to_standard": gen_vertex_form,     # Vertex → standard
    "quad.convert.standard_to_vertex": gen_vertex_form,     # Standard → vertex
    
    # Solving skills
    "quad.solve.by_factoring": gen_factor_a1,              # Solve by factoring
    "quad.solve.by_completing_square": gen_vertex_form,    # Solve by completing square
    "quad.solve.by_formula": gen_quadratic_formula,        # Quadratic formula
    "quad.solve.discriminant": gen_discriminant,           # Discriminant reasoning
    "quad.solve.by_graphing": gen_vertex_form,             # Solve by graphing
    
    # Graphing skills
    "quad.graph.vertex": gen_vertex_form,                  # Find vertex
    "quad.graph.axis": gen_vertex_form,                    # Axis of symmetry
    "quad.graph.direction": gen_identify_quadratic,        # Opening direction
    "quad.graph.intercepts": gen_factor_a1,                # Find intercepts
    "quad.graph.sketch": gen_vertex_form,                  # Sketch parabola
    
    # Modeling skills
    "quad.model.optimize": gen_vertex_form,                # Optimize with vertex
    "quad.model.projectile": gen_quadratic_formula,        # Projectile motion
    "quad.model.story": gen_quadratic_formula,             # Word problem mastery
    
    # graph.features intentionally omitted for MVP items
}

def generate_item(skill_id, difficulty="med"):
    fn = GEN_BY_SKILL.get(skill_id)
    if not fn:
        # fall back to a compatible related generator
        if skill_id == "quad.graph.features":
            return gen_vertex_form(difficulty)
        raise ValueError(f"No generator for skill {skill_id}")
    return fn(difficulty)
