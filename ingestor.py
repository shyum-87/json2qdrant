import json
import urllib.request
import uuid
from pathlib import Path
from typing import Any

import yaml
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    FilterSelector,
    MatchValue,
    PointStruct,
    VectorParams,
)


def load_config(config_path: str = "config.yaml") -> dict:
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    if chunk_size <= 0 or overlap < 0 or overlap >= chunk_size:
        raise ValueError("잘못된 chunk_size/overlap")
    text = text or ""
    if not text:
        return []
    step = chunk_size - overlap
    chunks: list[str] = []
    for start in range(0, len(text), step):
        piece = text[start : start + chunk_size]
        if piece:
            chunks.append(piece)
    return chunks


def load_documents(path: Path) -> list[dict]:
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        raise ValueError(f"빈 파일: {path.name}")
    # Try JSONL first if it looks multi-line
    if "\n" in raw:
        try:
            docs = [
                json.loads(line) for line in raw.splitlines() if line.strip()
            ]
            if docs and all(isinstance(d, dict) for d in docs):
                return docs
        except json.JSONDecodeError:
            pass
    data = json.loads(raw)
    if isinstance(data, list):
        if not all(isinstance(d, dict) for d in data):
            raise ValueError(f"배열 안에 객체가 아닌 항목: {path.name}")
        return data
    if isinstance(data, dict):
        return [data]
    raise ValueError(f"지원하지 않는 JSON 구조: {path.name}")


def get_qdrant_client(config: dict) -> QdrantClient:
    return QdrantClient(url=config["qdrant"]["url"], timeout=5)


def is_qdrant_healthy(config: dict) -> bool:
    try:
        client = QdrantClient(url=config["qdrant"]["url"], timeout=2)
        client.get_collections()
        return True
    except Exception:
        return False


def get_or_create_collection(client: QdrantClient, name: str, dim: int) -> None:
    existing = [c.name for c in client.get_collections().collections]
    if name not in existing:
        client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
        )


def delete_existing_doc(client: QdrantClient, collection: str, doc_id: str) -> None:
    client.delete(
        collection_name=collection,
        points_selector=FilterSelector(
            filter=Filter(
                must=[FieldCondition(key="doc_id", match=MatchValue(value=doc_id))]
            )
        ),
    )


def embed_chunks(model: Any, texts: list[str]) -> list[list[float]]:
    vectors: list[list[float]] = []
    for text in texts:
        response = model.create_embedding(text)
        vectors.append(response["data"][0]["embedding"])
    return vectors


_DOC_META_KEYS = (
    "doc_id",
    "title",
    "created_time",
    "source_file",
    "filename",
    "year",
    "week",
    "file_size",
    "processed_at",
    "document_type",
    "parts_total",
    "part_index",
)


def build_points(
    doc: dict,
    chunks: list[str],
    vectors: list[list[float]],
    collection: str,
) -> list[PointStruct]:
    if len(chunks) != len(vectors):
        raise ValueError("chunks and vectors length mismatch")
    base_meta = {key: doc.get(key) for key in _DOC_META_KEYS}
    total = len(chunks)
    points: list[PointStruct] = []
    for i, (chunk, vector) in enumerate(zip(chunks, vectors)):
        payload = dict(base_meta)
        payload["chunk_index"] = i
        payload["chunk_total"] = total
        payload["text"] = chunk
        payload["collection_name"] = collection
        points.append(PointStruct(id=str(uuid.uuid4()), vector=vector, payload=payload))
    return points


def _upsert_in_batches(
    client: QdrantClient,
    collection: str,
    points: list[PointStruct],
    batch_size: int = 32,
) -> None:
    for i in range(0, len(points), batch_size):
        client.upsert(collection_name=collection, points=points[i : i + batch_size])


def _fallback_doc_id(doc: dict) -> str:
    return f"{doc.get('source_file') or ''}::{doc.get('filename') or ''}"


def ingest_file(
    json_path: Path,
    collection: str,
    config: dict,
    model: Any,
    client: QdrantClient,
) -> dict:
    docs = load_documents(json_path)

    dim = config["embedding"]["embedding_dim"]
    chunk_cfg = config.get("chunking", {})
    chunk_size = int(chunk_cfg.get("chunk_size", 200))
    overlap = int(chunk_cfg.get("overlap", 50))

    get_or_create_collection(client, collection, dim)

    total_chunks = 0
    errors: list[str] = []

    for doc in docs:
        doc_id = doc.get("doc_id")
        if not doc_id:
            fallback = _fallback_doc_id(doc)
            errors.append(f"doc_id 누락, fallback 사용: {fallback}")
            doc_id = fallback

        content = doc.get("content") or ""
        if not content.strip():
            errors.append(f"빈 content: {doc_id}")
            delete_existing_doc(client, collection, doc_id)
            continue

        chunks = chunk_text(content, chunk_size, overlap)
        if not chunks:
            errors.append(f"청크 생성 실패: {doc_id}")
            continue

        delete_existing_doc(client, collection, doc_id)
        vectors = embed_chunks(model, chunks)
        points = build_points(doc, chunks, vectors, collection)
        _upsert_in_batches(client, collection, points)
        total_chunks += len(points)

    return {
        "file": json_path.name,
        "docs_processed": len(docs),
        "chunks_ingested": total_chunks,
        "errors": errors,
    }


class OllamaEmbedder:
    """Ollama /api/embeddings 래퍼. Llama.create_embedding과 동일한 반환 형태를 흉내낸다."""

    def __init__(self, base_url: str, model_name: str, timeout: float = 60.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name
        self.timeout = timeout

    def create_embedding(self, text: str) -> dict:
        payload = json.dumps({"model": self.model_name, "prompt": text}).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}/api/embeddings",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        embedding = body.get("embedding")
        if not embedding:
            raise RuntimeError(f"Ollama 임베딩 응답이 비어 있습니다: {body}")
        return {"data": [{"embedding": embedding}]}


def load_model(config: dict) -> Any:
    emb = config["embedding"]
    backend = emb.get("backend", "ollama")
    if backend == "ollama":
        return OllamaEmbedder(
            base_url=emb.get("ollama_url", "http://localhost:11434"),
            model_name=emb["model_name"],
        )
    if backend == "llama_cpp":
        from llama_cpp import Llama

        return Llama(
            model_path=emb["model_path"],
            n_gpu_layers=emb.get("n_gpu_layers", 0),
            n_ctx=emb.get("n_ctx", 512),
            embedding=True,
            verbose=False,
        )
    raise ValueError(f"알 수 없는 embedding.backend: {backend}")
