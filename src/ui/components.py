"""
Reusable UI rendering helpers for the Voice Data Analyst Streamlit app.
No backend logic is invented here; all helpers format existing pipeline outputs.
"""
import html
import re
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import plotly.express as px
import sqlglot
from sqlglot import exp
import streamlit as st

from src.db.connector import DatabaseSource
from src.ui.styles import (
    ACCENT_PRIMARY,
    CHART_PALETTE,
    TEXT_MUTED,
    TEXT_PRIMARY,
)

NON_SUMMABLE_KPI_KEYWORDS = (
    "avg",
    "average",
    "rate",
    "pct",
    "percent",
    "ratio",
    "score",
)

COUNT_KPI_KEYWORDS = (
    "count",
    "cnt",
    "num",
    "qty",
    "quantity",
    "orders",
    "units",
    "items",
    "stock",
)


def get_engine_badge_html(engine_type: str) -> str:
    """Return an HTML badge tinted by database engine (SQLite, DuckDB/CSV, Postgres)."""
    eng = (engine_type or "").strip().lower()
    if eng == "sqlite":
        cls = "vda-engine-badge vda-engine-sqlite"
        label = "SQLite"
    elif eng in ("duckdb", "csv"):
        cls = "vda-engine-badge vda-engine-duckdb"
        label = "DuckDB"
    elif eng in ("postgres", "postgresql"):
        cls = "vda-engine-badge vda-engine-postgres"
        label = "Postgres"
    else:
        cls = "vda-engine-badge vda-engine-default"
        label = eng.upper() if eng else "DB"
    return f'<span class="{cls}">{html.escape(label)}</span>'


def render_header() -> None:
    """Render the sticky title bar with subtitle and runtime status pills."""
    header_html = "".join(
        [
            '<div class="vda-header">',
            "<div>",
            '<div class="vda-title">Voice Data Analyst</div>',
            '<div class="vda-subtitle">Ask business questions by voice or text across connected databases.</div>',
            "</div>",
            '<div class="vda-status-pills">',
            '<span class="vda-status-pill"><span class="vda-status-dot"></span>Speech: <strong>local</strong></span>',
            '<span class="vda-status-pill"><span class="vda-status-dot"></span>TTS: <strong>local</strong></span>',
            '<span class="vda-status-pill"><span class="vda-status-dot vda-status-dot-cloud"></span>LLM: <strong>cloud</strong></span>',
            "</div>",
            "</div>",
        ]
    )
    st.markdown(header_html, unsafe_allow_html=True)


def render_voice_orb() -> None:
    """Render the idle CSS-only breathing voice orb placed above the audio input."""
    orb_html = "".join(
        [
            '<div class="vda-voice-hero">',
            '<div class="vda-orb-wrap" aria-hidden="true">',
            '<div class="vda-orb-halo"></div>',
            '<div class="vda-orb-core"></div>',
            "</div>",
            '<div class="vda-voice-instruction">Ask your data by voice</div>',
            "</div>",
        ]
    )
    st.markdown(orb_html, unsafe_allow_html=True)


def render_processing_waveform_html(stage_label: str) -> str:
    """Return HTML for the 6-bar animated processing waveform with the current stage name."""
    safe_stage = html.escape(stage_label)
    return "".join(
        [
            '<div class="vda-waveform-row">',
            '<div class="vda-waveform-bars" aria-hidden="true">',
            '<span class="vda-wave-bar"></span>',
            '<span class="vda-wave-bar"></span>',
            '<span class="vda-wave-bar"></span>',
            '<span class="vda-wave-bar"></span>',
            '<span class="vda-wave-bar"></span>',
            '<span class="vda-wave-bar"></span>',
            "</div>",
            f'<span class="vda-waveform-label">{safe_stage}</span>',
            "</div>",
        ]
    )


def render_speaking_equalizer_html() -> str:
    """Return HTML for a subtle 5-bar animated equalizer decoration for spoken answers."""
    return "".join(
        [
            '<div class="vda-eq" aria-hidden="true">',
            '<span class="vda-eq-bar"></span>',
            '<span class="vda-eq-bar"></span>',
            '<span class="vda-eq-bar"></span>',
            '<span class="vda-eq-bar"></span>',
            '<span class="vda-eq-bar"></span>',
            "</div>",
        ]
    )


def render_kpi_cards(kpi_items: List[Tuple[str, str]]) -> None:
    """Render equal-width KPI cards with uppercase label, large value, and top gradient accent border."""
    if not kpi_items:
        return
    kpi_cols = st.columns(len(kpi_items))
    for col, (label, value) in zip(kpi_cols, kpi_items):
        with col:
            card_html = "".join(
                [
                    '<div class="vda-kpi-card">',
                    f'<div class="vda-kpi-label">{html.escape(str(label))}</div>',
                    f'<div class="vda-kpi-value">{html.escape(str(value))}</div>',
                    "</div>",
                ]
            )
            st.markdown(card_html, unsafe_allow_html=True)


def render_empty_state(sources_list: List[Dict[str, Any]], profiles: Dict[str, Any]) -> None:
    """Render a friendly panel below the input with numbered tips (1, 2, 3) and connected sources."""
    source_rows = []
    for src in sources_list:
        src_name = html.escape(src["name"])
        badge_html = get_engine_badge_html(src.get("engine", ""))
        desc = html.escape(get_source_one_line_description(src, profiles.get(src["name"], {})))
        source_rows.append(
            "".join(
                [
                    '<div class="vda-empty-source-row">',
                    f"<strong>{src_name}</strong>",
                    badge_html,
                    f"<span>{desc}</span>",
                    "</div>",
                ]
            )
        )

    sources_block = (
        "".join(
            [
                '<div class="vda-empty-sources">',
                '<div class="vda-card-label" style="margin-bottom:4px;">Connected Sources</div>',
                "".join(source_rows),
                "</div>",
            ]
        )
        if source_rows
        else ""
    )

    empty_html = "".join(
        [
            '<div class="vda-empty-panel">',
            '<div class="vda-card-label">Getting Started</div>',
            '<div class="vda-empty-grid">',
            '<div class="vda-tip-card"><span class="vda-tip-num">1</span><span>Ask about revenue by category</span></div>',
            '<div class="vda-tip-card"><span class="vda-tip-num">2</span><span>Say \'now break it down by month\' to follow up</span></div>',
            '<div class="vda-tip-card"><span class="vda-tip-num">3</span><span>Try a dangerous request to see the refusal</span></div>',
            "</div>",
            sources_block,
            "</div>",
        ]
    )
    st.markdown(empty_html, unsafe_allow_html=True)


def format_total_metric_label(column_name: str) -> str:
    """Format a numeric column name for a Total KPI without duplicating 'Total'."""
    clean = column_name.replace("_", " ").strip().title()
    if clean.lower().startswith("total "):
        return clean
    if clean.lower() == "total":
        return "Total"
    return f"Total {clean}"


def build_numeric_kpi(df_result: pd.DataFrame) -> Optional[Tuple[str, str]]:
    """
    Build the numeric summary KPI (label, formatted_value) for the first summable numeric column.
    Skips ID, rank, and index columns. Returns None (hiding the card) if no suitable numeric
    column remains or if it looks like an average, rate, percentage, ratio, or score.
    """
    if df_result is None or df_result.empty:
        return None

    numeric_cols = df_result.select_dtypes(include=[np.number]).columns
    if len(numeric_cols) == 0:
        return None

    primary_col: Optional[str] = None
    col_lower = ""
    for col in numeric_cols:
        cname = str(col)
        clower = cname.lower()
        if (
            clower == "id"
            or clower.endswith("_id")
            or clower.startswith("id_")
            or clower in ("rank", "row_num", "row_number", "rownum", "index", "idx")
            or clower.endswith("_rank")
            or clower.startswith("rank_")
            or clower.endswith("_index")
            or clower.startswith("index_")
        ):
            continue
        primary_col = cname
        col_lower = clower
        break

    if primary_col is None:
        return None

    if any(keyword in col_lower for keyword in NON_SUMMABLE_KPI_KEYWORDS):
        return None

    aggregate_keywords = (
        "total", "sum", "count", "cnt", "avg", "average", "mean",
        "min", "max", "revenue", "sales", "spend", "spent", "spending",
        "income", "profit", "margin", "orders",
    )
    is_aggregate_col = any(keyword in col_lower for keyword in aggregate_keywords)

    # Never sum raw quantity-like columns (qty, quantity, units) in a row listing
    col_tokens = set(re.split(r"[^a-z0-9]+", col_lower))
    if not is_aggregate_col and bool(col_tokens & {"qty", "quantity", "units"}):
        return None

    # Hide the card for long plain row listings (> 20 rows with no aggregate)
    if len(df_result) > 20 and not is_aggregate_col:
        return None

    series = df_result[primary_col].dropna()
    if series.empty:
        return None

    total_val = series.sum()
    is_int_dtype = pd.api.types.is_integer_dtype(df_result[primary_col])
    is_count_like = any(keyword in col_lower for keyword in COUNT_KPI_KEYWORDS)
    if is_int_dtype or (is_count_like and float(total_val).is_integer()):
        formatted_val = f"{int(round(float(total_val))):,}"
    else:
        formatted_val = f"{float(total_val):,.2f}"

    if len(df_result) > 1:
        label = f"Sum of {len(df_result)} rows shown"
    else:
        label = format_total_metric_label(primary_col)

    return label, formatted_val


def extract_sql_tables(sql: str, dialect: str = "sqlite", fallback_tables: Optional[List[str]] = None) -> List[str]:
    """Extract table names referenced by a SQL query using sqlglot, with fallback."""
    tables: List[str] = []
    if sql:
        try:
            read_dialect = "postgres" if dialect == "postgres" else "sqlite"
            parsed = sqlglot.parse_one(sql, read=read_dialect)
            seen = set()
            for tbl in parsed.find_all(exp.Table):
                if tbl.name and tbl.name.lower() not in seen:
                    seen.add(tbl.name.lower())
                    tables.append(tbl.name)
        except Exception:
            pass
    if not tables and fallback_tables:
        tables = list(fallback_tables)
    return tables


def highlight_changed_phrases(
    text: str,
    phrases: List[str],
    css_class: str,
) -> str:
    """HTML-escape text and highlight exact matched phrases safely."""
    escaped = html.escape(text or "")
    unique_phrases = sorted({p for p in phrases if p and p.strip()}, key=len, reverse=True)
    for phrase in unique_phrases:
        escaped_phrase = html.escape(phrase)
        pattern = re.compile(r"\b" + re.escape(escaped_phrase) + r"\b", re.IGNORECASE)
        escaped = pattern.sub(
            lambda m: f'<span class="{css_class}">{m.group(0)}</span>',
            escaped,
        )
    return escaped


def render_transcript_comparison(
    raw_query: str,
    corrected_query: str,
    corrections_log: List[Dict[str, Any]],
    is_voice: bool,
) -> None:
    """
    Task 2: Show what was heard and what was corrected.
    - Voice questions: raw transcript and corrected question side by side with highlights.
    - Text questions: show corrected question only if it differs from the raw text.
    """
    differs = (raw_query.strip() != corrected_query.strip()) or bool(corrections_log)

    if is_voice:
        originals = [c.get("original", "") for c in corrections_log]
        corrected_terms = [c.get("corrected", "") for c in corrections_log]
        raw_html = highlight_changed_phrases(raw_query, originals, "vda-diff-old")
        corr_html = highlight_changed_phrases(corrected_query, corrected_terms, "vda-diff-new")

        col_raw, col_corr = st.columns(2)
        with col_raw:
            raw_box_html = "".join(
                [
                    '<div class="vda-transcript-box">',
                    '<div class="vda-card-label">Heard (Raw Transcript)</div>',
                    f"<div>{raw_html}</div>",
                    "</div>",
                ]
            )
            st.markdown(raw_box_html, unsafe_allow_html=True)
        with col_corr:
            label = "Corrected Question" if differs else "Corrected Question (No changes)"
            corr_box_html = "".join(
                [
                    '<div class="vda-transcript-box">',
                    f'<div class="vda-card-label">{label}</div>',
                    f"<div>{corr_html}</div>",
                    "</div>",
                ]
            )
            st.markdown(corr_box_html, unsafe_allow_html=True)
    elif differs:
        corrected_terms = [c.get("corrected", "") for c in corrections_log]
        corr_html = highlight_changed_phrases(corrected_query, corrected_terms, "vda-diff-new")
        changes_summary = ", ".join(
            f'"{html.escape(str(c.get("original", "")))}" -> "{html.escape(str(c.get("corrected", "")))}"'
            for c in corrections_log
        )
        suffix = (
            f'<div style="margin-top:6px;font-size:13.5px;color:#94A3B8;">Applied: {changes_summary}</div>'
            if changes_summary
            else ""
        )
        text_box_html = "".join(
            [
                '<div class="vda-transcript-box">',
                '<div class="vda-card-label">Corrected Question</div>',
                f"<div>{corr_html}</div>",
                suffix,
                "</div>",
            ]
        )
        st.markdown(text_box_html, unsafe_allow_html=True)


def render_routing_banner(
    source_name: str,
    engine_type: str,
    source_description: str,
    tables_used: List[str],
    is_followup: bool = False,
) -> None:
    """Task 3 & 5: Show chosen data source, tables used by SQL, and follow-up badge."""
    safe_source = html.escape(source_name)
    badge_html = get_engine_badge_html(engine_type)
    safe_desc = html.escape(source_description) if source_description else ""
    tables_str = ", ".join(html.escape(t) for t in tables_used) if tables_used else "None detected"

    desc_html = f'<span><span class="vda-route-key">Description:</span>{safe_desc}</span>' if safe_desc else ""
    followup_html = '<span class="vda-badge">Follow-up: modified previous query</span>' if is_followup else ""

    route_html = "".join(
        [
            '<div class="vda-route-bar">',
            f'<span><span class="vda-route-key">Source:</span><strong>{safe_source}</strong> {badge_html}</span>',
            f'<span><span class="vda-route-key">Tables used:</span>{tables_str}</span>',
            desc_html,
            followup_html,
            "</div>",
        ]
    )
    st.markdown(route_html, unsafe_allow_html=True)


def render_plotly_chart(df_result: pd.DataFrame, chart_rec: Dict[str, Any]) -> Tuple[Optional[Any], Optional[str]]:
    """
    Build a dark-themed Plotly chart styled with the app's accent color palette.
    Returns (fig, note), where note is populated when a categorical bar chart is capped to top 15 rows.
    """
    c_type = chart_rec.get("chart_type")
    fig = None
    note = None

    grid_rgba = "rgba(148, 163, 184, 0.14)"
    custom_layout = dict(
        font=dict(family="Inter, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif", size=14, color=TEXT_PRIMARY),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=24, r=24, t=52, b=32),
        xaxis=dict(
            showgrid=False,
            showline=False,
            zeroline=False,
            tickfont=dict(size=13, color=TEXT_MUTED),
            title_font=dict(size=13, color=TEXT_MUTED),
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor=grid_rgba,
            gridwidth=1,
            showline=False,
            zeroline=False,
            tickfont=dict(size=13, color=TEXT_MUTED),
            title_font=dict(size=13, color=TEXT_MUTED),
        ),
        title=dict(font=dict(size=16, color=TEXT_PRIMARY), x=0, xanchor="left"),
        legend=dict(font=dict(size=13, color=TEXT_MUTED)),
        hoverlabel=dict(bgcolor="#0B1020", bordercolor="#243049", font_color=TEXT_PRIMARY, font_size=13),
    )

    if c_type == "bar":
        x_col = chart_rec["x"]
        y_col = chart_rec["y"]
        total_rows = len(df_result)
        is_categorical = (
            x_col in df_result.columns
            and y_col in df_result.columns
            and not pd.api.types.is_datetime64_any_dtype(df_result[x_col])
        )
        custom_layout["barcornerradius"] = 6

        if is_categorical and total_rows > 15:
            plot_df = df_result.sort_values(by=y_col, ascending=False).head(15).copy()
            note = f"Showing top 15 of {total_rows} rows"
            fig = px.bar(
                plot_df,
                x=y_col,
                y=x_col,
                orientation="h",
                title=chart_rec.get("title", ""),
                color_discrete_sequence=[ACCENT_PRIMARY],
            )
            fig.update_traces(marker_line_width=0, marker_opacity=0.92)
            custom_layout["height"] = 480
            custom_layout["xaxis"] = dict(
                showgrid=True,
                gridcolor=grid_rgba,
                showline=False,
                zeroline=False,
                tickfont=dict(size=13, color=TEXT_MUTED),
                title_font=dict(size=13, color=TEXT_MUTED),
            )
            custom_layout["yaxis"] = dict(
                showgrid=False,
                showline=False,
                zeroline=False,
                autorange="reversed",
                type="category",
                automargin=True,
                tickfont=dict(size=13, color=TEXT_PRIMARY),
                title_font=dict(size=13, color=TEXT_MUTED),
            )
        else:
            fig = px.bar(
                df_result,
                x=x_col,
                y=y_col,
                title=chart_rec.get("title", ""),
                color_discrete_sequence=[ACCENT_PRIMARY],
            )
            fig.update_traces(marker_line_width=0, marker_opacity=0.92)
    elif c_type == "line":
        x_col = chart_rec["x"]
        y_col = chart_rec["y"]
        plot_df = df_result.copy()
        color_col = None

        if x_col in plot_df.columns and y_col in plot_df.columns:
            y_lower = str(y_col).lower()
            agg_func = "mean" if any(k in y_lower for k in ("avg", "average", "rate", "score")) else "sum"
            has_repeated_x = bool(plot_df[x_col].duplicated().any())

            if has_repeated_x:
                cat_cols = [
                    c
                    for c in plot_df.columns
                    if c not in (x_col, y_col)
                    and not pd.api.types.is_numeric_dtype(plot_df[c])
                    and not pd.api.types.is_datetime64_any_dtype(plot_df[c])
                ]
                if cat_cols:
                    chosen_cat = next(
                        (c for c in cat_cols if 1 <= plot_df[c].nunique(dropna=True) <= 8),
                        cat_cols[0],
                    )
                    n_groups = int(plot_df[chosen_cat].nunique(dropna=True))
                    if 1 <= n_groups <= 8:
                        if plot_df.duplicated(subset=[x_col, chosen_cat]).any():
                            plot_df = (
                                plot_df.groupby([x_col, chosen_cat], as_index=False, dropna=False)[y_col]
                                .agg(agg_func)
                            )
                        color_col = chosen_cat
                    else:
                        plot_df = (
                            plot_df.groupby(x_col, as_index=False, dropna=False)[y_col]
                            .agg(agg_func)
                        )
                        note = f"Aggregated across {n_groups:,} groups. See the Data Table tab for all rows."
                else:
                    total_rows = len(plot_df)
                    plot_df = (
                        plot_df.groupby(x_col, as_index=False, dropna=False)[y_col]
                        .agg(agg_func)
                    )
                    note = f"Aggregated across {total_rows:,} rows. See the Data Table tab for all rows."

            plot_df = plot_df.sort_values(by=x_col, ascending=True)

        fig = px.line(
            plot_df,
            x=x_col,
            y=y_col,
            color=color_col,
            title=chart_rec.get("title", ""),
            markers=True,
            color_discrete_sequence=CHART_PALETTE,
        )
        fig.update_traces(line=dict(width=2.5), marker=dict(size=7))
        if color_col is not None:
            custom_layout["showlegend"] = True
    elif c_type == "pie":
        fig = px.pie(
            df_result,
            names=chart_rec["names"],
            values=chart_rec["values"],
            title=chart_rec.get("title", ""),
            hole=0.48,
            color_discrete_sequence=CHART_PALETTE,
        )
        fig.update_traces(textfont_size=13, textfont_color=TEXT_PRIMARY)
    elif c_type == "scatter":
        fig = px.scatter(
            df_result,
            x=chart_rec["x"],
            y=chart_rec["y"],
            title=chart_rec.get("title", ""),
            color_discrete_sequence=CHART_PALETTE,
        )
        fig.update_traces(marker=dict(size=9, opacity=0.9))

    if fig is not None:
        fig.update_layout(**custom_layout)
    return fig, note


def compute_time_to_speech(timings: Dict[str, float]) -> float:
    """Compute total seconds up to and including Local TTS."""
    total = 0.0
    for stage, duration in timings.items():
        total += float(duration)
        if stage == "Local TTS":
            break
    return round(total, 3)


def render_performance_panel(timings: Dict[str, float]) -> None:
    """
    Task 7: Collapsible Performance section (open by default) with headline
    time-to-speech at top right, slimmer bars, and slowest stage in amber.
    """
    if not timings:
        return

    time_to_speech = compute_time_to_speech(timings)
    total = sum(timings.values())
    max_stage = max(timings.items(), key=lambda item: item[1])[0]
    max_val = max(timings.values()) if timings else 0.0

    rows_html = []
    for stage, duration in timings.items():
        is_slowest = stage == max_stage and max_val > 0
        row_cls = "vda-perf-slowest" if is_slowest else ""
        bar_cls = "vda-bar-fill-slowest" if is_slowest else "vda-bar-fill"
        pct_of_max = (duration / max_val * 100.0) if max_val > 0 else 0.0
        pct_of_total = (duration / total * 100.0) if total > 0 else 0.0
        stage_label = html.escape(stage.replace("_", " "))
        slow_tag = ' <span style="color:#FBBF24;font-size:12px;font-weight:600;">(Slowest)</span>' if is_slowest else ""

        rows_html.append(
            "".join(
                [
                    f'<tr class="{row_cls}">',
                    f'<td style="width:28%;">{stage_label}{slow_tag}</td>',
                    '<td style="width:46%;">',
                    '<div class="vda-bar-track">',
                    f'<div class="{bar_cls}" style="width:{max(pct_of_max, 2.0):.1f}%;"></div>',
                    "</div>",
                    "</td>",
                    f'<td style="width:14%;text-align:right;font-variant-numeric:tabular-nums;">{duration:.3f}s</td>',
                    f'<td style="width:12%;text-align:right;color:#94A3B8;font-variant-numeric:tabular-nums;">{pct_of_total:.1f}%</td>',
                    "</tr>",
                ]
            )
        )

    panel_html = "".join(
        [
            '<div class="vda-perf-header">',
            "<div>",
            '<div class="vda-card-label" style="margin-bottom:4px;">Time Until Spoken Answer Starts</div>',
            '<div style="font-size:13.5px;color:#94A3B8;">All pipeline stages up to and including local text-to-speech</div>',
            "</div>",
            f'<div class="vda-perf-value">{time_to_speech:.2f}s</div>',
            "</div>",
            '<table class="vda-perf-table">',
            "<thead><tr>",
            "<th>Stage</th>",
            "<th>Relative Duration</th>",
            '<th style="text-align:right;">Time</th>',
            '<th style="text-align:right;">Share</th>',
            "</tr></thead>",
            "<tbody>",
            "".join(rows_html),
            "</tbody>",
            "</table>",
        ]
    )

    with st.expander("Performance", expanded=True):
        st.markdown(panel_html, unsafe_allow_html=True)


def render_history_section(history: List[Dict[str, Any]]) -> None:
    """Task 5: Collapsible History section listing previous turns with collapsed SQL."""
    count = len(history)
    label = f"History ({count})" if count else "History"
    with st.expander(label, expanded=False):
        if not history:
            st.caption("No queries run in this session yet.")
            return

        items_html = []
        for idx, turn in enumerate(reversed(history), start=1):
            turn_num = count - idx + 1
            safe_q = html.escape(str(turn.get("question", "")))
            safe_src = html.escape(str(turn.get("source", "")))
            safe_sql = html.escape(str(turn.get("sql", "")))
            row_count = int(turn.get("row_count", 0))
            followup_badge = '<span class="vda-badge">Follow-up</span>' if turn.get("is_followup") else ""

            items_html.append(
                "".join(
                    [
                        '<div class="vda-history-item">',
                        f'<div style="font-weight:600;color:#E6EAF5;font-size:13.5px;">#{turn_num}: {safe_q}</div>',
                        '<div class="vda-history-meta">',
                        f'<span class="vda-badge-neutral">{safe_src}</span>',
                        f"<span>{row_count:,} rows</span>",
                        followup_badge,
                        "</div>",
                        '<details class="vda-history-sql">',
                        "<summary>Show SQL</summary>",
                        f"<pre><code>{safe_sql}</code></pre>",
                        "</details>",
                        "</div>",
                    ]
                )
            )

        st.markdown("".join(items_html), unsafe_allow_html=True)


def get_source_one_line_description(src: Dict[str, Any], profile: Dict[str, Any]) -> str:
    """Return a concise one-line description of what a connected source contains."""
    desc = (src.get("description") or "").strip()
    tables = list(profile.get("tables", {}).keys())
    if desc and desc.lower() != "in-memory csv engine":
        return desc
    if tables:
        preview = ", ".join(tables[:3])
        extra = f" and {len(tables) - 3} more" if len(tables) > 3 else ""
        return f"Contains {preview}{extra}"
    return f"{src.get('engine', 'database').upper()} data source"


def test_uri_connection(uri: str) -> Tuple[bool, str]:
    """
    Task 6: Test a SQLite or PostgreSQL URI before registering it.
    Uses sqlite3 directly for SQLite and existing DatabaseSource for Postgres.
    """
    clean_uri = (uri or "").strip()
    if not clean_uri:
        return False, "Please enter a connection URI first."

    try:
        if clean_uri.startswith("sqlite:///"):
            db_path = clean_uri.replace("sqlite:///", "", 1)
            if not db_path:
                return False, "SQLite URI is missing a file path."
            if db_path != ":memory:" and not Path(db_path).exists():
                return False, f"SQLite file not found: {db_path}"
            with sqlite3.connect(db_path) as conn:
                conn.execute("SELECT 1").fetchone()
            return True, "Connection successful (SQLite)."

        if clean_uri.startswith("postgresql://") or clean_uri.startswith("postgres://"):
            temp_src = DatabaseSource(name="_connection_test", engine_type="postgres", uri_or_path=clean_uri)
            conn = temp_src.get_connection()
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")
                    cur.fetchone()
            finally:
                conn.close()
            return True, "Connection successful (PostgreSQL)."

        return False, "Unsupported URI scheme. Use sqlite:///... or postgresql://..."
    except Exception as exc:
        return False, f"Connection failed: {exc}"
