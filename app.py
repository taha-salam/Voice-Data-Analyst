"""
Voice Data Analyst - Web Application
An interactive natural language and voice interface for querying databases.
"""
import os
import time
import base64
import pandas as pd
import plotly.express as px
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

# ---------------------------------------------------------
# Page Configuration
# ---------------------------------------------------------
st.set_page_config(
    page_title="Voice Data Analyst",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS Styling
st.markdown("""
<style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        margin-bottom: 0.2rem;
        color: #1E293B;
    }
    .sub-title {
        font-size: 1.05rem;
        color: #64748B;
        margin-bottom: 1.5rem;
    }
    .badge-pill {
        display: inline-block;
        padding: 0.25rem 0.6rem;
        font-size: 0.8rem;
        font-weight: 600;
        border-radius: 9999px;
        margin-right: 0.4rem;
    }
    .badge-local { background-color: #DCFCE7; color: #166534; }
    .badge-cloud { background-color: #E0E7FF; color: #3730A3; }
    .badge-safe  { background-color: #FEF3C7; color: #92400E; }
    .correction-box {
        background-color: #EFF6FF;
        border-left: 4px solid #3B82F6;
        padding: 0.75rem 1rem;
        border-radius: 4px;
        margin-bottom: 1rem;
        font-size: 0.95rem;
    }
    .security-box {
        background-color: #FEF2F2;
        border-left: 4px solid #EF4444;
        padding: 0.75rem 1rem;
        border-radius: 4px;
        margin-bottom: 1rem;
        color: #991B1B;
        font-weight: 500;
    }
    .latency-bar {
        font-family: monospace;
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        padding: 0.5rem 0.75rem;
        border-radius: 6px;
        font-size: 0.85rem;
        color: #334155;
        margin-top: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------
# Resource Initializers (Cached)
# ---------------------------------------------------------
@st.cache_resource(show_spinner="Initializing Voice Data Analyst Engines...")
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

    # Sample CSV: Sales Representatives
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
if "messages" not in st.session_state:
    st.session_state.messages = []
if "clarification_state" not in st.session_state:
    st.session_state.clarification_state = None


# ---------------------------------------------------------
# Sidebar: Multi-Source Database Manager
# ---------------------------------------------------------
with st.sidebar:
    st.image("https://img.icons8.com/isometric/100/database.png", width=64)
    st.title("Data Sources")
    st.caption("Zero-config Multi-Engine Database Connection")

    # Display Active Sources
    st.subheader("Connected Databases")
    for src in db_mgr.list_sources():
        with st.expander(f"📦 {src['name']} ({src['engine'].upper()})", expanded=False):
            st.write(f"**Path/URI:** `{src['path']}`")
            st.write(f"**Description:** {src['description']}")
            table_list = list(profiles.get(src['name'], {}).get("tables", {}).keys())
            st.write(f"**Tables ({len(table_list)}):** {', '.join(table_list)}")

    st.divider()

    # Upload New Data Source (CSV / SQLite)
    st.subheader("Add Data Source")
    upload_tab, uri_tab = st.tabs(["File Upload", "Connection URI"])

    with upload_tab:
        uploaded_file = st.file_uploader("Upload CSV or SQLite (.db/.sqlite)", type=["csv", "sqlite", "db"])
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
                
                # Re-profile and harvest
                new_src = db_mgr.get_source(safe_name if not file_name.endswith(".csv") else "csv_duckdb")
                if new_src:
                    profiles[new_src.name] = DatabaseProfiler(new_src).profile(sample_limit=5)
                    corrector.harvest_from_database(new_src)
                    st.success(f"Successfully loaded '{file_name}' into engine!")
                    st.rerun()

    with uri_tab:
        new_uri = st.text_input("Database URI", placeholder="postgresql://user:pass@localhost:5432/mydb")
        new_name = st.text_input("Source Identifier", placeholder="pg_production")
        if st.button("Connect URI"):
            if new_uri and new_name:
                try:
                    if new_uri.startswith("sqlite"):
                        db_mgr.register_sqlite(new_name, new_uri.replace("sqlite:///", ""))
                    else:
                        db_mgr.register_postgres(new_name, new_uri)
                    st.success(f"Connected to '{new_name}'!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Connection failed: {e}")

    st.divider()
    st.markdown("### System Architecture")
    st.markdown("""
    - <span class="badge-pill badge-local">Local ASR</span> `faster-whisper`
    - <span class="badge-pill badge-local">Local TTS</span> `pyttsx3 (SAPI5)`
    - <span class="badge-pill badge-cloud">LLM</span> `Groq 120B`
    - <span class="badge-pill badge-safe">Safety</span> `AST Read-Only`
    """, unsafe_allow_html=True)


# ---------------------------------------------------------
# Main UI: Voice & Text Interaction
# ---------------------------------------------------------
st.markdown('<div class="main-title">🎙️ Voice Data Analyst</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Speak natural business questions in English to query any connected database. Zero SQL required.</div>', unsafe_allow_html=True)

# Sample query quick chips
col_c1, col_c2, col_c3, col_c4 = st.columns(4)
sample_query = None
if col_c1.button("📊 Revenue by category"):
    sample_query = "What is the total revenue by product category?"
if col_c2.button("📍 Sales in Sao Paulo"):
    sample_query = "What were total sales in san paulo?"  # Intentionally misspelled to show correction
if col_c3.button("📦 Chicago warehouse stock"):
    sample_query = "How many units of gaming laptops are in the Chicago warehouse?"
if col_c4.button("🛡️ Test Attack Refusal"):
    sample_query = "DROP TABLE customers;"

# Input Section: Audio & Text
st.write("### Ask a Question")
input_col1, input_col2 = st.columns([1, 1])

with input_col1:
    audio_val = st.audio_input("Record your question with microphone:")

with input_col2:
    text_val = st.text_input("Or type your question here:", value=sample_query if sample_query else "", placeholder="e.g. Which products brought in the most revenue last quarter?")
    ask_button = st.button("Submit Question", type="primary")

# Clarification handling if pending
if st.session_state.clarification_state:
    c_state = st.session_state.clarification_state
    st.info(f"❓ **Clarification Needed:** {c_state['prompt']}")
    
    # Audio of clarifying question
    if "audio_path" in c_state:
        st.audio(c_state["audio_path"], format="audio/wav")

    cl_ans_col1, cl_ans_col2 = st.columns([3, 1])
    with cl_ans_col1:
        clarification_response = st.text_input("Your clarification response:", placeholder="e.g. by total spend / by order volume")
    with cl_ans_col2:
        if st.button("Submit Clarification"):
            if clarification_response:
                resolved_question = clarification_engine.resolve_clarification(c_state["original_question"], clarification_response)
                st.session_state.clarification_state = None
                text_val = resolved_question
                ask_button = True


# ---------------------------------------------------------
# Query Processing Pipeline
# ---------------------------------------------------------
should_run = (audio_val is not None) or (ask_button and text_val.strip())

if should_run and not st.session_state.clarification_state:
    tracker = LatencyTracker()
    raw_query = ""
    stt_latency = 0.0

    # 1. Speech Recognition (if audio input provided)
    if audio_val is not None:
        with st.spinner("Transcribing speech locally with faster-whisper..."):
            with tracker.time_stage("Local ASR"):
                audio_bytes = audio_val.read()
                stt_result = stt_engine.transcribe_audio_bytes(audio_bytes)
                raw_query = stt_result["text"]
                stt_latency = stt_result.get("latency", 0.0)
    else:
        raw_query = text_val.strip()

    if not raw_query:
        st.warning("No speech or text detected. Please speak into the mic or enter a question.")
    else:
        # Display the transcribed question
        st.markdown(f"**User Question:** *\"{raw_query}\"*")

        # 2. Domain Word Correction
        with tracker.time_stage("Domain Word Correction"):
            corrected_query, corrections_log = corrector.correct_transcript(raw_query)

        if corrections_log:
            correction_pills = []
            for c in corrections_log:
                correction_pills.append(f'<b>"{c["original"]}"</b> &rarr; <b>"{c["corrected"]}"</b> ({c["type"]})')
            st.markdown(f"""
            <div class="correction-box">
                🔍 <b>Domain Word Correction:</b> {', '.join(correction_pills)}
            </div>
            """, unsafe_allow_html=True)

        final_question = corrected_query

        # 3. Check for Spoken Clarification
        with tracker.time_stage("Ambiguity Check"):
            ambiguity_eval = clarification_engine.evaluate_ambiguity(final_question)

        if ambiguity_eval["needs_clarification"]:
            clarifying_prompt = ambiguity_eval["clarification_prompt"]
            audio_path, _ = tts_engine.synthesize_to_file(clarifying_prompt)
            st.session_state.clarification_state = {
                "original_question": final_question,
                "prompt": clarifying_prompt,
                "audio_path": audio_path
            }
            st.rerun()

        # 4. Multi-Source Routing
        with tracker.time_stage("Source Routing"):
            target_source_name = router.route_query(final_question, profiles)
            db_source = db_mgr.get_source(target_source_name)

        if not db_source:
            st.error(f"Could not locate data source for '{target_source_name}'")
        else:
            dialect = "sqlite" if db_source.engine_type in ("sqlite", "duckdb", "csv") else "postgres"
            target_profile = profiles.get(target_source_name, {})

            # 5. Schema Linking / Pruning
            with tracker.time_stage("Schema Linking"):
                linker = SchemaLinker(target_profile)
                schema_info = linker.link_schema(final_question)
                schema_prompt = schema_info["schema_prompt"]

            # 6. Check for Multi-Turn Follow-up
            is_followup = st.session_state.memory.is_followup(final_question)
            
            with tracker.time_stage("SQL Generation"):
                if is_followup:
                    st.info("🔄 Conversational follow-up detected. Modifying previous SQL query...")
                    sql_res = st.session_state.memory.generate_followup_sql(
                        followup_question=final_question,
                        schema_prompt=schema_prompt,
                        dialect=dialect
                    )
                else:
                    sql_res = sql_generator.generate_sql(
                        question=final_question,
                        schema_prompt=schema_prompt,
                        dialect=dialect
                    )

            # Check Safety / Refusal
            if sql_res.get("refusal") or not sql_res.get("is_safe"):
                st.markdown(f"""
                <div class="security-box">
                    🛡️ <b>Security Refusal:</b> {sql_res.get('reasoning', 'Destructive or unsafe query blocked by AST guardrails.')}
                </div>
                """, unsafe_allow_html=True)
            else:
                generated_sql = sql_res["sql"]

                # 7. Execute Query with Self-Repair Loop
                with tracker.time_stage("Database Execution"):
                    exec_result = repair_engine.execute_with_repair(
                        db_source=db_source,
                        initial_sql=generated_sql,
                        user_question=final_question,
                        schema_prompt=schema_prompt,
                        dialect=dialect
                    )

                if not exec_result["success"]:
                    st.error(f"Execution Error: {exec_result.get('error')}")
                else:
                    df_result = exec_result["df"]
                    final_sql = exec_result["final_sql"]

                    # If query was repaired, show badge
                    if exec_result.get("attempts", 1) > 1:
                        st.warning(f"⚠️ Query was self-repaired in {exec_result['attempts']} attempts to fix syntax/column mismatch.")

                    # Record in Conversational Memory
                    st.session_state.memory.add_turn(final_question, final_sql, target_source_name, len(df_result))

                    # 8. Analytics & Chart Recommendation
                    with tracker.time_stage("Visualization"):
                        chart_rec = analytics_engine.recommend_visualization(df_result)

                    # 9. Spoken Executive Insight Generation
                    with tracker.time_stage("Insight Generation"):
                        spoken_insight = analytics_engine.generate_spoken_insight(df_result, final_question, final_sql)

                    # 10. Local Text-to-Speech Synthesis
                    with tracker.time_stage("Local TTS"):
                        audio_path, tts_latency = tts_engine.synthesize_to_file(spoken_insight)

                    # ---------------------------------------------------------
                    # Display Results Section
                    # ---------------------------------------------------------
                    st.divider()

                    # Spoken Insight Banner with Audio Player
                    st.markdown("### 📢 Spoken Executive Summary")
                    st.info(f"**{spoken_insight}**")
                    if os.path.exists(audio_path):
                        st.audio(audio_path, format="audio/wav", autoplay=True)

                    # Visualization & Table Display
                    st.markdown("### 📊 Query Results")
                    res_col1, res_col2 = st.columns([3, 2])

                    with res_col1:
                        if chart_rec.get("show_chart"):
                            c_type = chart_rec.get("chart_type")
                            if c_type == "bar":
                                fig = px.bar(
                                    df_result,
                                    x=chart_rec["x"],
                                    y=chart_rec["y"],
                                    title=chart_rec["title"],
                                    color_discrete_sequence=["#3B82F6"]
                                )
                                fig.update_layout(xaxis_tickangle=-45)
                                st.plotly_chart(fig, use_container_width=True)
                            elif c_type == "line":
                                fig = px.line(
                                    df_result,
                                    x=chart_rec["x"],
                                    y=chart_rec["y"],
                                    title=chart_rec["title"],
                                    markers=True,
                                    color_discrete_sequence=["#10B981"]
                                )
                                st.plotly_chart(fig, use_container_width=True)
                            elif c_type == "pie":
                                fig = px.pie(
                                    df_result,
                                    names=chart_rec["names"],
                                    values=chart_rec["values"],
                                    title=chart_rec["title"],
                                    hole=0.3
                                )
                                st.plotly_chart(fig, use_container_width=True)
                            elif c_type == "scatter":
                                fig = px.scatter(
                                    df_result,
                                    x=chart_rec["x"],
                                    y=chart_rec["y"],
                                    title=chart_rec["title"]
                                )
                                st.plotly_chart(fig, use_container_width=True)
                        elif chart_rec.get("chart_type") == "metric":
                            st.metric(
                                label=chart_rec.get("metric_label", "Total"),
                                value=chart_rec.get("metric_value", "0")
                            )
                        else:
                            st.dataframe(df_result, use_container_width=True)

                    with res_col2:
                        st.dataframe(df_result, use_container_width=True, height=350)
                        st.caption(f"Showing {len(df_result)} records from source **{target_source_name}**")

                    # Collapsible SQL Drawer
                    with st.expander("🔍 View Executed SQL & Reasoning", expanded=False):
                        st.code(final_sql, language="sql")
                        st.caption(f"**Dialect:** {dialect.upper()} | **Source:** {target_source_name} | **Reasoning:** {sql_res.get('reasoning')}")

                    # Latency Breakdown Report (Module 10 Requirement)
                    st.markdown("### ⏱️ Latency Breakdown")
                    st.markdown(f"""
                    <div class="latency-bar">
                        {tracker.format_report().replace(chr(10), '<br>')}
                    </div>
                    """, unsafe_allow_html=True)
