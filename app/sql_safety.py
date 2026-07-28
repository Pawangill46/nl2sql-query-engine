"""
Safety layer: the single most important file in this project from an
interview-defensibility standpoint.

The LLM's output is TEXT. We never trust it blindly. Before executing
anything, we:
  1. Parse it to confirm it's a single SELECT statement (via sqlglot)
  2. Reject anything containing write/DDL keywords as a second guard
  3. Enforce a row limit so a query can't blow up memory or the response
  4. (Execution itself, in main.py, uses a timeout + read-only connection)

This is Day 5 of the build plan, but scaffolding it now so the interface
is ready when the LLM piece lands.
"""

import sqlglot
from sqlglot.errors import ParseError

FORBIDDEN_KEYWORDS = {
    "insert", "update", "delete", "drop", "alter", "truncate",
    "create", "grant", "revoke", "attach", "pragma",
}

MAX_ROW_LIMIT = 500


class UnsafeQueryError(Exception):
    pass


def validate_select_only(sql: str, dialect: str = "sqlite") -> str:
    """
    Raises UnsafeQueryError if the SQL is anything other than a read-only
    SELECT. Returns the (possibly row-limited) SQL string if it's safe.
    """
    sql_stripped = sql.strip().rstrip(";")

    try:
        parsed = sqlglot.parse_one(sql_stripped, read=dialect)
    except ParseError as e:
        raise UnsafeQueryError(f"Could not parse SQL: {e}")

    if parsed.key != "select":
        raise UnsafeQueryError(
            f"Only SELECT statements are allowed, got: {parsed.key}"
        )

    lowered = sql_stripped.lower()
    for keyword in FORBIDDEN_KEYWORDS:
        if keyword in lowered:
            raise UnsafeQueryError(f"Forbidden keyword detected: {keyword}")

    # Enforce a row cap if the query doesn't already have one, or has a
    # larger one than we allow.
    existing_limit = parsed.args.get("limit")
    if existing_limit is None:
        parsed = parsed.limit(MAX_ROW_LIMIT)
    else:
        try:
            limit_value = int(existing_limit.expression.this)
            if limit_value > MAX_ROW_LIMIT:
                parsed.set("limit", None)
                parsed = parsed.limit(MAX_ROW_LIMIT)
        except (AttributeError, ValueError):
            parsed.set("limit", None)
            parsed = parsed.limit(MAX_ROW_LIMIT)

    return parsed.sql(dialect=dialect)
