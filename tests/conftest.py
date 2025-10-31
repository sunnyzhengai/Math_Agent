"""
Pytest configuration and fixtures for golden tests.
"""

import pytest
import sys
from pathlib import Path

# Add parent directory to path so we can import engine modules
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def fresh_state():
    """Fixture: Fresh learner state."""
    return {
        "username": "test_user",
        "skills": {},
        "history": [],
        "questions_answered": 0
    }


@pytest.fixture
def beginner_state():
    """Fixture: Beginner with low mastery."""
    return {
        "username": "beginner",
        "skills": {
            "quad.form.identify.standard": {
                "p_mastery": 0.55,
                "streak": 0,
                "attempts": 3,
                "seen": 3,
                "correct": 1,
                "tag_counts": {"misconception": 2}
            }
        }
    }


@pytest.fixture
def intermediate_state():
    """Fixture: Intermediate with medium mastery."""
    return {
        "username": "intermediate",
        "skills": {
            "quad.convert.factor.simple": {
                "p_mastery": 0.72,
                "streak": 2,
                "attempts": 5,
                "seen": 5,
                "correct": 3,
                "tag_counts": {"correct": 3}
            }
        }
    }


@pytest.fixture
def advanced_state():
    """Fixture: Advanced with high mastery."""
    return {
        "username": "advanced",
        "skills": {
            "quad.solve.by_formula": {
                "p_mastery": 0.95,
                "streak": 8,
                "attempts": 10,
                "seen": 10,
                "correct": 9,
                "tag_counts": {"correct": 9}
            }
        }
    }


@pytest.fixture
def remediation_state():
    """Fixture: Learner with repeated misconception."""
    return {
        "username": "needs_remediation",
        "skills": {
            "quad.vertex.form": {
                "p_mastery": 0.65,
                "streak": 0,
                "attempts": 6,
                "seen": 6,
                "correct": 3,
                "tag_counts": {"vertex_sign_flip": 3}
            }
        }
    }


def pytest_configure(config):
    """Configure pytest plugins."""
    config.addinivalue_line(
        "markers", "golden: mark test as a golden snapshot test"
    )
    config.addinivalue_line(
        "markers", "deterministic: mark test as requiring deterministic seeds"
    )


def pytest_collection_modifyitems(config, items):
    """Automatically add markers to test files."""
    for item in items:
        if "golden" in item.fspath.strpath:
            item.add_marker(pytest.mark.golden)
        if "seed" in item.name or "deterministic" in item.name:
            item.add_marker(pytest.mark.deterministic)
