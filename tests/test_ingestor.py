import json as json_module
from unittest.mock import MagicMock

import pytest

from ingestor import (
    build_points,
    chunk_text,
    delete_existing_doc,
    embed_chunks,
    ingest_file,
    is_qdrant_healthy,
    load_chunk_document,
    load_config,
    upsert_points,
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
    chunks = [{"content": "첫 번째 청크"}, {"content": "두 번째 청크"}]

    result = embed_chunks(mock_model, chunks)

    assert len(result) == 2
    assert result[0] == [0.1, 0.2, 0.3]
    assert result[1] == [0.1, 0.2, 0.3]
    assert mock_model.create_embedding.call_count == 2


def test_embed_chunks_empty():
    mock_model = MagicMock()
    assert embed_chunks(mock_model, []) == []
    mock_model.create_embedding.assert_not_called()


def test_delete_existing_doc_filters_by_doc_id():
    mock_client = MagicMock()
    chunks = [
        {"chunk_id": 0, "content": "텍스트", "page": 1, "position": "first"},
    ]
    vectors = [[0.1, 0.2, 0.3]]
    source_meta = {
        "source": "test.pdf",
        "file_type": "pdf",
        "author": None,
        "title": None,
        "language": "ko",
    }
    mock_model = MagicMock()
    mock_model.create_embedding.return_value = {"data": [{"embedding": [0.1, 0.2, 0.3]}]}
    mock_client = MagicMock()
    mock_client.get_collections.return_value.collections = []

    result = ingest_file(f, "my_docs", config, mock_model, mock_client)

    assert result["file"] == "a.json"
    assert result["docs_processed"] == 1
    assert result["chunks_ingested"] == 4  # 500 chars, chunk=200, step=150 -> 4
    assert result["errors"] == []
    mock_client.create_collection.assert_called_once()
    mock_client.delete.assert_called_once()
    assert mock_client.upsert.called

    assert count == 1
    mock_client.upsert.assert_called_once()
    call_kwargs = mock_client.upsert.call_args.kwargs
    assert call_kwargs["collection_name"] == "my_docs"
    points = call_kwargs["points"]
    assert len(points) == 1
    assert points[0].payload["source"] == "test.pdf"
    assert points[0].payload["content"] == "텍스트"
    assert points[0].payload["language"] == "ko"
    assert points[0].vector == [0.1, 0.2, 0.3]

def test_ingest_file_jsonl_multi_doc(tmp_path):
    docs = [_doc("D1", "short"), _doc("D2", "A" * 300)]
    f = tmp_path / "a.jsonl"
    f.write_text("\n".join(json_module.dumps(d) for d in docs), encoding="utf-8")

def test_upsert_points_batching():
    mock_client = MagicMock()
    chunks = [
        {"chunk_id": i, "content": f"텍스트{i}", "page": None, "position": "middle"}
        for i in range(50)
    ]
    vectors = [[0.1] * 3 for _ in range(50)]
    source_meta = {
        "source": "big.pdf",
        "file_type": "pdf",
        "author": None,
        "title": None,
        "language": "ko",
    }
    mock_model = MagicMock()
    mock_model.create_embedding.return_value = {"data": [{"embedding": [0.0, 0.0, 0.0]}]}
    mock_client = MagicMock()
    mock_client.get_collections.return_value.collections = []

    result = ingest_file(f, "my_docs", config, mock_model, mock_client)

    assert result["docs_processed"] == 2
    # D1: "short" -> 1 chunk. D2: 300 chars, chunk=200/overlap=50 -> starts 0,150 -> 2 chunks
    assert result["chunks_ingested"] == 3
    assert mock_client.delete.call_count == 2

def test_ingest_file(tmp_path):
    json_data = {
        "source": "보고서.pdf",
        "file_type": "pdf",
        "author": "홍길동",
        "title": "2024 보고서",
        "language": "ko",
        "chunks": [
            {"chunk_id": 0, "content": "첫 번째 내용", "page": 1, "position": "first"},
            {"chunk_id": 1, "content": "두 번째 내용", "page": 1, "position": "last"},
        ],
    }
    json_file = tmp_path / "보고서.json"
    json_file.write_text(json_module.dumps(json_data, ensure_ascii=False), encoding="utf-8")

def test_ingest_file_skips_empty_content(tmp_path):
    doc = _doc("D1", content="")
    f = tmp_path / "a.json"
    f.write_text(json_module.dumps(doc), encoding="utf-8")

    config = {
        "embedding": {"embedding_dim": 3},
        "chunking": {"chunk_size": 200, "overlap": 50},
    }
    mock_model = MagicMock()
    mock_client = MagicMock()
    mock_client.get_collections.return_value.collections = []

    result = ingest_file(f, "my_docs", config, mock_model, mock_client)

    assert result["chunks_ingested"] == 0
    assert result["docs_processed"] == 1
    assert any("빈 content" in e for e in result["errors"])
    mock_client.upsert.assert_not_called()


def test_ingest_file_missing_doc_id_uses_fallback(tmp_path):
    doc = _doc("D1", content="hello")
    doc.pop("doc_id")
    f = tmp_path / "a.json"
    f.write_text(json_module.dumps(doc), encoding="utf-8")

    config = {
        "embedding": {"embedding_dim": 3},
        "chunking": {"chunk_size": 200, "overlap": 50},
    }
    mock_model = MagicMock()
    mock_model.create_embedding.return_value = {"data": [{"embedding": [0.0, 0.0, 0.0]}]}
    mock_client = MagicMock()
    mock_client.get_collections.return_value.collections = []

    with pytest.raises(ValueError, match="청크가 없습니다"):
        ingest_file(json_file, "my_docs", config, mock_model, mock_client)


def test_load_chunk_document_jsonl(tmp_path):
    jsonl_file = tmp_path / "file1.jsonl"
    jsonl_file.write_text(
        "\n".join(
            [
                json_module.dumps(
                    {
                        "source": "source.pdf",
                        "file_type": "pdf",
                        "language": "ko",
                        "chunk_id": 0,
                        "content": "첫 번째",
                        "page": 1,
                        "position": "first",
                    },
                    ensure_ascii=False,
                ),
                json_module.dumps(
                    {
                        "source": "source.pdf",
                        "file_type": "pdf",
                        "language": "ko",
                        "chunk_id": 1,
                        "content": "두 번째",
                        "page": 1,
                        "position": "last",
                    },
                    ensure_ascii=False,
                ),
            ]
        ),
        encoding="utf-8",
    )

    data = load_chunk_document(jsonl_file)

    assert data["source"] == "source.pdf"
    assert data["file_type"] == "pdf"
    assert len(data["chunks"]) == 2
    assert data["chunks"][0]["content"] == "첫 번째"
    assert data["chunks"][1]["chunk_id"] == 1


def test_ingest_file_jsonl(tmp_path):
    jsonl_file = tmp_path / "file1.jsonl"
    jsonl_file.write_text(
        "\n".join(
            [
                json_module.dumps(
                    {
                        "source": "source.pdf",
                        "file_type": "pdf",
                        "chunk_id": 0,
                        "content": "첫 번째",
                    },
                    ensure_ascii=False,
                ),
                json_module.dumps(
                    {
                        "source": "source.pdf",
                        "file_type": "pdf",
                        "chunk_id": 1,
                        "content": "두 번째",
                    },
                    ensure_ascii=False,
                ),
            ]
        ),
        encoding="utf-8",
    )

    config = {"embedding": {"embedding_dim": 1024}}
    mock_model = MagicMock()
    mock_model.create_embedding.return_value = {"data": [{"embedding": [0.1] * 1024}]}
    mock_client = MagicMock()
    mock_client.get_collections.return_value.collections = []

    result = ingest_file(jsonl_file, "my_docs", config, mock_model, mock_client)

    assert result["source"] == "source.pdf"
    assert result["chunks_ingested"] == 2
    mock_client.upsert.assert_called_once()


def test_load_chunk_document_jsonl_nested_content(tmp_path):
    jsonl_file = tmp_path / "nested.jsonl"
    jsonl_file.write_text(
        "\n".join(
            [
                json_module.dumps(
                    {
                        "source": "weekly_reports.pdf",
                        "file_type": "pdf",
                        "chunk_id": 0,
                        "chunk": {"content": "중첩 첫 번째"},
                    },
                    ensure_ascii=False,
                ),
                json_module.dumps(
                    {
                        "source": "weekly_reports.pdf",
                        "file_type": "pdf",
                        "chunk_id": 1,
                        "payload": {"text": "중첩 두 번째"},
                    },
                    ensure_ascii=False,
                ),
            ]
        ),
        encoding="utf-8",
    )

    data = load_chunk_document(jsonl_file)

    assert len(data["chunks"]) == 2
    assert data["chunks"][0]["content"] == "중첩 첫 번째"
    assert data["chunks"][1]["content"] == "중첩 두 번째"
