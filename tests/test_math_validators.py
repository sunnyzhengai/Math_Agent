"""
Tests for algebraic validity of generated answers.
"""
import pytest
from engine.math_validators import (
    expand_factorization,
    check_factorization_valid,
    check_quadratic_formula_valid,
    validate_item_math
)

class TestExpandFactorization:
    """Tests for expand_factorization helper."""
    
    def test_expand_x_plus_2_times_x_plus_3(self):
        result = expand_factorization("(x + 2)(x + 3)")
        assert result == (1, 5, 6), "(x+2)(x+3) = x^2 + 5x + 6"
    
    def test_expand_x_minus_1_times_x_plus_6(self):
        result = expand_factorization("(x - 1)(x + 6)")
        assert result == (1, 5, -6), "(x-1)(x+6) = x^2 + 5x - 6"
    
    def test_expand_x_minus_2_times_x_minus_3(self):
        result = expand_factorization("(x - 2)(x - 3)")
        assert result == (1, -5, 6), "(x-2)(x-3) = x^2 - 5x + 6"
    
    def test_invalid_pattern_returns_none(self):
        result = expand_factorization("not a factorization")
        assert result is None

class TestCheckFactorizationValid:
    """Tests for factorization validation against stem."""
    
    def test_factorization_correct(self):
        stem = "Factor: x² + 5x + 6"
        correct = "(x + 2)(x + 3)"
        assert check_factorization_valid(stem, correct)
    
    def test_factorization_wrong_sum(self):
        """x² + 5x + 6 should NOT factor as (x+2)(x+2)"""
        stem = "Factor: x² + 5x + 6"
        correct = "(x + 2)(x + 2)"
        assert not check_factorization_valid(stem, correct)
    
    def test_factorization_wrong_product(self):
        """x² + 5x + 6 should NOT factor as (x+3)(x+2) if values don't multiply to 6"""
        stem = "Factor: x² + 5x + 6"
        correct = "(x + 1)(x + 6)"
        assert not check_factorization_valid(stem, correct)
    
    def test_factorization_with_superscript(self):
        """Should handle ² notation"""
        stem = "Factor: x² + 3x + 2"
        correct = "(x + 1)(x + 2)"
        assert check_factorization_valid(stem, correct)
    
    def test_factorization_with_caret(self):
        """Should handle ^ notation"""
        stem = "Factor: x^2 + 3x + 2"
        correct = "(x + 1)(x + 2)"
        assert check_factorization_valid(stem, correct)
    
    def test_negative_coefficients(self):
        stem = "Factor: x² - 5x + 6"
        correct = "(x - 2)(x - 3)"
        assert check_factorization_valid(stem, correct)
    
    def test_unrecognized_pattern_passes(self):
        """If pattern doesn't match, return True to avoid false negatives"""
        stem = "Some weird stem"
        correct = "(x + 2)(x + 3)"
        assert check_factorization_valid(stem, correct)

class TestCheckQuadraticFormulaValid:
    """Tests for quadratic formula root validation."""
    
    def test_formula_correct_roots(self):
        stem = "Solve using the quadratic formula: 1x² -5x + 6 = 0"
        correct = "x = 2, 3"
        assert check_quadratic_formula_valid(stem, correct)
    
    def test_formula_incorrect_roots(self):
        stem = "Solve using the quadratic formula: 1x² -5x + 6 = 0"
        correct = "x = 1, 2"
        assert not check_quadratic_formula_valid(stem, correct)
    
    def test_formula_single_root(self):
        """x² - 2x + 1 = (x-1)² has single root x=1"""
        stem = "Solve using the quadratic formula: 1x² -2x + 1 = 0"
        correct = "x = 1"
        assert check_quadratic_formula_valid(stem, correct)
    
    def test_formula_with_superscript(self):
        stem = "Solve using the quadratic formula: 1x² -3x + 2 = 0"
        correct = "x = 1, 2"
        assert check_quadratic_formula_valid(stem, correct)
    
    def test_unrecognized_pattern_passes(self):
        """If pattern doesn't match, return True"""
        stem = "Some weird stem"
        correct = "x = 1, 2"
        assert check_quadratic_formula_valid(stem, correct)

class TestValidateItemMath:
    """Integration tests for validate_item_math."""
    
    def test_factor_item_valid(self):
        item = {
            "skill_id": "quad.factor.a1",
            "stem": "Factor: x² + 5x + 6",
            "solution": "(x + 2)(x + 3)"
        }
        is_valid, msg = validate_item_math(item)
        assert is_valid
    
    def test_factor_item_invalid(self):
        item = {
            "skill_id": "quad.factor.a1",
            "stem": "Factor: x² + 5x + 6",
            "solution": "(x + 1)(x + 2)"
        }
        is_valid, msg = validate_item_math(item)
        assert not is_valid
        assert "invalid" in msg.lower()
    
    def test_formula_item_valid(self):
        item = {
            "skill_id": "quad.formula",
            "stem": "Solve using the quadratic formula: 1x² -3x + 2 = 0",
            "solution": "x = 1, 2"
        }
        is_valid, msg = validate_item_math(item)
        assert is_valid
    
    def test_formula_item_invalid(self):
        item = {
            "skill_id": "quad.formula",
            "stem": "Solve using the quadratic formula: 1x² -3x + 2 = 0",
            "solution": "x = 2, 3"
        }
        is_valid, msg = validate_item_math(item)
        assert not is_valid
        assert "invalid" in msg.lower()
    
    def test_unknown_skill_passes(self):
        """Unknown skills should pass (no rules defined)"""
        item = {
            "skill_id": "quad.unknown",
            "stem": "Some stem",
            "solution": "Some solution"
        }
        is_valid, msg = validate_item_math(item)
        assert is_valid
