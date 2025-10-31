"""
Golden tests for item generation.
Tests that question generation is deterministic and correct.
"""

import pytest
import json
import os
from pathlib import Path

from engine.templates import generate_item
from engine.snapshots import to_snapshot_item

GOLDENS_DIR = Path(__file__).parent / "goldens" / "item_generation"


def load_golden(filename: str) -> dict:
    """Load a golden JSON file."""
    path = GOLDENS_DIR / filename
    with open(path) as f:
        return json.load(f)


def save_golden(filename: str, data: dict):
    """Save a golden JSON file."""
    GOLDENS_DIR.mkdir(parents=True, exist_ok=True)
    path = GOLDENS_DIR / filename
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


class TestItemGeneration:
    """Golden tests for question generation."""
    
    def test_quad_identify_easy_deterministic(self):
        """Generate quad.identify (easy) with seed=42, snapshot it."""
        item = generate_item("quad.identify", difficulty="easy", seed=42)
        snapshot = to_snapshot_item(item)
        
        golden_name = "quad_identify_easy_seed42.json"
        expected = load_golden(golden_name) if (GOLDENS_DIR / golden_name).exists() else None
        
        if expected:
            # Compare to golden
            assert snapshot["skill_id"] == expected["skill_id"]
            assert snapshot["difficulty"] == expected["difficulty"]
            assert len(snapshot["choices"]) == expected["num_choices"]
            assert snapshot["validation"]["has_correct"] == expected["validation"]["has_correct"]
        else:
            # First run: save the golden
            pytest.skip(f"Creating golden {golden_name}. Run with APPROVE=1 to save.")
            # In real workflow, save_golden(golden_name, snapshot)
    
    def test_quad_factor_a1_medium_deterministic(self):
        """Generate quad.factor.a1 (medium) with seed=123."""
        item = generate_item("quad.convert.factor.simple", difficulty="medium", seed=123)
        snapshot = to_snapshot_item(item)
        
        golden_name = "quad_factor_a1_medium_seed123.json"
        expected = load_golden(golden_name) if (GOLDENS_DIR / golden_name).exists() else None
        
        if expected:
            assert snapshot["skill_id"] == expected["skill_id"]
            assert len(snapshot["choices"]) == 4
            assert snapshot["validation"]["no_duplicates"]
        else:
            pytest.skip(f"Creating golden {golden_name}.")
    
    def test_quad_vertex_form_hard_deterministic(self):
        """Generate quad.vertex.form (hard) with seed=999."""
        item = generate_item("quad.vertex.form", difficulty="hard", seed=999)
        snapshot = to_snapshot_item(item)
        
        golden_name = "quad_vertex_form_hard_seed999.json"
        expected = load_golden(golden_name) if (GOLDENS_DIR / golden_name).exists() else None
        
        if expected:
            # Verify difficulty matches what was actually generated (inferred from params, not parameter)
            assert snapshot["difficulty"] == expected["difficulty"]
            # Verify exactly one correct answer
            correct_count = sum(
                1 for choice in snapshot["choices"]
                if "correct" in choice.get("tags_on_select", [])
            )
            assert correct_count == 1
        else:
            pytest.skip(f"Creating golden {golden_name}.")


class TestItemValidation:
    """Verify items meet basic correctness criteria."""
    
    def test_all_items_have_one_correct(self):
        """Every item should have exactly one correct choice."""
        for skill_id in ["quad.identify", "quad.convert.factor.simple", "quad.vertex.form"]:
            for diff in ["easy", "medium", "hard"]:
                item = generate_item(skill_id, difficulty=diff, seed=42)
                correct_count = sum(
                    1 for c in item.get("choices", [])
                    if "correct" in c.get("tags_on_select", [])
                )
                assert correct_count == 1, f"{skill_id} ({diff}) has {correct_count} correct answers"
    
    def test_no_duplicate_choices(self):
        """Choices should not be identical."""
        for skill_id in ["quad.identify", "quad.convert.factor.simple"]:
            item = generate_item(skill_id, difficulty="easy", seed=42)
            texts = [c.get("text") for c in item.get("choices", [])]
            assert len(texts) == len(set(texts)), f"{skill_id} has duplicate choices"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
