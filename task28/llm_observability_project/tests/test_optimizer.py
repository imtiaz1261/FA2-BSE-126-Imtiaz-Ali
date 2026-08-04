from app.services.prompt_optimizer import optimize_prompt


def test_removes_filler_and_duplicates():
    text = (
        "Could you please explain RAG?\n"
        "Could you please explain RAG?\n"
        "Please note that it's useful."
    )
    result = optimize_prompt(text)
    assert result["optimized_tokens"] < result["original_tokens"]
    assert "please" not in result["optimized_prompt"].lower()


def test_empty_prompt_does_not_crash():
    result = optimize_prompt("")
    assert result["reduction_pct"] == 0.0
