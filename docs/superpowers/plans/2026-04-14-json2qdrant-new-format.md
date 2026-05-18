# json2qdrant New Input Format Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rewrite the ingestor to accept flat-metadata JSON/JSONL files, chunk `content` with overlap inside the ingestor, re-upsert by `doc_id`, and fix the Streamlit empty-label warning.

**Architecture:** `ingestor.py` gains `load_documents`, `chunk_text`, `delete_existing_doc`, and a rewritten `ingest_file` that iterates docs inside a file. `app_ingest.py` exposes chunk_size/overlap settings, rebuilds the file list columns, and replaces empty checkbox labels with a visible-but-collapsed label. Tests are rewritten against the new format.

**Tech Stack:** Python 3, Streamlit, qdrant-client, PyYAML, pytest, Ollama HTTP API.

---

## File Structure

- **Modify** `ingestor.py` — replace old chunk-array ingestion with flat-format loader + chunker + doc_id-keyed re-upsert.
- **Modify** `config.yaml` — add `chunking:` section.
- **Modify** `app_ingest.py` — new settings inputs, rebuilt file list, empty-label fix.
- **Modify** `i18n.py` — new keys in ko and zh.
- **Rewrite** `tests/test_ingestor.py` — new tests against new format.
- **Rewrite** `tests/sample.json` and remove stale fixtures — new flat format.

---

## Task 1: Add chunking config section

**Files:**
- Modify: `config.yaml`

- [ ] **Step 1: Append chunking section**

Edit `config.yaml` so it contains:

```yaml
embedding:
  backend: ollama
  embedding_dim: 1024
  model_name: bge-m3:latest
  ollama_url: http://localhost:11434
paths:
  input_dir: ./input
qdrant:
  default_collection: my_documents
  url: http://localhost:6333
ui:
  language: ko
chunking:
  chunk_size: 200
  overlap: 50
```

- [ ] **Step 2: Commit**

```bash
git add config.yaml
git commit -m "chore: add chunking config defaults"
```

---

## Task 2: Implement `chunk_text`

**Files:**
- Modify: `ingestor.py` (add function near top, after imports)
- Test: `tests/test_ingestor.py` (new file, rewritten progressively)

- [ ] **Step 1: Replace `tests/test_ingestor.py` with a fresh skeleton**

Overwrite the file with:

```python
import json as json_module
from unittest.mock import MagicMock, patch

import pytest

from ingestor import chunk_text
```

- [ ] **Step 2: Write failing tests for `chunk_text`**

Append to `tests/test_ingestor.py`:

```python
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
```

- [ ] **Step 3: Run tests, confirm they fail with ImportError on `chunk_text`**

Run: `pytest tests/test_ingestor.py -v`
Expected: ImportError for `chunk_text`.

- [ ] **Step 4: Add `chunk_text` to `ingestor.py`**

Insert after the existing `load_config` function:

```python
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
        if start + chunk_size >= len(text):
            break
    return chunks
```

- [ ] **Step 5: Run tests, confirm pass**

Run: `pytest tests/test_ingestor.py -v`
Expected: all five `chunk_text` tests pass.

- [ ] **Step 6: Commit**

```bash
git add ingestor.py tests/test_ingestor.py
git commit -m "feat(ingestor): add chunk_text with size/overlap slicing"
```

---

## Task 3: Implement `load_documents`

**Files:**
- Modify: `ingestor.py`
- Test: `tests/test_ingestor.py`

- [ ] **Step 1: Extend import line in test file**

Change the import at the top of `tests/test_ingestor.py`:

```python
from ingestor import chunk_text, load_documents
```

- [ ] **Step 2: Add failing tests**

Append:

```python
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
```

- [ ] **Step 3: Run tests, confirm they fail with ImportError**

Run: `pytest tests/test_ingestor.py -v`
Expected: ImportError on `load_documents`.

- [ ] **Step 4: Implement `load_documents`**

Add to `ingestor.py` after `chunk_text`:

```python
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
```

- [ ] **Step 5: Run tests**

Run: `pytest tests/test_ingestor.py -v`
Expected: all `load_documents` tests pass.

- [ ] **Step 6: Commit**

```bash
git add ingestor.py tests/test_ingestor.py
git commit -m "feat(ingestor): add load_documents with jsonl/array/object detection"
```

---

## Task 4: Replace `embed_chunks` signature (strings not dicts)

**Files:**
- Modify: `ingestor.py`
- Test: `tests/test_ingestor.py`

- [ ] **Step 1: Update test import**

```python
from ingestor import chunk_text, embed_chunks, load_documents
```

- [ ] **Step 2: Add failing tests**

```python
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
```

- [ ] **Step 3: Run tests (they should fail because old `embed_chunks` expects dicts)**

Run: `pytest tests/test_ingestor.py::test_embed_chunks_returns_vectors -v`
Expected: TypeError on `chunk["text"]` because we now pass strings.

- [ ] **Step 4: Rewrite `embed_chunks` in `ingestor.py`**

Replace the existing `embed_chunks` function with:

```python
def embed_chunks(model: Any, texts: list[str]) -> list[list[float]]:
    vectors: list[list[float]] = []
    for text in texts:
        response = model.create_embedding(text)
        vectors.append(response["data"][0]["embedding"])
    return vectors
```

- [ ] **Step 5: Run tests**

Run: `pytest tests/test_ingestor.py::test_embed_chunks_returns_vectors tests/test_ingestor.py::test_embed_chunks_empty -v`
Expected: both pass.

- [ ] **Step 6: Commit**

```bash
git add ingestor.py tests/test_ingestor.py
git commit -m "refactor(ingestor): embed_chunks accepts plain text list"
```

---

## Task 5: Implement `delete_existing_doc` and remove `delete_existing_source`

**Files:**
- Modify: `ingestor.py`
- Test: `tests/test_ingestor.py`

- [ ] **Step 1: Update test import**

```python
from ingestor import (
    chunk_text,
    delete_existing_doc,
    embed_chunks,
    load_documents,
)
```

- [ ] **Step 2: Add failing test**

```python
def test_delete_existing_doc_filters_by_doc_id():
    mock_client = MagicMock()
    delete_existing_doc(mock_client, "my_docs", "2025_W34_abc")

    mock_client.delete.assert_called_once()
    kwargs = mock_client.delete.call_args.kwargs
    assert kwargs["collection_name"] == "my_docs"
    condition = kwargs["points_selector"].filter.must[0]
    assert condition.key == "doc_id"
    assert condition.match.value == "2025_W34_abc"
```

- [ ] **Step 3: Run test, confirm ImportError**

Run: `pytest tests/test_ingestor.py::test_delete_existing_doc_filters_by_doc_id -v`
Expected: ImportError.

- [ ] **Step 4: Replace `delete_existing_source` in `ingestor.py`**

Remove the `delete_existing_source` function entirely and add:

```python
def delete_existing_doc(client: QdrantClient, collection: str, doc_id: str) -> None:
    client.delete(
        collection_name=collection,
        points_selector=FilterSelector(
            filter=Filter(
                must=[FieldCondition(key="doc_id", match=MatchValue(value=doc_id))]
            )
        ),
    )
```

- [ ] **Step 5: Run test**

Run: `pytest tests/test_ingestor.py::test_delete_existing_doc_filters_by_doc_id -v`
Expected: pass.

- [ ] **Step 6: Commit**

```bash
git add ingestor.py tests/test_ingestor.py
git commit -m "refactor(ingestor): key re-upsert on doc_id instead of source"
```

---

## Task 6: Implement `build_points` with full metadata copy

**Files:**
- Modify: `ingestor.py`
- Test: `tests/test_ingestor.py`

- [ ] **Step 1: Update test import**

```python
from ingestor import (
    build_points,
    chunk_text,
    delete_existing_doc,
    embed_chunks,
    load_documents,
)
```

- [ ] **Step 2: Add failing test**

```python
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
```

- [ ] **Step 3: Run tests, confirm ImportError**

Run: `pytest tests/test_ingestor.py -v -k build_points`
Expected: ImportError.

- [ ] **Step 4: Add `build_points` to `ingestor.py`**

```python
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
```

- [ ] **Step 5: Run tests**

Run: `pytest tests/test_ingestor.py -v -k build_points`
Expected: both pass.

- [ ] **Step 6: Commit**

```bash
git add ingestor.py tests/test_ingestor.py
git commit -m "feat(ingestor): add build_points with full metadata copy"
```

---

## Task 7: Rewrite `ingest_file` and remove old `upsert_points`

**Files:**
- Modify: `ingestor.py`
- Test: `tests/test_ingestor.py`

- [ ] **Step 1: Update test import**

```python
from ingestor import (
    build_points,
    chunk_text,
    delete_existing_doc,
    embed_chunks,
    get_or_create_collection,
    ingest_file,
    is_qdrant_healthy,
    load_config,
    load_documents,
)
```

- [ ] **Step 2: Add failing ingest_file tests**

```python
def test_ingest_file_single_doc(tmp_path):
    doc = _doc("D1", content="A" * 500)
    f = tmp_path / "a.json"
    f.write_text(json_module.dumps(doc), encoding="utf-8")

    config = {
        "embedding": {"embedding_dim": 3},
        "chunking": {"chunk_size": 200, "overlap": 50},
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


def test_ingest_file_jsonl_multi_doc(tmp_path):
    docs = [_doc("D1", "short"), _doc("D2", "A" * 300)]
    f = tmp_path / "a.jsonl"
    f.write_text("\n".join(json_module.dumps(d) for d in docs), encoding="utf-8")

    config = {
        "embedding": {"embedding_dim": 3},
        "chunking": {"chunk_size": 200, "overlap": 50},
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

    result = ingest_file(f, "my_docs", config, mock_model, mock_client)

    assert result["docs_processed"] == 1
    assert any("doc_id" in e for e in result["errors"])
    # still deletes using fallback key
    mock_client.delete.assert_called_once()
```

- [ ] **Step 3: Run tests, confirm failure**

Run: `pytest tests/test_ingestor.py -v -k ingest_file`
Expected: failures because old `ingest_file` signature expects `chunks` field.

- [ ] **Step 4: Rewrite `ingest_file` in `ingestor.py`**

Remove the old `ingest_file` and `upsert_points` functions entirely, then add:

```python
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
```

- [ ] **Step 5: Run all tests**

Run: `pytest tests/test_ingestor.py -v`
Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add ingestor.py tests/test_ingestor.py
git commit -m "feat(ingestor): rewrite ingest_file for flat-format docs"
```

---

## Task 8: Delete stale fixtures and regenerate `tests/sample.json`

**Files:**
- Delete: `tests/Chain-of-Retrieval_Augmented_Generation.json` (if uses old format)
- Modify: `tests/sample.json`

- [ ] **Step 1: Check fixtures**

Run: `pytest tests/ -v` to confirm nothing else relies on the old fixtures.
Expected: tests pass (only `test_ingestor.py` exists).

- [ ] **Step 2: Replace `tests/sample.json` with new format**

Overwrite `tests/sample.json`:

```json
{
  "doc_id": "2025_W34_sample",
  "title": "샘플 주간보고",
  "content": "이것은 샘플 주간보고 내용입니다. 청크 테스트용 본문이며 충분한 길이를 갖도록 반복합니다. " ,
  "created_time": "2025-08-24",
  "source_file": "input/sample.docx",
  "filename": "sample.docx",
  "year": 2025,
  "week": 34,
  "file_size": 1234,
  "processed_at": "2025-08-24 00:00:00",
  "document_type": "weekly_report",
  "parts_total": 1,
  "part_index": 1
}
```

- [ ] **Step 3: Remove unused old fixture**

Run: `git rm tests/Chain-of-Retrieval_Augmented_Generation.json` (only if it was old format and unused)

If unsure, inspect it first — if it contains `"chunks": [...]`, remove it.

- [ ] **Step 4: Commit**

```bash
git add tests/sample.json
git commit -m "test: update sample fixtures to flat-format"
```

---

## Task 9: Add i18n keys for new UI (ko and zh)

**Files:**
- Modify: `i18n.py`

- [ ] **Step 1: Add keys to both language blocks**

In `i18n.py`, inside the `"ko"` dict add (keep all existing keys):

```python
        "col_doc_id": "**doc_id / 제목**",
        "col_doc_type": "**문서 타입**",
        "col_est_chunks": "**예상 청크 수**",
        "chunk_size_label": "청크 크기 (문자)",
        "overlap_label": "오버랩 (문자)",
        "checkbox_select_label": "선택",
        "log_doc_success": "✅ {name} → {docs}개 문서, {chunks}개 청크 적재 완료",
        "log_doc_partial": "⚠️ {name} → {docs}개 문서, {chunks}개 청크 (에러 {errors}건)",
        "multi_docs_label": "{n} docs",
```

In the `"zh"` dict add:

```python
        "col_doc_id": "**doc_id / 标题**",
        "col_doc_type": "**文档类型**",
        "col_est_chunks": "**预估块数**",
        "chunk_size_label": "块大小 (字符)",
        "overlap_label": "重叠 (字符)",
        "checkbox_select_label": "选择",
        "log_doc_success": "✅ {name} → {docs} 个文档, {chunks} 个块已导入",
        "log_doc_partial": "⚠️ {name} → {docs} 个文档, {chunks} 个块 ({errors} 个错误)",
        "multi_docs_label": "{n} docs",
```

Also update the stale `no_json_files` / `col_source` text to not reference `file2json` chunking if desired (leave as-is — not in scope).

- [ ] **Step 2: Commit**

```bash
git add i18n.py
git commit -m "i18n: add keys for chunking UI and new file list columns"
```

---

## Task 10: Rewrite `app_ingest.py` — settings, file list, empty label fix

**Files:**
- Modify: `app_ingest.py`

- [ ] **Step 1: Update the settings expander section**

Inside `with st.expander(tr("settings_header"), expanded=False):`, after the existing `model_name_input = st.text_input(...)` line and before the save button, add:

```python
    chunk_size_input = st.number_input(
        tr("chunk_size_label"),
        min_value=50,
        max_value=8000,
        value=int(config.get("chunking", {}).get("chunk_size", 200)),
        step=10,
    )
    overlap_input = st.number_input(
        tr("overlap_label"),
        min_value=0,
        max_value=max(0, int(chunk_size_input) - 1),
        value=int(config.get("chunking", {}).get("overlap", 50)),
        step=10,
    )
```

And inside the `if st.button(tr("save_settings_btn")):` block, add before `save_config()`:

```python
        config.setdefault("chunking", {})
        config["chunking"]["chunk_size"] = int(chunk_size_input)
        config["chunking"]["overlap"] = int(overlap_input)
```

- [ ] **Step 2: Replace file list reading block**

Replace the existing block from `if not json_files:` through the `st.divider()` after the rows loop with:

```python
if not json_files:
    st.info(tr("no_json_files"))
else:
    from ingestor import load_documents, chunk_text  # local import avoids top-level cycle risk

    chunk_size = int(config.get("chunking", {}).get("chunk_size", 200))
    overlap = int(config.get("chunking", {}).get("overlap", 50))

    file_rows = []
    for f in json_files:
        try:
            docs = load_documents(f)
            if len(docs) == 1:
                label = docs[0].get("doc_id") or docs[0].get("title") or f.name
                doc_type = docs[0].get("document_type") or "-"
            else:
                label = tr("multi_docs_label", n=len(docs))
                types = {d.get("document_type") for d in docs if d.get("document_type")}
                doc_type = ", ".join(sorted(t for t in types if t)) or "-"
            est_chunks = sum(
                len(chunk_text(d.get("content") or "", chunk_size, overlap))
                for d in docs
            )
        except Exception as e:
            label = tr("read_error")
            doc_type = str(e)[:40]
            est_chunks = "-"
        file_rows.append(
            {"file": f, "name": f.name, "label": label, "doc_type": doc_type, "chunks": est_chunks}
        )

    h1, h2, h3, h4, h5 = st.columns([0.5, 2.5, 2.5, 1.5, 1])
    h1.markdown(tr("col_select"))
    h2.markdown(tr("col_filename"))
    h3.markdown(tr("col_doc_id"))
    h4.markdown(tr("col_doc_type"))
    h5.markdown(tr("col_est_chunks"))
    st.divider()

    selections = {}
    for row in file_rows:
        c1, c2, c3, c4, c5 = st.columns([0.5, 2.5, 2.5, 1.5, 1])
        with c1:
            selections[row["name"]] = st.checkbox(
                tr("checkbox_select_label"),
                value=True,
                key=f"sel_{row['name']}",
                label_visibility="collapsed",
            )
        with c2:
            st.text(row["name"])
        with c3:
            st.text(row["label"])
        with c4:
            st.text(row["doc_type"])
        with c5:
            st.text(str(row["chunks"]))

    st.divider()
```

- [ ] **Step 3: Update ingest result logging**

In the result-logging loop, replace:

```python
                logs.append(
                    tr("log_success", name=json_path.name, n=result["chunks_ingested"])
                )
```

with:

```python
                if result["errors"]:
                    logs.append(
                        tr(
                            "log_doc_partial",
                            name=json_path.name,
                            docs=result["docs_processed"],
                            chunks=result["chunks_ingested"],
                            errors=len(result["errors"]),
                        )
                    )
                else:
                    logs.append(
                        tr(
                            "log_doc_success",
                            name=json_path.name,
                            docs=result["docs_processed"],
                            chunks=result["chunks_ingested"],
                        )
                    )
```

- [ ] **Step 4: Manual smoke run**

Run: `streamlit run app_ingest.py`
Expected:
- No `'label' got an empty value` warning in the terminal.
- Settings expander shows chunk size / overlap inputs.
- File list columns: 선택 / 파일명 / doc_id / 문서 타입 / 예상 청크 수.
- Loading `tests/sample.json` into `input/` shows correct estimated chunks.

Stop the server with Ctrl+C after confirming.

- [ ] **Step 5: Run the test suite**

Run: `pytest tests/ -v`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add app_ingest.py
git commit -m "feat(ui): add chunk settings, rebuild file list, fix empty label"
```

---

## Task 11: Final verification

- [ ] **Step 1: Full test run**

Run: `pytest tests/ -v`
Expected: all green.

- [ ] **Step 2: Git log check**

Run: `git log --oneline -15`
Expected: commits from tasks 1–10 visible, clean history.

- [ ] **Step 3: Inspect working tree**

Run: `git status`
Expected: clean (no uncommitted changes).

---

## Self-Review Notes

- Spec coverage: chunking config (T1), load_documents (T3), chunk_text (T2), embed_chunks refactor (T4), delete_existing_doc (T5), build_points + metadata copy (T6), ingest_file rewrite with empty/missing-doc_id handling (T7), fixture refresh (T8), i18n ko+zh (T9), UI settings + list + label fix (T10). All covered.
- i18n: spec mentioned "en" but codebase only has ko/zh — plan matches codebase reality.
- Type consistency: `ingest_file` return shape `{file, docs_processed, chunks_ingested, errors}` is used consistently in T7 tests and T10 UI log code.
- No placeholders — every code step contains literal code.
