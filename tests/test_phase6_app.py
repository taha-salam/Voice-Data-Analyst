"""
Integration test for Phase 6: Streamlit Web App Initialization & Pipeline Execution.
"""
import os
import io
import pytest
from app import initialize_system
from src.utils.latency_tracker import LatencyTracker

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

def test_audio_recording_and_latency_tracker_pipeline():
    """
    CRITICAL: Simulate the EXACT user audio microphone recording workflow
    and verify LatencyTracker.time_stage() context manager across all pipeline stages.
    """
    engines = initialize_system()
    tracker = LatencyTracker()
    
    # Generate realistic audio bytes
    test_phrase = "What is the total revenue in sao paulo?"
    temp_wav, _ = engines["tts"].synthesize_to_file(test_phrase)
    
    with open(temp_wav, "rb") as f:
        audio_bytes = f.read()
    
    if os.path.exists(temp_wav):
        os.remove(temp_wav)
        
    # 1. Simulate Local ASR with tracker.time_stage
    with tracker.time_stage("Local ASR"):
        stt_res = engines["stt"].transcribe_audio_bytes(audio_bytes)
        raw_query = stt_res["text"]
    
    assert "Local ASR" in tracker.timings
    assert tracker.timings["Local ASR"] > 0
    assert len(raw_query) > 0
    
    # 2. Domain Word Correction
    with tracker.time_stage("Domain Word Correction"):
        corrected, _ = engines["corrector"].correct_transcript(raw_query)
    
    # 3. Source Routing
    with tracker.time_stage("Source Routing"):
        target_src = engines["router"].route_query(corrected, engines["profiles"])
        
    # 4. Schema Linking
    with tracker.time_stage("Schema Linking"):
        from src.nlp.schema_linker import SchemaLinker
        schema_info = SchemaLinker(engines["profiles"][target_src]).link_schema(corrected)
        
    # 5. SQL Generation
    with tracker.time_stage("SQL Generation"):
        sql_res = engines["sql_gen"].generate_sql(
            question=corrected,
            schema_prompt=schema_info["schema_prompt"],
            dialect="sqlite"
        )
        
    # 6. Database Execution
    with tracker.time_stage("Database Execution"):
        db_source = engines["db_mgr"].get_source(target_src)
        exec_res = engines["repair"].execute_with_repair(
            db_source=db_source,
            initial_sql=sql_res["sql"],
            user_question=corrected,
            schema_prompt=schema_info["schema_prompt"],
            dialect="sqlite"
        )
    
    assert exec_res["success"] is True
    
    # 7. Visualization
    with tracker.time_stage("Visualization"):
        _ = engines["analytics"].recommend_visualization(exec_res["df"])
        
    # 8. Insight Generation
    with tracker.time_stage("Insight Generation"):
        spoken = engines["analytics"].generate_spoken_insight(exec_res["df"], corrected, exec_res["final_sql"])
        
    # 9. Local TTS
    with tracker.time_stage("Local TTS"):
        _, _ = engines["tts"].synthesize_to_file(spoken[:100])
        
    # Verify all stages recorded in LatencyTracker
    assert len(tracker.timings) == 9
    assert tracker.total_latency() > 0.0
    
    # Verify report formatting methods work without error
    table_str = tracker.format_summary_table()
    report_str = tracker.format_report()
    assert "Total End-to-End" in table_str
    assert "Total End-to-End" in report_str
    print(f"\n[LATENCY TRACKER VERIFICATION PASSED]\n{report_str}")
