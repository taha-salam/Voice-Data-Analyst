"""
Voice Data Analyst - Executive Business Intelligence Workspace
Natural Language & Local Voice Interface for Multi-Engine Relational Databases.
"""
import os
import time
import base64
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

# ---------------------------------------------------------
# Page Configuration & Clean Typography Styling
# ---------------------------------------------------------
st.set_page_config(
    page_title="Voice Data Analyst",
    page_icon="none",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Design System: Clean, Minimalist Enterprise Theme (No Emojis)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

    /* Global Typography */
    html, body, [class*="css"], [class*="st-"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }

    /* Clean Brand Navigation Header */
    .brand-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 1.25rem 1.5rem;
        background: #FFFFFF;
        border: 1px solid #E5E7EB;
        border-radius: 8px;
        box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.03);
        margin-bottom: 1.25rem;
    }
    .brand-title {
        font-size: 1.35rem;
        font-weight: 700;
        color: #111827;
        letter-spacing: -0.02em;
        line-height: 1.2;
    }
    .brand-subtitle {
        font-size: 0.85rem;
        color: #6B7280;
        font-weight: 400;
        margin-top: 0.15rem;
    }
    .status-group {
        display: flex;
        gap: 0.5rem;
        flex-wrap: wrap;
    }
    .status-badge {
        display: inline-flex;
        align-items: center;
        gap: 0.35rem;
        padding: 0.25rem 0.65rem;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 500;
        border: 1px solid #E5E7EB;
        background: #F9FAFB;
        color: #374151;
    }
    .status-dot-green {
        width: 6px;
        height: 6px;
        border-radius: 50%;
        background-color: #10B981;
    }
    .status-dot-blue {
        width: 6px;
        height: 6px;
        border-radius: 50%;
        background-color: #3B82F6;
    }

    /* Executive Spoken Takeaway Banner */
    .executive-card {
        background: #F8FAFC;
        border-left: 3px solid #1E293B;
        border-top: 1px solid #E2E8F0;
        border-right: 1px solid #E2E8F0;
        border-bottom: 1px solid #E2E8F0;
        border-radius: 6px;
        padding: 1.2rem 1.4rem;
        margin: 1rem 0;
    }
    .executive-tag {
        font-size: 0.72rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: #64748B;
        margin-bottom: 0.35rem;
    }
    .executive-speech {
        font-size: 1.1rem;
        font-weight: 600;
        color: #0F172A;
        line-height: 1.5;
    }

    /* Diagnostic Banners */
    .alignment-alert {
        background: #F0FDF4;
        border: 1px solid #DCFCE7;
        border-left: 3px solid #16A34A;
        border-radius: 6px;
        padding: 0.65rem 0.9rem;
        margin-bottom: 0.85rem;
        font-size: 0.85rem;
        color: #15803D;
    }
    .security-alert {
        background: #FEF2F2;
        border: 1px solid #FEE2E2;
        border-left: 3px solid #DC2626;
        border-radius: 6px;
        padding: 0.85rem 1rem;
        margin: 0.85rem 0;
        color: #991B1B;
        font-size: 0.88rem;
        font-weight: 600;
    }

    /* Performance Metric Tiles */
    .perf-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(110px, 1fr));
        gap: 0.5rem;
        margin-top: 0.5rem;
    }
    .perf-tile {
        background: #F9FAFB;
        border: 1px solid #E5E7EB;
        border-radius: 6px;
        padding: 0.6rem 0.75rem;
        text-align: center;
    }
    .perf-tile-label {
        font-size: 0.68rem;
        font-weight: 600;
        color: #6B7280;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }
    .perf-tile-val {
        font-size: 0.95rem;
        font-weight: 600;
        color: #111827;
        margin-top: 0.15rem;
        font-family: 'JetBrains Mono', monospace;
    }

    /* Streamlit Widget Polishing */
    button[data-baseweb="tab"] {
        font-size: 0.9rem !important;
        font-weight: 500 !important;
        color: #6B7280 !important;
        padding: 0.5rem 1rem !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        color: #111827 !important;
        border-bottom-color: #111827 !important;
        font-weight: 600 !important;
    }
    div.stButton > button {
        border-radius: 6px !important;
        font-weight: 500 !important;
        font-size: 0.88rem !important;
    }
    div.stButton > button[kind="primary"] {
        background-color: #0F172A !important;
        color: #FFFFFF !important;
        border: none !important;
    }
    div.stButton > button[kind="primary"]:hover {
        background-color: #1E293B !important;
    }
</style>
""", unsafe_allow_html=True)


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


# ---------------------------------------------------------
# Top Navigation & Brand Header (Clean, No Emojis)
# ---------------------------------------------------------
st.markdown("""
<div class="brand-header">
    <div>
        <div class="brand-title">Voice Data Analyst</div>
        <div class="brand-subtitle">Natural Language & Voice Query Workspace for Multi-Engine Databases</div>
    </div>
    <div class="status-group">
        <span class="status-badge"><span class="status-dot-green"></span> Offline ASR (faster-whisper)</span>
        <span class="status-badge"><span class="status-dot-green"></span> Offline TTS (SAPI5)</span>
        <span class="status-badge"><span class="status-dot-blue"></span> Groq 120B Reasoning</span>
        <span class="status-badge"><span class="status-dot-blue"></span> AST Read-Only Safe</span>
    </div>
</div>
""", unsafe_allow_html=True)


# ---------------------------------------------------------
# Sidebar: Connected Databases (Clean, Professional)
# ---------------------------------------------------------
with st.sidebar:
    st.markdown("#### Connected Databases")
    st.caption("Active data sources with auto-profiled schemas:")

    for src in db_mgr.list_sources():
        src_profile = profiles.get(src['name'], {})
        tables = src_profile.get("tables", {})
        engine_label = src['engine'].upper()

        with st.expander(f"{src['name']} ({engine_label})", expanded=False):
            st.markdown(f"**Description:** {src['description']}")
            st.markdown(f"**Tables:** `{len(tables)}` | **Storage:** `{Path(src['path']).name}`")
            for tname, tinfo in tables.items():
                col_names = [c["name"] for c in tinfo.get("columns", [])]
                st.markdown(f"- **`{tname}`** ({tinfo.get('row_count', 0):,} rows)")
                st.caption(f"Columns: {', '.join(col_names[:5])}{'...' if len(col_names) > 5 else ''}")

    st.markdown("---")
    st.markdown("#### Add Data Source")
    up_tab, uri_tab = st.tabs(["Upload File", "Database URI"])

    with up_tab:
        uploaded_file = st.file_uploader("Upload CSV or SQLite (.db/.sqlite)", type=["csv", "sqlite", "db"], label_visibility="collapsed")
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
                
                new_src = db_mgr.get_source(safe_name if not file_name.endswith(".csv") else f"csv_{safe_name}")
                if new_src:
                    profiles[new_src.name] = DatabaseProfiler(new_src).profile(sample_limit=5)
                    corrector.harvest_from_database(new_src)
                    st.success(f"Connected source '{file_name}'")
                    st.rerun()

    with uri_tab:
        new_uri = st.text_input("Connection URI", placeholder="postgresql://user:pass@localhost:5432/mydb")
        new_name = st.text_input("Identifier", placeholder="pg_analytics")
        if st.button("Connect Database", use_container_width=True):
            if new_uri and new_name:
                try:
                    if new_uri.startswith("sqlite"):
                        db_mgr.register_sqlite(new_name, new_uri.replace("sqlite:///", ""))
                    else:
                        db_mgr.register_postgres(new_name, new_uri)
                    st.success(f"Connected to '{new_name}'")
                    st.rerun()
                except Exception as e:
                    st.error(f"Connection error: {e}")


# ---------------------------------------------------------
# Main Interaction Card (Clean Container)
# ---------------------------------------------------------
query_card = st.container(border=True)

with query_card:
    st.markdown("**Example Questions**")
    prompt_mapping = {
        "Total Revenue by Category": "What is the total revenue by product category?",
        "Sales in São Paulo (Phonetic Test)": "What was the total revenue in san paulo?",
        "Low Stock Products (Inventory DB)": "Which products in the inventory have stock quantity less than 50?",
        "Sales Representative Quotas (CSV)": "List all sales representatives and their target quotas",
        "Security Attack Test (Refusal)": "DROP TABLE customers;"
    }

    selected_pill = st.pills(
        "Examples",
        options=list(prompt_mapping.keys()),
        selection_mode="single",
        label_visibility="collapsed"
    )

    if selected_pill:
        st.session_state.selected_query = prompt_mapping[selected_pill]

    # Input Modality: Tabs for Voice and Text
    tab_voice, tab_text = st.tabs(["Voice Input", "Text Query"])

    audio_val = None
    with tab_voice:
        st.caption("Click to record your question using your microphone (processed 100% offline via local faster-whisper):")
        audio_val = st.audio_input("Microphone input", label_visibility="collapsed")

    text_val = ""
    ask_button = False
    with tab_text:
        text_col1, text_col2 = st.columns([5, 1])
        with text_col1:
            text_val = st.text_input(
                "Query input",
                value=st.session_state.selected_query,
                placeholder="Ask a question about sales, inventory, or customers...",
                label_visibility="collapsed"
            )
        with text_col2:
            ask_button = st.button("Execute", type="primary", use_container_width=True)


# ---------------------------------------------------------
# Ambiguity Clarification Modal
# ---------------------------------------------------------
if st.session_state.clarification_state:
    c_state = st.session_state.clarification_state
    st.warning(f"Clarification Required: {c_state['prompt']}")
    
    if "audio_path" in c_state and os.path.exists(c_state["audio_path"]):
        st.audio(c_state["audio_path"], format="audio/wav")

    cl_col1, cl_col2 = st.columns([4, 1])
    with cl_col1:
        clarification_response = st.text_input("Clarification response", placeholder="e.g. by total spend / by order volume", label_visibility="collapsed")
    with cl_col2:
        if st.button("Submit Clarification", use_container_width=True):
            if clarification_response:
                resolved_question = clarification_engine.resolve_clarification(c_state["original_question"], clarification_response)
                st.session_state.clarification_state = None
                st.session_state.selected_query = resolved_question
                text_val = resolved_question
                ask_button = True
                st.rerun()


# ---------------------------------------------------------
# Query Execution Engine
# ---------------------------------------------------------
should_run = (audio_val is not None) or (ask_button and text_val.strip()) or (st.session_state.selected_query and ask_button)

if should_run and not st.session_state.clarification_state:
    tracker = LatencyTracker()
    raw_query = ""
    stt_latency = 0.0

    # 1. Local Speech-to-Text (faster-whisper)
    if audio_val is not None:
        with st.spinner("Transcribing speech locally (CPU int8)..."):
            with tracker.time_stage("Local ASR"):
                audio_bytes = audio_val.getvalue()
                stt_result = stt_engine.transcribe_audio_bytes(audio_bytes)
                raw_query = stt_result.get("text", "")
                stt_latency = stt_result.get("latency", 0.0)
    else:
        raw_query = text_val.strip() if text_val.strip() else st.session_state.selected_query

    if not raw_query:
        st.info("Please speak into the microphone or enter a question above.")
    else:
        # 2. Phonetic Domain Word Correction
        with tracker.time_stage("Domain Word Correction"):
            corrected_query, corrections_log = corrector.correct_transcript(raw_query)

        # Show phonetic alignment alert if words were modified
        if corrections_log:
            correction_pills = []
            for c in corrections_log:
                correction_pills.append(f'"{c["original"]}" → "{c["corrected"]}"')
            st.markdown(f"""
            <div class="alignment-alert">
                Phonetic Alignment: Aligned {', '.join(correction_pills)} with active database entities.
            </div>
            """, unsafe_allow_html=True)

        final_question = corrected_query

        # 3. Spoken Clarification Engine
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
            st.error(f"Could not locate registered data source for '{target_source_name}'")
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
            
            with tracker.time_stage("SQL Generation"):
                if is_followup:
                    st.toast("Follow-up context applied to query plan", icon="✓")
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

            # 7. Zero-Trust Security Validation & Attack Refusal
            if sql_res.get("refusal") or not sql_res.get("is_safe"):
                st.markdown(f"""
                <div class="security-alert">
                    Security Violation Refused: {sql_res.get('reasoning', 'Unsafe statement blocked by AST guardrail. Read-only SELECT statements only.')}
                </div>
                """, unsafe_allow_html=True)
            else:
                generated_sql = sql_res["sql"]

                # 8. Database Execution with Autonomous Self-Repair
                with tracker.time_stage("Database Execution"):
                    exec_result = repair_engine.execute_with_repair(
                        db_source=db_source,
                        initial_sql=generated_sql,
                        user_question=final_question,
                        schema_prompt=schema_prompt,
                        dialect=dialect
                    )

                if not exec_result["success"]:
                    st.error(f"Database Execution Error: {exec_result.get('error')}")
                else:
                    df_result = exec_result["df"]
                    final_sql = exec_result["final_sql"]

                    if exec_result.get("attempts", 1) > 1:
                        st.info(f"Self-repair successfully resolved schema error in {exec_result['attempts']} attempts.")

                    # Update Conversational Memory
                    st.session_state.memory.add_turn(final_question, final_sql, target_source_name, len(df_result))

                    # 9. Analytics & Visualization Recommendation
                    with tracker.time_stage("Visualization"):
                        chart_rec = analytics_engine.recommend_visualization(df_result)

                    # 10. Executive Spoken Insight Synthesis
                    with tracker.time_stage("Insight Generation"):
                        spoken_insight = analytics_engine.generate_spoken_insight(df_result, final_question, final_sql)

                    # 11. Local Offline TTS Audio Synthesis
                    with tracker.time_stage("Local TTS"):
                        audio_path, tts_latency = tts_engine.synthesize_to_file(spoken_insight)

                    # ---------------------------------------------------------
                    # Results Section (Polished, Modern)
                    # ---------------------------------------------------------
                    
                    # Executive Spoken Takeaway Card
                    st.markdown(f"""
                    <div class="executive-card">
                        <div class="executive-tag">Executive Summary</div>
                        <div class="executive-speech">"{spoken_insight}"</div>
                    </div>
                    """, unsafe_allow_html=True)

                    if os.path.exists(audio_path):
                        st.audio(audio_path, format="audio/wav", autoplay=True)

                    # KPI Metrics Grid
                    kpi_c1, kpi_c2, kpi_c3, kpi_c4 = st.columns(4)
                    with kpi_c1:
                        st.metric("Target Source", target_source_name.upper())
                    with kpi_c2:
                        st.metric("Total Rows", f"{len(df_result):,}")
                    with kpi_c3:
                        numeric_cols = df_result.select_dtypes(include=[np.number]).columns
                        if len(numeric_cols) > 0:
                            primary_col = numeric_cols[0]
                            st.metric(f"Total {primary_col.replace('_', ' ').title()}", f"{df_result[primary_col].sum():,.2f}")
                        else:
                            st.metric("Status", "Completed")
                    with kpi_c4:
                        st.metric("Turnaround Time", f"{tracker.total_latency():.2f}s")

                    # Data Visualization & Table Tabs
                    tab_vis, tab_data, tab_sql = st.tabs(["Visualization", "Data Table", "Executed SQL"])

                    with tab_vis:
                        if chart_rec.get("show_chart") and not df_result.empty:
                            c_type = chart_rec.get("chart_type")
                            fig = None
                            
                            custom_layout = dict(
                                font=dict(family="Inter, sans-serif", size=12, color="#1F2937"),
                                paper_bgcolor="rgba(0,0,0,0)",
                                plot_bgcolor="rgba(0,0,0,0)",
                                margin=dict(l=20, r=20, t=40, b=20),
                                xaxis=dict(gridcolor="#F3F4F6"),
                                yaxis=dict(gridcolor="#F3F4F6")
                            )

                            if c_type == "bar":
                                fig = px.bar(
                                    df_result,
                                    x=chart_rec["x"],
                                    y=chart_rec["y"],
                                    title=f"<b>{chart_rec['title']}</b>",
                                    color_discrete_sequence=["#1E293B"]
                                )
                                fig.update_traces(marker_line_width=0, marker_opacity=0.9)
                            elif c_type == "line":
                                fig = px.line(
                                    df_result,
                                    x=chart_rec["x"],
                                    y=chart_rec["y"],
                                    title=f"<b>{chart_rec['title']}</b>",
                                    markers=True,
                                    color_discrete_sequence=["#2563EB"]
                                )
                            elif c_type == "pie":
                                fig = px.pie(
                                    df_result,
                                    names=chart_rec["names"],
                                    values=chart_rec["values"],
                                    title=f"<b>{chart_rec['title']}</b>",
                                    hole=0.45,
                                    color_discrete_sequence=px.colors.sequential.Blues_r
                                )
                            elif c_type == "scatter":
                                fig = px.scatter(
                                    df_result,
                                    x=chart_rec["x"],
                                    y=chart_rec["y"],
                                    title=f"<b>{chart_rec['title']}</b>",
                                    color_discrete_sequence=["#2563EB"]
                                )

                            if fig:
                                fig.update_layout(**custom_layout)
                                st.plotly_chart(fig, use_container_width=True)
                            else:
                                st.dataframe(df_result, use_container_width=True)
                        else:
                            st.dataframe(df_result, use_container_width=True)

                    with tab_data:
                        st.dataframe(df_result, use_container_width=True)
                        csv_data = df_result.to_csv(index=False).encode('utf-8')
                        st.download_button(
                            label="Export Dataset to CSV",
                            data=csv_data,
                            file_name=f"{target_source_name}_query_result.csv",
                            mime="text/csv"
                        )

                    with tab_sql:
                        st.code(final_sql, language="sql")
                        st.caption(f"Dialect: {dialect.upper()} | AST Security: Passed Read-Only SELECT check")
                        if sql_res.get("reasoning"):
                            st.caption(f"Planner Reasoning: {sql_res['reasoning']}")

                    # Latency Profile Breakdown
                    st.markdown("#### Performance Breakdown")
                    st.markdown("""
                    <div class="perf-grid">
                    """ + "".join([
                        f"""
                        <div class="perf-tile">
                            <div class="perf-tile-label">{stage.replace('_', ' ')}</div>
                            <div class="perf-tile-val">{duration:.3f}s</div>
                        </div>
                        """
                        for stage, duration in tracker.timings.items()
                    ]) + """
                    </div>
                    """, unsafe_allow_html=True)
