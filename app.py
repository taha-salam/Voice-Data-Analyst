"""
Voice Data Analyst - Executive Business Intelligence Workspace
Natural Language & Local Voice Interface for Multi-Engine Relational Databases.
"""
import os
import time
import base64
import hashlib
import html
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from pathlib import Path

# Project internal imports
from src.config import Config
from src.db.connector import DatabaseManager, DatabaseSource
from src.db.profiler import DatabaseProfiler
from src.nlp.domain_corrector import DomainWordCorrector
from src.nlp.schema_linker import SchemaLinker, MultiSourceRouter
from src.nlp.sql_generator import SQLGenerator
from src.nlp.guardrails import SafetyGuardrail
from src.nlp.self_repair import SelfRepairEngine
from src.nlp.clarification import ClarificationEngine
from src.nlp.memory import ConversationMemory
from src.nlp.summarizer import AnalyticsEngine
from src.voice.stt import LocalSTT
from src.voice.tts import LocalTTS
from src.utils.latency_tracker import LatencyTracker
from src.ui.styles import get_app_css
from src.ui.components import (
    build_numeric_kpi,
    extract_sql_tables,
    format_total_metric_label,
    get_engine_badge_html,
    get_source_one_line_description,
    render_empty_state,
    render_header,
    render_history_section,
    render_kpi_cards,
    render_performance_panel,
    render_plotly_chart,
    render_routing_banner,
    render_transcript_comparison,
    test_uri_connection,
)

# ---------------------------------------------------------
# Page Configuration
# ---------------------------------------------------------
st.set_page_config(
    page_title="Voice Data Analyst",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling: Clean, Minimalist Enterprise Theme without Icon Collision
st.markdown(get_app_css(), unsafe_allow_html=True)


# ---------------------------------------------------------
# Resource Initializers (Cached)
# ---------------------------------------------------------
@st.cache_resource(show_spinner=False)
def initialize_system():
    Config.ensure_directories()
    
    # 1. Initialize Database Manager & Register Default Sources
    db_mgr = DatabaseManager()
    
    # Primary: Olist Brazilian E-Commerce
    if Config.OLIST_DB_PATH.exists():
        db_mgr.register_sqlite("olist", str(Config.OLIST_DB_PATH), "Olist Brazilian E-Commerce")
    else:
        from src.db.seed_data import seed_olist_database
        seed_olist_database(Config.OLIST_DB_PATH)
        db_mgr.register_sqlite("olist", str(Config.OLIST_DB_PATH), "Olist Brazilian E-Commerce")
        
    # Secondary: Inventory & Warehouses
    if Config.SECONDARY_DB_PATH.exists():
        db_mgr.register_sqlite("inventory", str(Config.SECONDARY_DB_PATH), "Warehouse & Inventory")
    else:
        from src.db.seed_data import seed_secondary_database
        seed_secondary_database(Config.SECONDARY_DB_PATH)
        db_mgr.register_sqlite("inventory", str(Config.SECONDARY_DB_PATH), "Warehouse & Inventory")

    # Sample CSV: Sales Representatives (via DuckDB)
    csv_file = Config.DATA_DIR / "sample_csvs" / "sales_representatives.csv"
    if csv_file.exists():
        db_mgr.register_csv("sales_csv", str(csv_file), "sales_reps", "Sales Representatives CSV")

    # 2. Extract Profiles
    profiles = {}
    for name, src in db_mgr.sources.items():
        profiler = DatabaseProfiler(src)
        profiles[name] = profiler.profile(sample_limit=8)

    # 3. Dynamic Domain Word Corrector
    corrector = DomainWordCorrector()
    for name, src in db_mgr.sources.items():
        corrector.harvest_from_database(src)

    # 4. Voice Engines
    stt_engine = LocalSTT(model_size=Config.WHISPER_MODEL_SIZE, device="cpu", compute_type="int8")
    tts_engine = LocalTTS(voice_speed=180)

    # 5. NLP & SQL Engines
    sql_generator = SQLGenerator()
    repair_engine = SelfRepairEngine()
    clarification_engine = ClarificationEngine()
    analytics_engine = AnalyticsEngine()
    router = MultiSourceRouter(db_mgr)

    return {
        "db_mgr": db_mgr,
        "profiles": profiles,
        "corrector": corrector,
        "stt": stt_engine,
        "tts": tts_engine,
        "sql_gen": sql_generator,
        "repair": repair_engine,
        "clarifier": clarification_engine,
        "analytics": analytics_engine,
        "router": router
    }

# Load engines
engines = initialize_system()
db_mgr = engines["db_mgr"]
profiles = engines["profiles"]
corrector = engines["corrector"]
stt_engine = engines["stt"]
tts_engine = engines["tts"]
sql_generator = engines["sql_gen"]
repair_engine = engines["repair"]
clarification_engine = engines["clarifier"]
analytics_engine = engines["analytics"]
router = engines["router"]

# Session State for History & Memory
if "memory" not in st.session_state:
    st.session_state.memory = ConversationMemory()
if "clarification_state" not in st.session_state:
    st.session_state.clarification_state = None
if "selected_query" not in st.session_state:
    st.session_state.selected_query = ""
if "query_history" not in st.session_state:
    st.session_state.query_history = []
if "pending_query" not in st.session_state:
    st.session_state.pending_query = None
if "last_audio_hash" not in st.session_state:
    st.session_state.last_audio_hash = None
if "last_clarify_audio_hash" not in st.session_state:
    st.session_state.last_clarify_audio_hash = None
if "last_result" not in st.session_state:
    st.session_state.last_result = None
if "uri_test_result" not in st.session_state:
    st.session_state.uri_test_result = None


# ---------------------------------------------------------
# Sidebar: Connected Data Sources (Clean, No Collisions)
# ---------------------------------------------------------
with st.sidebar:
    st.markdown("### Data Sources")
    st.caption("Connected database engines")

    sources_list = db_mgr.list_sources()
    if not sources_list:
        st.info("No data sources connected. Upload a file or connect a URI below.")

    for src in sources_list:
        src_name = src["name"]
        src_profile = profiles.get(src_name, {})
        tables = src_profile.get("tables", {})
        engine_badge = get_engine_badge_html(src["engine"])
        one_line_desc = get_source_one_line_description(src, src_profile)
        table_names = list(tables.keys())
        tables_preview = ", ".join(table_names[:4]) + ("..." if len(table_names) > 4 else "")
        table_count_label = f"{len(tables)} {'table' if len(tables) == 1 else 'tables'}"

        source_card_html = "".join(
            [
                '<div class="vda-source-card">',
                '<div class="vda-source-header">',
                f'<span class="vda-source-name">{html.escape(src_name)}</span>',
                engine_badge,
                "</div>",
                f'<div class="vda-source-desc">{html.escape(one_line_desc)}</div>',
                f'<div class="vda-source-tables">{table_count_label}: {html.escape(tables_preview) if tables_preview else "None"}</div>',
                "</div>",
            ]
        )
        st.markdown(source_card_html, unsafe_allow_html=True)
        if st.button("Remove", key=f"remove_src_{src_name}", type="tertiary"):
            db_mgr.sources.pop(src_name, None)
            profiles.pop(src_name, None)
            st.rerun()

    st.markdown("---")
    st.markdown("### Connect Source")
    up_tab, uri_tab = st.tabs(["CSV / SQLite", "Postgres URI"])

    with up_tab:
        uploaded_file = st.file_uploader("Upload CSV or SQLite (.sqlite/.db)", type=["csv", "sqlite", "db"])
        if uploaded_file is not None:
            file_name = uploaded_file.name
            safe_name = Path(file_name).stem.lower().replace("-", "_").replace(" ", "_")
            save_path = Config.DATA_DIR / file_name

            if not save_path.exists():
                with open(save_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())

                if file_name.endswith(".csv"):
                    db_mgr.register_csv(f"csv_{safe_name}", str(save_path), safe_name, f"Uploaded CSV: {file_name}")
                else:
                    db_mgr.register_sqlite(safe_name, str(save_path), f"Uploaded SQLite DB: {file_name}")

                new_src = db_mgr.get_source(safe_name if not file_name.endswith(".csv") else "csv_duckdb")
                if new_src:
                    profiles[new_src.name] = DatabaseProfiler(new_src).profile(sample_limit=5)
                    corrector.harvest_from_database(new_src)
                    st.success(f"Connected '{file_name}'")
                    st.rerun()

    with uri_tab:
        new_uri = st.text_input("Connection URI", placeholder="postgresql://user:pass@localhost:5432/mydb")
        new_name = st.text_input("Identifier", placeholder="pg_analytics")
        new_desc = st.text_input("Description (optional)", placeholder="Production sales database")

        btn_test_col, btn_conn_col = st.columns(2)
        with btn_test_col:
            if st.button("Test connection", use_container_width=True):
                ok, msg = test_uri_connection(new_uri)
                st.session_state.uri_test_result = (ok, msg)
        with btn_conn_col:
            if st.button("Connect URI", type="primary", use_container_width=True):
                if new_uri and new_name:
                    try:
                        if new_uri.startswith("sqlite"):
                            registered = db_mgr.register_sqlite(
                                new_name.strip(),
                                new_uri.replace("sqlite:///", "", 1),
                                description=new_desc.strip(),
                            )
                        else:
                            registered = db_mgr.register_postgres(
                                new_name.strip(),
                                new_uri.strip(),
                                description=new_desc.strip(),
                            )
                        profiles[registered.name] = DatabaseProfiler(registered).profile(sample_limit=5)
                        corrector.harvest_from_database(registered)
                        st.session_state.uri_test_result = None
                        st.success(f"Connected to '{registered.name}'")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Connection error: {e}")
                else:
                    st.warning("Enter both a connection URI and an identifier.")

        if st.session_state.uri_test_result is not None:
            ok, msg = st.session_state.uri_test_result
            if ok:
                st.success(msg)
            else:
                st.error(msg)


# ---------------------------------------------------------
# Main Page Header & Query Studio
# ---------------------------------------------------------
render_header()

# Example Questions (Using native pills without button text truncation)
st.markdown('<div class="vda-section-label">Try an example</div>', unsafe_allow_html=True)
prompt_mapping = {
    "Total Revenue by Category": "What is the total revenue by product category?",
    "Sales in Sao Paulo (Phonetic Test)": "What was the total revenue in san paulo?",
    "Low Stock Products (Inventory DB)": "Which products in the inventory have stock quantity less than 50?",
    "Sales Representative Quotas (CSV)": "List all sales representatives and their target quotas",
    "Security Attack Test (Refusal)": "DROP TABLE customers;"
}

selected_pill = st.pills(
    "Example Questions",
    options=list(prompt_mapping.keys()),
    selection_mode="single",
    label_visibility="collapsed"
)

if selected_pill:
    st.session_state.selected_query = prompt_mapping[selected_pill]

# Query Input Container
with st.container(border=True):
    tab_voice, tab_text = st.tabs(["Voice Input", "Text Query"])

    audio_val = None
    with tab_voice:
        st.markdown('<div class="vda-card-label" style="margin-bottom:4px;">Speak Your Question</div>', unsafe_allow_html=True)
        st.caption("Click the microphone to record. Speech is transcribed locally with faster-whisper.")
        audio_val = st.audio_input("Record question", label_visibility="collapsed")

    text_val = ""
    ask_button = False
    with tab_text:
        st.caption("Type a business question or pick an example above.")
        text_col1, text_col2 = st.columns([5, 1])
        with text_col1:
            text_val = st.text_input(
                "Type question",
                value=st.session_state.selected_query,
                placeholder="e.g. Which product category had the highest sales revenue?",
                label_visibility="collapsed"
            )
        with text_col2:
            ask_button = st.button("Run Query", type="primary", use_container_width=True)


# ---------------------------------------------------------
# Ambiguity Clarification Modal
# ---------------------------------------------------------
if st.session_state.clarification_state:
    c_state = st.session_state.clarification_state
    clarify_html = "".join(
        [
            '<div class="vda-clarify-card">',
            '<div class="vda-card-label">Clarification Needed</div>',
            f"<div>{html.escape(c_state['prompt'])}</div>",
            "</div>",
        ]
    )
    st.markdown(clarify_html, unsafe_allow_html=True)

    if "audio_path" in c_state and c_state["audio_path"] and os.path.exists(c_state["audio_path"]):
        st.audio(c_state["audio_path"], format="audio/wav", autoplay=True)

    cl_voice_col, cl_text_col = st.columns([1, 2])
    with cl_voice_col:
        st.caption("Answer by voice")
        clarify_audio = st.audio_input(
            "Speak clarification",
            key="clarification_audio_input",
            label_visibility="collapsed",
        )
        if clarify_audio is not None:
            c_bytes = clarify_audio.getvalue()
            c_hash = hashlib.md5(c_bytes).hexdigest()
            if c_hash != st.session_state.last_clarify_audio_hash:
                st.session_state.last_clarify_audio_hash = c_hash
                with st.spinner("Transcribing clarification..."):
                    c_stt = stt_engine.transcribe_audio_bytes(c_bytes)
                    spoken_answer = (c_stt.get("text") or "").strip()
                if spoken_answer:
                    resolved_question = clarification_engine.resolve_clarification(
                        c_state["original_question"], spoken_answer
                    )
                    st.session_state.clarification_state = None
                    st.session_state.selected_query = resolved_question
                    st.session_state.pending_query = {
                        "text": resolved_question,
                        "is_voice": True,
                        "skip_ambiguity": True,
                    }
                    st.rerun()
                else:
                    st.warning("No speech detected. Try speaking again or type your answer.")

    with cl_text_col:
        st.caption("Or type your answer")
        txt_col, btn_col, cancel_col = st.columns([3, 1, 1])
        with txt_col:
            clarification_response = st.text_input(
                "Clarification response",
                placeholder="e.g. by total spend or by order volume",
                label_visibility="collapsed",
            )
        with btn_col:
            if st.button("Submit", type="primary", use_container_width=True):
                if clarification_response.strip():
                    resolved_question = clarification_engine.resolve_clarification(
                        c_state["original_question"], clarification_response.strip()
                    )
                    st.session_state.clarification_state = None
                    st.session_state.selected_query = resolved_question
                    st.session_state.pending_query = {
                        "text": resolved_question,
                        "is_voice": bool(c_state.get("is_voice", False)),
                        "skip_ambiguity": True,
                    }
                    st.rerun()
        with cancel_col:
            if st.button("Cancel", use_container_width=True):
                st.session_state.clarification_state = None
                st.rerun()


# ---------------------------------------------------------
# Query Execution Engine
# ---------------------------------------------------------
pending_job = st.session_state.pending_query
new_voice_bytes = None
if audio_val is not None:
    audio_bytes_candidate = audio_val.getvalue()
    audio_hash = hashlib.md5(audio_bytes_candidate).hexdigest()
    if audio_hash != st.session_state.last_audio_hash:
        new_voice_bytes = audio_bytes_candidate
        st.session_state.last_audio_hash = audio_hash

text_submitted = ask_button and bool(text_val.strip() or st.session_state.selected_query.strip())
should_run = (pending_job is not None) or (new_voice_bytes is not None) or text_submitted

if should_run and not st.session_state.clarification_state:
    st.session_state.pending_query = None
    tracker = LatencyTracker()
    raw_query = ""
    is_voice_query = False
    skip_ambiguity = False

    with st.status("Running query...", expanded=True) as status:
        # 1. Local Speech-to-Text (faster-whisper)
        if pending_job is not None:
            raw_query = pending_job["text"].strip()
            is_voice_query = bool(pending_job.get("is_voice", False))
            skip_ambiguity = bool(pending_job.get("skip_ambiguity", False))
        elif new_voice_bytes is not None:
            is_voice_query = True
            status.update(label="Transcribing...")
            st.write("Transcribing")
            with tracker.time_stage("Local ASR"):
                stt_result = stt_engine.transcribe_audio_bytes(new_voice_bytes)
                raw_query = stt_result.get("text", "").strip()
        else:
            raw_query = text_val.strip() if text_val.strip() else st.session_state.selected_query.strip()

        if not raw_query:
            status.update(label="No question detected", state="error", expanded=False)
            st.session_state.last_result = {
                "kind": "info",
                "message": "Please speak into the microphone or enter a question above.",
            }
        elif not db_mgr.list_sources():
            status.update(label="No data sources connected", state="error", expanded=False)
            st.session_state.last_result = {
                "kind": "db_error",
                "raw_query": raw_query,
                "corrected_query": raw_query,
                "corrections_log": [],
                "is_voice": is_voice_query,
                "message": "No data sources are connected. Connect a database or upload a file in the sidebar.",
            }
        else:
            # 2. Phonetic Domain Word Correction
            status.update(label="Correcting...")
            st.write("Correcting")
            with tracker.time_stage("Domain Word Correction"):
                corrected_query, corrections_log = corrector.correct_transcript(raw_query)

            final_question = corrected_query

            # 3. Spoken Clarification Engine
            needs_clarification = False
            if not skip_ambiguity:
                with tracker.time_stage("Ambiguity Check"):
                    ambiguity_eval = clarification_engine.evaluate_ambiguity(final_question)
                needs_clarification = bool(ambiguity_eval.get("needs_clarification"))

            if needs_clarification:
                clarifying_prompt = ambiguity_eval["clarification_prompt"]
                status.update(label="Speaking clarification...")
                st.write("Speaking")
                audio_path, _ = tts_engine.synthesize_to_file(clarifying_prompt)
                st.session_state.clarification_state = {
                    "original_question": final_question,
                    "prompt": clarifying_prompt,
                    "audio_path": audio_path,
                    "is_voice": is_voice_query,
                }
                st.rerun()

            # 4. Multi-Source Routing
            status.update(label="Routing...")
            st.write("Routing")
            with tracker.time_stage("Source Routing"):
                target_source_name = router.route_query(final_question, profiles)
                db_source = db_mgr.get_source(target_source_name)

            if not db_source:
                status.update(label="Data source not found", state="error", expanded=False)
                st.session_state.last_result = {
                    "kind": "db_error",
                    "raw_query": raw_query,
                    "corrected_query": corrected_query,
                    "corrections_log": corrections_log,
                    "is_voice": is_voice_query,
                    "message": f"Could not locate registered data source for '{target_source_name}'.",
                }
            else:
                dialect = "sqlite" if db_source.engine_type in ("sqlite", "duckdb", "csv") else "postgres"
                target_profile = profiles.get(target_source_name, {})

                # 5. Schema Linking & Dynamic FK Bridging
                with tracker.time_stage("Schema Linking"):
                    linker = SchemaLinker(target_profile)
                    schema_info = linker.link_schema(final_question)
                    schema_prompt = schema_info["schema_prompt"]

                # 6. Conversational Memory & Multi-turn Follow-up
                is_followup = st.session_state.memory.is_followup(final_question)
                last_turn = st.session_state.memory.get_last_turn() if is_followup else None
                previous_sql = last_turn.sql if last_turn else None

                status.update(label="Generating SQL...")
                st.write("Generating SQL")
                with tracker.time_stage("SQL Generation"):
                    if is_followup:
                        try:
                            sql_res = st.session_state.memory.generate_followup_sql(
                                followup_question=final_question,
                                schema_prompt=schema_prompt,
                                dialect=dialect,
                            )
                            if sql_res.get("previous_sql"):
                                previous_sql = sql_res["previous_sql"]
                        except Exception as exc:
                            sql_res = {
                                "sql": None,
                                "reasoning": f"LLM Generation Error: {exc}",
                                "is_safe": False,
                                "refusal": False,
                            }
                    else:
                        sql_res = sql_generator.generate_sql(
                            question=final_question,
                            schema_prompt=schema_prompt,
                            dialect=dialect,
                        )

                reasoning_text = str(sql_res.get("reasoning") or "")
                is_llm_error = "LLM Generation Error" in reasoning_text

                # 7. Zero-Trust Security Validation & Attack Refusal vs LLM Generation Error
                if is_llm_error:
                    status.update(label="Could not generate a query", state="error", expanded=False)
                    st.session_state.last_result = {
                        "kind": "llm_error",
                        "raw_query": raw_query,
                        "corrected_query": corrected_query,
                        "corrections_log": corrections_log,
                        "is_voice": is_voice_query,
                        "source_name": target_source_name,
                        "engine_type": db_source.engine_type,
                        "source_description": db_source.description,
                        "tables_used": schema_info.get("selected_tables", []),
                        "is_followup": is_followup,
                        "message": reasoning_text,
                        "timings": dict(tracker.timings),
                    }
                elif sql_res.get("refusal") or not sql_res.get("is_safe"):
                    refusal_detail = reasoning_text or "Unsafe statement blocked by guardrail. Read-only SELECT statements only."
                    refusal_speech = "I cannot run that query because only read-only SELECT queries are allowed."
                    status.update(label="Speaking...")
                    st.write("Speaking")
                    with tracker.time_stage("Local TTS"):
                        refusal_audio_path, _ = tts_engine.synthesize_to_file(refusal_speech)
                    status.update(label="Query refused by safety guardrail", state="error", expanded=False)
                    st.session_state.last_result = {
                        "kind": "refusal",
                        "raw_query": raw_query,
                        "corrected_query": corrected_query,
                        "corrections_log": corrections_log,
                        "is_voice": is_voice_query,
                        "source_name": target_source_name,
                        "engine_type": db_source.engine_type,
                        "source_description": db_source.description,
                        "tables_used": schema_info.get("selected_tables", []),
                        "is_followup": is_followup,
                        "message": refusal_detail,
                        "audio_path": refusal_audio_path,
                        "autoplay": True,
                        "timings": dict(tracker.timings),
                    }
                else:
                    generated_sql = sql_res["sql"]

                    # 8. Database Execution with Autonomous Self-Repair
                    status.update(label="Running...")
                    st.write("Running")
                    with tracker.time_stage("Database Execution"):
                        exec_result = repair_engine.execute_with_repair(
                            db_source=db_source,
                            initial_sql=generated_sql,
                            user_question=final_question,
                            schema_prompt=schema_prompt,
                            dialect=dialect,
                        )

                    if not exec_result["success"]:
                        status.update(label="Database execution error", state="error", expanded=False)
                        st.session_state.last_result = {
                            "kind": "db_error",
                            "raw_query": raw_query,
                            "corrected_query": corrected_query,
                            "corrections_log": corrections_log,
                            "is_voice": is_voice_query,
                            "source_name": target_source_name,
                            "engine_type": db_source.engine_type,
                            "source_description": db_source.description,
                            "tables_used": extract_sql_tables(generated_sql, dialect, schema_info.get("selected_tables", [])),
                            "is_followup": is_followup,
                            "message": f"Database Execution Error: {exec_result.get('error')}",
                            "sql": generated_sql,
                            "timings": dict(tracker.timings),
                        }
                    else:
                        df_result = exec_result["df"]
                        final_sql = exec_result["final_sql"]
                        tables_used = extract_sql_tables(final_sql, dialect, schema_info.get("selected_tables", []))

                        # Update Conversational Memory & Session History
                        st.session_state.memory.add_turn(final_question, final_sql, target_source_name, len(df_result))
                        st.session_state.query_history.append(
                            {
                                "question": final_question,
                                "source": target_source_name,
                                "sql": final_sql,
                                "row_count": len(df_result),
                                "is_followup": is_followup,
                                "previous_sql": previous_sql,
                            }
                        )

                        # 9. Analytics & Visualization Recommendation
                        status.update(label="Summarizing...")
                        st.write("Summarizing")
                        with tracker.time_stage("Visualization"):
                            chart_rec = analytics_engine.recommend_visualization(df_result)

                        # 10. Executive Spoken Insight Synthesis
                        with tracker.time_stage("Insight Generation"):
                            spoken_insight = analytics_engine.generate_spoken_insight(df_result, final_question, final_sql)

                        # 11. Local Offline TTS Audio Synthesis
                        status.update(label="Speaking...")
                        st.write("Speaking")
                        with tracker.time_stage("Local TTS"):
                            audio_path, tts_latency = tts_engine.synthesize_to_file(spoken_insight)

                        status.update(label="Query complete", state="complete", expanded=False)

                        st.session_state.last_result = {
                            "kind": "success",
                            "raw_query": raw_query,
                            "corrected_query": corrected_query,
                            "corrections_log": corrections_log,
                            "is_voice": is_voice_query,
                            "source_name": target_source_name,
                            "engine_type": db_source.engine_type,
                            "source_description": db_source.description,
                            "tables_used": tables_used,
                            "dialect": dialect,
                            "is_followup": is_followup,
                            "previous_sql": previous_sql,
                            "final_sql": final_sql,
                            "sql_reasoning": reasoning_text,
                            "attempts": exec_result.get("attempts", 1),
                            "df_result": df_result,
                            "chart_rec": chart_rec,
                            "spoken_insight": spoken_insight,
                            "audio_path": audio_path,
                            "autoplay": True,
                            "timings": dict(tracker.timings),
                            "total_latency": tracker.total_latency(),
                        }


# ---------------------------------------------------------
# Results Section (Clean, Non-Redundant)
# ---------------------------------------------------------
result = st.session_state.last_result
if result is not None:
    kind = result.get("kind")

    if kind == "info":
        st.info(result["message"])
    else:
        # Transcript / Domain Correction Display (Task 2)
        render_transcript_comparison(
            raw_query=result.get("raw_query", ""),
            corrected_query=result.get("corrected_query", ""),
            corrections_log=result.get("corrections_log", []),
            is_voice=bool(result.get("is_voice", False)),
        )

        # Routing Transparency Banner (Task 3 & 5)
        if result.get("source_name"):
            render_routing_banner(
                source_name=result["source_name"],
                engine_type=result.get("engine_type", ""),
                source_description=result.get("source_description", ""),
                tables_used=result.get("tables_used", []),
                is_followup=bool(result.get("is_followup", False)),
            )

        if kind == "llm_error":
            warning_html = "".join(
                [
                    '<div class="vda-warning-card">',
                    '<div class="vda-warning-title">Could not generate a query</div>',
                    f'<div>{html.escape(result.get("message", ""))}</div>',
                    "</div>",
                ]
            )
            st.markdown(warning_html, unsafe_allow_html=True)

        elif kind == "refusal":
            refusal_html = "".join(
                [
                    '<div class="vda-refusal-card">',
                    '<div class="vda-refusal-title">Query Refused by Safety Guardrail</div>',
                    f'<div>{html.escape(result.get("message", ""))}</div>',
                    "</div>",
                ]
            )
            st.markdown(refusal_html, unsafe_allow_html=True)
            refusal_audio = result.get("audio_path")
            if refusal_audio and os.path.exists(refusal_audio):
                st.audio(refusal_audio, format="audio/wav", autoplay=bool(result.get("autoplay", False)))
                result["autoplay"] = False

        elif kind == "db_error":
            st.error(result.get("message", "Database execution failed."))
            if result.get("sql"):
                st.code(result["sql"], language="sql")

        elif kind == "success":
            df_result = result["df_result"]
            final_sql = result["final_sql"]
            target_source_name = result["source_name"]
            dialect = result["dialect"]
            chart_rec = result["chart_rec"]
            spoken_insight = result["spoken_insight"]

            if result.get("attempts", 1) > 1:
                st.info(f"Self-repair resolved a SQL error in {result['attempts']} attempts.")

            # Executive Spoken Takeaway Card (with audio player inside)
            with st.container(border=True):
                summary_html = "".join(
                    [
                        '<div class="vda-summary-marker">',
                        '<div class="vda-card-label">Spoken Summary</div>',
                        f'<div class="vda-summary-text">"{html.escape(spoken_insight)}"</div>',
                        "</div>",
                    ]
                )
                st.markdown(summary_html, unsafe_allow_html=True)
                audio_path = result.get("audio_path")
                if audio_path and os.path.exists(audio_path):
                    st.audio(audio_path, format="audio/wav", autoplay=bool(result.get("autoplay", False)))
                    result["autoplay"] = False

            # Summary Metrics Row
            kpi_items = [
                ("Data Source", target_source_name.upper()),
                ("Rows", f"{len(df_result):,}"),
                ("Total Time", f"{result['total_latency']:.2f}s"),
            ]
            numeric_kpi = build_numeric_kpi(df_result)
            if numeric_kpi is not None:
                kpi_items.append(numeric_kpi)

            render_kpi_cards(kpi_items)

            # Data Visualization & Table Tabs
            tab_vis, tab_data, tab_sql = st.tabs(["Visualization", "Data Table", "Executed SQL"])

            with tab_vis:
                if chart_rec.get("show_chart") and not df_result.empty:
                    fig, chart_note = render_plotly_chart(df_result, chart_rec)
                    if fig is not None:
                        if chart_note:
                            st.caption(chart_note)
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.dataframe(df_result, use_container_width=True, hide_index=True)
                else:
                    st.dataframe(df_result, use_container_width=True, hide_index=True)

            with tab_data:
                st.dataframe(df_result, use_container_width=True, hide_index=True)
                csv_data = df_result.to_csv(index=False).encode("utf-8")
                st.download_button(
                    label="Export CSV",
                    data=csv_data,
                    file_name=f"{target_source_name}_query_result.csv",
                    mime="text/csv",
                )

            with tab_sql:
                if result.get("is_followup") and result.get("previous_sql"):
                    prev_col, new_col = st.columns(2)
                    with prev_col:
                        st.caption("Previous SQL")
                        st.code(result["previous_sql"], language="sql")
                    with new_col:
                        st.caption("Modified SQL (Follow-up)")
                        st.code(final_sql, language="sql")
                else:
                    st.code(final_sql, language="sql")

                sql_pills_html = "".join(
                    [
                        '<div class="vda-sql-pills">',
                        f'<span class="vda-badge-neutral">Dialect: {html.escape(dialect.upper())}</span>',
                        '<span class="vda-badge-success">Read-only SELECT verified</span>',
                        "</div>",
                    ]
                )
                st.markdown(sql_pills_html, unsafe_allow_html=True)
                if result.get("sql_reasoning"):
                    st.caption(f"Reasoning: {result['sql_reasoning']}")

            # Performance Breakdown (Module 10 Requirement)
            st.markdown('<div class="vda-section-label" style="margin-top:16px;">Performance</div>', unsafe_allow_html=True)
            render_performance_panel(result.get("timings", {}))
elif not st.session_state.clarification_state:
    render_empty_state(db_mgr.list_sources(), profiles)

# Collapsible Conversation History (Task 5)
render_history_section(st.session_state.query_history)
