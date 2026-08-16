import random, pytest
from app.ab_core import assign_variant, response_length, validate_feedback

def test_assignment():
    a = assign_variant(0.5, random.Random(1))
    assert a.variant in {"A", "B"} and a.interaction_id

def test_length():
    assert response_length("one two three") == 3

def test_feedback():
    assert validate_feedback("up") == "up"
    with pytest.raises(ValueError):
        validate_feedback("bad")

def test_weight():
    with pytest.raises(ValueError):
        assign_variant(1.0)
