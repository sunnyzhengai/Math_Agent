"""
Math validators: Ensure algebraically correct answers.
"""
import re

def expand_factorization(expr: str):
    """
    Very basic algebraic expander for patterns like (x + p)(x + q)
    Returns coefficients (a, b, c) for ax^2 + bx + c.
    
    Example:
        "(x + 2)(x + 3)" → (1, 5, 6)  [since (x+2)(x+3) = x^2 + 5x + 6]
    """
    # Normalize: remove spaces, handle +- patterns
    expr_norm = expr.replace(" ", "")
    
    # Pattern: (x +/- p)(x +/- q)
    # Capture both the sign+number pairs
    m = re.match(r"\(x\s*([+-]\s*\d+)\)\(x\s*([+-]\s*\d+)\)", expr.replace(" ", ""))
    if not m:
        return None
    
    # Extract p and q, handling spaces in the sign
    p_str = m.group(1).replace(" ", "")
    q_str = m.group(2).replace(" ", "")
    
    try:
        p = int(p_str)
        q = int(q_str)
    except ValueError:
        return None
    
    # (x + p)(x + q) = x^2 + (p+q)x + pq
    a, b, c = 1, p + q, p * q
    return a, b, c

def check_factorization_valid(stem: str, correct: str) -> bool:
    """
    Verifies that expanding the correct answer yields coefficients
    matching the trinomial in the stem.
    
    Args:
        stem: e.g., "Factor: x² + 5x + 6"
        correct: e.g., "(x + 2)(x + 3)"
    
    Returns:
        True if valid (or pattern not recognized), False if invalid
    """
    # Extract coefficients from stem: "Factor: ax^2 + bx + c" or "Factor: x² ..."
    # Handle both caret (^) and superscript (²) notation
    stem_norm = stem.replace("²", "^2").replace(" ", "")
    
    # Try to match: Factor:x^2{b}x{c}
    # where {b} and {c} are signed integers
    m = re.search(r"x\^2([+-]\d+)x([+-]\d+)", stem_norm)
    if not m:
        # Pattern doesn't match; skip validation (return True to avoid false negatives)
        return True
    
    try:
        b_stem = int(m.group(1))
        c_stem = int(m.group(2))
    except (ValueError, IndexError):
        return True
    
    # Expand the factorization
    result = expand_factorization(correct)
    if result is None:
        return False  # Couldn't parse factorization
    
    _, b_factored, c_factored = result
    
    # Check if they match
    return b_stem == b_factored and c_stem == c_factored

def check_quadratic_formula_valid(stem: str, correct: str) -> bool:
    """
    Verifies that the numeric roots satisfy ax^2 + bx + c = 0.
    
    Args:
        stem: e.g., "Solve using the quadratic formula: 1x² -3x + 2 = 0"
        correct: e.g., "x = 1, 2"
    
    Returns:
        True if roots are valid solutions, False otherwise
    """
    # Extract a, b, c from stem
    # Pattern: {a}x^2 {b}x {c}
    stem_norm = stem.replace("²", "^2").replace(" ", "")
    
    m = re.search(r"(\d+)x\^2([+-]\d+)x([+-]\d+)", stem_norm)
    if not m:
        # Can't parse; skip validation
        return True
    
    try:
        a = int(m.group(1))
        b = int(m.group(2))
        c = int(m.group(3))
    except (ValueError, IndexError):
        return True
    
    # Extract roots from correct answer
    # Pattern: "x = r1, r2" or "x = r1"
    nums = re.findall(r"(-?\d+)", correct)
    if not nums:
        return False  # No numbers found in answer
    
    try:
        roots = [int(n) for n in nums]
    except ValueError:
        return False
    
    # Check if each root satisfies the equation
    def f(x):
        return a * x * x + b * x + c
    
    for root in roots:
        if abs(f(root)) > 1e-6:  # Allow tiny floating-point error
            return False
    
    return True

def validate_item_math(item: dict) -> tuple[bool, str]:
    """
    Comprehensive math validation for an item.
    
    Returns:
        (is_valid, error_message)
    """
    skill_id = item.get("skill_id", "")
    stem = item.get("stem", "")
    solution = item.get("solution", "")
    
    if skill_id == "quad.factor.a1":
        if not check_factorization_valid(stem, solution):
            return False, f"Factorization answer invalid for given trinomial: {stem} → {solution}"
    
    elif skill_id == "quad.formula":
        if not check_quadratic_formula_valid(stem, solution):
            return False, f"Quadratic formula roots invalid: {stem} → {solution}"
    
    # All other skills pass for now
    return True, ""
