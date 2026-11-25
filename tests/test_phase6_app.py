"""
Integration test for Phase 6: Streamlit Web App Initialization & Pipeline Execution.
"""
import pytest
from app import initialize_system

def test_app_initialization():
    """Verify that all core engines initialize cleanly in the web app."""
    engines = initialize_system()
    
    assert "db_mgr" in engines
    assert "profiles" in engines
    assert "corrector" in engines
    assert "stt" in engines
    assert "tts" in engines
    assert "sql_gen" in engines
    assert "repair" in engines
    assert "clarifier" in engines
    assert "analytics" in engines
    assert "router" in engines
    
    # Check data sources registered
    sources = engines["db_mgr"].list_sources()
    source_names = [s["name"] for s in sources]
    assert "olist" in source_names
    assert "inventory" in source_names
    assert "csv_duckdb" in source_names or "sales_csv" in source_names

def test_end_to_end_pipeline_simulation():
    """Simulate an end-to-end voice-to-SQL query through the entire application stack."""
    engines = initialize_system()
    
    # User raw query with misheard domain word ("san paulo")
    raw_query = "What is the total revenue in san paulo?"
    
    # 1. Domain Correction
    corrected_query, corrections = engines["corrector"].correct_transcript(raw_query)
    assert "sao paulo" in corrected_query.lower()
    
    # 2. Source Routing
    target_src = engines["router"].route_query(corrected_query, engines["profiles"])
    assert target_src == "olist"
    
    # 3. Schema Linking
    linker = engines["router"]
    from src.nlp.schema_linker import SchemaLinker
    schema_info = SchemaLinker(engines["profiles"][target_src]).link_schema(corrected_query)
    
    # 4. SQL Generation
    sql_res = engines["sql_gen"].generate_sql(
        question=corrected_query,
        schema_prompt=schema_info["schema_prompt"],
        dialect="sqlite"
    )
    assert sql_res["is_safe"] is True
    assert sql_res["sql"] is not None
    
    # 5. Database Execution with Self-Repair
    db_source = engines["db_mgr"].get_source(target_src)
    exec_res = engines["repair"].execute_with_repair(
        db_source=db_source,
        initial_sql=sql_res["sql"],
        user_question=corrected_query,
        schema_prompt=schema_info["schema_prompt"],
        dialect="sqlite"
    )
    assert exec_res["success"] is True
    assert not exec_res["df"].empty
    
    # 6. Analytics & Spoken Insight
    chart_rec = engines["analytics"].recommend_visualization(exec_res["df"])
    assert "chart_type" in chart_rec
    
    spoken_summary = engines["analytics"].generate_spoken_insight(
        df=exec_res["df"],
        question=corrected_query,
        sql=exec_res["final_sql"]
    )
    print(f"\nGenerated spoken insight in app test: {repr(spoken_summary)}")
    assert len(spoken_summary) >= 3
    
    # 7. Local TTS Audio Generation
    audio_path, latency = engines["tts"].synthesize_to_file(spoken_summary)
    assert audio_path != ""
    assert latency > 0.0
