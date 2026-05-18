# json2qdrant — 새 입력 포맷 지원 설계

**작성일**: 2026-04-14
**상태**: 승인 대기 → 구현 준비

## 배경

초기 설계 당시 `file2json` 단계에서 청크 분할까지 수행하고, ingestor는 이미 쪼개진 `chunks` 배열을 그대로 Qdrant에 적재했다. 실제 운영에서는 다음과 같이 바꾸고자 한다:

- `file2json`은 **청킹 없이** 원본을 플랫한 JSON 메타데이터 + `content` 본문으로만 변환한다.
- 청킹/오버랩/임베딩/적재는 전적으로 `ingestor`의 책임이다.
- 회사 환경에서 이 포맷을 적재하려 할 때 Streamlit의 `'label' got an empty value` 경고가 발생하며 RAG 생성이 중단되는 문제도 같이 수정한다.

## 새 입력 포맷

단일 문서 예시:

```json
{
  "doc_id": "2015_W40_14ab024f",
  "title": "40주차 주간보고",
  "content": "내용~~~",
  "created_time": "2025-08-24",
  "source_file": "file경로path",
  "filename": "~~~",
  "year": 2015,
  "week": 40,
  "file_size": 21231,
  "processed_at": "2025-08-24 00:00:00",
  "document_type": "weekly_report",
  "parts_total": 1,
  "part_index": 1
}
```

`year`/`week`은 원본에서 파싱 불가 시 `null`. 파일은 `input/` 디렉터리에 놓이며 `.json` 또는 `.jsonl` 확장자를 가진다. 확장자와 무관하게 내용 기반 자동 감지:

1. 여러 줄 + 각 줄이 JSON 객체 → JSONL
2. 단일 JSON 배열 → 여러 문서
3. 단일 JSON 객체 → 문서 하나

## 목표

1. 새 포맷의 JSON/JSONL 파일을 읽어 `content`를 청크/오버랩으로 분할하고 Qdrant에 임베딩 적재한다.
2. 청크 크기와 오버랩은 `config.yaml`과 UI에서 설정 가능해야 한다(기본값 `chunk_size=200`, `overlap=50`).
3. `doc_id`를 식별자로 사용해 재적재 시 기존 포인트를 삭제 후 재삽입한다.
4. Streamlit 빈 label 경고를 제거한다.
5. 한/영/중 i18n 키를 추가하고 기존 UI 흐름을 유지한다.

## 비목표

- `file2json` 스크립트 자체 수정
- 구 포맷(`chunks` 배열이 포함된 JSON) 하위 호환 — 제거
- 토큰 기반 청킹, 문단 경계 기반 분할
- 임베딩 백엔드 변경

## 아키텍처

```
input/*.json|*.jsonl
      │
      ▼
[load_documents]  자동감지(단일 객체 / 배열 / jsonl) → list[dict]
      │
      ▼
[chunk_text]       문자 기반 chunk_size/overlap 분할
      │
      ▼
[OllamaEmbedder]   현행 유지
      │
      ▼
[Qdrant]           doc_id 기준 삭제 후 재삽입, payload에 메타 복사
```

## 모듈 변경

### `ingestor.py`

새 함수:

- `load_documents(path: Path) -> list[dict]` — 자동 감지 로더
- `chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]` — 문자 기반 슬라이딩 윈도우
- `delete_existing_doc(client, collection, doc_id)` — `doc_id` 필터로 기존 포인트 삭제
- `build_points(doc: dict, chunks: list[str], vectors: list[list[float]], collection: str) -> list[PointStruct]`

재작성:

- `ingest_file(json_path, collection, config, model, client)`
  - `load_documents`로 문서 리스트 획득
  - 문서마다: `doc_id` 기준 삭제 → `chunk_text(content)` → 빈 청크면 스킵+로그 → `embed_chunks(list[str])` → `upsert_points`
  - `doc_id` 누락 시: `source_file + filename` 조합을 fallback 삭제 키로 사용하고 경고 로그
  - 반환값: `{file, docs_processed, chunks_ingested, errors: list[str]}`

제거:

- `delete_existing_source`
- 구 payload(`source`, `file_type`, 구 `chunk_id`, `page`, `position`, `author`, `language`)

변경:

- `embed_chunks(model, texts: list[str]) -> list[list[float]]` — `dict` 리스트 대신 문자열 리스트를 받도록 단순화

### `chunk_text` 로직

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

### Qdrant payload

청크 하나당:

```python
{
  "doc_id": "...",
  "title": "...",
  "created_time": "...",
  "source_file": "...",
  "filename": "...",
  "year": ...,
  "week": ...,
  "file_size": ...,
  "processed_at": "...",
  "document_type": "...",
  "parts_total": ...,
  "part_index": ...,
  "chunk_index": 0,
  "chunk_total": 7,
  "text": "청크 본문",
  "collection_name": "my_documents",
}
```

Point ID는 계속 `uuid4()`. 재적재는 `doc_id` 필터 삭제로 처리하므로 안정 ID 불필요.

### `config.yaml`

```yaml
chunking:
  chunk_size: 200
  overlap: 50
```

### `app_ingest.py`

설정 패널(`settings_header` expander)에 추가:

- `st.number_input(chunk_size, min_value=50, max_value=8000)`
- `st.number_input(overlap, min_value=0, max_value=chunk_size-1)`
- 저장 버튼이 `config["chunking"]`을 갱신

파일 목록 컬럼 재구성(header + row):

| 선택 | 파일명 | doc_id / title | 문서 타입 | 예상 청크 수 |
|------|--------|----------------|-----------|--------------|

- jsonl/배열이면 `doc_id` 칸에 `N docs` 표기
- 예상 청크 수는 `sum(ceil(max(len(content) - overlap, 0) / step) for doc in docs)`
- 파싱 실패 시 행에 에러 텍스트

label 경고 수정:

- `app_ingest.py:150` `st.checkbox("", ...)` → `st.checkbox("select", ..., label_visibility="collapsed")` (또는 i18n 키)
- 파일 전체에서 빈 문자열 label 사용 위젯 점검

i18n 신규 키(ko/en/zh):

- `col_doc_id`, `col_doc_type`, `col_est_chunks`
- `chunk_size_label`, `overlap_label`
- `log_doc_success`(`{file}: {docs} docs, {chunks} chunks`)
- `checkbox_select_label`

### 테스트 (`tests/`)

- `test_load_documents`
  - 단일 객체, 배열, jsonl 세 케이스
  - 지원하지 않는 구조에 `ValueError`
- `test_chunk_text`
  - 빈 문자열 → `[]`
  - `len(text) < chunk_size` → 한 덩어리
  - 긴 문자열에서 오버랩 경계와 마지막 조각 검증
  - 잘못된 파라미터에 `ValueError`
- `test_build_points_payload`
  - 메타 전체 전파, `chunk_index`/`chunk_total` 정확성
  - `doc_id` 누락 시 fallback 동작

## 오류 처리

- 빈 `content`: 해당 문서 스킵 + `errors`에 기록
- `doc_id` 누락: 경고 로그, fallback 키로 삭제
- JSONL 중 일부 줄 파싱 실패: 해당 줄만 스킵 + 기록, 파일 전체는 계속 진행
- Qdrant 오류: 파일 단위로 에러 집계해 UI 로그에 표시, 다른 파일은 계속 처리

## 마이그레이션 영향

- 구 포맷을 사용하는 기존 테스트/픽스처는 새 포맷으로 교체
- `tests/` 아래 샘플 JSON은 새 포맷 기준으로 재작성
