# json2qdrant Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** file2json이 생성한 JSON 파일의 각 chunk를 bge-m3 GGUF 모델로 임베딩하여 로컬 Qdrant 벡터 DB에 적재하는 독립 Streamlit 앱을 만든다.

**Architecture:** `ingestor.py`에 모든 임베딩/Qdrant 로직을 단일 책임 함수로 구성하고, `app_ingest.py`가 Streamlit UI로 이를 호출한다. Qdrant 바이너리는 `qdrant/` 폴더에 포함하고 UI에서 실행 가능하다. 모델은 Streamlit 세션당 최초 1회만 로드하여 `st.session_state`에 캐싱한다.

**Tech Stack:** Python 3.10+, venv, llama-cpp-python (GGUF 임베딩), qdrant-client, Streamlit, PyYAML, pytest

---

## 파일 맵

| 파일 | 역할 |
|------|------|
| `ingestor.py` | config 로드, Qdrant 연결, 컬렉션 관리, 임베딩, upsert |
| `app_ingest.py` | Streamlit UI — 서버 상태, 파일 목록, 적재 트리거, 로그 |
| `config.yaml` | Qdrant URL, 컬렉션명, 모델 경로, 임베딩 설정 |
| `requirements.txt` | Python 의존성 |
| `qdrant/qdrant.exe` | Qdrant Windows 바이너리 (수동 다운로드) |
| `qdrant/start_qdrant.bat` | Qdrant 실행 배치 파일 |
| `input/.gitkeep` | JSON 파일 드롭 위치 자리 표시자 |
| `tests/test_ingestor.py` | ingestor.py 단위 테스트 |

---

### Task 1: 프로젝트 스캐폴딩

**Files:**
- Create: `requirements.txt`
- Create: `config.yaml`
- Create: `.gitignore`
- Create: `qdrant/start_qdrant.bat`
- Create: `input/.gitkeep`
- Create: `tests/__init__.py`

- [ ] **Step 1: 가상환경 생성**

```bash
cd E:/json2qdrant
python -m venv .venv
.venv\Scripts\activate
```

Expected: `(.venv)` 프롬프트 표시

- [ ] **Step 2: requirements.txt 생성**

```
streamlit>=1.32.0
qdrant-client>=1.9.0
llama-cpp-python>=0.2.90
pyyaml>=6.0.1
pytest>=8.0.0
```

- [ ] **Step 3: config.yaml 생성**

```yaml
qdrant:
  url: http://localhost:6333
  default_collection: my_documents

embedding:
  model_path: C:/Users/shyum/.ollama/models/blobs/sha256-REPLACE_WITH_ACTUAL_HASH
  n_gpu_layers: 0
  n_ctx: 512
  embedding_dim: 1024

paths:
  input_dir: ./input
```

> `model_path`의 `sha256-REPLACE_WITH_ACTUAL_HASH`는 실제 bge-m3 GGUF 파일명으로 교체 필요.  
> `.ollama/models/blobs/` 폴더에서 `sha256-`으로 시작하는 가장 큰 파일이 bge-m3 모델 파일.

- [ ] **Step 4: .gitignore 생성**

```
.venv/
__pycache__/
*.pyc
input/
!input/.gitkeep
qdrant/qdrant.exe
qdrant/storage/
.claude/
```

- [ ] **Step 5: start_qdrant.bat 생성**

```bat
@echo off
cd /d "%~dp0"
qdrant.exe
pause
```

- [ ] **Step 6: 폴더 생성**

```bash
mkdir -p input tests qdrant
touch input/.gitkeep tests/__init__.py
```

- [ ] **Step 7: 의존성 설치**

```bash
pip install -r requirements.txt
```

> `llama-cpp-python` 설치 실패 시: Python 3.14용 사전 빌드 wheel이 없을 수 있음.  
> 이 경우 외부 네트워크에서 아래 명령으로 wheel을 다운로드 후 파일로 설치:
> ```bash
> # 외부 네트워크 환경에서
> pip download llama-cpp-python --only-binary=:all: -d ./wheels/
> # 폐쇄망에서
> pip install --no-index --find-links=./wheels/ llama-cpp-python
> ```

Expected: 오류 없이 설치 완료

- [ ] **Step 8: Qdrant 바이너리 다운로드 안내**

외부 네트워크에서 아래 URL에서 `qdrant-x86_64-pc-windows-msvc.zip` 다운로드:
```
https://github.com/qdrant/qdrant/releases/latest
```
압축 해제 후 `qdrant.exe`를 `E:/json2qdrant/qdrant/` 폴더에 복사.

- [ ] **Step 9: 커밋**

```bash
git add requirements.txt config.yaml .gitignore qdrant/start_qdrant.bat input/.gitkeep tests/__init__.py
git commit -m "chore: initial project scaffold"
```

---

### Task 2: load_config 및 is_qdrant_healthy

**Files:**
- Create: `ingestor.py`
- Create: `tests/test_ingestor.py`

- [ ] **Step 1: ingestor.py 뼈대 작성**

```python
# ingestor.py
import json
import uuid
import yaml
from pathlib import Path

from llama_cpp import Llama
from qdrant_client import QdrantClient
from qdrant_client.models import (
    VectorParams, Distance, PointStruct,
    Filter, FieldCondition, MatchValue, FilterSelector,
)


def load_config(config_path: str = "config.yaml") -> dict:
    raise NotImplementedError


def get_qdrant_client(config: dict) -> QdrantClient:
    raise NotImplementedError


def is_qdrant_healthy(config: dict) -> bool:
    raise NotImplementedError


def get_or_create_collection(client: QdrantClient, name: str, dim: int) -> None:
    raise NotImplementedError


def delete_existing_source(client: QdrantClient, collection: str, source: str) -> None:
    raise NotImplementedError


def embed_chunks(model: Llama, chunks: list[dict]) -> list[list[float]]:
    raise NotImplementedError


def upsert_points(
    client: QdrantClient,
    collection: str,
    chunks: list[dict],
    vectors: list[list[float]],
    source_meta: dict,
    batch_size: int = 32,
) -> int:
    raise NotImplementedError


def ingest_file(
    json_path: Path,
    collection: str,
    config: dict,
    model: Llama,
    client: QdrantClient,
) -> dict:
    raise NotImplementedError
```

- [ ] **Step 2: 실패하는 테스트 작성**

```python
# tests/test_ingestor.py
import pytest
import json as json_module
from unittest.mock import patch, MagicMock
from ingestor import load_config, is_qdrant_healthy


def test_load_config(tmp_path):
    cfg = tmp_path / "config.yaml"
    cfg.write_text(
        "qdrant:\n  url: http://localhost:6333\n  default_collection: test\n"
        "embedding:\n  model_path: /model.gguf\n  embedding_dim: 1024\n"
        "paths:\n  input_dir: ./input\n",
        encoding="utf-8"
    )
    config = load_config(str(cfg))
    assert config["qdrant"]["url"] == "http://localhost:6333"
    assert config["embedding"]["embedding_dim"] == 1024


def test_is_qdrant_healthy_true():
    mock_client = MagicMock()
    mock_client.get_collections.return_value = MagicMock()
    with patch("ingestor.QdrantClient", return_value=mock_client):
        with patch("ingestor.load_config", return_value={"qdrant": {"url": "http://localhost:6333"}}):
            config = {"qdrant": {"url": "http://localhost:6333"}}
            result = is_qdrant_healthy(config)
    assert result is True


def test_is_qdrant_healthy_false():
    with patch("ingestor.QdrantClient", side_effect=Exception("연결 거부")):
        config = {"qdrant": {"url": "http://localhost:6333"}}
        result = is_qdrant_healthy(config)
    assert result is False
```

- [ ] **Step 3: 테스트 실행 — 실패 확인**

```bash
pytest tests/test_ingestor.py -v
```

Expected: `NotImplementedError` 또는 FAILED 3개

- [ ] **Step 4: 구현**

```python
def load_config(config_path: str = "config.yaml") -> dict:
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_qdrant_client(config: dict) -> QdrantClient:
    return QdrantClient(url=config["qdrant"]["url"], timeout=5)


def is_qdrant_healthy(config: dict) -> bool:
    try:
        client = QdrantClient(url=config["qdrant"]["url"], timeout=2)
        client.get_collections()
        return True
    except Exception:
        return False
```

- [ ] **Step 5: 테스트 통과 확인**

```bash
pytest tests/test_ingestor.py -v
```

Expected: 3개 PASSED

- [ ] **Step 6: 커밋**

```bash
git add ingestor.py tests/test_ingestor.py
git commit -m "feat: add load_config and is_qdrant_healthy"
```

---

### Task 3: get_or_create_collection

**Files:**
- Modify: `ingestor.py`
- Modify: `tests/test_ingestor.py`

- [ ] **Step 1: 실패하는 테스트 추가**

```python
# tests/test_ingestor.py 에 추가
from ingestor import get_or_create_collection
from qdrant_client.models import VectorParams, Distance


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
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

```bash
pytest tests/test_ingestor.py::test_get_or_create_collection_creates_new tests/test_ingestor.py::test_get_or_create_collection_skips_existing -v
```

Expected: FAILED

- [ ] **Step 3: 구현**

```python
def get_or_create_collection(client: QdrantClient, name: str, dim: int) -> None:
    """컬렉션이 없으면 Cosine 거리 기반으로 생성."""
    existing = [c.name for c in client.get_collections().collections]
    if name not in existing:
        client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
        )
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
pytest tests/test_ingestor.py -v
```

Expected: 5개 PASSED

- [ ] **Step 5: 커밋**

```bash
git add ingestor.py tests/test_ingestor.py
git commit -m "feat: add get_or_create_collection"
```

---

### Task 4: delete_existing_source

**Files:**
- Modify: `ingestor.py`
- Modify: `tests/test_ingestor.py`

- [ ] **Step 1: 실패하는 테스트 추가**

```python
# tests/test_ingestor.py 에 추가
from ingestor import delete_existing_source


def test_delete_existing_source():
    mock_client = MagicMock()

    delete_existing_source(mock_client, "my_docs", "보고서.pdf")

    mock_client.delete.assert_called_once()
    call_kwargs = mock_client.delete.call_args.kwargs
    assert call_kwargs["collection_name"] == "my_docs"
    # filter 내부에 source 값이 포함되어 있는지 확인
    selector = call_kwargs["points_selector"]
    condition = selector.filter.must[0]
    assert condition.key == "source"
    assert condition.match.value == "보고서.pdf"
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

```bash
pytest tests/test_ingestor.py::test_delete_existing_source -v
```

Expected: FAILED

- [ ] **Step 3: 구현**

```python
def delete_existing_source(client: QdrantClient, collection: str, source: str) -> None:
    """같은 source 파일의 기존 Point를 모두 삭제."""
    client.delete(
        collection_name=collection,
        points_selector=FilterSelector(
            filter=Filter(
                must=[FieldCondition(key="source", match=MatchValue(value=source))]
            )
        ),
    )
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
pytest tests/test_ingestor.py -v
```

Expected: 6개 PASSED

- [ ] **Step 5: 커밋**

```bash
git add ingestor.py tests/test_ingestor.py
git commit -m "feat: add delete_existing_source"
```

---

### Task 5: embed_chunks

**Files:**
- Modify: `ingestor.py`
- Modify: `tests/test_ingestor.py`

- [ ] **Step 1: 실패하는 테스트 추가**

```python
# tests/test_ingestor.py 에 추가
from ingestor import embed_chunks


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
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

```bash
pytest tests/test_ingestor.py::test_embed_chunks_returns_vectors tests/test_ingestor.py::test_embed_chunks_empty -v
```

Expected: FAILED

- [ ] **Step 3: 구현**

```python
def embed_chunks(model: Llama, chunks: list[dict]) -> list[list[float]]:
    """각 청크 텍스트를 임베딩 벡터로 변환."""
    vectors = []
    for chunk in chunks:
        response = model.create_embedding(chunk["text"])
        vector = response["data"][0]["embedding"]
        vectors.append(vector)
    return vectors
```

- [ ] **Step 4: 테스트 통과 확인**

```bash
pytest tests/test_ingestor.py -v
```

Expected: 8개 PASSED

- [ ] **Step 5: 커밋**

```bash
git add ingestor.py tests/test_ingestor.py
git commit -m "feat: add embed_chunks"
```

---

### Task 6: upsert_points 및 ingest_file

**Files:**
- Modify: `ingestor.py`
- Modify: `tests/test_ingestor.py`

- [ ] **Step 1: 실패하는 테스트 추가**

```python
# tests/test_ingestor.py 에 추가
from ingestor import upsert_points, ingest_file


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
    """32개 초과 시 여러 배치로 나눠 upsert"""
    mock_client = MagicMock()
    chunks = [{"chunk_id": i, "text": f"텍스트{i}", "page": None, "position": "middle"} for i in range(50)]
    vectors = [[0.1] * 3 for _ in range(50)]
    source_meta = {"source": "big.pdf", "file_type": "pdf", "author": None, "title": None, "language": "ko"}

    count = upsert_points(mock_client, "col", chunks, vectors, source_meta, batch_size=32)

    assert count == 50
    assert mock_client.upsert.call_count == 2  # 32 + 18


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
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

```bash
pytest tests/test_ingestor.py::test_upsert_points tests/test_ingestor.py::test_upsert_points_batching tests/test_ingestor.py::test_ingest_file tests/test_ingestor.py::test_ingest_file_empty_chunks -v
```

Expected: FAILED

- [ ] **Step 3: upsert_points 구현**

```python
def upsert_points(
    client: QdrantClient,
    collection: str,
    chunks: list[dict],
    vectors: list[list[float]],
    source_meta: dict,
    batch_size: int = 32,
) -> int:
    """청크+벡터를 Qdrant에 배치 단위로 upsert."""
    points = []
    for chunk, vector in zip(chunks, vectors):
        payload = {
            "source": source_meta["source"],
            "file_type": source_meta["file_type"],
            "chunk_id": chunk["chunk_id"],
            "text": chunk["text"],
            "page": chunk.get("page"),
            "position": chunk.get("position"),
            "author": source_meta.get("author"),
            "title": source_meta.get("title"),
            "language": source_meta.get("language"),
            "collection_name": collection,
        }
        points.append(PointStruct(id=str(uuid.uuid4()), vector=vector, payload=payload))

    for i in range(0, len(points), batch_size):
        client.upsert(collection_name=collection, points=points[i : i + batch_size])

    return len(points)
```

- [ ] **Step 4: ingest_file 구현**

```python
def ingest_file(
    json_path: Path,
    collection: str,
    config: dict,
    model: Llama,
    client: QdrantClient,
) -> dict:
    """JSON 파일 1개를 읽어 임베딩 후 Qdrant에 적재."""
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    chunks = data.get("chunks", [])
    if not chunks:
        raise ValueError(f"청크가 없습니다: {json_path.name}")

    source_meta = {
        "source": data["source"],
        "file_type": data["file_type"],
        "author": data.get("author"),
        "title": data.get("title"),
        "language": data.get("language"),
    }

    dim = config["embedding"]["embedding_dim"]
    get_or_create_collection(client, collection, dim)
    delete_existing_source(client, collection, data["source"])
    vectors = embed_chunks(model, chunks)
    count = upsert_points(client, collection, chunks, vectors, source_meta)

    return {
        "source": data["source"],
        "collection": collection,
        "chunks_ingested": count,
    }
```

- [ ] **Step 5: 전체 테스트 통과 확인**

```bash
pytest tests/test_ingestor.py -v
```

Expected: 12개 PASSED

- [ ] **Step 6: 커밋**

```bash
git add ingestor.py tests/test_ingestor.py
git commit -m "feat: add upsert_points and ingest_file"
```

---

### Task 7: Streamlit UI (app_ingest.py)

**Files:**
- Create: `app_ingest.py`

단위 테스트 없음 — Streamlit UI는 수동 확인.

- [ ] **Step 1: app_ingest.py 작성**

```python
# app_ingest.py
import json
import subprocess
import yaml
from pathlib import Path

import streamlit as st

from ingestor import (
    load_config,
    get_qdrant_client,
    is_qdrant_healthy,
    get_or_create_collection,
    load_model,
    ingest_file,
)

st.set_page_config(page_title="json2qdrant 벡터 DB 적재기", layout="wide")
st.title("🗄️ json2qdrant 벡터 DB 적재기")

config = load_config()
input_dir = Path(config["paths"]["input_dir"])
input_dir.mkdir(exist_ok=True)

# Qdrant 서버 상태
healthy = is_qdrant_healthy(config)
col_status, col_start = st.columns([4, 1])
with col_status:
    if healthy:
        st.success(f"🟢 Qdrant 연결됨 ({config['qdrant']['url']})")
    else:
        st.error(f"🔴 Qdrant 연결 안 됨 ({config['qdrant']['url']})")
with col_start:
    if st.button("🚀 Qdrant 시작"):
        qdrant_exe = Path("qdrant/qdrant.exe")
        if qdrant_exe.exists():
            subprocess.Popen([str(qdrant_exe.resolve())], cwd=str(qdrant_exe.parent.resolve()))
            st.info("Qdrant 시작 중... 잠시 후 🔄 새로고침하세요.")
        else:
            st.error("qdrant/qdrant.exe 파일이 없습니다. releases 페이지에서 다운로드 후 qdrant/ 폴더에 복사하세요.")

# 설정 패널
with st.expander("⚙️ 설정", expanded=False):
    collection_name = st.text_input("컬렉션 이름", value=config["qdrant"]["default_collection"])
    model_path = st.text_input("bge-m3 GGUF 모델 경로", value=config["embedding"]["model_path"])
    if st.button("설정 저장"):
        config["qdrant"]["default_collection"] = collection_name
        config["embedding"]["model_path"] = model_path
        with open("config.yaml", "w", encoding="utf-8") as f:
            yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
        if "model" in st.session_state:
            del st.session_state["model"]  # 모델 경로 변경 시 재로드
        st.success("저장되었습니다. 모델이 재로드됩니다.")
        st.rerun()
else:
    collection_name = config["qdrant"]["default_collection"]
    model_path = config["embedding"]["model_path"]

# 모델 로드 (세션당 1회 캐싱)
if "model" not in st.session_state:
    if Path(model_path).exists():
        with st.spinner("bge-m3 모델 로딩 중... (처음 한 번만 실행됩니다)"):
            st.session_state["model"] = load_model(config)
    else:
        st.warning(f"⚠️ 모델 파일을 찾을 수 없습니다: {model_path}\n설정에서 경로를 수정하세요.")
        st.session_state["model"] = None

# 파일 목록
col_title, col_refresh = st.columns([5, 1])
with col_title:
    st.subheader("input/ 폴더 현황")
with col_refresh:
    if st.button("🔄 새로고침"):
        st.rerun()

json_files = sorted(f for f in input_dir.iterdir() if f.is_file() and f.suffix == ".json")

if not json_files:
    st.info("input/ 폴더에 JSON 파일이 없습니다. file2json의 output/ 폴더에서 파일을 복사하세요.")
else:
    file_rows = []
    for f in json_files:
        try:
            with open(f, "r", encoding="utf-8") as fp:
                data = json.load(fp)
            total_chunks = data.get("total_chunks", 0)
            source = data.get("source", f.name)
        except Exception:
            total_chunks = "읽기 오류"
            source = f.name
        file_rows.append({"file": f, "name": f.name, "source": source, "chunks": total_chunks})

    h1, h2, h3, h4 = st.columns([0.5, 3, 2.5, 1])
    h1.markdown("**선택**")
    h2.markdown("**JSON 파일명**")
    h3.markdown("**원본 문서**")
    h4.markdown("**청크 수**")
    st.divider()

    selections = {}
    for row in file_rows:
        c1, c2, c3, c4 = st.columns([0.5, 3, 2.5, 1])
        with c1:
            selections[row["name"]] = st.checkbox("", value=True, key=f"sel_{row['name']}")
        with c2:
            st.text(row["name"])
        with c3:
            st.text(row["source"])
        with c4:
            st.text(str(row["chunks"]))

    st.divider()

    col_all, col_sel = st.columns(2)
    with col_all:
        ingest_all = st.button(
            "🔄 전체 적재", use_container_width=True,
            disabled=not healthy or st.session_state.get("model") is None
        )
    with col_sel:
        ingest_selected = st.button(
            "✅ 선택 파일만 적재", use_container_width=True,
            disabled=not healthy or st.session_state.get("model") is None
        )

    files_to_ingest = []
    if ingest_all:
        files_to_ingest = [row["file"] for row in file_rows]
    elif ingest_selected:
        files_to_ingest = [row["file"] for row in file_rows if selections.get(row["name"])]

    if files_to_ingest:
        st.subheader("적재 결과 로그")
        progress_bar = st.progress(0)
        log_placeholder = st.empty()
        logs = []

        client = get_qdrant_client(config)
        model = st.session_state["model"]

        for i, json_path in enumerate(files_to_ingest):
            try:
                result = ingest_file(json_path, collection_name, config, model, client)
                logs.append(f"✅ {json_path.name} → {result['chunks_ingested']} vectors 적재 완료")
            except Exception as e:
                logs.append(f"❌ {json_path.name} → 오류: {e}")

            progress_bar.progress((i + 1) / len(files_to_ingest))
            log_placeholder.text("\n".join(logs))

        st.success(f"적재 완료! ({len(files_to_ingest)}개 처리)")
        st.rerun()
```

- [ ] **Step 2: ingestor.py에 load_model 구현 추가**

`ingestor.py`에 아래 함수를 추가:

```python
def load_model(config: dict) -> Llama:
    """GGUF 모델 파일 로드. CPU 전용 기본값."""
    return Llama(
        model_path=config["embedding"]["model_path"],
        n_gpu_layers=config["embedding"].get("n_gpu_layers", 0),
        n_ctx=config["embedding"].get("n_ctx", 512),
        embedding=True,
        verbose=False,
    )
```

- [ ] **Step 3: 전체 테스트 통과 확인**

```bash
pytest tests/test_ingestor.py -v
```

Expected: 12개 PASSED (load_model은 실제 모델 없이 테스트 불가, 모킹으로 대체)

- [ ] **Step 4: import 검증**

```bash
.venv\Scripts\python -c "import app_ingest" 2>&1
```

Expected: Streamlit ScriptRunContext 경고만 출력, ImportError 없음

- [ ] **Step 5: 수동 테스트 — Qdrant 없이**

```bash
streamlit run app_ingest.py
```

확인 사항:
1. 🔴 Qdrant 연결 안 됨 표시
2. 적재 버튼이 비활성화(disabled) 상태
3. 모델 파일 경로가 없으면 ⚠️ 경고 표시
4. `input/` 폴더 비어 있으면 안내 메시지 표시

- [ ] **Step 6: 수동 테스트 — Qdrant + 모델 있을 때**

1. `qdrant/qdrant.exe` 복사 후 `[🚀 Qdrant 시작]` 클릭 → 🟢 연결됨 확인
2. `config.yaml`의 `model_path`를 실제 bge-m3 GGUF 경로로 수정
3. `input/`에 file2json이 생성한 JSON 파일 복사
4. `🔄 새로고침` → 파일 목록 표시 확인
5. `🔄 전체 적재` → 진행률 + 로그 표시 확인
6. Qdrant UI(`http://localhost:6333/dashboard`)에서 컬렉션 및 벡터 수 확인

- [ ] **Step 7: 커밋**

```bash
git add app_ingest.py ingestor.py
git commit -m "feat: add Streamlit UI and load_model for vector ingestion"
```

---

## 완료 기준

- [ ] `pytest tests/test_ingestor.py -v` → 12개 PASSED, 0 FAILED
- [ ] `streamlit run app_ingest.py` 실행 시 ImportError 없음
- [ ] Qdrant + 실제 모델 환경에서 JSON → Qdrant 적재 동작 확인
- [ ] 같은 파일 재적재 시 기존 벡터 삭제 후 새로 적재됨
- [ ] 청크 없는 JSON 파일은 오류 로그 출력 후 건너뜀
- [ ] 모델 세션 내 최초 1회만 로드 (새로고침 시 재로드 없음)
