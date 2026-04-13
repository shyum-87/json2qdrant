# json2qdrant 설계 문서

**작성일:** 2026-04-13  
**상태:** 승인됨  
**범위:** file2json이 생성한 JSON 파일을 읽어 bge-m3 GGUF 임베딩 모델로 벡터화하고 로컬 Qdrant에 적재하는 독립 Streamlit 앱

---

## 1. 개요

폐쇄망(사내 로컬 PC) 환경에서 동작하는 벡터 DB 적재 도구. `file2json`이 생성한 JSON 파일의 각 chunk를 bge-m3 GGUF 모델로 임베딩하여 로컬 Qdrant 벡터 DB에 저장한다. Qdrant 바이너리도 이 프로젝트에 포함하여 단독으로 실행 가능하다.

---

## 2. 프로젝트 위치 및 구조

`file2json/`과 나란히 위치하는 독립 프로젝트.

```
E:/
├── file2json/              # 기존 프로젝트
└── json2qdrant/            # 이 프로젝트
    ├── app_ingest.py           # Streamlit UI 진입점
    ├── ingestor.py             # 임베딩 + Qdrant 적재 로직
    ├── config.yaml             # 설정 파일
    ├── requirements.txt        # Python 의존성
    ├── qdrant/
    │   ├── qdrant.exe              # Windows 바이너리 (수동 다운로드)
    │   └── start_qdrant.bat        # Qdrant 실행 배치 파일
    ├── input/                  # JSON 파일 드롭 위치
    └── tests/
        └── test_ingestor.py
```

---

## 3. 핵심 라이브러리

| 역할 | 라이브러리 |
|------|-----------|
| Qdrant 클라이언트 | `qdrant-client` |
| GGUF 임베딩 로드 | `llama-cpp-python` |
| Streamlit UI | `streamlit` |
| 설정 관리 | `pyyaml` |
| 고유 ID 생성 | `uuid` (표준 라이브러리) |

---

## 4. 설정 파일 (config.yaml)

```yaml
qdrant:
  url: http://localhost:6333
  default_collection: my_documents

embedding:
  model_path: C:/Users/shyum/.ollama/models/blobs/sha256-<hash>
  n_gpu_layers: 0       # CPU만 사용 (GPU 있으면 -1)
  n_ctx: 512            # 컨텍스트 윈도우
  embedding_dim: 1024   # bge-m3 출력 차원

paths:
  input_dir: ./input
```

> `model_path`는 앱 UI에서도 수정 가능하며, 수정 시 config.yaml에 저장된다.

---

## 5. 데이터 흐름

```
input/ 폴더 스캔
    → JSON 파일 목록 표시 (체크박스 선택)
    → 컬렉션 이름 확인 (없으면 Qdrant에 신규 생성, dim=1024, distance=Cosine)
    → 같은 source(파일명)의 기존 Point 삭제 (payload 필터로)
    → 각 chunk.text → llama-cpp-python으로 1024차원 벡터 생성
    → 벡터 + payload를 Qdrant에 upsert (배치 단위)
    → 완료 로그 표시
```

---

## 6. Qdrant Point 구조

JSON 파일의 청크 1개 = Qdrant Point 1개.

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "vector": [0.02, -0.13, "...1024차원"],
  "payload": {
    "source": "사내보고서.pdf",
    "file_type": "pdf",
    "chunk_id": 3,
    "text": "청크 텍스트 내용...",
    "page": 2,
    "position": "middle",
    "author": "홍길동",
    "title": "보고서 제목",
    "language": "ko",
    "collection_name": "my_documents"
  }
}
```

**ID 생성:** `uuid.uuid4()`로 매번 새 UUID 생성. 덮어쓰기는 기존 Point 삭제 후 재삽입 방식.

**배치 크기:** 청크 32개씩 묶어 Qdrant에 업로드 (메모리 효율).

---

## 7. ingestor.py 함수 구성

```python
def load_model(config: dict) -> Llama
def get_or_create_collection(client: QdrantClient, name: str, dim: int) -> None
def delete_existing_source(client: QdrantClient, collection: str, source: str) -> int
def embed_chunks(model: Llama, chunks: list[dict]) -> list[list[float]]
def upsert_points(client: QdrantClient, collection: str, chunks: list[dict],
                  vectors: list[list[float]], source_meta: dict) -> int
def ingest_file(json_path: Path, collection: str, config: dict) -> dict
```

`ingest_file`이 전체 흐름을 조율하고, 나머지는 단일 책임 함수.

---

## 8. Streamlit UI 구성

### 화면 레이아웃

```
┌─────────────────────────────────────────────────┐
│  🗄️ json2qdrant 벡터 DB 적재기                  │
├─────────────────────────────────────────────────┤
│  [Qdrant 서버 상태]                              │
│  상태: 🟢 연결됨 (http://localhost:6333)          │
│  [🚀 Qdrant 시작] 버튼                           │
│                                                 │
│  [설정]                                          │
│  컬렉션 이름: [my_documents        ]             │
│  모델 경로:   [C:/Users/.ollama/... ]            │
│  [설정 저장]                                     │
│                                                 │
│  [input/ 폴더 현황]  [🔄 새로고침]               │
│  ┌───────────────────────────────────────────┐  │
│  │ □ 파일명              청크수  상태         │  │
│  │ ■ 사내보고서.pdf       12     대기중       │  │
│  │ ■ 실적표.xlsx          8     대기중       │  │
│  └───────────────────────────────────────────┘  │
│                                                 │
│  [🔄 전체 적재]  [✅ 선택 파일만 적재]            │
│                                                 │
│  [적재 결과 로그]                                │
│  ✅ 사내보고서.pdf → 12 vectors 적재 완료        │
│  ❌ 실적표.xlsx → 오류: 모델 로드 실패           │
└─────────────────────────────────────────────────┘
```

### UI 동작 규칙

- 앱 시작 시 Qdrant 연결 상태 자동 확인 (🟢 연결됨 / 🔴 연결 안 됨)
- `[🚀 Qdrant 시작]` 클릭 시 `qdrant/qdrant.exe`를 `subprocess`로 백그라운드 실행
- `input/` 폴더 JSON 파일 목록 표시, 체크박스로 선택
- 적재 시 파일별 진행률 및 실시간 로그 출력
- 같은 source의 기존 Point는 자동 삭제 후 재적재 (덮어쓰기)
- 모델은 세션 내 최초 1회만 로드, 이후 재사용 (`st.session_state`에 캐싱)

---

## 9. Qdrant 설치 방법

1. [https://github.com/qdrant/qdrant/releases](https://github.com/qdrant/qdrant/releases) 에서 `qdrant-x86_64-pc-windows-msvc.zip` 다운로드 (외부 네트워크 환경)
2. 압축 해제 후 `qdrant.exe`를 `json2qdrant/qdrant/` 폴더에 복사
3. `start_qdrant.bat` 실행 또는 UI에서 `[🚀 Qdrant 시작]` 클릭

**start_qdrant.bat 내용:**
```bat
@echo off
cd /d "%~dp0"
qdrant.exe
```

---

## 10. 환경 및 실행 방법

- **OS:** Windows 10/11 (폐쇄망 로컬 PC)
- **Python:** 3.10 이상, `venv` 가상환경
- **실행:**
  ```bash
  cd E:/json2qdrant
  python -m venv .venv
  .venv\Scripts\activate
  pip install -r requirements.txt
  streamlit run app_ingest.py
  ```

> `llama-cpp-python`은 Windows에서 사전 빌드된 wheel이 필요할 수 있음.  
> 외부 네트워크에서 `pip download llama-cpp-python --platform win_amd64`로 wheel 파일을 미리 받아 옮길 것.

---

## 11. 오류 처리 방침

- Qdrant 연결 실패: UI에 🔴 표시, 적재 버튼 비활성화
- 모델 파일 경로 오류: 명확한 오류 메시지와 경로 재설정 안내
- 빈 JSON 파일 또는 chunks 없음: 경고 로그 후 건너뜀
- 임베딩 실패 (개별 청크): 오류 로그 후 해당 파일 전체 롤백 (삭제된 기존 Point 복구 불가 → 재적재 필요 안내)

---

## 12. 범위 외 (Out of Scope)

- Rerank (챗봇 서브시스템에서 처리)
- 임베딩 모델 교체 UI (config.yaml 직접 수정)
- Qdrant 클라우드 연동
- 멀티 컬렉션 동시 적재
- 챗봇 UI (별도 서브시스템)
