import json as json_module
from unittest.mock import MagicMock, patch

import pytest

from ingestor import (
    delete_existing_source,
    embed_chunks,
    get_or_create_collection,
    ingest_file,
    is_qdrant_healthy,
    load_config,
    upsert_points,
)


def test_load_config(tmp_path):
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        "qdrant:\n  url: http://localhost:6333\n  default_collection: test\n"
        "embedding:\n  model_path: /model.gguf\n  embedding_dim: 1024\n"
        "paths:\n  input_dir: ./input\n",
        encoding="utf-8",
    )
    config = load_config(str(cfg))
    assert config["qdrant"]["url"] == "http://localhost:6333"
    assert config["embedding"]["embedding_dim"] == 1024


def test_is_qdrant_healthy_true():
    mock_client = MagicMock()
    mock_client.get_collections.return_value = MagicMock()
    with patch("ingestor.QdrantClient", return_value=mock_client):
        config = {"qdrant": {"url": "http://localhost:6333"}}
        assert is_qdrant_healthy(config) is True


def test_is_qdrant_healthy_false():
    with patch("ingestor.QdrantClient", side_effect=Exception("연결 거부")):
        config = {"qdrant": {"url": "http://localhost:6333"}}
        assert is_qdrant_healthy(config) is False


def test_get_or_create_collection_creates_new():
    mock_client = MagicMock()
    mock_client.get_collections.return_value.collections = []

    get_or_create_collection(mock_client, "new_col", 1024)

    mock_client.create_collection.assert_called_once()
    call_kwargs = mock_client.create_collection.call_args.kwargs
    assert call_kwargs["collection_name"] == "new_col"


def test_get_or_create_collection_skips_existing():
    mock_client = MagicMock()
    existing = MagicMock()
    existing.name = "existing_col"
    mock_client.get_collections.return_value.collections = [existing]

    get_or_create_collection(mock_client, "existing_col", 1024)

    mock_client.create_collection.assert_not_called()


def test_delete_existing_source():
    mock_client = MagicMock()

    delete_existing_source(mock_client, "my_docs", "보고서.pdf")

    mock_client.delete.assert_called_once()
    call_kwargs = mock_client.delete.call_args.kwargs
    assert call_kwargs["collection_name"] == "my_docs"
    selector = call_kwargs["points_selector"]
    condition = selector.filter.must[0]
    assert condition.key == "source"
    assert condition.match.value == "보고서.pdf"


def test_embed_chunks_returns_vectors():
    mock_model = MagicMock()
    mock_model.create_embedding.return_value = {
        "data": [{"embedding": [0.1, 0.2, 0.3]}]
    }
    chunks = [{"text": "첫 번째 청크"}, {"text": "두 번째 청크"}]

    result = embed_chunks(mock_model, chunks)

    assert len(result) == 2
    assert result[0] == [0.1, 0.2, 0.3]
    assert result[1] == [0.1, 0.2, 0.3]
    assert mock_model.create_embedding.call_count == 2


def test_embed_chunks_empty():
    mock_model = MagicMock()
    result = embed_chunks(mock_model, [])
    assert result == []
    mock_model.create_embedding.assert_not_called()


def test_upsert_points():
    mock_client = MagicMock()
    chunks = [
        {"chunk_id": 0, "text": "텍스트", "page": 1, "position": "first"},
    ]
    vectors = [[0.1, 0.2, 0.3]]
    source_meta = {
        "source": "test.pdf",
        "file_type": "pdf",
        "author": None,
        "title": None,
        "language": "ko",
    }

    count = upsert_points(mock_client, "my_docs", chunks, vectors, source_meta)

    assert count == 1
    mock_client.upsert.assert_called_once()
    call_kwargs = mock_client.upsert.call_args.kwargs
    assert call_kwargs["collection_name"] == "my_docs"
    points = call_kwargs["points"]
    assert len(points) == 1
    assert points[0].payload["source"] == "test.pdf"
    assert points[0].payload["text"] == "텍스트"
    assert points[0].payload["language"] == "ko"
    assert points[0].vector == [0.1, 0.2, 0.3]


def test_upsert_points_batching():
    mock_client = MagicMock()
    chunks = [
        {"chunk_id": i, "text": f"텍스트{i}", "page": None, "position": "middle"}
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

    count = upsert_points(mock_client, "col", chunks, vectors, source_meta, batch_size=32)

    assert count == 50
    assert mock_client.upsert.call_count == 2


def test_ingest_file(tmp_path):
    json_data = {
        "source": "보고서.pdf",
        "file_type": "pdf",
        "author": "홍길동",
        "title": "2024 보고서",
        "language": "ko",
        "chunks": [
            {"chunk_id": 0, "text": "첫 번째 내용", "page": 1, "position": "first"},
            {"chunk_id": 1, "text": "두 번째 내용", "page": 1, "position": "last"},
        ],
    }
    json_file = tmp_path / "보고서.json"
    json_file.write_text(json_module.dumps(json_data, ensure_ascii=False), encoding="utf-8")

    config = {"embedding": {"embedding_dim": 1024}}

    mock_model = MagicMock()
    mock_model.create_embedding.return_value = {"data": [{"embedding": [0.1] * 1024}]}
    mock_client = MagicMock()
    mock_client.get_collections.return_value.collections = []

    result = ingest_file(json_file, "my_docs", config, mock_model, mock_client)

    assert result["source"] == "보고서.pdf"
    assert result["collection"] == "my_docs"
    assert result["chunks_ingested"] == 2
    mock_client.create_collection.assert_called_once()
    mock_client.delete.assert_called_once()
    mock_client.upsert.assert_called_once()


def test_ingest_file_empty_chunks(tmp_path):
    json_data = {"source": "empty.pdf", "file_type": "pdf", "chunks": []}
    json_file = tmp_path / "empty.json"
    json_file.write_text(json_module.dumps(json_data), encoding="utf-8")

    config = {"embedding": {"embedding_dim": 1024}}
    mock_model = MagicMock()
    mock_client = MagicMock()
    mock_client.get_collections.return_value.collections = []

    with pytest.raises(ValueError, match="청크가 없습니다"):
        ingest_file(json_file, "my_docs", config, mock_model, mock_client)
