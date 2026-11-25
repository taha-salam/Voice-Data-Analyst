"""
Unit tests for Phase 1: Database Connectors, Ingestion, and Profiling.
"""
import pytest
import sqlite3
import pandas as pd
from pathlib import Path
from src.config import Config
from src.db.connector import DatabaseManager, DatabaseSource
from src.db.profiler import DatabaseProfiler

@pytest.fixture(scope="session", autouse=True)
def setup_databases():
    """Ensure databases exist before tests."""
    from src.db.seed_data import seed_olist_database, seed_secondary_database, seed_sample_csvs
    Config.ensure_directories()
    seed_olist_database(Config.OLIST_DB_PATH)
    seed_secondary_database(Config.SECONDARY_DB_PATH)
    seed_sample_csvs(Config.DATA_DIR / "sample_csvs")

def test_olist_sqlite_tables_and_data():
    """Verify Olist SQLite database structure and row counts."""
    assert Config.OLIST_DB_PATH.exists()
    conn = sqlite3.connect(Config.OLIST_DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in cursor.fetchall()]
    expected_tables = ["orders", "order_items", "products", "customers", "order_payments", "order_reviews", "sellers", "product_category_name_translation"]
    
    for t in expected_tables:
        assert t in tables, f"Expected table {t} missing in Olist DB"
        cursor.execute(f"SELECT count(*) FROM {t}")
        count = cursor.fetchone()[0]
        assert count > 0, f"Table {t} should have rows, found 0"
    conn.close()

def test_database_manager_multi_source():
    """Verify DatabaseManager handles multiple sources (SQLite + CSV/DuckDB)."""
    db_mgr = DatabaseManager()
    
    # 1. Register Olist SQLite
    olist_src = db_mgr.register_sqlite("olist", str(Config.OLIST_DB_PATH), "Primary E-Commerce DB")
    assert olist_src is not None
    
    # Execute query on SQLite
    df_olist, elapsed_sqlite = olist_src.execute_query("SELECT count(*) as total_orders FROM orders")
    assert not df_olist.empty
    assert df_olist["total_orders"].iloc[0] > 0
    assert elapsed_sqlite >= 0
    
    # 2. Register Secondary SQLite (Inventory)
    sec_src = db_mgr.register_sqlite("inventory", str(Config.SECONDARY_DB_PATH), "Inventory & Warehouses DB")
    df_sec, _ = sec_src.execute_query("SELECT count(*) as total_warehouses FROM warehouses")
    assert not df_sec.empty
    assert df_sec["total_warehouses"].iloc[0] > 0
    
    # 3. Register CSV via DuckDB
    csv_path = Config.DATA_DIR / "sample_csvs" / "sales_representatives.csv"
    assert csv_path.exists()
    csv_src = db_mgr.register_csv("sales_csv", str(csv_path), "sales_reps")
    df_csv, elapsed_csv = csv_src.execute_query("SELECT rep_name, actual_sales FROM sales_reps WHERE actual_sales > 150000")
    assert not df_csv.empty
    assert len(df_csv) >= 2
    assert elapsed_csv >= 0

def test_database_profiler():
    """Verify zero-config automated schema profiler discovers tables, columns, and sample values."""
    db_mgr = DatabaseManager()
    olist_src = db_mgr.register_sqlite("olist", str(Config.OLIST_DB_PATH))
    
    profiler = DatabaseProfiler(olist_src)
    profile = profiler.profile(sample_limit=5)
    
    assert profile["source_name"] == "olist"
    assert "orders" in profile["tables"]
    assert "customers" in profile["tables"]
    
    orders_meta = profile["tables"]["orders"]
    col_names = [c["name"] for c in orders_meta["columns"]]
    assert "order_id" in col_names
    assert "customer_id" in col_names
    assert "order_purchase_timestamp" in col_names
    assert orders_meta["row_count"] > 0
    
    # Verify sample values were extracted
    customers_meta = profile["tables"]["customers"]
    assert "customer_city" in customers_meta["sample_values"]
    assert len(customers_meta["sample_values"]["customer_city"]) > 0
