"""
Core abstraction of the project.

Why this exists: an Excel file and a live SQL database are fundamentally
different things, but once loaded, both can be queried through the SAME
interface if we normalize Excel into a SQLite table on upload.

This means the rest of the app (schema introspection, SQL generation,
execution, safety checks) never needs to know or care whether the original
source was an .xlsx file or a Postgres connection string. One code path,
two input types.

Interview talking point: "Why not just special-case Excel with pandas
queries?" -> Because then you'd need two separate LLM prompting strategies,
two separate safety layers, and two separate result formatters. Normalizing
early means one pipeline to build, test, and secure.
"""

from abc import ABC, abstractmethod
from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import Engine


class DataSource(ABC):
    """Common interface every data source must implement."""

    @abstractmethod
    def get_engine(self) -> Engine:
        """Return a SQLAlchemy engine pointing at queryable tables."""
        raise NotImplementedError

    def get_schema_summary(self) -> dict:
        """
        Extract table/column/type info via SQLAlchemy's inspector.
        This is the exact information we hand to the LLM later, so keep
        it compact -- token cost scales with schema size (this matters a
        lot once you have many tables, see Phase 3).
        """
        engine = self.get_engine()
        inspector = inspect(engine)
        schema = {}
        for table_name in inspector.get_table_names():
            columns = inspector.get_columns(table_name)
            schema[table_name] = [
                {"name": col["name"], "type": str(col["type"])}
                for col in columns
            ]
        return schema


class SQLSource(DataSource):
    """Wraps a real database connection string (Postgres, MySQL, etc.)."""

    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self._engine = None

    def get_engine(self) -> Engine:
        if self._engine is None:
            # IMPORTANT: in Phase 5 (safety layer) this should connect
            # as a READ-ONLY database role, not the app's default user.
            self._engine = create_engine(self.connection_string)
        return self._engine


class ExcelSource(DataSource):
    """Wraps an uploaded Excel/CSV file, materialized into SQLite."""

    def __init__(self, sqlite_path: str):
        # sqlite_path is produced by excel_loader.py BEFORE this object
        # is constructed -- this class just wraps the resulting file.
        self.sqlite_path = sqlite_path
        self._engine = None

    def get_engine(self) -> Engine:
        if self._engine is None:
            self._engine = create_engine(f"sqlite:///{self.sqlite_path}")
        return self._engine
