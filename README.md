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

## 폐쇄망/이동식 PC 설치 주의

`venv` 또는 `.venv` 폴더는 생성 당시의 절대 경로를 실행 파일에 기록합니다. 다른 PC나 다른 드라이브로 프로젝트를 복사하면 `streamlit.exe`가 예전 경로의 `python.exe`를 실행하려고 하며 다음과 같은 오류가 발생할 수 있습니다.

```text
Fatal error in launcher: Unable to create process using '"G:\...\.venv\Scripts\python.exe" ...'
```

이 경우 복사해 온 `venv`/`.venv`는 재사용하지 말고 새 PC의 프로젝트 경로에서 다시 만드세요.

```powershell
# 프로젝트 루트에서 실행
Deactivate 2>$null
Remove-Item -Recurse -Force .\venv, .\.venv -ErrorAction SilentlyContinue
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m streamlit run .\app_ingest.py
```

폐쇄망이라 인터넷 설치가 불가능하면, 외부망 PC에서 동일한 Python 버전/아키텍처로 wheelhouse를 준비한 뒤 복사해서 설치하세요.

```powershell
# 외부망 PC
py -3.10 -m pip download -r requirements.txt -d wheelhouse

# 폐쇄망 PC
python -m pip install --no-index --find-links .\wheelhouse -r requirements.txt
```

`streamlit run ...` 대신 `python -m streamlit run ...`을 사용하면 현재 활성화된 가상환경의 Python을 명확히 사용하므로 launcher 경로 문제를 피하는 데 도움이 됩니다.

첫 실행 시 터미널에 `Welcome to Streamlit!`와 `Email:` 안내가 뜨고 브라우저가 백지 화면처럼 보이면, Streamlit의 온보딩/사용 통계 안내가 먼저 표시된 상황일 수 있습니다. 이 저장소는 `.streamlit/config.toml`에서 사용 통계 수집을 끄고 `127.0.0.1:8501` 로컬 실행을 기본값으로 지정하므로, 최신 파일을 받은 뒤 아래 명령으로 다시 실행하세요.

```powershell
python -m streamlit run .\app_ingest.py
```

이미 실행 중인 Streamlit 프로세스가 있으면 `Ctrl + C`로 종료한 뒤 재실행하세요. 접속은 `Network URL`이 아니라 같은 PC의 `http://127.0.0.1:8501` 또는 `http://localhost:8501`을 우선 사용하세요.

그래도 브라우저가 백지면 Streamlit 서버 응답과 브라우저/WebSocket 연결 문제를 분리해서 확인하세요.

```powershell
# Streamlit 서버가 살아있는지 확인합니다. 정상이라면 ok가 반환됩니다.
Invoke-RestMethod http://127.0.0.1:8501/_stcore/health

# 사내 프록시가 localhost 통신까지 가로채는 환경이면 현재 PowerShell 세션에서 우회합니다.
$env:NO_PROXY = "localhost,127.0.0.1"
$env:no_proxy = "localhost,127.0.0.1"
python -m streamlit run .\app_ingest.py --server.address 127.0.0.1 --browser.serverAddress 127.0.0.1 --server.headless true --logger.level debug
```

`/_stcore/health`가 `ok`인데 화면만 백지라면 앱 Python 코드보다는 브라우저 캐시, 보안 프로그램, 프록시, WebSocket 차단 가능성이 큽니다. Edge/Chrome의 InPrivate 창에서 `http://127.0.0.1:8501`로 다시 열고, 개발자 도구 콘솔에 WebSocket 또는 JavaScript 오류가 있는지 확인하세요. 터미널에 Python traceback이 추가로 찍히면 그 전체 로그를 확인해야 합니다.

Edge 개발자 도구에 `edge Translation started`, `Translation timed out`, `edge.microsoft.com/translate/auth`, `Uncaught SyntaxError: Unexpected token '{'`가 함께 보이면 Edge의 자동 번역 기능이 Streamlit 프론트엔드 JavaScript에 개입한 상황일 수 있습니다. 이 경우 앱 서버는 정상이어도 화면이 백지로 보일 수 있으므로 아래 순서로 브라우저 번역을 끄고 다시 접속하세요.

1. 주소창의 번역 아이콘에서 **이 사이트 번역 안 함** 또는 **원문 보기**를 선택합니다.
2. Edge 설정(`edge://settings/languages`)에서 **내가 읽는 언어가 아닌 페이지 번역 제안**을 끕니다.
3. `http://127.0.0.1:8501`를 새 InPrivate 창에서 열거나, Chrome/다른 브라우저로 열어 비교합니다.
4. 그래도 동일하면 개발자 도구 콘솔의 첫 번째 JavaScript 오류와 Network 탭의 실패 요청을 확인합니다.

번역 기능을 꺼도 `Uncaught SyntaxError: Unexpected token '{'`만 계속 보이면, 브라우저가 받은 Streamlit 프론트엔드 번들 또는 정적 자산 응답을 확인해야 합니다. 중국/폐쇄망 PC에 이미 `streamlit==1.56.0` wheel만 준비된 경우를 지원하기 위해 이 프로젝트는 `requirements.txt`에서 Streamlit을 `1.56.0`으로 고정합니다. `python -m streamlit version`도 `1.56.0`이어야 합니다.

먼저 현재 PowerShell이 실제로 어떤 Python/Streamlit을 쓰는지 진단하세요.

```powershell
# PowerShell의 where는 별칭일 수 있으므로 where.exe 또는 Get-Command를 사용합니다.
where.exe python
Get-Command python

# python이 어떤 실행 파일인지 확인합니다. 가상환경이면 보통 .\sessvenv\Scripts\python.exe 여야 합니다.
python -c "import sys; print(sys.executable); print(sys.version)"

# pip show가 오래된 pip/Python 조합에서 깨질 수 있으므로 importlib.metadata로 확인합니다.
python -c "import importlib.metadata as m; print(m.version('streamlit'))"
python .\diagnose_streamlit_env.py
```

`diagnose_streamlit_env.py`가 `status=version_mismatch`를 출력하면 현재 활성화된 가상환경이 `requirements.txt`와 다릅니다. 또한 `python -c "import sys; print(sys.executable)"` 결과가 `D:\Miniconda3\python.exe`처럼 전역/conda Python을 가리키면, 프롬프트에 `(sessvenv)`가 보여도 실제 `python` 명령은 프로젝트 가상환경을 쓰지 않는 상태입니다. 이때는 아래처럼 가상환경의 Python을 명시해서 실행해 보세요.

```powershell
.\sessvenv\Scripts\python.exe -c "import sys; print(sys.executable); print(sys.version)"
.\sessvenv\Scripts\python.exe .\diagnose_streamlit_env.py
.\sessvenv\Scripts\python.exe -m streamlit run .\smoke_streamlit.py --server.address 127.0.0.1 --browser.serverAddress 127.0.0.1 --server.headless true
```

폐쇄망 PC에 있는 wheelhouse 기준으로 다시 설치하려면 다음 명령을 사용합니다.

```powershell
python -m pip install --no-index --find-links .\wheelhouse --force-reinstall -r requirements.txt
python .\diagnose_streamlit_env.py
```

버전이 맞는데도 백지면 먼저 json2qdrant 앱을 배제하고 Streamlit 자체 렌더링만 확인합니다. 아래 smoke-test 앱은 Qdrant/Ollama/config/input 파일을 전혀 읽지 않습니다.

```powershell
python -m streamlit run .\smoke_streamlit.py --server.address 127.0.0.1 --browser.serverAddress 127.0.0.1 --server.headless true
```

- `smoke_streamlit.py`도 백지이면 json2qdrant 코드 문제가 아니라 Streamlit 프론트엔드, 브라우저, 캐시, 보안 프로그램, WebSocket/정적 JS 차단 문제입니다.
- `smoke_streamlit.py`는 보이는데 `app_ingest.py`만 백지이면 터미널의 Python traceback 또는 앱 설정/입력 파일 문제를 확인해야 합니다.

그 다음 Streamlit을 켜둔 상태에서 프론트엔드 응답을 점검합니다.

```powershell
python .\diagnose_streamlit_env.py --probe-url http://127.0.0.1:8501
```

`/_stcore/health`가 `ok`이고 정적 JS의 `content_type`이 JavaScript 계열이면 서버와 자산 제공은 정상입니다. 이 경우 Edge의 캐시/사이트 데이터, 호환성 모드(IE mode), 보안 프로그램의 스크립트 검사, 확장 프로그램 문제가 남습니다. Edge에서 `Ctrl+F5` 강력 새로고침, 사이트 데이터 삭제, InPrivate 창, IE mode 비활성화, Chrome/다른 브라우저 비교를 순서대로 확인하세요.

정적 JS의 `content_type`이 JSON/HTML이거나 `probe_static_js_sample`이 `{`로 시작하면 Streamlit JavaScript 파일 요청이 보안 장비/프록시/브라우저 기능에 의해 다른 응답으로 바뀐 것입니다. 이 경우 앱 코드가 아니라 로컬 브라우저/보안 환경에서 `http://127.0.0.1:8501/static/...js` 요청을 예외 처리해야 합니다.

`python -m pip show streamlit`이 `AttributeError: module 'pkgutil' has no attribute 'ImpImporter'`로 실패하면 앱 문제가 아니라 오래된 pip가 Python 3.12+와 맞지 않는 상황입니다. 버전 확인은 위의 `importlib.metadata` 명령이나 `diagnose_streamlit_env.py`를 사용하고, pip 자체는 wheelhouse에 있는 최신 pip wheel 또는 `python -m ensurepip --upgrade`로 복구해야 합니다.

Streamlit debug 로그의 `No ASGI app assignments found`, `RuntimeState.NO_SESSIONS_CONNECTED`는 보통 치명적 오류가 아닙니다. `Server started on port 8501`와 `URL: http://127.0.0.1:8501`가 표시되면 서버는 기동된 상태이며, 브라우저가 접속하면 세션 상태가 바뀝니다.

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
4. `input/` 폴더에 JSON/JSONL 파일 배치 (file2json의 `output/`에서 복사)
5. **🔄 새로고침** → 파일 목록 갱신
6. **✅ 선택 파일만 적재** 또는 **🔄 전체 적재** 클릭

## 입력 JSON/JSONL 포맷

file2json 출력과 호환되는 스키마입니다. 청크 본문 필드는 `content`를 기본으로 사용하며, 구버전 `text`도 읽을 수 있습니다:

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
      "content": "청크 본문...",
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
├── input/            # 입력 JSON/JSONL 배치 위치
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
| `upsert_points(client, collection, chunks, vectors, source_meta)` | 페이로드(`source`, `page`, `content` 등)와 함께 UUID 포인트로 upsert |
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
5. **파일 테이블** — `input/*.json`, `input/*.jsonl` 스캔 → 각 파일의 `total_chunks`, `source` 파싱 → 체크박스로 선택
6. **적재** — 선택/전체 파일을 순회하며 `ingest_file()` 호출. 결과를 진행 바와 로그로 실시간 표시
7. **번역 적용** — UI 문자열은 모두 로컬 헬퍼 `tr("key", **kwargs)`를 경유 (`tr`은 `t`를 `st.session_state["lang"]`로 바인딩)

### 언어 토글 동작 상세

- **상태 저장소**: `st.session_state["lang"]` (런타임) + `config.yaml`의 `ui.language` (영속)
- **초기화**: 앱 시작 시 `config["ui"]["language"]` → session_state로 복사 (없으면 `ko` 기본값)
- **변경**: radio 위젯 반환값이 session_state와 다르면 즉시 저장 + `st.rerun()`
- **폴백**: 지원하지 않는 언어 코드가 들어오면 `ko`로 정규화
- **키 누락 방어**: 테스트(`tests/test_i18n.py`)로 한/중 키 집합 일치 검증

## 폐쇄망 설치 및 USB 이전

Git 저장소 파일만 USB로 옮기면 Python 패키지는 설치할 수 있어도 앱이 완전히 동작하지 않을 수 있습니다.
폐쇄망에서 실행하려면 프로젝트 소스, Python wheel 패키지, 그리고 Python 패키지가 아닌 로컬 실행 의존성을 함께 준비해야 합니다.

### 준비해야 할 항목

1. **프로젝트 소스**
   - 이 저장소 전체를 USB로 복사합니다.
   - `input/`, `config.yaml`, `qdrant/` 폴더도 함께 옮깁니다.

2. **Python wheelhouse**
   - `requirements.txt`에는 상위 의존성만 있습니다.
   - 실제 설치에는 `streamlit`, `qdrant-client`, `pyyaml`, `pytest` 외에도 `numpy`, `pandas`, `pyarrow`, `grpcio`, `pydantic`, `tornado` 같은 전이 의존성이 필요합니다.
   - 온라인 PC에서 폐쇄망 PC와 같은 OS, CPU 아키텍처, Python minor 버전에 맞춰 wheel을 내려받아야 합니다.

3. **Qdrant 실행 파일**
   - 이 프로젝트는 `qdrant/qdrant.exe`를 사용해 로컬 Qdrant를 실행합니다.
   - `qdrant/` 폴더 안의 `qdrant.exe`, `start_qdrant.bat`, 필요 시 `storage/` 데이터를 함께 옮깁니다.

4. **Ollama 및 임베딩 모델**
   - `config.yaml` 기본 설정은 로컬 Ollama API를 사용합니다.

   ```yaml
   embedding:
     backend: ollama
     model_name: bge-m3:latest
     ollama_url: http://localhost:11434
   ```

   - 폐쇄망 PC에도 Ollama 실행 환경과 `bge-m3:latest` 모델이 있어야 합니다.
   - `ollama pull bge-m3`는 인터넷이 필요하므로 온라인 PC에서 모델을 먼저 받은 뒤 Ollama 모델 저장소를 함께 이전합니다.
   - Windows 기본 모델 저장 위치는 보통 `%USERPROFILE%\.ollama\models`입니다.

### 온라인 PC에서 wheelhouse 만들기

현재 가상환경 기준으로 고정된 패키지 목록을 만들고 wheel 파일을 내려받습니다.

```powershell
.\.venv\Scripts\python.exe -m pip freeze > requirements-lock.txt
.\.venv\Scripts\python.exe -m pip download -r requirements-lock.txt -d wheelhouse --only-binary=:all:
```

USB에 다음 항목을 복사합니다.

```text
json2qdrant/
requirements-lock.txt
wheelhouse/
Ollama 설치 파일 또는 실행 환경
Ollama 모델 저장소(%USERPROFILE%\.ollama\models)
```

### Python 버전별 wheelhouse 만들기

폐쇄망 PC의 Python 버전이 여러 가지일 수 있다면 wheelhouse를 Python 버전별로 따로 준비합니다.
같은 Windows x64 환경이라도 Python 3.14용 wheel과 Python 3.11용 wheel은 일부 패키지에서 호환되지 않을 수 있습니다.

권장 폴더 구조:

```text
offline-packages/
  py314/
    requirements-lock-py314.txt
    wheelhouse/
  py311/
    requirements-lock-py311.txt
    wheelhouse/
  py310/
    requirements-lock-py310.txt
    wheelhouse/
```

Windows Python Launcher(`py`)가 설치되어 있으면 버전별로 다음처럼 생성할 수 있습니다.

```powershell
# Python 3.14
py -3.14 -m venv .venv314
.\.venv314\Scripts\python.exe -m pip install -U pip
.\.venv314\Scripts\python.exe -m pip install -r requirements.txt
.\.venv314\Scripts\python.exe -m pip freeze > offline-packages\py314\requirements-lock-py314.txt
.\.venv314\Scripts\python.exe -m pip download -r offline-packages\py314\requirements-lock-py314.txt -d offline-packages\py314\wheelhouse --only-binary=:all:

# Python 3.11
py -3.11 -m venv .venv311
.\.venv311\Scripts\python.exe -m pip install -U pip
.\.venv311\Scripts\python.exe -m pip install -r requirements.txt
.\.venv311\Scripts\python.exe -m pip freeze > offline-packages\py311\requirements-lock-py311.txt
.\.venv311\Scripts\python.exe -m pip download -r offline-packages\py311\requirements-lock-py311.txt -d offline-packages\py311\wheelhouse --only-binary=:all:

# Python 3.10
py -3.10 -m venv .venv310
.\.venv310\Scripts\python.exe -m pip install -U pip
.\.venv310\Scripts\python.exe -m pip install -r requirements.txt
.\.venv310\Scripts\python.exe -m pip freeze > offline-packages\py310\requirements-lock-py310.txt
.\.venv310\Scripts\python.exe -m pip download -r offline-packages\py310\requirements-lock-py310.txt -d offline-packages\py310\wheelhouse --only-binary=:all:
```

폐쇄망 PC에서는 설치된 Python 버전에 맞는 lock 파일과 wheelhouse를 선택합니다.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --no-index --find-links offline-packages\py311\wheelhouse -r offline-packages\py311\requirements-lock-py311.txt
```

주의사항:

- 이 프로젝트는 Python 3.10 이상을 권장합니다.
- Python 3.9는 권장하지 않습니다. 최신 `streamlit`, `pandas`, `pyarrow`, `qdrant-client` 계열 패키지가 Python 3.9 지원을 중단했을 수 있어 별도 버전 고정이 필요할 수 있습니다.
- 같은 Python 버전이라도 OS와 CPU 아키텍처가 다르면 wheel이 다릅니다. Windows x64 폐쇄망이면 온라인 PC도 Windows x64에서 만드는 방식이 가장 안전합니다.
- `requirements-lock` 파일은 Python 버전별로 따로 유지합니다. 하나의 lock 파일을 여러 Python 버전에 공용으로 쓰면 설치 실패가 날 수 있습니다.

### Streamlit 백지 화면 대응 및 버전별 wheel 평가

폐쇄망 PC에서 Streamlit 서버는 정상 실행되지만 브라우저 화면이 에러 없이 백지로 나오는 경우가 있습니다.
이 경우 Python 서버 문제가 아니라 브라우저에서 로드되는 Streamlit 프론트엔드 JavaScript 번들, WebSocket, 보안 프로그램, 프록시, 브라우저 호환성 문제가 원인일 수 있습니다.

먼저 다음 항목을 확인합니다.

- 브라우저 개발자 도구 Console에 JavaScript 에러가 있는지 확인합니다.
- Network 탭에서 `static/js/...` 파일이 정상적으로 `200` 응답을 받는지 확인합니다.
- WebSocket 연결이 실패하는지 확인합니다.
- `localhost:8501` 대신 `http://127.0.0.1:8501`로 접속해 봅니다.
- 사내 보안 프로그램이나 프록시가 로컬 WebSocket 또는 JavaScript 파일 로드를 차단하는지 확인합니다.
- 브라우저가 너무 오래된 Chromium/Edge/Chrome 기반이 아닌지 확인합니다.

실행 옵션도 함께 테스트합니다.

```powershell
.\.venv\Scripts\python.exe -m streamlit run app_ingest.py `
  --server.headless true `
  --browser.gatherUsageStats false `
  --server.enableCORS false `
  --server.enableXsrfProtection false
```

Streamlit 버전 문제 가능성을 확인하려면 버전별 wheelhouse를 따로 만들어 폐쇄망에서 교체 테스트합니다.
현재 코드 기준 권장 테스트 순서는 다음과 같습니다.

```text
1.56.0  현재 개발 환경에서 확인한 버전
1.50.0
1.40.2
1.32.2  requirements.txt의 최소 요구 버전에 가까운 안정 후보
1.28.2
1.25.0  더 낮은 버전 테스트용, 코드 호환성 패치가 필요할 수 있음
```

현재 앱은 `st.rerun`, `st.divider`, `st.session_state`, `st.columns`, `st.expander`, `st.button(use_container_width=...)`를 사용합니다.
Streamlit 1.28 이하까지 낮출 경우 `st.rerun()` 대신 `st.experimental_rerun()` fallback이 필요할 수 있습니다.
따라서 우선은 **Python 3.11 + Streamlit 1.32.2 / 1.40.2 / 1.50.0** 조합을 먼저 평가하는 것을 권장합니다.

온라인 PC에서 Python 3.11 기준으로 Streamlit 버전별 wheelhouse를 만드는 예:

```powershell
$versions = @("1.56.0", "1.50.0", "1.40.2", "1.32.2", "1.28.2", "1.25.0")

foreach ($st in $versions) {
    $envName = ".venv-st-$st"
    $outDir = "offline-packages\py311\streamlit-$st"

    py -3.11 -m venv $envName
    & "$envName\Scripts\python.exe" -m pip install -U pip

    & "$envName\Scripts\python.exe" -m pip install `
        "streamlit==$st" `
        "qdrant-client>=1.9.0" `
        "pyyaml>=6.0.1" `
        "pytest>=8.0.0"

    New-Item -ItemType Directory -Force -Path $outDir | Out-Null

    & "$envName\Scripts\python.exe" -m pip freeze > "$outDir\requirements-lock.txt"

    & "$envName\Scripts\python.exe" -m pip download `
        -r "$outDir\requirements-lock.txt" `
        -d "$outDir\wheelhouse" `
        --only-binary=:all:
}
```

폐쇄망 PC에서는 테스트할 Streamlit 버전의 wheelhouse를 선택해 설치합니다.

```powershell
python -m venv .venv

.\.venv\Scripts\python.exe -m pip install `
  --no-index `
  --find-links offline-packages\py311\streamlit-1.32.2\wheelhouse `
  -r offline-packages\py311\streamlit-1.32.2\requirements-lock.txt
```

버전을 바꿔 다시 테스트할 때는 기존 `.venv`를 새로 만들거나, 테스트 전용 폴더를 버전별로 나누는 방식을 권장합니다.

#### Edge 브라우저에서 `Unexpected token '{'`와 함께 백지 화면이 나오는 경우

Streamlit 서버가 정상 실행되고 터미널에 에러가 없는데 Edge 브라우저 화면만 백지이고 Console에 `Unexpected token '{'`가 표시된다면, Python 코드보다 브라우저의 JavaScript 해석 문제일 가능성이 높습니다.
특히 폐쇄망/기관망 PC에서는 Edge 정책, IE 모드, 구형 브라우저, 보안 프로그램이 원인이 될 수 있습니다.

가능성이 높은 원인:

1. **Edge가 IE 모드 또는 구형 렌더링 엔진으로 실행 중**
   - Edge 주소창에 IE 모드 아이콘이 있는지 확인합니다.
   - `edge://settings/defaultBrowser`에서 IE 모드 설정을 확인합니다.
   - 사내 Edge Enterprise Site List에 `localhost`, `127.0.0.1`, PC IP, Streamlit 접속 주소가 IE 모드 대상으로 등록되어 있는지 확인합니다.
   - IE 모드는 최신 JavaScript 문법을 제대로 해석하지 못할 수 있습니다.

2. **구형 Edge/Chromium이 Streamlit 프론트엔드 번들의 최신 JavaScript 문법을 지원하지 않음**
   - Edge 주소창에서 `edge://version`을 열어 실제 버전을 확인합니다.
   - 최신 Edge/Chrome 또는 Chrome Portable로 접속 테스트합니다.
   - 업데이트가 불가능하면 Streamlit 버전을 낮춰 테스트합니다.
   - 우선 테스트 조합은 `Python 3.11 + Streamlit 1.32.2`, `1.40.2`, `1.50.0`입니다.

3. **정적 JavaScript 파일이 정상 JS가 아닌 내용으로 내려옴**
   - 보안 솔루션, 프록시, 백신, DLP가 JS 파일을 차단하거나 응답 내용을 바꿀 수 있습니다.
   - F12 개발자 도구 → Network 탭 → `static/js/...js` 파일을 확인합니다.
   - Status가 `200`인지, Response가 실제 JavaScript인지, Content-Type이 JavaScript 계열인지 확인합니다.
   - 해당 JS URL을 브라우저 주소창에 직접 열었을 때 차단 페이지나 다른 내용이 보이면 보안/프록시 문제입니다.

4. **WebSocket 연결 실패**
   - F12 개발자 도구 → Network 탭 → WS 필터에서 WebSocket 요청이 실패하는지 확인합니다.
   - `localhost:8501` 대신 `http://127.0.0.1:8501`로 접속합니다.
   - 필요 시 `--server.enableWebsocketCompression false` 옵션을 추가합니다.

5. **브라우저 캐시 꼬임**
   - Streamlit 버전을 여러 번 바꿔 테스트하면 캐시된 JS chunk가 남아 화면이 깨질 수 있습니다.
   - Ctrl+F5로 강력 새로고침합니다.
   - 개발자 도구 Network 탭에서 Disable cache를 체크합니다.
   - InPrivate 모드로 접속합니다.
   - 포트를 바꿔 실행합니다. 예: `--server.port 8502`

진단 순서:

```powershell
# Streamlit 자체 예제도 백지인지 확인
.\.venv\Scripts\python.exe -m streamlit hello
```

- `streamlit hello`도 백지이면 앱 코드 문제가 아니라 Streamlit/브라우저/보안정책 문제일 가능성이 큽니다.
- `streamlit hello`는 정상이고 `app_ingest.py`만 백지이면 앱 코드, 설정, 특정 의존성 문제를 봅니다.

접속 주소도 바꿔 테스트합니다.

```text
http://localhost:8501
http://127.0.0.1:8501
http://PC의IP주소:8501
```

백지 화면이 계속되면 다음 실행 옵션으로 테스트합니다.

```powershell
.\.venv\Scripts\python.exe -m streamlit run app_ingest.py `
  --server.headless true `
  --browser.gatherUsageStats false `
  --server.enableCORS false `
  --server.enableXsrfProtection false `
  --server.enableWebsocketCompression false
```

조치 우선순위:

1. Edge IE 모드 여부 확인 및 해제
2. 최신 Edge/Chrome 또는 Chrome Portable로 접속 테스트
3. `127.0.0.1` 주소로 접속
4. 개발자 도구에서 `static/js/...` 응답과 WebSocket 실패 여부 확인
5. Streamlit `1.32.2`, `1.40.2`, `1.50.0` 순서로 wheelhouse 교체 테스트
6. 그래도 실패하면 보안 프로그램/프록시/DLP에서 `localhost`, `127.0.0.1`, `8501` 포트, Streamlit 정적 JS 파일 차단 여부 확인

### 폐쇄망 PC에서 설치

폐쇄망 PC에서 프로젝트 폴더로 이동한 뒤 가상환경을 만들고, 인터넷 없이 wheelhouse에서만 설치합니다.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --no-index --find-links wheelhouse -r requirements-lock.txt
```

설치 확인:

```powershell
.\.venv\Scripts\python.exe -m pytest tests --basetemp .\.tmp_pytest\basetemp
```

실행:

```powershell
.\.venv\Scripts\python.exe -m streamlit run app_ingest.py
```

### 동작 조건 체크리스트

- 폐쇄망 PC의 Python 버전과 wheel을 만든 Python minor 버전이 일치해야 합니다. 예: Python 3.14용 wheel은 Python 3.11 환경에서 일부 설치가 실패할 수 있습니다.
- `qdrant/qdrant.exe`가 존재하고 `http://localhost:6333`에서 Qdrant가 실행되어야 합니다.
- Ollama가 실행 중이고 `http://localhost:11434/api/embeddings`에 응답해야 합니다.
- Ollama에 `bge-m3:latest` 모델이 설치되어 있어야 합니다.
- `config.yaml`의 `embedding.embedding_dim` 값은 사용하는 임베딩 모델의 실제 차원과 일치해야 합니다. 현재 기본값은 `1024`입니다.
- 외부 인터넷 없이 동작하려면 Qdrant와 Ollama가 모두 로컬에서 실행되어야 합니다.

## 테스트

```bash
pytest tests/
```

## 라이선스

이 프로젝트의 라이선스 파일을 참조하세요.
