"""
Multi-source database connection manager supporting SQLite, PostgreSQL, and DuckDB (for CSVs).
"""
import sqlite3
import pandas as pd
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
import duckdb

class DatabaseSource:
    def __init__(self, name: str, engine_type: str, uri_or_path: str, description: str = ""):
        self.name = name
        self.engine_type = engine_type.lower()  # 'sqlite', 'postgres', 'duckdb', 'csv'
        self.uri_or_path = uri_or_path
        self.description = description
        self._duckdb_con = None

    def get_connection(self):
        if self.engine_type == "sqlite":
            return sqlite3.connect(self.uri_or_path)
        elif self.engine_type == "duckdb" or self.engine_type == "csv":
            if self._duckdb_con is None:
                self._duckdb_con = duckdb.connect(database=":memory:")
            return self._duckdb_con
        elif self.engine_type == "postgres":
            import psycopg2
            return psycopg2.connect(self.uri_or_path)
        else:
            raise ValueError(f"Unsupported engine type: {self.engine_type}")

    def execute_query(self, sql: str, timeout: int = 15) -> Tuple[pd.DataFrame, float]:
        """Executes a SQL query and returns result as DataFrame and execution time in seconds."""
        import time
        start_time = time.time()
        
        if self.engine_type == "sqlite":
            with sqlite3.connect(self.uri_or_path) as conn:
                df = pd.read_sql_query(sql, conn)
        elif self.engine_type in ("duckdb", "csv"):
            con = self.get_connection()
            df = con.execute(sql).df()
        elif self.engine_type == "postgres":
            import psycopg2
            with psycopg2.connect(self.uri_or_path) as conn:
                df = pd.read_sql_query(sql, conn)
        else:
            raise ValueError(f"Unknown engine: {self.engine_type}")
            
        elapsed = time.time() - start_time
        return df, elapsed


class DatabaseManager:
    """Manages active databases and multi-source query dispatching."""
    def __init__(self):
        self.sources: Dict[str, DatabaseSource] = {}

    def register_sqlite(self, name: str, db_path: str, description: str = "") -> DatabaseSource:
        source = DatabaseSource(name=name, engine_type="sqlite", uri_or_path=str(db_path), description=description)
        self.sources[name] = source
        return source

    def register_postgres(self, name: str, uri: str, description: str = "") -> DatabaseSource:
        source = DatabaseSource(name=name, engine_type="postgres", uri_or_path=uri, description=description)
        self.sources[name] = source
        return source

    def register_csv(self, name: str, file_path: str, table_name: str, description: str = "") -> DatabaseSource:
        """Loads a CSV into an in-memory DuckDB table."""
        source = self.sources.get("csv_duckdb")
        if not source:
            source = DatabaseSource(name="csv_duckdb", engine_type="duckdb", uri_or_path=":memory:", description="In-memory CSV engine")
            self.sources["csv_duckdb"] = source
        
        con = source.get_connection()
        # Sanitize table name
        safe_table = "".join(c for c in table_name if c.isalnum() or c == "_")
        con.execute(f"CREATE TABLE IF NOT EXISTS {safe_table} AS SELECT * FROM read_csv_auto('{file_path}')")
        return source

    def get_source(self, name: str) -> Optional[DatabaseSource]:
        return self.sources.get(name)

    def list_sources(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": name,
                "engine": src.engine_type,
                "path": src.uri_or_path,
                "description": src.description
            }
            for name, src in self.sources.items()
        ]
