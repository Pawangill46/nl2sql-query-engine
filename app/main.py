"""
FastAPI app tying the pieces together:
  POST /upload      -> Excel/CSV file -> ExcelSource
  POST /connect      -> DB connection string -> SQLSource
  POST /query        -> natural language question -> SQL -> results

IMPORTANT: load_dotenv() must run before any of our own modules are
imported, because llm_service.py reads GEMINI_API_KEY at import time.
"""

from dotenv import load_dotenv
load_dotenv()

import os
import shutil
import tempfile
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import text

from app.datasource import ExcelSource, SQLSource
from app.excel_loader import excel_to_sqlite
from app.sql_safety import validate_select_only, UnsafeQueryError
from app.llm_service import generate_sql_with_retry

app = FastAPI(title="NL-to-SQL Query Engine")

# Allows the React frontend (running on a different port during local
# dev, e.g. localhost:5173) to call this API. Restricted to localhost
# origins -- tighten this before ever deploying publicly.
app.add_middleware(
    CORSMiddleware,
    # Wide open for local dev -- avoids chasing exact port/origin mismatches
    # across different dev environments (plain Windows, WSL, containers,
    # forwarded ports). Tighten this to specific origins before ever
    # deploying publicly.
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

_active_source = {"source": None, "dialect": "sqlite"}


class ConnectRequest(BaseModel):
    connection_string: str
    dialect: str = "postgresql"


class QueryRequest(BaseModel):
    question: str


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    tmp_path = os.path.join(tempfile.gettempdir(), file.filename)
    with open(tmp_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    db_path = excel_to_sqlite(tmp_path)
    _active_source["source"] = ExcelSource(db_path)
    _active_source["dialect"] = "sqlite"

    schema = _active_source["source"].get_schema_summary()
    return {"status": "loaded", "tables": schema}


@app.post("/connect")
async def connect_database(req: ConnectRequest):
    source = SQLSource(req.connection_string)
    try:
        schema = source.get_schema_summary()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not connect: {e}")

    _active_source["source"] = source
    _active_source["dialect"] = req.dialect
    return {"status": "connected", "tables": schema}


@app.post("/query")
async def query(req: QueryRequest):
    source = _active_source["source"]
    if source is None:
        raise HTTPException(status_code=400, detail="No data source loaded. Call /upload or /connect first.")

    schema = source.get_schema_summary()
    engine = source.get_engine()

    def execute_fn(sql: str):
        safe_sql = validate_select_only(sql, dialect=_active_source["dialect"])
        with engine.connect() as conn:
            result = conn.execute(text(safe_sql))
            rows = [dict(row._mapping) for row in result]
        return rows

    outcome = generate_sql_with_retry(
        req.question, schema, execute_fn, dialect=_active_source["dialect"]
    )

    if outcome["error"] and outcome["result"] is None:
        raise HTTPException(status_code=422, detail=outcome["error"])

    return outcome


@app.get("/health")
async def health():
    return {"status": "ok"}