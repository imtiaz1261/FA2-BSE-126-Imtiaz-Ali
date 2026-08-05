"""
Tests for captioner.py — uses a mocked OpenAI client and temporary files
so no real API key, network call, or actual image is needed.
"""

import os
import tempfile
import pytest
from unittest.mock import MagicMock
from captioner import (
    caption_image,
    validate_image_path,
    CaptionError,
    MAX_IMAGE_SIZE_MB,
)


def make_mock_client(reply_text: str):
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content=reply_text))]
    mock_client.chat.completions.create.return_value = mock_response
    return mock_client


@pytest.fixture
def fake_jpg(tmp_path):
    """Creates a tiny fake .jpg file (content doesn't need to be a real
    image since the mocked client never actually decodes it)."""
    path = tmp_path / "test_image.jpg"
    path.write_bytes(b"fake image bytes")
    return str(path)


def test_validate_image_path_accepts_supported_extension(fake_jpg):
    mime_type = validate_image_path(fake_jpg)
    assert mime_type == "image/jpeg"


def test_validate_image_path_missing_file_raises(tmp_path):
    missing = tmp_path / "does_not_exist.jpg"
    with pytest.raises(CaptionError):
        validate_image_path(str(missing))


def test_validate_image_path_unsupported_extension_raises(tmp_path):
    path = tmp_path / "document.pdf"
    path.write_bytes(b"not an image")
    with pytest.raises(CaptionError):
        validate_image_path(str(path))


def test_validate_image_path_empty_path_raises():
    with pytest.raises(CaptionError):
        validate_image_path("")


def test_validate_image_path_too_large_raises(tmp_path):
    path = tmp_path / "big.jpg"
    # Write just over the size limit.
    with open(path, "wb") as f:
        f.write(b"0" * ((MAX_IMAGE_SIZE_MB + 1) * 1024 * 1024))
    with pytest.raises(CaptionError):
        validate_image_path(str(path))


def test_caption_image_returns_stripped_caption(fake_jpg):
    client = make_mock_client("  A red bicycle parked against a brick wall.  ")
    result = caption_image(client, fake_jpg)
    assert result == "A red bicycle parked against a brick wall."


def test_caption_image_empty_response_raises(fake_jpg):
    client = make_mock_client("   ")
    with pytest.raises(CaptionError):
        caption_image(client, fake_jpg)


def test_caption_image_wraps_api_errors(fake_jpg):
    client = MagicMock()
    client.chat.completions.create.side_effect = Exception("network down")
    with pytest.raises(CaptionError):
        caption_image(client, fake_jpg)
