# Golden Test Suite

Deterministic, snapshot-based testing for the Quadratics MVP adaptive learning engine.

## Quick Start

```bash
make test              # Run all tests
make test-verbose      # Verbose output
make test-approve      # Approve snapshot changes
make clean             # Remove test artifacts
```

## Architecture

### 1. **Determinism Hooks**

All engine functions accept optional determinism parameters:

```python
# Generate items with fixed randomness
item = generate_item("quad.factor.a1", difficulty="easy", seed=42)

# Select difficulty with hint (for testing)
item = generate_adaptive_item(skill_id, state, difficulty_hint="hard")
```

### 2. **Snapshot Helpers** (`engine/snapshots.py`)

Convert runtime objects to reproducible JSON:

```python
from engine.snapshots import to_snapshot_item

item = generate_item("quad.identify", "easy", seed=42)
snapshot = to_snapshot_item(item)
# {
#   "skill_id": "quad.identify",
#   "difficulty": "easy",
#   "stem": "Is the following expression a quadratic? ...",
#   "choices": [...],
#   "validation": {"has_correct": True, "no_duplicates": True}
# }
```

### 3. **Test Categories**

#### A. **Item Generation** (`test_item_goldens.py`)
- Deterministic generation with seeds
- Validation: exactly one correct, no duplicates, math-valid
- Golden snapshots per skill × difficulty

#### B. **Planner Logic** (`test_planner_goldens.py`)
- Difficulty selection rules (mastery → easy/medium/hard)
- Progression array sequencing
- Fallback to adaptive after progression exhausted

#### C. **Mastery Updates** (`test_mastery_goldens.py`)
- Correct/wrong answer deltas
- Streak tracking
- Bounds checking (capped at 0.0 and 1.0)
- Multi-step sequences (e.g., W, W, R, R)

#### D. **Validators**
- All items have exactly one "correct" choice
- No duplicate choices
- Math is algebraically valid

### 4. **Test Fixtures** (`tests/conftest.py`)

Pre-built learner states for reproducible scenarios:

```python
def test_with_fixture(beginner_state):
    # beginner_state has mastery=0.55, 2 misconceptions
    item = generate_adaptive_item("quad.factor.a1", beginner_state)
    assert item["adaptive_difficulty"] == "easy"
```

Available fixtures:
- `fresh_state`: Empty learner
- `beginner_state`: Low mastery, some errors
- `intermediate_state`: Medium mastery, progressing
- `advanced_state`: High mastery, many correct
- `remediation_state`: Repeated misconception tag

## Test Results

```
50 passed, 3 failed, 3 skipped
```

### Failures (Real Bugs Found!)

1. **Duplicate Choice in `quad.factor.simple`**
   - Choice `(x + 3)(x + 4)` appears twice
   - Impact: Learner gets partial credit for wrong answer

2. **Mastery Threshold Bug**
   - 100% mastery returns `"medium"` instead of `"hard"`
   - Impact: Advanced learners get trivially easy questions

3. **Remediation Picker**
   - Returns wrong skill when multiple misconceptions exist
   - Impact: Targeting wrong remediation

## Workflow

### During Development

```bash
# Edit code
# Run tests
pytest -q

# If intentional change, approve new snapshots
APPROVE=1 pytest tests/test_item_goldens.py::TestItemGeneration::test_quad_identify_easy_deterministic
```

### Snapshot Updates

Edit `tests/goldens/` to review/approve changes:

```
tests/goldens/
  item_generation/
    quad_identify_easy_seed42.json
    quad_factor_a1_medium_seed123.json
    quad_vertex_form_hard_seed999.json
  planner/
    next_skill_low_mastery.json
  mastery/
    update_correct.json
    update_wrong.json
```

## Adding New Tests

### 1. Create fixture in `conftest.py`

```python
@pytest.fixture
def my_scenario():
    return {"skills": {...}}
```

### 2. Write test in appropriate file

```python
def test_my_scenario(my_scenario):
    item = generate_adaptive_item("quad.factor.a1", my_scenario)
    snapshot = to_snapshot_item(item)
    # assert or compare to golden
```

### 3. Run and approve

```bash
pytest tests/test_my_scenario.py -v
APPROVE=1 pytest tests/test_my_scenario.py  # Save goldens
```

## CI Integration

TODO: Add GitHub Actions workflow to:
1. Run all tests on PR
2. Block merge if tests fail
3. Require approval for snapshot changes

## Bugs Identified

See `test_item_goldens.py::TestItemValidation::test_no_duplicate_choices` for current failures.

Next: Fix and re-test to confirm all pass.
