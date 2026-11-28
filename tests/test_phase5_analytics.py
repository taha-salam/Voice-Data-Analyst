"""
Unit and Integration tests for Phase 5: Spoken Clarification, Multi-Turn Voice Follow-ups, and Analytics.
Tests ambiguity detection, conversational SQL modification, chart recommendation, and spoken insights.
"""
import pytest
import pandas as pd
from src.config import Config
from src.db.connector import DatabaseManager
from src.db.profiler import DatabaseProfiler
from src.nlp.schema_linker import SchemaLinker
from src.nlp.sql_generator import SQLGenerator
from src.nlp.clarification import ClarificationEngine
from src.nlp.memory import ConversationMemory
from src.nlp.summarizer import AnalyticsEngine
from src.voice.tts import LocalTTS

@pytest.fixture(scope="module")
def setup_phase5():
    Config.ensure_directories()
    db_mgr = DatabaseManager()
    olist_src = db_mgr.register_sqlite("olist", str(Config.OLIST_DB_PATH))
    profile = DatabaseProfiler(olist_src).profile(sample_limit=5)
    linker = SchemaLinker(profile)
    sql_gen = SQLGenerator()
    clarifier = ClarificationEngine()
    memory = ConversationMemory()
    analytics = AnalyticsEngine()
    tts = LocalTTS()
    
    return {
        "olist_src": olist_src,
        "linker": linker,
        "sql_gen": sql_gen,
        "clarifier": clarifier,
        "memory": memory,
        "analytics": analytics,
        "tts": tts,
        "profile": profile
    }

def test_clarification_engine_detects_ambiguity(setup_phase5):
    """Verify that underspecified queries trigger a spoken clarifying question."""
    clarifier = setup_phase5["clarifier"]
    
    # 1. Ambiguous query: "show me top customers" (no metric)
    res1 = clarifier.evaluate_ambiguity("show me top customers")
    assert res1["needs_clarification"] is True
    assert "clarification_prompt" in res1
    assert "spend" in res1["clarification_prompt"].lower() or "orders" in res1["clarification_prompt"].lower()
    print(f"\nAmbiguous Query: 'show me top customers'")
    print(f"Spoken Clarification: '{res1['clarification_prompt']}'")
    
    # 2. Ambiguous query: "top products"
    res2 = clarifier.evaluate_ambiguity("who are the top products")
    assert res2["needs_clarification"] is True

    # 3. Typo-tolerant ambiguous query: "show me the top cutomers"
    res_typo = clarifier.evaluate_ambiguity("show me the top cutomers")
    assert res_typo["needs_clarification"] is True
    assert "spend" in res_typo["clarification_prompt"].lower() or "orders" in res_typo["clarification_prompt"].lower()
    
    # 4. Unambiguous query: "top 5 products by revenue"
    res3 = clarifier.evaluate_ambiguity("top 5 products by revenue")
    assert res3["needs_clarification"] is False
    
    # 5. Resolve clarification with 'both' and default limit 10
    resolved_both = clarifier.resolve_clarification("show me top customers", "give me both")
    assert "top 10" in resolved_both.lower()
    assert "total spend and total number of orders" in resolved_both.lower()

    # 6. Resolve clarification with user spoken answer
    resolved = clarifier.resolve_clarification("show me top customers", "by total spend")
    assert "top 10" in resolved.lower()
    assert "total spend" in resolved.lower()
    print(f"Resolved Question: '{resolved}'")

def test_conversational_voice_followups(setup_phase5):
    """Verify multi-turn voice follow-ups modify the previous query instead of starting over."""
    olist_src = setup_phase5["olist_src"]
    linker = setup_phase5["linker"]
    sql_gen = setup_phase5["sql_gen"]
    memory = setup_phase5["memory"]
    
    # Turn 1: Initial query
    q1 = "What is the total revenue by product category?"
    s1 = linker.link_schema(q1)
    r1 = sql_gen.generate_sql(q1, s1["schema_prompt"], dialect="sqlite")
    assert r1["sql"] is not None
    
    df1, _ = olist_src.execute_query(r1["sql"])
    assert not df1.empty
    memory.add_turn(q1, r1["sql"], "olist", len(df1))
    
    print(f"\nTurn 1 Question: {q1}")
    print(f"Turn 1 SQL:      {r1['sql']}")
    
    # Turn 2: Voice Follow-up: "now break it down by month"
    q2 = "now break it down by month"
    assert memory.is_followup(q2) is True
    
    s2 = linker.link_schema(f"{q1} {q2}")
    r2 = memory.generate_followup_sql(q2, s2["schema_prompt"], dialect="sqlite")
    
    assert r2["is_safe"] is True, f"Followup SQL failed safety check: {r2}"
    assert r2["sql"] is not None
    print(f"Turn 2 Follow-up: '{q2}'")
    print(f"Turn 2 SQL:       {r2['sql']}")
    
    # Verify execution of modified query
    df2, _ = olist_src.execute_query(r2["sql"])
    assert not df2.empty
    # Must have grouped by month or date
    assert any(term in r2["sql"].lower() for term in ["strftime", "month", "order_purchase_timestamp"])

def test_analytics_visualization_recommendation():
    """Verify automatic chart selection matches dataset structure."""
    # 1. Time Series -> Line Chart
    df_time = pd.DataFrame({
        "month": ["2023-01", "2023-02", "2023-03"],
        "revenue": [12000.5, 15500.0, 18900.2]
    })
    rec1 = AnalyticsEngine.recommend_visualization(df_time)
    assert rec1["chart_type"] == "line"
    assert rec1["show_chart"] is True
    assert rec1["x"] == "month"
    
    # 2. Categorical vs Numerical -> Bar Chart
    df_cat = pd.DataFrame({
        "category": ["electronics", "furniture", "toys", "health"],
        "units": [450, 280, 150, 95]
    })
    rec2 = AnalyticsEngine.recommend_visualization(df_cat)
    assert rec2["chart_type"] == "bar"
    assert rec2["show_chart"] is True
    
    # 3. Single Metric -> Metric Card
    df_scalar = pd.DataFrame({"total_customers": [500]})
    rec3 = AnalyticsEngine.recommend_visualization(df_scalar)
    assert rec3["chart_type"] == "metric"
    assert rec3["show_chart"] is False

def test_spoken_insight_generation_and_audio_synthesis(setup_phase5):
    """Verify statistical insight generation for audio listening and synthesis with LocalTTS."""
    analytics = setup_phase5["analytics"]
    tts = setup_phase5["tts"]
    
    df_monthly = pd.DataFrame({
        "order_month": ["January", "February", "March", "April"],
        "total_sales": [32000.0, 34500.0, 52000.0, 31000.0]
    })
    
    question = "Show monthly sales for the first four months"
    sql = "SELECT order_month, sum(sales) FROM orders GROUP BY order_month"
    
    spoken_summary = analytics.generate_spoken_insight(df_monthly, question, sql)
    
    print(f"\nGenerated Spoken Insight: '{spoken_summary}'")
    assert len(spoken_summary) > 10
    # Must highlight key facts (e.g. March or peak or 52000)
    assert any(term in spoken_summary.lower() for term in ["march", "52", "peak", "highest", "total", "sales", "149"])
    
    # Synthesize to audio file using local TTS
    audio_path, latency = tts.synthesize_to_file(spoken_summary)
    assert audio_path != ""
    assert latency > 0.0
    print(f"Synthesized Audio Path: {audio_path} ({latency:.2f}s)")


def test_empty_content_with_reasoning_uses_template_fallback():
    """A mocked response with empty content and planning text in reasoning must use the template summary."""
    from types import SimpleNamespace
    from unittest.mock import MagicMock

    engine = AnalyticsEngine(api_key="test-key", model="openai/gpt-oss-120b")
    mock_message = SimpleNamespace(
        content="",
        reasoning="We need to produce one punchy sentence under 20 words... Let's craft:",
    )
    mock_response = SimpleNamespace(choices=[SimpleNamespace(message=mock_message)])
    engine.client = MagicMock()
    engine.client.chat.completions.create.return_value = mock_response

    df = pd.DataFrame({
        "category": ["electronics", "furniture", "toys"],
        "revenue": [52000.5, 34500.0, 13500.0],
    })
    sql = "SELECT category, SUM(revenue) AS revenue FROM sales GROUP BY category ORDER BY revenue DESC LIMIT 3"

    summary = engine.generate_spoken_insight(df, "Top 3 categories by revenue", sql)

    # Verify Groq call parameters for gpt-oss models
    call_kwargs = engine.client.chat.completions.create.call_args.kwargs
    assert call_kwargs["max_tokens"] == 400
    assert call_kwargs["reasoning_effort"] == "low"
    assert call_kwargs["include_reasoning"] is False

    # Verify reasoning text is never spoken and template fallback is used
    assert "we need" not in summary.lower()
    assert "let's craft" not in summary.lower()
    assert summary == (
        "Among the top 3 results, electronics leads with 52,000.50. "
        "The rows shown total 100,000.50."
    )


def test_summary_validator_rejects_invalid_and_accepts_valid():
    """Verify the spoken summary validator enforces length, banned phrases, and terminal punctuation."""
    assert AnalyticsEngine._is_valid_summary("March led the four months with 52,000 in sales.") is True
    assert AnalyticsEngine._is_valid_summary("Sales peaked in March!") is True
    assert AnalyticsEngine._is_valid_summary("Did March lead with 52,000?") is True

    # Empty or whitespace
    assert AnalyticsEngine._is_valid_summary("") is False
    assert AnalyticsEngine._is_valid_summary("   ") is False

    # Longer than 40 words
    long_text = " ".join(["word"] * 41) + "."
    assert AnalyticsEngine._is_valid_summary(long_text) is False

    # Banned phrases (case-insensitive)
    assert AnalyticsEngine._is_valid_summary("We need to explain March sales.") is False
    assert AnalyticsEngine._is_valid_summary("Let's craft a quick answer.") is False
    assert AnalyticsEngine._is_valid_summary("This MUST BE UNDER twenty words.") is False
    assert AnalyticsEngine._is_valid_summary("The user asked about March.") is False
    assert AnalyticsEngine._is_valid_summary("Summarizing the top rows shows March.") is False

    # Missing terminal punctuation (e.g., cut off mid-sentence)
    assert AnalyticsEngine._is_valid_summary("March led the four months with 52,000") is False


def test_summarizer_does_not_praise_leader_when_all_metrics_are_zero_or_null():
    """When ranked results have all zero or null metric values, summarizer must not claim a leader."""
    from unittest.mock import MagicMock

    engine = AnalyticsEngine(api_key="test-key", model="openai/gpt-oss-120b")
    engine.client = MagicMock()

    df_zeros = pd.DataFrame({
        "customer_id": ["cust_1", "cust_2", "cust_3"],
        "spend": [0.0, 0.0, 0.0],
    })
    sql = "SELECT customer_id, SUM(payment_value) AS spend FROM customers GROUP BY customer_id ORDER BY spend DESC LIMIT 3"

    summary_zeros = engine.generate_spoken_insight(df_zeros, "top 3 customers by spend", sql)
    assert "leads" not in summary_zeros.lower()
    assert "cust_1" not in summary_zeros.lower()
    assert "no spend values" in summary_zeros.lower()
    assert "incomplete" in summary_zeros.lower()
    engine.client.chat.completions.create.assert_not_called()

    df_nulls = pd.DataFrame({
        "customer_id": ["cust_1", "cust_2"],
        "spend": [None, None],
    })
    summary_nulls = engine.generate_spoken_insight(df_nulls, "top 2 customers by spend", sql)
    assert "leads" not in summary_nulls.lower()
    assert "cust_1" not in summary_nulls.lower()
    assert "no spend values" in summary_nulls.lower()


def test_followup_detection_rejects_standalone_and_cross_source_but_keeps_references():
    """Standalone questions and cross-source queries must not be follow-ups; explicit references must be."""
    memory = ConversationMemory(api_key="test-key", model="openai/gpt-oss-120b")
    memory.add_turn(
        question="Which branch sold the most?",
        sql="SELECT branch_name, SUM(qty) FROM tickets GROUP BY branch_name",
        source_name="cafe_db",
        row_count=3,
    )

    # Standalone questions after an unrelated turn must NOT be follow-ups
    assert memory.is_followup("total revenue by category?") is False
    assert memory.is_followup("What is the total revenue by category?") is False
    assert memory.is_followup("top 10 customers by spend") is False

    # Explicit reference follow-up on the same source MUST still be a follow-up
    assert memory.is_followup("now break it down by month") is True
    assert memory.is_followup("now break it down by month", current_source="cafe_db") is True
    assert memory.is_followup("same for last year", current_source="cafe_db") is True
    assert memory.is_followup("by month", current_source="cafe_db") is True

    # Cross-source query must NOT be a follow-up even if it contains a reference word
    assert memory.is_followup("now break it down by month", current_source="olist") is False
