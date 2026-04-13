# json2qdrant

file2json으로 추출한 JSON 청크 파일을 임베딩하여 [Qdrant](https://qdrant.tech) 벡터 DB에 적재하는 Streamlit 기반 도구입니다. 한국어/중국어 UI 토글을 지원합니다.

## 주요 기능

- 📂 `input/` 폴더의 JSON 청크 파일 자동 감지 및 목록화
- 🧠 [Ollama](https://ollama.com) HTTP API를 통한 임베딩 생성 (기본: `bge-m3:latest`, 1024-dim)
- 🗄️ Qdrant 컬렉션 자동 생성 및 upsert (기존 `source` 값은 삭제 후 재적재)
- ✅ 파일별 선택 적재 / 전체 적재
- 🟢 Qdrant 연결 상태 표시 및 로컬 Qdrant 실행 버튼
- 🌐 **한국어 / 中文 실시간 언어 전환** (config.yaml에 영속)

## 요구 사항

- Python 3.10+
- [Qdrant](https://github.com/qdrant/qdrant/releases) (로컬 바이너리 또는 Docker)
- [Ollama](https://ollama.com) + 임베딩 모델 (`ollama pull bge-m3`)

## 설치

```bash
git clone https://github.com/shyum-87/json2qdrant.git
cd json2qdrant
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux
pip install -r requirements.txt
```

## Qdrant 준비

**옵션 1. 로컬 바이너리 (Windows)**
1. [Qdrant releases](https://github.com/qdrant/qdrant/releases)에서 `qdrant-x86_64-pc-windows-msvc.zip` 다운로드
2. `qdrant.exe`를 프로젝트의 `qdrant/` 폴더에 복사
3. 앱의 **🚀 Qdrant 시작** 버튼으로 실행 가능

**옵션 2. Docker**
```bash
docker run -p 6333:6333 -v qdrant_storage:/qdrant/storage qdrant/qdrant
```

## Ollama 준비

```bash
ollama serve                 # 백그라운드 실행
ollama pull bge-m3           # 임베딩 모델 다운로드 (1024-dim)
```

## 실행

```bash
streamlit run app_ingest.py
```

브라우저가 열리면:
1. 우상단에서 **한국어 / 中文** 언어 선택
2. Qdrant 연결 상태 확인 (🟢이면 정상)
3. 필요 시 **⚙️ 설정**에서 컬렉션 이름, Ollama URL, 모델명 수정
4. `input/` 폴더에 JSON 파일 배치 (file2json의 `output/`에서 복사)
5. **🔄 새로고침** → 파일 목록 갱신
6. **✅ 선택 파일만 적재** 또는 **🔄 전체 적재** 클릭

## 입력 JSON 포맷

file2json 출력과 호환되는 스키마:

```json
{
  "source": "example.pdf",
  "file_type": "pdf",
  "title": "문서 제목",
  "author": "저자",
  "language": "ko",
  "total_chunks": 42,
  "chunks": [
    {
      "chunk_id": "c1",
      "text": "청크 본문...",
      "page": 1,
      "position": 0
    }
  ]
}
```

## 설정 (`config.yaml`)

```yaml
qdrant:
  url: http://localhost:6333
  default_collection: my_documents

embedding:
  backend: ollama
  ollama_url: http://localhost:11434
  model_name: bge-m3:latest
  embedding_dim: 1024

paths:
  input_dir: ./input

ui:
  language: ko   # ko | zh (언어 토글 시 자동 갱신)
```

## 프로젝트 구조

```
json2qdrant/
├── app_ingest.py     # Streamlit UI (엔트리포인트)
├── ingestor.py       # Qdrant/Ollama 핵심 로직
├── i18n.py           # 한/중 번역 딕셔너리 + t() 헬퍼
├── config.yaml       # 런타임 설정
├── requirements.txt
├── input/            # 입력 JSON 배치 위치
├── qdrant/           # (선택) 로컬 Qdrant 바이너리
├── tests/
└── docs/superpowers/specs/
```

## 코드 설명

### `ingestor.py` — 핵심 로직 (UI 비의존)

Streamlit에 의존하지 않는 순수 함수 모음. 단위 테스트 가능.

| 함수 | 역할 |
|---|---|
| `load_config(path)` | `config.yaml`을 읽어 dict 반환 |
| `is_qdrant_healthy(config)` | Qdrant에 2초 타임아웃으로 `get_collections()` 호출하여 연결 확인 |
| `get_qdrant_client(config)` | `QdrantClient` 인스턴스 생성 |
| `load_model(config)` | Ollama HTTP 클라이언트 래퍼 초기화 |
| `get_or_create_collection(client, name, dim)` | 컬렉션이 없으면 `Cosine` 거리로 생성 |
| `delete_existing_source(client, collection, source)` | 동일 `source` 포인트를 필터 삭제 (재적재 시 중복 방지) |
| `embed_chunks(model, chunks)` | 청크별로 Ollama에 임베딩 요청, 벡터 리스트 반환 |
| `upsert_points(client, collection, chunks, vectors, source_meta)` | 페이로드(`source`, `page`, `text` 등)와 함께 UUID 포인트로 upsert |
| `ingest_file(json_path, collection, config, model, client)` | 위 단계를 한 파일에 대해 오케스트레이션 |

### `i18n.py` — 경량 i18n 레이어

외부 라이브러리 없는 인라인 딕셔너리 방식.

```python
TRANSLATIONS = {
    "ko": {"title": "🗄️ json2qdrant 벡터 DB 적재기", ...},
    "zh": {"title": "🗄️ json2qdrant 向量数据库导入工具", ...},
}

def t(key: str, lang: str, **kwargs) -> str:
    # 1. 해당 언어의 값 조회
    # 2. 없으면 ko 폴백
    # 3. 그것도 없으면 key 문자열 자체 반환 (개발 중 누락 감지)
    # 4. kwargs가 있으면 .format(**kwargs) 적용
```

- 모든 동적 값은 `{url}`, `{name}`, `{n}`, `{error}` 같은 **명명된 플레이스홀더**를 사용해 언어별 어순 차이를 허용합니다.
- 한/중 키 집합이 동일해야 하며, 테스트로 검증합니다.

### `app_ingest.py` — Streamlit UI

흐름:

1. **설정 로드** — `load_config()` → `config["ui"]` 기본값 주입 → `st.session_state["lang"]` 초기화
2. **언어 토글** — 제목 우측 `st.radio`(가로). 변경 감지 시 `config.yaml` 저장 → `st.rerun()`
3. **Qdrant 상태 바** — `is_qdrant_healthy()` 결과를 초록/빨강으로 표시. `qdrant/qdrant.exe` 존재 시 **🚀 Qdrant 시작** 버튼 동작
4. **설정 expander** — 컬렉션 이름/Ollama URL/모델명 편집 → 저장 시 `config.yaml` 갱신 및 모델 재로드
5. **파일 테이블** — `input/*.json` 스캔 → 각 파일의 `total_chunks`, `source` 파싱 → 체크박스로 선택
6. **적재** — 선택/전체 파일을 순회하며 `ingest_file()` 호출. 결과를 진행 바와 로그로 실시간 표시
7. **번역 적용** — UI 문자열은 모두 로컬 헬퍼 `tr("key", **kwargs)`를 경유 (`tr`은 `t`를 `st.session_state["lang"]`로 바인딩)

### 언어 토글 동작 상세

- **상태 저장소**: `st.session_state["lang"]` (런타임) + `config.yaml`의 `ui.language` (영속)
- **초기화**: 앱 시작 시 `config["ui"]["language"]` → session_state로 복사 (없으면 `ko` 기본값)
- **변경**: radio 위젯 반환값이 session_state와 다르면 즉시 저장 + `st.rerun()`
- **폴백**: 지원하지 않는 언어 코드가 들어오면 `ko`로 정규화
- **키 누락 방어**: 테스트(`tests/test_i18n.py`)로 한/중 키 집합 일치 검증

## 테스트

```bash
pytest tests/
```

## 라이선스

이 프로젝트의 라이선스 파일을 참조하세요.
