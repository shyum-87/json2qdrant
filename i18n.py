TRANSLATIONS: dict[str, dict[str, str]] = {
    "ko": {
        "lang_label": "언어",
        "lang_ko": "한국어",
        "lang_zh": "中文",
        "page_title": "json2qdrant 벡터 DB 적재기",
        "title": "🗄️ json2qdrant 벡터 DB 적재기",
        "qdrant_connected": "🟢 Qdrant 연결됨 ({url})",
        "qdrant_disconnected": "🔴 Qdrant 연결 안 됨 ({url})",
        "qdrant_start_btn": "🚀 Qdrant 시작",
        "qdrant_starting": "Qdrant 시작 중... 잠시 후 🔄 새로고침하세요.",
        "qdrant_exe_missing": "qdrant/qdrant.exe 파일이 없습니다. releases 페이지에서 다운로드 후 qdrant/ 폴더에 복사하세요.",
        "settings_header": "⚙️ 설정",
        "collection_name": "컬렉션 이름",
        "ollama_url": "Ollama URL",
        "model_name": "임베딩 모델명",
        "save_settings_btn": "설정 저장",
        "settings_saved": "저장되었습니다. 모델이 재로드됩니다.",
        "embed_init_spinner": "임베딩 백엔드 초기화 중...",
        "embed_init_failed": "⚠️ 임베딩 백엔드 초기화 실패: {error}",
        "input_folder_header": "input/ 폴더 현황",
        "refresh_btn": "🔄 새로고침",
        "no_json_files": "input/ 폴더에 JSON/JSONL 파일이 없습니다. file2json의 output/ 폴더에서 파일을 복사하세요.",
        "read_error": "읽기 오류",
        "col_select": "**선택**",
        "row_select_label": "{name} 선택",
        "col_filename": "**JSON/JSONL 파일명**",
        "col_source": "**원본 문서**",
        "col_chunks": "**청크 수**",
        "ingest_all_btn": "🔄 전체 적재",
        "ingest_selected_btn": "✅ 선택 파일만 적재",
        "ingest_log_header": "적재 결과 로그",
        "log_success": "✅ {name} → {n} vectors 적재 완료",
        "log_error": "❌ {name} → 오류: {error}",
        "ingest_done": "적재 완료! ({n}개 처리)",
    },
    "zh": {
        "lang_label": "语言",
        "lang_ko": "한국어",
        "lang_zh": "中文",
        "page_title": "json2qdrant 向量数据库导入工具",
        "title": "🗄️ json2qdrant 向量数据库导入工具",
        "qdrant_connected": "🟢 Qdrant 已连接 ({url})",
        "qdrant_disconnected": "🔴 Qdrant 未连接 ({url})",
        "qdrant_start_btn": "🚀 启动 Qdrant",
        "qdrant_starting": "Qdrant 启动中... 请稍后点击 🔄 刷新。",
        "qdrant_exe_missing": "找不到 qdrant/qdrant.exe 文件。请从 releases 页面下载后复制到 qdrant/ 文件夹。",
        "settings_header": "⚙️ 设置",
        "collection_name": "集合名称",
        "ollama_url": "Ollama URL",
        "model_name": "嵌入模型名称",
        "save_settings_btn": "保存设置",
        "settings_saved": "已保存。模型将重新加载。",
        "embed_init_spinner": "正在初始化嵌入后端...",
        "embed_init_failed": "⚠️ 嵌入后端初始化失败: {error}",
        "input_folder_header": "input/ 文件夹状态",
        "refresh_btn": "🔄 刷新",
        "no_json_files": "input/ 文件夹中没有 JSON/JSONL 文件。请从 file2json 的 output/ 文件夹复制文件。",
        "read_error": "读取错误",
        "col_select": "**选择**",
        "row_select_label": "选择 {name}",
        "col_filename": "**JSON/JSONL 文件名**",
        "col_source": "**源文档**",
        "col_chunks": "**块数量**",
        "ingest_all_btn": "🔄 全部导入",
        "ingest_selected_btn": "✅ 仅导入选中文件",
        "ingest_log_header": "导入结果日志",
        "log_success": "✅ {name} → 已导入 {n} 个向量",
        "log_error": "❌ {name} → 错误: {error}",
        "ingest_done": "导入完成！(已处理 {n} 个)",
    },
}

DEFAULT_LANG = "ko"
SUPPORTED_LANGS = ("ko", "zh")


def normalize_lang(lang: str | None) -> str:
    if lang in SUPPORTED_LANGS:
        return lang
    return DEFAULT_LANG


def t(key: str, lang: str, **kwargs) -> str:
    lang = normalize_lang(lang)
    value = TRANSLATIONS.get(lang, {}).get(key)
    if value is None:
        value = TRANSLATIONS[DEFAULT_LANG].get(key, key)
    if kwargs:
        try:
            return value.format(**kwargs)
        except (KeyError, IndexError):
            return value
    return value
