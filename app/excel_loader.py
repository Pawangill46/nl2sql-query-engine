"""
Converts an uploaded Excel/CSV file into a SQLite database on disk,
so it can be wrapped by ExcelSource and queried through the same
pipeline as a real database.

Does NOT delete the existing .db file before writing -- Windows keeps
a stricter file lock than Linux/Mac, so a delete-then-recreate pattern
throws PermissionError if a previous connection hasn't fully released
the handle yet. Instead, we let pandas' to_sql(if_exists="replace")
overwrite each table's content directly, which achieves the same
"start fresh" result without ever touching the file handle.
"""

import os
import tempfile
import sqlite3
import pandas as pd
import re


def _sanitize_name(name: str) -> str:
    name = re.sub(r"[^0-9a-zA-Z_]", "_", str(name).strip())
    if re.match(r"^\d", name):
        name = f"col_{name}"
    return name.lower()


def excel_to_sqlite(file_path: str, output_dir: str = None) -> str:
    if output_dir is None:
        output_dir = os.path.join(tempfile.gettempdir(), "nl2sql_dbs")

    os.makedirs(output_dir, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    db_path = os.path.join(output_dir, f"{_sanitize_name(base_name)}.db")

    conn = sqlite3.connect(db_path)

    try:
        if file_path.lower().endswith(".csv"):
            df = pd.read_csv(file_path)
            table_name = _sanitize_name(base_name)
            df.columns = [_sanitize_name(c) for c in df.columns]
            df.to_sql(table_name, conn, index=False, if_exists="replace")
        else:
            sheets = pd.read_excel(file_path, sheet_name=None)
            for sheet_name, df in sheets.items():
                table_name = _sanitize_name(sheet_name)
                df.columns = [_sanitize_name(c) for c in df.columns]
                df.to_sql(table_name, conn, index=False, if_exists="replace")
    finally:
        conn.close()

    return db_path


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        path = excel_to_sqlite(sys.argv[1])
        print(f"Loaded into: {path}")