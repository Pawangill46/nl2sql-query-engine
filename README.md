# NL-to-SQL Query Engine

Query an Excel/CSV file or a live database using plain English. Under the
hood, everything is normalized to SQL execution against a single, unified
pipeline — Excel gets loaded into SQLite on upload, so the same schema
introspection, LLM prompting, safety validation, and execution code path
handles both input types.

## Architecture

```
Excel/CSV --> excel_loader.py --> SQLite  --\
                                              >-- DataSource (common interface)
Postgres/MySQL connection string ------------/
                                              |
                                    schema introspection (SQLAlchemy inspect)
                                              |
                              question + schema --> Claude API --> SQL
                                              |
                                    sql_safety.py (SELECT-only, row limit)
                                              |
                                    execute against read-only connection
                                              |
                              on failure: feed error back to LLM, retry once
                                              |
                                          results (+ SQL shown to user)
```

## Why these design decisions

- **Single `DataSource` abstraction for Excel and SQL**: avoids maintaining
  two separate prompting/safety/execution paths for what is functionally
  the same problem once schema is known.
- **SELECT-only validation via AST parsing (`sqlglot`)**, not string
  matching: string matching on keywords like "DROP" can be bypassed with
  comments, casing tricks, or subqueries. Parsing the actual SQL AST and
  checking the statement type is the only reliable guard.
- **Row limit enforcement**: prevents a single query from returning
  unbounded results and blowing up memory or the response payload.
- **Error-retry loop**: LLM-generated SQL fails sometimes (wrong column
  name, ambiguous join). Feeding the real database error back to the model
  and letting it self-correct once is far more robust than failing
  immediately.
- **Schema shown compactly to the LLM**: table + column + type only, not
  full sample data, to keep prompt size and cost predictable as schemas
  grow (see "Known Limitations" below for what happens at real scale).

## Known limitations / next steps

- Schema is currently sent to the LLM in full on every query. For a
  database with 50+ tables, this won't fit in context economically —
  the fix is a retrieval step that embeds each table's schema and only
  pulls the top-k relevant tables per question (RAG applied to schema
  instead of documents).
- Single in-memory session (`_active_source` in `main.py`) — fine for a
  local demo, not for multiple concurrent users. Would need a real
  session/user model to scale.
- No caching yet: identical questions re-hit the LLM every time. A
  hash(question + schema version) → cached SQL layer would cut cost and
  latency.
- No automated evaluation set yet. A benchmark of (question, expected
  result) pairs with an accuracy script would turn "it works" into a
  measurable number.

## Setup

```bash
cp .env.example .env         # add your ANTHROPIC_API_KEY
docker compose up --build
```

API available at `http://localhost:8000`. Interactive docs at
`http://localhost:8000/docs`.

### Endpoints

- `POST /upload` — multipart file upload (.xlsx or .csv)
- `POST /connect` — `{"connection_string": "...", "dialect": "postgresql"}`
- `POST /query` — `{"question": "What is the average salary in CS department?"}`

## Local dev without Docker

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=your_key_here
uvicorn app.main:app --reload
```
