"""
Golden tests for mastery updates.
Tests that mastery calculations match expected behavior.
"""

import pytest
from engine.state import update_after_answer
from engine.snapshots import to_snapshot_mastery_update


class TestMasteryUpdates:
    """Test mastery edge updates."""
    
    def test_correct_answer_increases_mastery(self):
        """Correct answer should increase p_mastery by delta_win (0.08)."""
        state = {
            "username": "test",
            "skills": {
                "quad.factor.a1": {
                    "p_mastery": 0.60,
                    "streak": 0,
                    "attempts": 0,
                    "seen": 0,
                    "correct": 0,
                    "tag_counts": {}
                }
            }
        }
        
        before = state["skills"]["quad.factor.a1"].copy()
        update_after_answer(state, "quad.factor.a1", correct=True, tags=[])
        after = state["skills"]["quad.factor.a1"]
        
        # 0.60 + 0.08 = 0.68
        assert after["p_mastery"] == pytest.approx(0.68, abs=0.001)
        assert after["streak"] == 1
        assert after["attempts"] == 1
    
    def test_wrong_answer_decreases_mastery(self):
        """Wrong answer should decrease p_mastery by delta_loss (0.12)."""
        state = {
            "username": "test",
            "skills": {
                "quad.factor.a1": {
                    "p_mastery": 0.75,
                    "streak": 3,
                    "attempts": 5,
                    "seen": 5,
                    "correct": 4,
                    "tag_counts": {}
                }
            }
        }
        
        before = state["skills"]["quad.factor.a1"].copy()
        update_after_answer(state, "quad.factor.a1", correct=False, tags=["sign_error"])
        after = state["skills"]["quad.factor.a1"]
        
        # 0.75 - 0.12 = 0.63
        assert after["p_mastery"] == pytest.approx(0.63, abs=0.001)
        assert after["streak"] == 0  # Reset on wrong
        assert after["attempts"] == 6
    
    def test_mastery_bounded_at_one(self):
        """Mastery should be capped at 1.0."""
        state = {
            "username": "test",
            "skills": {
                "quad.factor.a1": {
                    "p_mastery": 0.95,
                    "streak": 8,
                    "attempts": 10,
                    "seen": 10,
                    "correct": 9,
                    "tag_counts": {}
                }
            }
        }
        
        update_after_answer(state, "quad.factor.a1", correct=True, tags=[])
        # 0.95 + 0.08 = 1.03 → capped at 1.0
        assert state["skills"]["quad.factor.a1"]["p_mastery"] == 1.0
    
    def test_mastery_bounded_at_zero(self):
        """Mastery should be capped at 0.0."""
        state = {
            "username": "test",
            "skills": {
                "quad.factor.a1": {
                    "p_mastery": 0.05,
                    "streak": 0,
                    "attempts": 1,
                    "seen": 1,
                    "correct": 0,
                    "tag_counts": {}
                }
            }
        }
        
        update_after_answer(state, "quad.factor.a1", correct=False, tags=[])
        # 0.05 - 0.12 = -0.07 → capped at 0.0
        assert state["skills"]["quad.factor.a1"]["p_mastery"] == 0.0
    
    def test_streak_increments_on_correct(self):
        """Streak should increment on correct answer."""
        state = {
            "username": "test",
            "skills": {
                "quad.factor.a1": {
                    "p_mastery": 0.6,
                    "streak": 2,
                    "attempts": 2,
                    "seen": 2,
                    "correct": 2,
                    "tag_counts": {}
                }
            }
        }
        
        update_after_answer(state, "quad.factor.a1", correct=True, tags=[])
        assert state["skills"]["quad.factor.a1"]["streak"] == 3
    
    def test_streak_resets_on_wrong(self):
        """Streak should reset to 0 on wrong answer."""
        state = {
            "username": "test",
            "skills": {
                "quad.factor.a1": {
                    "p_mastery": 0.6,
                    "streak": 5,
                    "attempts": 5,
                    "seen": 5,
                    "correct": 5,
                    "tag_counts": {}
                }
            }
        }
        
        update_after_answer(state, "quad.factor.a1", correct=False, tags=[])
        assert state["skills"]["quad.factor.a1"]["streak"] == 0


class TestMasterySequence:
    """Test a sequence of updates."""
    
    def test_sequence_wrong_wrong_right_right(self):
        """Simulate: W, W, R, R sequence."""
        state = {
            "username": "test",
            "skills": {
                "quad.factor.a1": {
                    "p_mastery": 0.60,
                    "streak": 0,
                    "attempts": 0,
                    "seen": 0,
                    "correct": 0,
                    "tag_counts": {}
                }
            }
        }
        
        skill_id = "quad.factor.a1"
        expected_sequence = []
        
        # Wrong (0.60 - 0.12 = 0.48)
        update_after_answer(state, skill_id, correct=False, tags=[])
        expected_sequence.append({
            "correct": False,
            "mastery": pytest.approx(0.48, abs=0.001),
            "streak": 0
        })
        
        # Wrong (0.48 - 0.12 = 0.36)
        update_after_answer(state, skill_id, correct=False, tags=[])
        expected_sequence.append({
            "correct": False,
            "mastery": pytest.approx(0.36, abs=0.001),
            "streak": 0
        })
        
        # Right (0.36 + 0.08 = 0.44)
        update_after_answer(state, skill_id, correct=True, tags=[])
        expected_sequence.append({
            "correct": True,
            "mastery": pytest.approx(0.44, abs=0.001),
            "streak": 1
        })
        
        # Right (0.44 + 0.08 = 0.52)
        update_after_answer(state, skill_id, correct=True, tags=[])
        expected_sequence.append({
            "correct": True,
            "mastery": pytest.approx(0.52, abs=0.001),
            "streak": 2
        })
        
        # Verify final state
        skill_state = state["skills"][skill_id]
        assert skill_state["p_mastery"] == pytest.approx(0.52, abs=0.001)
        assert skill_state["streak"] == 2
        assert skill_state["attempts"] == 4


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
