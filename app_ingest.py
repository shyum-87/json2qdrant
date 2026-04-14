import json
import subprocess
from pathlib import Path

import streamlit as st
import yaml

from i18n import DEFAULT_LANG, SUPPORTED_LANGS, normalize_lang, t
from ingestor import (
    chunk_text,
    get_qdrant_client,
    ingest_file,
    is_qdrant_healthy,
    load_config,
    load_documents,
    load_model,
)

config = load_config()
config.setdefault("ui", {})
config["ui"].setdefault("language", DEFAULT_LANG)

if "lang" not in st.session_state:
    st.session_state["lang"] = normalize_lang(config["ui"]["language"])

lang = st.session_state["lang"]


def tr(key: str, **kwargs) -> str:
    return t(key, st.session_state["lang"], **kwargs)


def save_config() -> None:
    with open("config.yaml", "w", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False)


st.set_page_config(page_title=tr("page_title"), layout="wide")

col_title, col_lang = st.columns([5, 1])
with col_title:
    st.title(tr("title"))
with col_lang:
    lang_options = list(SUPPORTED_LANGS)
    lang_labels = {code: t(f"lang_{code}", lang) for code in lang_options}
    selected = st.radio(
        tr("lang_label"),
        options=lang_options,
        index=lang_options.index(lang),
        format_func=lambda code: lang_labels[code],
        horizontal=True,
        key="lang_radio",
    )
    if selected != st.session_state["lang"]:
        st.session_state["lang"] = selected
        config["ui"]["language"] = selected
        save_config()
        st.rerun()

input_dir = Path(config["paths"]["input_dir"])
input_dir.mkdir(exist_ok=True)

healthy = is_qdrant_healthy(config)
col_status, col_start = st.columns([4, 1])
with col_status:
    if healthy:
        st.success(tr("qdrant_connected", url=config["qdrant"]["url"]))
    else:
        st.error(tr("qdrant_disconnected", url=config["qdrant"]["url"]))
with col_start:
    if st.button(tr("qdrant_start_btn")):
        qdrant_exe = Path("qdrant/qdrant.exe")
        if qdrant_exe.exists():
            subprocess.Popen(
                [str(qdrant_exe.resolve())],
                cwd=str(qdrant_exe.parent.resolve()),
            )
            st.info(tr("qdrant_starting"))
        else:
            st.error(tr("qdrant_exe_missing"))

with st.expander(tr("settings_header"), expanded=False):
    collection_name_input = st.text_input(
        tr("collection_name"), value=config["qdrant"]["default_collection"]
    )
    ollama_url_input = st.text_input(
        tr("ollama_url"), value=config["embedding"].get("ollama_url", "http://localhost:11434")
    )
    model_name_input = st.text_input(
        tr("model_name"), value=config["embedding"].get("model_name", "bge-m3:latest")
    )
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
    if st.button(tr("save_settings_btn")):
        config["qdrant"]["default_collection"] = collection_name_input
        config["embedding"]["backend"] = "ollama"
        config["embedding"]["ollama_url"] = ollama_url_input
        config["embedding"]["model_name"] = model_name_input
        config.setdefault("chunking", {})
        config["chunking"]["chunk_size"] = int(chunk_size_input)
        config["chunking"]["overlap"] = int(overlap_input)
        save_config()
        if "model" in st.session_state:
            del st.session_state["model"]
        st.success(tr("settings_saved"))
        st.rerun()

collection_name = config["qdrant"]["default_collection"]

if "model" not in st.session_state:
    try:
        with st.spinner(tr("embed_init_spinner")):
            st.session_state["model"] = load_model(config)
    except Exception as e:
        st.warning(tr("embed_init_failed", error=str(e)))
        st.session_state["model"] = None

col_sub, col_refresh = st.columns([5, 1])
with col_sub:
    st.subheader(tr("input_folder_header"))
with col_refresh:
    if st.button(tr("refresh_btn")):
        st.rerun()

json_files = sorted(
    f for f in input_dir.iterdir() if f.is_file() and f.suffix == ".json"
)

if not json_files:
    st.info(tr("no_json_files"))
else:
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
                doc_type = ", ".join(sorted(dt for dt in types if dt)) or "-"
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

    col_all, col_sel = st.columns(2)
    disabled = not healthy or st.session_state.get("model") is None
    with col_all:
        ingest_all = st.button(
            tr("ingest_all_btn"), use_container_width=True, disabled=disabled
        )
    with col_sel:
        ingest_selected = st.button(
            tr("ingest_selected_btn"), use_container_width=True, disabled=disabled
        )

    files_to_ingest = []
    if ingest_all:
        files_to_ingest = [row["file"] for row in file_rows]
    elif ingest_selected:
        files_to_ingest = [
            row["file"] for row in file_rows if selections.get(row["name"])
        ]

    if files_to_ingest:
        st.subheader(tr("ingest_log_header"))
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
            except Exception as e:
                logs.append(tr("log_error", name=json_path.name, error=str(e)))

            progress_bar.progress((i + 1) / len(files_to_ingest))
            log_placeholder.text("\n".join(logs))

        st.success(tr("ingest_done", n=len(files_to_ingest)))
