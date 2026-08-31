MAX_CHARACTERS = 5000


def validate_text(text: str) -> str | None:
    if not text or not text.strip():
        return "Please enter some text before generating speech."

    if len(text) > MAX_CHARACTERS:
        return (
            f"Text is too long. Please keep it under "
            f"{MAX_CHARACTERS:,} characters."
        )

    if len(text.strip()) < 2:
        return "Please enter at least 2 characters."

    return None
