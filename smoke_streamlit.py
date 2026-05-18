"""Minimal Streamlit smoke-test app.

Run this file to check whether Streamlit itself can render in the browser
without loading json2qdrant, Qdrant, Ollama, config.yaml, or input files.
"""

from __future__ import annotations

from datetime import datetime

import streamlit as st


st.set_page_config(page_title="Streamlit Smoke Test", layout="centered")
st.title("Hello Streamlit")
st.success("If you can see this message, the Streamlit frontend is rendering.")
st.write("This smoke-test app does not import json2qdrant modules.")
st.code("python -m streamlit run .\\smoke_streamlit.py", language="powershell")
st.caption(f"Rendered at: {datetime.now().isoformat(timespec='seconds')}")
