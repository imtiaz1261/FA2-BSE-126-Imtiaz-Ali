from app import count_tokens

def test_token_count_is_positive():
    assert count_tokens("Hello, world!", "llama-3.3-70b-versatile") > 0

def test_empty_string_has_zero_tokens():
    assert count_tokens("", "llama-3.3-70b-versatile") == 0
