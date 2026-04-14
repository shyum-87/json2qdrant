import json as json_module
from unittest.mock import MagicMock, patch

import pytest

from ingestor import (
    build_points,
    chunk_text,
    delete_existing_doc,
    embed_chunks,
    load_documents,
)


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


def test_embed_chunks_returns_vectors():
    mock_model = MagicMock()
    mock_model.create_embedding.return_value = {
        "data": [{"embedding": [0.1, 0.2, 0.3]}]
    }
    result = embed_chunks(mock_model, ["첫", "둘"])
    assert result == [[0.1, 0.2, 0.3], [0.1, 0.2, 0.3]]
    assert mock_model.create_embedding.call_count == 2


def test_embed_chunks_empty():
    mock_model = MagicMock()
    assert embed_chunks(mock_model, []) == []
    mock_model.create_embedding.assert_not_called()


def test_delete_existing_doc_filters_by_doc_id():
    mock_client = MagicMock()
    delete_existing_doc(mock_client, "my_docs", "2025_W34_abc")

    mock_client.delete.assert_called_once()
    kwargs = mock_client.delete.call_args.kwargs
    assert kwargs["collection_name"] == "my_docs"
    condition = kwargs["points_selector"].filter.must[0]
    assert condition.key == "doc_id"
    assert condition.match.value == "2025_W34_abc"


def test_build_points_copies_metadata_and_indexes():
    doc = _doc("D42", content="body")
    chunks = ["a", "bb", "ccc"]
    vectors = [[0.1], [0.2], [0.3]]

    points = build_points(doc, chunks, vectors, collection="my_docs")

    assert len(points) == 3
    for i, p in enumerate(points):
        payload = p.payload
        assert payload["doc_id"] == "D42"
        assert payload["title"] == "T"
        assert payload["document_type"] == "weekly_report"
        assert payload["year"] == 2025
        assert payload["week"] == 34
        assert payload["source_file"] == "path/f.txt"
        assert payload["filename"] == "f.txt"
        assert payload["parts_total"] == 1
        assert payload["part_index"] == 1
        assert payload["chunk_index"] == i
        assert payload["chunk_total"] == 3
        assert payload["text"] == chunks[i]
        assert payload["collection_name"] == "my_docs"
    assert points[0].vector == [0.1]


def test_build_points_length_mismatch_raises():
    doc = _doc("D", "x")
    with pytest.raises(ValueError):
        build_points(doc, ["a", "b"], [[0.1]], collection="c")
