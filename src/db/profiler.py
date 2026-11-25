"""
Automated database profiler: discovers tables, columns, data types, sample values, and foreign keys.
Works with SQLite, DuckDB, and PostgreSQL without manual configuration.
"""
import sqlite3
import pandas as pd
from typing import Dict, Any, List, Optional
from pathlib import Path

class DatabaseProfiler:
    """Profiles any relational database for zero-config schema extraction."""
    
    def __init__(self, db_source):
        self.source = db_source

    def profile(self, sample_limit: int = 5) -> Dict[str, Any]:
        """Profiles the database and returns structured schema metadata."""
        if self.source.engine_type == "sqlite":
            return self._profile_sqlite(sample_limit)
        elif self.source.engine_type in ("duckdb", "csv"):
            return self._profile_duckdb(sample_limit)
        elif self.source.engine_type == "postgres":
            return self._profile_postgres(sample_limit)
        else:
            raise ValueError(f"Unsupported engine: {self.source.engine_type}")

    def _profile_sqlite(self, sample_limit: int) -> Dict[str, Any]:
        profile_data = {
            "source_name": self.source.name,
            "engine": "sqlite",
            "tables": {}
        }
        
        with sqlite3.connect(self.source.uri_or_path) as conn:
            cursor = conn.cursor()
            # 1. Fetch tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
            tables = [row[0] for row in cursor.fetchall()]
            
            for table in tables:
                table_info = {
                    "columns": [],
                    "primary_keys": [],
                    "foreign_keys": [],
                    "row_count": 0,
                    "sample_values": {}
                }
                
                # Row count
                try:
                    cursor.execute(f"SELECT count(*) FROM \"{table}\"")
                    table_info["row_count"] = cursor.fetchone()[0]
                except Exception:
                    table_info["row_count"] = 0
                
                # Column details: cid, name, type, notnull, dflt_value, pk
                cursor.execute(f"PRAGMA table_info(\"{table}\")")
                for col in cursor.fetchall():
                    cid, name, col_type, notnull, dflt_value, pk = col
                    table_info["columns"].append({
                        "name": name,
                        "type": col_type or "TEXT",
                        "notnull": bool(notnull)
                    })
                    if pk:
                        table_info["primary_keys"].append(name)
                
                # Foreign keys: id, seq, table, from, to, on_update, on_delete, match
                cursor.execute(f"PRAGMA foreign_key_list(\"{table}\")")
                for fk in cursor.fetchall():
                    table_info["foreign_keys"].append({
                        "from_column": fk[3],
                        "to_table": fk[2],
                        "to_column": fk[4]
                    })
                
                # Sample categorical / distinct values for up to 10 columns
                for col in table_info["columns"][:10]:
                    col_name = col["name"]
                    try:
                        cursor.execute(
                            f"SELECT DISTINCT \"{col_name}\" FROM \"{table}\" "
                            f"WHERE \"{col_name}\" IS NOT NULL LIMIT {sample_limit}"
                        )
                        samples = [str(r[0]) for r in cursor.fetchall()]
                        table_info["sample_values"][col_name] = samples
                    except Exception:
                        table_info["sample_values"][col_name] = []
                
                profile_data["tables"][table] = table_info
                
        return profile_data

    def _profile_duckdb(self, sample_limit: int) -> Dict[str, Any]:
        profile_data = {
            "source_name": self.source.name,
            "engine": "duckdb",
            "tables": {}
        }
        con = self.source.get_connection()
        tables_df = con.execute("SHOW TABLES").df()
        table_names = tables_df.iloc[:, 0].tolist() if not tables_df.empty else []
        
        for table in table_names:
            table_info = {
                "columns": [],
                "primary_keys": [],
                "foreign_keys": [],
                "row_count": 0,
                "sample_values": {}
            }
            try:
                table_info["row_count"] = con.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
            except Exception:
                table_info["row_count"] = 0
                
            cols_df = con.execute(f"DESCRIBE {table}").df()
            for _, row in cols_df.iterrows():
                col_name = row['column_name']
                col_type = row['column_type']
                table_info["columns"].append({"name": col_name, "type": col_type, "notnull": False})
                
                try:
                    samples_df = con.execute(f"SELECT DISTINCT \"{col_name}\" FROM {table} WHERE \"{col_name}\" IS NOT NULL LIMIT {sample_limit}").df()
                    table_info["sample_values"][col_name] = [str(v) for v in samples_df.iloc[:, 0].tolist()]
                except Exception:
                    table_info["sample_values"][col_name] = []
                    
            profile_data["tables"][table] = table_info
            
        return profile_data

    def _profile_postgres(self, sample_limit: int) -> Dict[str, Any]:
        # PostgreSQL information_schema query
        import psycopg2
        profile_data = {
            "source_name": self.source.name,
            "engine": "postgres",
            "tables": {}
        }
        with psycopg2.connect(self.source.uri_or_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)
            tables = [r[0] for r in cursor.fetchall()]
            for table in tables:
                table_info = {
                    "columns": [],
                    "primary_keys": [],
                    "foreign_keys": [],
                    "row_count": 0,
                    "sample_values": {}
                }
                cursor.execute(f"SELECT count(*) FROM \"{table}\"")
                table_info["row_count"] = cursor.fetchone()[0]
                
                cursor.execute(f"""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns 
                    WHERE table_name = '{table}'
                """)
                for col in cursor.fetchall():
                    table_info["columns"].append({"name": col[0], "type": col[1], "notnull": col[2] == 'NO'})
                
                profile_data["tables"][table] = table_info
        return profile_data
