from app.services.cost_tracker import calculate_cost


def test_known_model_pricing():
    result = calculate_cost("llama-3.1-8b-instant", 1_000_000, 1_000_000)
    assert result["priced"] is True
    assert result["cost_usd"] > 0


def test_unknown_model_returns_unpriced():
    result = calculate_cost("nonexistent-model", 100, 100)
    assert result["priced"] is False
    assert result["cost_usd"] == 0.0
