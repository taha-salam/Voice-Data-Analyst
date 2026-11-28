"""
Unit tests for unseen-database accuracy fixes:
1. Join-aware 1-hop schema linking on an unseen SQLite database.
2. Missing-metric detection returning non-refusal error status.
3. Preventing the summarizer from summing averages/rates/scores or AVG() aliases.
4. Skipping ID, rank, and index columns in build_numeric_kpi.
"""
import sqlite3
from types import SimpleNamespace
from unittest.mock import MagicMock

import pandas as pd
import pytest

from src.db.connector import DatabaseManager
from src.db.profiler import DatabaseProfiler
from src.nlp.schema_linker import SchemaLinker
from src.nlp.sql_generator import SQLGenerator
from src.nlp.summarizer import AnalyticsEngine
from src.ui.components import build_numeric_kpi


@pytest.fixture
def unseen_cafe_profile(tmp_path):
    """Creates a small unseen SQLite database (tickets, menu_items, branches, baristas) and profiles it."""
    db_path = tmp_path / "cafe_test.sqlite"
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.executescript(
        """
        CREATE TABLE branches (
            branch_id INTEGER PRIMARY KEY,
            branch_name TEXT,
            city TEXT
        );
        CREATE TABLE baristas (
            barista_id INTEGER PRIMARY KEY,
            barista_name TEXT,
            branch_id INTEGER
        );
        CREATE TABLE menu_items (
            item_id INTEGER PRIMARY KEY,
            item_name TEXT,
            category TEXT,
            unit_price REAL
        );
        CREATE TABLE tickets (
            ticket_id INTEGER PRIMARY KEY,
            item_id INTEGER,
            branch_id INTEGER,
            barista_id INTEGER,
            qty INTEGER,
            tip REAL
        );

        INSERT INTO branches VALUES (1, 'Downtown', 'Seattle'), (2, 'Midtown', 'Portland');
        INSERT INTO baristas VALUES (1, 'Sam', 1), (2, 'Maya', 2);
        INSERT INTO menu_items VALUES
            (1, 'Latte', 'Coffee', 5.50),
            (2, 'Espresso', 'Coffee', 3.50),
            (3, 'Croissant', 'Pastry', 4.25);
        INSERT INTO tickets VALUES
            (1, 1, 1, 1, 3, 2.50),
            (2, 2, 1, 1, 2, 1.00),
            (3, 3, 2, 2, 4, 3.00);
        """
    )
    conn.commit()
    conn.close()

    source = DatabaseManager().register_sqlite("cafe_test", str(db_path))
    return DatabaseProfiler(source).profile(sample_limit=5)


def test_join_aware_schema_linking_unseen_db(unseen_cafe_profile):
    """'top 3 menu items by revenue' must link both menu_items and tickets via shared item_id."""
    linker = SchemaLinker(unseen_cafe_profile)
    result = linker.link_schema("What are the top 3 menu items by revenue?")
    selected = set(result["selected_tables"])

    assert "menu_items" in selected
    assert "tickets" in selected
    assert len(selected) <= 5
    assert "TABLE: menu_items" in result["schema_prompt"]
    assert "TABLE: tickets" in result["schema_prompt"]


def test_missing_metric_profit_returns_non_refusal_error(unseen_cafe_profile):
    """Asking for 'profit' on a schema with no profit/cost columns must return status 'error' with suggestions."""
    linker = SchemaLinker(unseen_cafe_profile)
    schema_info = linker.link_schema("Show branches ranked by highest profit")

    sql_gen = SQLGenerator(api_key="test-key", model="openai/gpt-oss-120b")
    sql_gen.client = MagicMock()

    result = sql_gen.generate_sql(
        question="Show branches ranked by highest profit",
        schema_prompt=schema_info["schema_prompt"],
        dialect="sqlite",
    )

    assert result["status"] == "error"
    assert result["status"] != "refused"
    assert result["refusal"] is False
    assert result["is_safe"] is False
    assert result["sql"] is None
    assert "no profit data" in result["reasoning"].lower()
    assert "instead" in result["reasoning"].lower()
    assert "which would you like?" in result["reasoning"].lower()
    sql_gen.client.chat.completions.create.assert_not_called()


def test_summarizer_never_totals_averages():
    """Summarizer must describe highest and lowest for averages/AVG() aliases and never sum them."""
    engine = AnalyticsEngine(api_key="test-key", model="openai/gpt-oss-120b")

    df = pd.DataFrame({
        "branch_name": ["Downtown", "Midtown", "Uptown"],
        "avg_tip": [75.10, 82.31, 68.00],
    })
    sql = "SELECT branch_name, AVG(tip) AS avg_tip FROM tickets GROUP BY branch_name"

    # Even if a mocked LLM tries to total the averages, validator rejects it and uses the non-summable template
    bad_llm_resp = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content="Midtown leads with 82.31, totaling 225.41 across them."
                )
            )
        ]
    )
    engine.client = MagicMock()
    engine.client.chat.completions.create.return_value = bad_llm_resp

    summary = engine.generate_spoken_insight(df, "average tip per branch", sql)
    assert "total" not in summary.lower()
    assert "225.41" not in summary
    assert "midtown" in summary.lower()
    assert "82.31" in summary
    assert "uptown" in summary.lower()
    assert "68" in summary

    # Also verify SQL AVG() alias detection when column name itself does not contain 'avg'
    df_alias = pd.DataFrame({
        "branch_name": ["Downtown", "Midtown"],
        "branch_tip": [4.50, 6.25],
    })
    sql_alias = "SELECT branch_name, AVG(tip) AS branch_tip FROM tickets GROUP BY branch_name"
    template_alias = AnalyticsEngine._build_template_summary(df_alias, sql_alias)
    assert "total" not in template_alias.lower()
    assert "10.75" not in template_alias
    assert "midtown" in template_alias.lower()
    assert "downtown" in template_alias.lower()


def test_build_numeric_kpi_skips_id_and_rank_columns():
    """build_numeric_kpi must skip ID, rank, and index columns, and hide the card if none remain."""
    # Skips branch_id and sums revenue instead
    df_with_metric = pd.DataFrame({
        "branch_id": [1, 2, 3],
        "rank": [1, 2, 3],
        "branch_name": ["Downtown", "Midtown", "Uptown"],
        "revenue": [100.0, 250.5, 149.5],
    })
    kpi = build_numeric_kpi(df_with_metric)
    assert kpi == ("Sum of 3 rows shown", "500.00")

    # Only ID / rank / index numeric columns -> hide card (None)
    df_only_ids = pd.DataFrame({
        "id": [10, 20, 30],
        "branch_id": [1, 2, 3],
        "id_code": [100, 200, 300],
        "item_rank": [1, 2, 3],
        "row_index": [0, 1, 2],
        "branch_name": ["Downtown", "Midtown", "Uptown"],
    })
    assert build_numeric_kpi(df_only_ids) is None

    # ID column + non-summable avg column -> skip ID, see avg_tip is non-summable -> hide card (None)
    df_id_and_avg = pd.DataFrame({
        "branch_id": [1, 2, 3],
        "avg_tip": [4.5, 5.0, 3.5],
    })
    assert build_numeric_kpi(df_id_and_avg) is None


def test_row_listing_summary_and_kpi_hide_ids_and_qty():
    """Plain row listings must use a deterministic template without ID/tip totals and hide the KPI card."""
    df_rows = pd.DataFrame({
        "ticket_id": list(range(442, 492)),
        "branch_id": [1, 2] * 25,
        "barista_id": [1, 2] * 25,
        "item_id": [1, 2, 3, 1, 2] * 10,
        "qty": [2, 3] * 25,
        "sold_on": [f"2025-01-{(i % 28) + 1:02d}" for i in range(50)],
        "tip": [10.0] * 49 + [148.48],
    })
    sql = "SELECT ticket_id, branch_id, barista_id, item_id, qty, sold_on, tip FROM tickets LIMIT 50"

    engine = AnalyticsEngine(api_key="test-key", model="openai/gpt-oss-120b")
    engine.client = MagicMock()

    summary = engine.generate_spoken_insight(df_rows, "Show recent tickets", sql)
    engine.client.chat.completions.create.assert_not_called()
    assert "showing 50 rows" in summary.lower()
    assert "2025-01-01" in summary
    assert "2025-01-28" in summary
    assert "tip" not in summary.lower()
    assert "$" not in summary
    assert "491" not in summary

    # KPI card must be hidden (never sums ticket_id or qty, and hides >20-row plain listings)
    assert build_numeric_kpi(df_rows) is None

    # Short row listing with qty must also hide KPI card
    assert build_numeric_kpi(df_rows.head(5)) is None


def test_count_result_states_count_without_currency_sign():
    """A COUNT query must state the count and never attach a currency symbol."""
    df_count = pd.DataFrame({"ticket_count": [491]})
    sql = "SELECT COUNT(*) AS ticket_count FROM tickets"

    engine = AnalyticsEngine(api_key="test-key", model="openai/gpt-oss-120b")
    # Even if a mocked LLM mistakenly adds a dollar sign, validator rejects it and uses clean template
    engine.client = MagicMock()
    engine.client.chat.completions.create.return_value = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="There are $491 tickets."))]
    )

    summary = engine.generate_spoken_insight(df_count, "How many tickets are there?", sql)
    assert "491" in summary
    assert "$" not in summary
    assert "dollar" not in summary.lower()
