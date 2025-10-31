"""
Golden tests for planner decisions.
Tests that skill/difficulty selection matches expected behavior.
"""

import pytest
from pathlib import Path
import json
import random

from engine.planner import generate_adaptive_item, select_difficulty

GOLDENS_DIR = Path(__file__).parent / "goldens" / "planner"


class TestDifficultySelection:
    """Test the select_difficulty logic."""
    
    def test_low_mastery_gets_easy(self):
        """Mastery < 0.5 should select easy."""
        random.seed(42)
        diff = select_difficulty(p_mastery=0.4, streak=0)
        assert diff == "easy"
    
    def test_medium_mastery_gets_medium(self):
        """0.5 <= mastery < 0.7 should select medium."""
        random.seed(42)
        diff = select_difficulty(p_mastery=0.6, streak=0)
        assert diff == "medium"
    
    def test_high_mastery_gets_hard(self):
        """0.7 <= mastery < 0.85 should select hard."""
        random.seed(42)
        diff = select_difficulty(p_mastery=0.75, streak=0)
        assert diff == "hard"
    
    def test_advanced_mastery_gets_hard(self):
        """Mastery >= 0.85 should select hard."""
        random.seed(42)
        diff = select_difficulty(p_mastery=0.95, streak=5)
        assert diff == "hard"


class TestProgressionArray:
    """Test that progression arrays work correctly."""
    
    def test_progression_q1_is_easy(self):
        """First question should follow progression[0]."""
        state = {
            "username": "test",
            "skills": {
                "quad.form.identify.standard": {
                    "p_mastery": 0.6,
                    "streak": 0,
                    "attempts": 0
                }
            }
        }
        item = generate_adaptive_item("quad.form.identify.standard", state, seed=42)
        assert item["adaptive_difficulty"] == "easy"
        assert item["difficulty_source"] == "progression"
        assert item["progression_index"] == 0
    
    def test_progression_q3_is_medium(self):
        """Third question should follow progression[2]."""
        state = {
            "username": "test",
            "skills": {
                "quad.form.identify.standard": {
                    "p_mastery": 0.99,  # Even at 100%, follows progression
                    "streak": 5,
                    "attempts": 2  # Third attempt (0-indexed)
                }
            }
        }
        item = generate_adaptive_item("quad.form.identify.standard", state, seed=42)
        assert item["adaptive_difficulty"] == "medium"
        assert item["difficulty_source"] == "progression"
        assert item["progression_index"] == 2
    
    def test_progression_exhausted_falls_back_to_adaptive(self):
        """After progression array, should use adaptive."""
        state = {
            "username": "test",
            "skills": {
                "quad.form.identify.standard": {
                    "p_mastery": 0.99,
                    "streak": 10,
                    "attempts": 7  # Beyond progression array length (7 items)
                }
            }
        }
        item = generate_adaptive_item("quad.form.identify.standard", state, seed=42)
        assert item["difficulty_source"] == "adaptive"
        assert item["progression_index"] == 7
    
    def test_difficulty_hint_override(self):
        """difficulty_hint should override progression."""
        state = {
            "username": "test",
            "skills": {
                "quad.form.identify.standard": {
                    "p_mastery": 0.6,
                    "attempts": 0
                }
            }
        }
        item = generate_adaptive_item(
            "quad.form.identify.standard", 
            state, 
            seed=42,
            difficulty_hint="hard"
        )
        assert item["adaptive_difficulty"] == "hard"
        assert item["difficulty_source"] == "hint"


class TestSessionCadence:
    """Test 10-step session cadence."""
    
    def test_10_step_cadence_progression(self):
        """A 10-step session should follow correct cadence."""
        state = {
            "username": "test",
            "skills": {}
        }
        
        skill_id = "quad.form.identify.standard"
        cadence = []
        
        for attempt in range(10):
            # Initialize skill if needed
            if skill_id not in state["skills"]:
                state["skills"][skill_id] = {
                    "p_mastery": 0.6,
                    "streak": 0,
                    "attempts": 0
                }
            
            # Generate item
            item = generate_adaptive_item(skill_id, state, seed=42 + attempt)
            cadence.append(item["adaptive_difficulty"])
            
            # Simulate correct answer
            state["skills"][skill_id]["attempts"] += 1
            state["skills"][skill_id]["p_mastery"] = min(1.0, state["skills"][skill_id]["p_mastery"] + 0.08)
        
        # Check cadence: easy, easy, medium, medium, hard, hard, hard (then adaptive)
        expected = ["easy", "easy", "medium", "medium", "hard", "hard", "hard"]
        actual = cadence[:7]
        assert actual == expected, f"Expected {expected}, got {actual}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
