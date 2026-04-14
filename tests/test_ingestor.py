import json as json_module
from unittest.mock import MagicMock, patch

import pytest

from ingestor import chunk_text, load_documents


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


def _doc(doc_id="D1", content="hello"):
    return {
        "doc_id": doc_id,
        "title": "T",
        "content": content,
        "created_time": "2025-08-24",
        "source_file": "path/f.txt",
        "filename": "f.txt",
        "year": 2025,
        "week": 34,
        "file_size": 10,
        "processed_at": "2025-08-24 00:00:00",
        "document_type": "weekly_report",
        "parts_total": 1,
        "part_index": 1,
    }


def test_load_documents_single_object(tmp_path):
    f = tmp_path / "a.json"
    f.write_text(json_module.dumps(_doc("A")), encoding="utf-8")
    docs = load_documents(f)
    assert len(docs) == 1
    assert docs[0]["doc_id"] == "A"


def test_load_documents_array(tmp_path):
    f = tmp_path / "a.json"
    f.write_text(json_module.dumps([_doc("A"), _doc("B")]), encoding="utf-8")
    docs = load_documents(f)
    assert [d["doc_id"] for d in docs] == ["A", "B"]


def test_load_documents_jsonl(tmp_path):
    f = tmp_path / "a.jsonl"
    lines = [json_module.dumps(_doc("A")), json_module.dumps(_doc("B"))]
    f.write_text("\n".join(lines), encoding="utf-8")
    docs = load_documents(f)
    assert [d["doc_id"] for d in docs] == ["A", "B"]


def test_load_documents_rejects_scalar(tmp_path):
    f = tmp_path / "a.json"
    f.write_text("42", encoding="utf-8")
    with pytest.raises(ValueError):
        load_documents(f)
