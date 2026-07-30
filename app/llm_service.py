"""
Talks to the Gemini API to turn (schema + question) into SQL, and
implements the error-retry loop.
"""

import os
from google import genai

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

MODEL_NAME = "gemini-3.6-flash"

SYSTEM_PROMPT = """You are a SQL generation assistant. Given a database \
schema and a natural language question, output ONLY a single valid SELECT \
SQL query. No explanation, no markdown fences, no semicolon. \
If the question cannot be answered with the given schema, output exactly: \
CANNOT_ANSWER: <short reason>"""


def _format_schema(schema: dict) -> str:
    lines = []
    for table, columns in schema.items():
        col_str = ", ".join(f"{c['name']} ({c['type']})" for c in columns)
        lines.append(f"Table {table}: {col_str}")
    return "\n".join(lines)


def _call_gemini(prompt: str) -> str:
    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=f"{SYSTEM_PROMPT}\n\n{prompt}",
    )
    return response.text.strip()


def generate_sql(question: str, schema: dict, dialect: str = "sqlite") -> str:
    prompt = f"""Database dialect: {dialect}

Schema:
{_format_schema(schema)}

Question: {question}

SQL:"""
    return _call_gemini(prompt)


def generate_sql_with_retry(
    question: str, schema: dict, execute_fn, dialect: str = "sqlite", max_retries: int = 1
):
    sql = generate_sql(question, schema, dialect)
    attempt = 0
    last_error = None

    while attempt <= max_retries:
        if sql.startswith("CANNOT_ANSWER"):
            return {"sql": None, "result": None, "error": sql}

        try:
            result = execute_fn(sql)
            return {"sql": sql, "result": result, "error": None, "attempts": attempt + 1}
        except Exception as e:
            last_error = str(e)
            attempt += 1
            if attempt > max_retries:
                break
            fix_prompt = f"""The following SQL failed:
{sql}

Database error:
{last_error}

Schema:
{_format_schema(schema)}

Fix the query. Output ONLY the corrected SQL, no explanation."""
            sql = _call_gemini(fix_prompt)

    return {"sql": sql, "result": None, "error": last_error, "attempts": attempt}
