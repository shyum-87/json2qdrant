import json
import subprocess
from pathlib import Path

import streamlit as st
import yaml

from ingestor import (
    get_qdrant_client,
    ingest_file,
    is_qdrant_healthy,
    load_config,
    load_model,
)

st.set_page_config(page_title="json2qdrant 벡터 DB 적재기", layout="wide")
st.title("🗄️ json2qdrant 벡터 DB 적재기")

config = load_config()
input_dir = Path(config["paths"]["input_dir"])
input_dir.mkdir(exist_ok=True)

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
            subprocess.Popen(
                [str(qdrant_exe.resolve())],
                cwd=str(qdrant_exe.parent.resolve()),
            )
            st.info("Qdrant 시작 중... 잠시 후 🔄 새로고침하세요.")
        else:
            st.error(
                "qdrant/qdrant.exe 파일이 없습니다. releases 페이지에서 다운로드 후 "
                "qdrant/ 폴더에 복사하세요."
            )

with st.expander("⚙️ 설정", expanded=False):
    collection_name_input = st.text_input(
        "컬렉션 이름", value=config["qdrant"]["default_collection"]
    )
    ollama_url_input = st.text_input(
        "Ollama URL", value=config["embedding"].get("ollama_url", "http://localhost:11434")
    )
    model_name_input = st.text_input(
        "임베딩 모델명", value=config["embedding"].get("model_name", "bge-m3:latest")
    )
    if st.button("설정 저장"):
        config["qdrant"]["default_collection"] = collection_name_input
        config["embedding"]["backend"] = "ollama"
        config["embedding"]["ollama_url"] = ollama_url_input
        config["embedding"]["model_name"] = model_name_input
        with open("config.yaml", "w", encoding="utf-8") as f:
            yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
        if "model" in st.session_state:
            del st.session_state["model"]
        st.success("저장되었습니다. 모델이 재로드됩니다.")
        st.rerun()

collection_name = config["qdrant"]["default_collection"]

if "model" not in st.session_state:
    try:
        with st.spinner("임베딩 백엔드 초기화 중..."):
            st.session_state["model"] = load_model(config)
    except Exception as e:
        st.warning(f"⚠️ 임베딩 백엔드 초기화 실패: {e}")
        st.session_state["model"] = None

col_title, col_refresh = st.columns([5, 1])
with col_title:
    st.subheader("input/ 폴더 현황")
with col_refresh:
    if st.button("🔄 새로고침"):
        st.rerun()

json_files = sorted(
    f for f in input_dir.iterdir() if f.is_file() and f.suffix == ".json"
)

if not json_files:
    st.info(
        "input/ 폴더에 JSON 파일이 없습니다. file2json의 output/ 폴더에서 파일을 복사하세요."
    )
else:
    file_rows = []
    for f in json_files:
        try:
            with open(f, "r", encoding="utf-8") as fp:
                data = json.load(fp)
            total_chunks = data.get("total_chunks", len(data.get("chunks", [])))
            source = data.get("source", f.name)
        except Exception:
            total_chunks = "읽기 오류"
            source = f.name
        file_rows.append(
            {"file": f, "name": f.name, "source": source, "chunks": total_chunks}
        )

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
            selections[row["name"]] = st.checkbox(
                "", value=True, key=f"sel_{row['name']}", label_visibility="collapsed"
            )
        with c2:
            st.text(row["name"])
        with c3:
            st.text(row["source"])
        with c4:
            st.text(str(row["chunks"]))

    st.divider()

    col_all, col_sel = st.columns(2)
    disabled = not healthy or st.session_state.get("model") is None
    with col_all:
        ingest_all = st.button(
            "🔄 전체 적재", use_container_width=True, disabled=disabled
        )
    with col_sel:
        ingest_selected = st.button(
            "✅ 선택 파일만 적재", use_container_width=True, disabled=disabled
        )

    files_to_ingest = []
    if ingest_all:
        files_to_ingest = [row["file"] for row in file_rows]
    elif ingest_selected:
        files_to_ingest = [
            row["file"] for row in file_rows if selections.get(row["name"])
        ]

    if files_to_ingest:
        st.subheader("적재 결과 로그")
        progress_bar = st.progress(0)
        log_placeholder = st.empty()
        logs = []

        client = get_qdrant_client(config)
        model = st.session_state["model"]

        for i, json_path in enumerate(files_to_ingest):
            try:
                result = ingest_file(
                    json_path, collection_name, config, model, client
                )
                logs.append(
                    f"✅ {json_path.name} → {result['chunks_ingested']} vectors 적재 완료"
                )
            except Exception as e:
                logs.append(f"❌ {json_path.name} → 오류: {e}")

            progress_bar.progress((i + 1) / len(files_to_ingest))
            log_placeholder.text("\n".join(logs))

        st.success(f"적재 완료! ({len(files_to_ingest)}개 처리)")
