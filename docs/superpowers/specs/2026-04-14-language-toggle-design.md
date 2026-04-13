# 한국어/중국어 언어 토글 설계

**작성일:** 2026-04-14
**대상 파일:** `app_ingest.py`, `config.yaml`
**목적:** 기존 Streamlit UI에 한국어 ↔ 중국어(간체, zh-CN) 언어 전환 토글 추가

## 1. 배경

`app_ingest.py`는 단일 파일 Streamlit 앱으로, 모든 UI 문자열(제목, 버튼, 상태/에러 메시지, 테이블 헤더, 로그 포맷 등 약 25~30개)이 한국어로 하드코딩되어 있다. 중국어 사용자를 지원하기 위해 언어 토글을 도입한다.

## 2. 아키텍처 개요

`app_ingest.py`에 인라인 i18n 레이어를 추가한다. 구성요소 3개:

1. **`TRANSLATIONS` 딕셔너리** — 파일 상단에 `{"ko": {...}, "zh": {...}}` 형태로 모든 UI 문자열을 보관. 키는 의미 기반 이름 사용 (`title`, `qdrant_connected`, `ingest_all_btn` 등).
2. **`t(key, **kwargs)` 헬퍼 함수** — 현재 언어(`st.session_state["lang"]`)에 맞는 문자열을 반환. 포맷팅이 필요한 경우 `.format(**kwargs)` 적용.
3. **언어 토글 위젯** — 페이지 최상단 제목 오른쪽에 `st.radio` 가로형 (`한국어` / `中文`).

외부 라이브러리(`gettext`, `streamlit-i18n` 등)는 도입하지 않는다. 문자열 수가 적고 단일 파일 앱이라 인라인 방식이 가장 단순하다.

## 3. 설정 지속성

`config.yaml`에 새 섹션 추가:

```yaml
ui:
  language: ko  # ko | zh
```

### 동작

- 앱 시작 시 `config["ui"]["language"]`를 읽어 `st.session_state["lang"]` 초기화. 키가 없으면 `ko` 기본값.
- `load_config()` 또는 앱 초기화 시점에 `config.setdefault("ui", {"language": "ko"})` 처리로 기존 `config.yaml`과의 호환성 보장.
- 사용자가 토글을 변경하면 즉시 `config.yaml`에 저장하고 `st.rerun()`을 호출해 전체 UI를 재렌더한다.
- 저장 방식은 기존 "설정 저장" 버튼과 동일하게 `yaml.dump(..., allow_unicode=True, default_flow_style=False)` 사용.

## 4. 번역 대상 문자열

현재 `app_ingest.py`에서 번역할 문자열 (카테고리별):

### 제목 / 섹션 헤더
- `🗄️ json2qdrant 벡터 DB 적재기` (page_title, title)
- `input/ 폴더 현황`
- `적재 결과 로그`
- `⚙️ 설정`

### 상태 메시지
- `🟢 Qdrant 연결됨 ({url})`
- `🔴 Qdrant 연결 안 됨 ({url})`
- `Qdrant 시작 중... 잠시 후 🔄 새로고침하세요.`
- `qdrant/qdrant.exe 파일이 없습니다. releases 페이지에서 다운로드 후 qdrant/ 폴더에 복사하세요.`
- `⚠️ 임베딩 백엔드 초기화 실패: {error}`

### 버튼 레이블
- `🚀 Qdrant 시작`
- `🔄 새로고침`
- `🔄 전체 적재`
- `✅ 선택 파일만 적재`
- `설정 저장`

### 설정 패널
- `컬렉션 이름`
- `Ollama URL`
- `임베딩 모델명`
- `저장되었습니다. 모델이 재로드됩니다.`

### 테이블 헤더
- `**선택**`
- `**JSON 파일명**`
- `**원본 문서**`
- `**청크 수**`

### 안내 / 빈 상태
- `input/ 폴더에 JSON 파일이 없습니다. file2json의 output/ 폴더에서 파일을 복사하세요.`
- `읽기 오류` (청크 수 컬럼에 표시되는 에러 플레이스홀더)

### 진행/로그 포맷
- `임베딩 백엔드 초기화 중...` (spinner)
- `✅ {name} → {n} vectors 적재 완료`
- `❌ {name} → 오류: {error}`
- `적재 완료! ({n}개 처리)`

### 번역 제외
- 파일 경로, 모델명, 컬렉션 이름 등 `config.yaml`의 실제 값
- Qdrant URL 값
- 로그 이모지 (✅, ❌, 🟢, 🔴 등은 언어 중립적이므로 유지)

### 중국어 표기 기준
중국어는 **간체(zh-CN)** 로 작성한다. 예:
- `한국어` → `中文`
- `🗄️ json2qdrant 벡터 DB 적재기` → `🗄️ json2qdrant 向量数据库导入工具`
- `🚀 Qdrant 시작` → `🚀 启动 Qdrant`
- `컬렉션 이름` → `集合名称`
- `적재 결과 로그` → `导入结果日志`

(실제 번역문은 구현 시 전체 확정)

## 5. 데이터 흐름

```
앱 시작
  → load_config() 호출
  → config.setdefault("ui", {"language": "ko"})
  → st.session_state["lang"] ← config["ui"]["language"] (최초 1회만)
  → 최상단 radio 렌더 (현재 lang으로 기본 선택)
  → radio 값이 session_state["lang"]과 다르면:
      · config["ui"]["language"] 업데이트
      · config.yaml 저장
      · st.session_state["lang"] 업데이트
      · st.rerun()
  → 이후 모든 UI 렌더링에서 t("key") 또는 t("key", **kwargs) 사용
```

## 6. 에러 처리 / 엣지 케이스

- **누락된 번역 키:** `t(key)`는 현재 언어에 키가 없으면 한국어(`ko`)로 폴백, 그것도 없으면 키 문자열 자체를 반환한다. 이렇게 하면 개발 중 누락을 화면에서 바로 발견할 수 있다.
- **기존 config.yaml 호환:** `ui` 섹션이 없어도 앱이 정상 동작하며, 언어 변경 시 또는 설정 저장 시 자동으로 섹션이 생성된다.
- **포맷 문자열 어순 차이:** 모든 동적 값은 `{name}`, `{url}`, `{n}`, `{error}` 같은 명명된 플레이스홀더를 사용한다. 언어별로 어순이 달라도 `.format(**kwargs)` 방식이 허용한다.
- **언어 토글 즉시 반영:** `st.rerun()`으로 세션 상태 재진입 시 모든 위젯이 새 언어로 다시 렌더된다. 진행 중인 적재 작업은 영향받지 않는다(토글은 적재 루프 외부에서만 반응).
- **잘못된 언어 값:** `config.yaml`에 `ko`/`zh` 이외의 값이 들어 있으면 `ko`로 폴백한다.

## 7. 테스트 계획

### 수동 테스트
1. `streamlit run app_ingest.py` 실행.
2. 최상단에 언어 토글(`한국어` / `中文`)이 표시되는지 확인.
3. `中文`으로 전환 → 모든 UI 텍스트(제목, 버튼, 설정 패널, 테이블 헤더, 안내 메시지)가 중국어로 바뀌는지 확인.
4. 브라우저 새로고침 → 중국어가 유지되는지 확인 (config.yaml 영속성).
5. Streamlit 재시작 → 마지막 선택 언어가 유지되는지 확인.
6. 적재 버튼을 눌러 진행 로그/완료 메시지까지 선택 언어로 표시되는지 확인.
7. Qdrant 연결 끊긴 상태, `input/` 폴더 비어있는 상태 등 에러/빈 상태 메시지도 전환되는지 확인.
8. `한국어`로 돌아왔을 때 완전히 원복되는지 확인.

### 단위 테스트
`tests/`에 `test_i18n.py` 추가:
- `t("title")`이 각 언어에 대해 올바른 문자열을 반환하는지.
- `t("unknown_key")`가 키 문자열 자체를 반환하는 폴백 동작 검증.
- `TRANSLATIONS["ko"]`와 `TRANSLATIONS["zh"]`의 키 집합이 완전히 동일한지 (누락 방지).
- 포맷팅: `t("qdrant_connected", url="http://x")`가 `{url}`을 올바르게 치환하는지.

Streamlit 런타임에 의존하지 않도록 `TRANSLATIONS`와 `t()`는 순수 함수로 설계해 테스트 가능하게 둔다. `st.session_state`에 직접 접근하지 않도록, `t()`는 언어 인자를 받거나 모듈 레벨 getter를 경유한다.

## 8. 범위 외 (Non-goals)

- 2개 이상의 언어(영어, 일본어 등) 지원 — 현재는 한/중만.
- 날짜/숫자 지역화(locale formatting).
- RTL 언어 지원.
- `ingestor.py`의 로그/예외 메시지 번역 (사용자 직접 노출 없는 내부 로깅은 그대로 유지).
- `config.yaml`의 다른 섹션 재구조화.
