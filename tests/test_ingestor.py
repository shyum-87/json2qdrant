import json as json_module
from unittest.mock import MagicMock, patch

import pytest

from ingestor import chunk_text


def test_chunk_text_empty_returns_empty_list():
    assert chunk_text("", 200, 50) == []


def test_chunk_text_shorter_than_chunk_size_single_chunk():
    result = chunk_text("hello world", 200, 50)
    assert result == ["hello world"]


def test_chunk_text_respects_size_and_overlap():
    text = "A" * 500
    result = chunk_text(text, 200, 50)
    # step = 150, starts at 0, 150, 300, 450
    assert len(result) == 4
    assert result[0] == "A" * 200
    assert result[1] == "A" * 200
    assert result[-1] == "A" * 50  # final slice: text[450:500]


def test_chunk_text_overlap_content_matches():
    text = "".join(chr(ord("a") + (i % 26)) for i in range(500))
    chunks = chunk_text(text, 200, 50)
    # overlap region of chunk[0] tail and chunk[1] head must match
    assert chunks[0][-50:] == chunks[1][:50]


def test_chunk_text_invalid_params_raise():
    with pytest.raises(ValueError):
        chunk_text("abc", 0, 0)
    with pytest.raises(ValueError):
        chunk_text("abc", 100, 100)
    with pytest.raises(ValueError):
        chunk_text("abc", 100, -1)
