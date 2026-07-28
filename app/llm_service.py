"""
Talks to the Claude API to turn (schema + question) into SQL, and
implements the error-retry loop: if execution fails, we feed the actual
DB error back to the model and ask it to fix its own query.

Day 4 (first working query) and Day 5 (retry loop) live here.
"""

import os
import anthropic

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

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


def generate_sql(question: str, schema: dict, dialect: str = "sqlite") -> str:
    prompt = f"""Database dialect: {dialect}

Schema:
{_format_schema(schema)}

Question: {question}

SQL:"""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=500,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip()


def generate_sql_with_retry(
    question: str, schema: dict, execute_fn, dialect: str = "sqlite", max_retries: int = 1
):
    """
    execute_fn: a callable that takes a SQL string, runs it, and either
    returns results or raises an exception. Keeping this injected (rather
    than importing the DB layer here) keeps this module testable in
    isolation -- worth mentioning if asked about your testing approach.
    """
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
            # Feed the real DB error back to the model and ask for a fix.
            fix_prompt = f"""The following SQL failed:
{sql}

Database error:
{last_error}

Schema:
{_format_schema(schema)}

Fix the query. Output ONLY the corrected SQL, no explanation."""
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=500,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": fix_prompt}],
            )
            sql = response.content[0].text.strip()

    return {"sql": sql, "result": None, "error": last_error, "attempts": attempt}
