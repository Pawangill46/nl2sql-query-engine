"""
Converts an uploaded Excel/CSV file into a SQLite database on disk,
so it can be wrapped by ExcelSource and queried through the same
pipeline as a real database.

Day 2 of the build plan lives here.
"""

import os
import sqlite3
import pandas as pd
import re


def _sanitize_name(name: str) -> str:
    """
    Sheet names and column names from Excel can contain spaces, dots,
    or start with a digit -- none of which are safe as SQL identifiers.
    We normalize them so the LLM-generated SQL doesn't break on
    something like a column literally named "Q1 Revenue (%)".
    """
    name = re.sub(r"[^0-9a-zA-Z_]", "_", str(name).strip())
    if re.match(r"^\d", name):
        name = f"col_{name}"
    return name.lower()


def excel_to_sqlite(file_path: str, output_dir: str = "/tmp/nl2sql_dbs") -> str:
    """
    Reads every sheet in an Excel file (or a single CSV) and writes each
    as its own table in a fresh SQLite database.

    Returns the path to the resulting .db file.
    """
    os.makedirs(output_dir, exist_ok=True)
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    db_path = os.path.join(output_dir, f"{_sanitize_name(base_name)}.db")

    # Start clean each time -- avoids stale tables from a previous upload
    if os.path.exists(db_path):
        os.remove(db_path)

    conn = sqlite3.connect(db_path)

    if file_path.lower().endswith(".csv"):
        df = pd.read_csv(file_path)
        table_name = _sanitize_name(base_name)
        df.columns = [_sanitize_name(c) for c in df.columns]
        df.to_sql(table_name, conn, index=False, if_exists="replace")
    else:
        sheets = pd.read_excel(file_path, sheet_name=None)  # dict of all sheets
        for sheet_name, df in sheets.items():
            table_name = _sanitize_name(sheet_name)
            df.columns = [_sanitize_name(c) for c in df.columns]
            df.to_sql(table_name, conn, index=False, if_exists="replace")

    conn.close()
    return db_path


if __name__ == "__main__":
    # quick manual smoke test -- run: python excel_loader.py sample.xlsx
    import sys
    if len(sys.argv) > 1:
        path = excel_to_sqlite(sys.argv[1])
        print(f"Loaded into: {path}")
