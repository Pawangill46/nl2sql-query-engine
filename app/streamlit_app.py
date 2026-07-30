"""
Simple Streamlit frontend for the NL-to-SQL Query Engine.

This talks to the FastAPI backend (main.py) over HTTP -- it does NOT
import any of the backend code directly. That separation matters: the
frontend and backend could run on completely different machines, and
this file only knows about the API contract (the request/response
shapes), not the implementation behind it.

Run with: streamlit run app/streamlit_app.py
(keep `uvicorn app.main:app --reload` running in a separate terminal --
this frontend calls that server)
"""

import streamlit as st
import requests
import pandas as pd

API_BASE = "http://localhost:8000"

st.set_page_config(page_title="NL-to-SQL Query Engine", page_icon="🔎", layout="centered")

st.title("🔎 NL-to-SQL Query Engine")
st.caption("Upload a spreadsheet, ask questions in plain English, get real answers.")

# Session state tracks whether data has been uploaded yet, and remembers
# the query history for this browser session.
if "data_loaded" not in st.session_state:
    st.session_state.data_loaded = False
if "tables" not in st.session_state:
    st.session_state.tables = []
if "history" not in st.session_state:
    st.session_state.history = []

# ---- Upload section ----
st.subheader("1. Load your data")
uploaded_file = st.file_uploader("Upload an Excel (.xlsx) or CSV file", type=["xlsx", "xls", "csv"])

if uploaded_file is not None:
    if st.button("Load into engine"):
        with st.spinner("Reading file and building schema..."):
            files = {"file": (uploaded_file.name, uploaded_file.getvalue())}
            try:
                resp = requests.post(f"{API_BASE}/upload", files=files, timeout=30)
                if resp.status_code == 200:
                    data = resp.json()
                    st.session_state.data_loaded = True
                    st.session_state.tables = data.get("tables", [])
                    st.success(f"Loaded tables: {', '.join(st.session_state.tables)}")
                else:
                    st.error(f"Upload failed: {resp.text}")
            except requests.exceptions.ConnectionError:
                st.error(
                    "Could not reach the backend at "
                    f"{API_BASE}. Make sure `uvicorn app.main:app --reload` "
                    "is running in another terminal."
                )

if st.session_state.data_loaded:
    st.info(f"Active tables: {', '.join(st.session_state.tables)}")

st.divider()

# ---- Query section ----
st.subheader("2. Ask a question")

if not st.session_state.data_loaded:
    st.warning("Upload and load a file first.")
else:
    question = st.text_input(
        "Ask anything about your data",
        placeholder="e.g. what is the average package for CSE students",
    )

    if st.button("Ask", type="primary") and question.strip():
        with st.spinner("Thinking..."):
            try:
                resp = requests.post(
                    f"{API_BASE}/query", json={"question": question}, timeout=60
                )
                if resp.status_code == 200:
                    outcome = resp.json()
                    st.session_state.history.insert(0, {"question": question, **outcome})
                else:
                    st.error(f"Query failed: {resp.json().get('detail', resp.text)}")
            except requests.exceptions.ConnectionError:
                st.error("Could not reach the backend. Is the FastAPI server running?")

    # ---- Show results, most recent first ----
    for entry in st.session_state.history:
        with st.container(border=True):
            st.markdown(f"**Q: {entry['question']}**")

            if entry.get("sql"):
                st.code(entry["sql"], language="sql")

            result = entry.get("result")
            if result:
                df = pd.DataFrame(result)
                st.dataframe(df, use_container_width=True)

                # Auto-chart: only when there's a numeric column and more
                # than one row -- a single-value result (like an AVG) is
                # better shown as a number, not a one-bar chart.
                numeric_cols = df.select_dtypes(include="number").columns
                if len(numeric_cols) > 0 and len(df) > 1:
                    st.bar_chart(df.set_index(df.columns[0])[numeric_cols[0]])
            elif entry.get("error"):
                st.warning(f"No result: {entry['error']}")

            attempts = entry.get("attempts")
            if attempts and attempts > 1:
                st.caption(f"⚠️ Took {attempts} attempts (self-corrected after an initial failure)")
