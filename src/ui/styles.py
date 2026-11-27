"""
Shared dark design system and CSS styles for the Voice Data Analyst Streamlit app.
Defines all theme tokens as CSS custom properties (:root), GPU-friendly voice
animations (transform/opacity only), prefers-reduced-motion support, and explicit
dark-mode contrast rules for every native Streamlit widget.
"""

ACCENT_PRIMARY = "#3B82F6"
ACCENT_SECONDARY = "#8B5CF6"
ACCENT_DARK = "#2563EB"

TEXT_PRIMARY = "#E6EAF5"
TEXT_MUTED = "#94A3B8"

BG_BASE = "#0B1020"
BG_SURFACE = "#121A2F"
BG_RAISED = "#18223B"
BORDER_SUBTLE = "#243049"

SUCCESS_COLOR = "#34D399"
WARNING_COLOR = "#FBBF24"
ERROR_COLOR = "#F87171"

CHART_PALETTE = [
    "#3B82F6",
    "#6366F1",
    "#8B5CF6",
    "#38BDF8",
    "#818CF8",
    "#60A5FA",
    "#A78BFA",
]


def get_app_css() -> str:
    """Return the global dark stylesheet for the Streamlit interface."""
    return f"""<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

:root {{
    --vda-bg: {BG_BASE};
    --vda-surface: {BG_SURFACE};
    --vda-raised: {BG_RAISED};
    --vda-code-bg: #070B16;
    --vda-border: {BORDER_SUBTLE};
    --vda-border-hover: #334568;

    --vda-text: {TEXT_PRIMARY};
    --vda-text-muted: {TEXT_MUTED};

    --vda-accent: {ACCENT_PRIMARY};
    --vda-accent-2: {ACCENT_SECONDARY};
    --vda-accent-grad: linear-gradient(135deg, {ACCENT_PRIMARY} 0%, {ACCENT_SECONDARY} 100%);
    --vda-accent-tint: rgba(59, 130, 246, 0.12);
    --vda-accent-border: rgba(99, 102, 241, 0.36);
    --vda-accent-glow: 0 0 24px rgba(59, 130, 246, 0.24), 0 0 42px rgba(139, 92, 246, 0.14);

    --vda-success: {SUCCESS_COLOR};
    --vda-success-bg: rgba(52, 211, 153, 0.12);
    --vda-success-border: rgba(52, 211, 153, 0.34);

    --vda-warning: {WARNING_COLOR};
    --vda-warning-bg: rgba(251, 191, 36, 0.12);
    --vda-warning-border: rgba(251, 191, 36, 0.34);

    --vda-error: {ERROR_COLOR};
    --vda-error-bg: rgba(248, 113, 113, 0.12);
    --vda-error-border: rgba(248, 113, 113, 0.36);

    --vda-font: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    --vda-space-1: 8px;
    --vda-space-2: 16px;
    --vda-space-3: 24px;
    --vda-space-4: 32px;

    --vda-radius: 12px;
    --vda-radius-sm: 8px;
    --vda-shadow: 0 4px 16px rgba(0, 0, 0, 0.28);
    --vda-transition: 150ms ease;
}}

/* Hide Streamlit Deploy button, menu, and default footer */
[data-testid="stAppDeployButton"],
footer,
#MainMenu {{
    display: none !important;
}}

/* Transparent/dark top Streamlit header bar */
header[data-testid="stHeader"] {{
    background: rgba(11, 16, 32, 0.85) !important;
    backdrop-filter: blur(8px);
    border-bottom: none !important;
}}
header[data-testid="stHeader"] button,
header[data-testid="stHeader"] svg {{
    color: var(--vda-text-muted) !important;
    fill: var(--vda-text-muted) !important;
}}

/* Base page layout and typography */
html, body, .stApp {{
    background-color: var(--vda-bg) !important;
    color: var(--vda-text) !important;
    font-family: var(--vda-font);
}}

[data-testid="stAppViewContainer"],
[data-testid="stAppViewContainer"] > .main {{
    background-color: var(--vda-bg) !important;
    overflow-x: hidden;
}}

.block-container {{
    padding-top: 3.25rem !important;
    padding-bottom: var(--vda-space-4) !important;
    padding-left: var(--vda-space-3) !important;
    padding-right: var(--vda-space-3) !important;
    max-width: 1200px !important;
    margin: 0 auto !important;
}}

.stMarkdown, .stMarkdown p, .stMarkdown li, label, .stTextInput input {{
    font-family: var(--vda-font);
    font-size: 15px;
    line-height: 1.55;
    color: var(--vda-text);
}}

.stCaption, small {{
    color: var(--vda-text-muted) !important;
    font-size: 13.5px !important;
}}

/* Tidy dark scrollbar */
::-webkit-scrollbar {{
    width: 8px;
    height: 8px;
}}
::-webkit-scrollbar-track {{
    background: var(--vda-bg);
}}
::-webkit-scrollbar-thumb {{
    background: #2B3B5C;
    border-radius: 999px;
}}
::-webkit-scrollbar-thumb:hover {{
    background: #3B507A;
}}

/* Focus rings */
button:focus-visible,
input:focus-visible,
textarea:focus-visible,
[tabindex]:focus-visible {{
    outline: 2px solid var(--vda-accent) !important;
    outline-offset: 2px !important;
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.28) !important;
}}

/* Sticky Header Bar */
.vda-header {{
    position: sticky;
    top: 0;
    z-index: 40;
    background: rgba(11, 16, 32, 0.92);
    backdrop-filter: blur(10px);
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: var(--vda-space-2);
    padding: var(--vda-space-1) 0 var(--vda-space-2) 0;
    margin-bottom: var(--vda-space-3);
    border-bottom: 1px solid var(--vda-border);
}}
.vda-title {{
    font-size: 28px;
    font-weight: 700;
    color: var(--vda-text);
    letter-spacing: -0.025em;
    line-height: 1.2;
    margin: 0 0 4px 0;
}}
.vda-subtitle {{
    font-size: 14.5px;
    color: var(--vda-text-muted);
    margin: 0;
    line-height: 1.45;
}}
.vda-status-pills {{
    display: flex;
    flex-wrap: wrap;
    gap: var(--vda-space-1);
    align-items: center;
}}
.vda-status-pill {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: var(--vda-surface);
    border: 1px solid var(--vda-border);
    border-radius: 999px;
    padding: 5px 12px;
    font-size: 12.5px;
    font-weight: 500;
    color: var(--vda-text-muted);
}}
.vda-status-pill strong {{
    color: var(--vda-text);
    font-weight: 600;
}}
.vda-status-dot {{
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: var(--vda-success);
    display: inline-block;
}}
.vda-status-dot-cloud {{
    background: var(--vda-accent);
}}

/* Small uppercase labels */
.vda-section-label,
.vda-card-label {{
    font-size: 12px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--vda-text-muted);
    margin: 0 0 var(--vda-space-1) 0;
}}

/* Sidebar (~320px wide, dark surface) */
section[data-testid="stSidebar"] {{
    min-width: 320px !important;
    max-width: 320px !important;
    background-color: var(--vda-surface) !important;
    border-right: 1px solid var(--vda-border);
    color: var(--vda-text) !important;
}}
section[data-testid="stSidebar"] .block-container {{
    padding-top: var(--vda-space-3) !important;
    padding-left: var(--vda-space-2) !important;
    padding-right: var(--vda-space-2) !important;
}}
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3,
section[data-testid="stSidebar"] h4,
section[data-testid="stSidebar"] label,
section[data-testid="stSidebar"] .stMarkdown p {{
    color: var(--vda-text) !important;
}}
section[data-testid="stSidebar"] .stCaption,
section[data-testid="stSidebar"] small {{
    color: var(--vda-text-muted) !important;
}}
section[data-testid="stSidebar"] hr {{
    border-color: var(--vda-border) !important;
}}
section[data-testid="stSidebar"] [data-testid="stTabs"] button {{
    padding: 8px 10px !important;
    font-size: 13.5px !important;
}}

/* Tighter sidebar source cards */
.vda-source-card {{
    background: var(--vda-raised);
    border: 1px solid var(--vda-border);
    border-radius: var(--vda-radius-sm);
    padding: 10px 12px;
    margin-bottom: 2px;
    transition: border-color var(--vda-transition);
}}
.vda-source-card:hover {{
    border-color: var(--vda-border-hover);
}}
.vda-source-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 8px;
    margin-bottom: 4px;
}}
.vda-source-name {{
    font-weight: 600;
    font-size: 14px;
    color: var(--vda-text);
    word-break: break-word;
}}
.vda-source-desc {{
    font-size: 13px;
    color: var(--vda-text-muted);
    line-height: 1.35;
    margin-bottom: 3px;
}}
.vda-source-tables {{
    font-size: 12px;
    color: var(--vda-text-muted);
    line-height: 1.3;
}}

/* Colored engine badges for dark theme */
.vda-engine-badge {{
    display: inline-block;
    border-radius: 999px;
    padding: 2px 9px;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    white-space: nowrap;
}}
.vda-engine-sqlite {{
    background: rgba(59, 130, 246, 0.16);
    color: #93C5FD;
    border: 1px solid rgba(59, 130, 246, 0.36);
}}
.vda-engine-duckdb {{
    background: rgba(52, 211, 153, 0.15);
    color: #6EE7B7;
    border: 1px solid rgba(52, 211, 153, 0.34);
}}
.vda-engine-postgres {{
    background: rgba(139, 92, 246, 0.18);
    color: #C4B5FD;
    border: 1px solid rgba(139, 92, 246, 0.38);
}}
.vda-engine-default {{
    background: var(--vda-surface);
    color: var(--vda-text-muted);
    border: 1px solid var(--vda-border);
}}

/* Quiet text-style Remove button in sidebar */
section[data-testid="stSidebar"] button[kind="tertiary"] {{
    color: var(--vda-text-muted) !important;
    font-size: 12.5px !important;
    font-weight: 500 !important;
    padding: 2px 6px !important;
    min-height: 24px !important;
    margin-bottom: 8px !important;
    transition: color var(--vda-transition), background-color var(--vda-transition) !important;
}}
section[data-testid="stSidebar"] button[kind="tertiary"]:hover {{
    color: var(--vda-error) !important;
    background-color: var(--vda-error-bg) !important;
}}

/* File uploader dark styling */
[data-testid="stFileUploader"] section[data-testid="stFileUploaderDropzone"] {{
    background-color: var(--vda-raised) !important;
    border: 1px dashed var(--vda-border-hover) !important;
    border-radius: var(--vda-radius-sm) !important;
    color: var(--vda-text) !important;
}}
[data-testid="stFileUploaderDropzoneInstructions"],
[data-testid="stFileUploaderDropzoneInstructions"] span,
[data-testid="stFileUploaderDropzoneInstructions"] small,
[data-testid="stFileUploader"] label {{
    color: var(--vda-text-muted) !important;
}}
[data-testid="stFileUploaderDropzone"] button {{
    background-color: var(--vda-surface) !important;
    color: var(--vda-text) !important;
    border: 1px solid var(--vda-border) !important;
}}
[data-testid="stFileUploaderDropzone"] button:hover {{
    border-color: var(--vda-accent) !important;
    color: #93C5FD !important;
}}

/* Text inputs dark styling (larger comfortable box) */
[data-testid="stTextInput"] input {{
    background-color: var(--vda-raised) !important;
    color: var(--vda-text) !important;
    border: 1px solid var(--vda-border) !important;
    border-radius: var(--vda-radius-sm) !important;
    padding: 12px 14px !important;
    font-size: 15px !important;
    min-height: 46px !important;
}}
[data-testid="stTextInput"] input:focus {{
    border-color: var(--vda-accent) !important;
}}
[data-testid="stTextInput"] input::placeholder {{
    color: var(--vda-text-muted) !important;
}}

/* Bordered containers styled as dark surface cards */
[data-testid="stVerticalBlockBorderWrapper"] {{
    background: var(--vda-surface) !important;
    border: 1px solid var(--vda-border) !important;
    border-radius: var(--vda-radius) !important;
    box-shadow: var(--vda-shadow);
    padding: var(--vda-space-2) var(--vda-space-3);
    margin-bottom: var(--vda-space-3);
}}

/* Voice Hero Orb (CSS keyframes, transform & opacity only) */
.vda-voice-hero {{
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    padding: var(--vda-space-2) 0 var(--vda-space-1) 0;
}}
.vda-orb-wrap {{
    position: relative;
    width: 84px;
    height: 84px;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-bottom: var(--vda-space-2);
}}
.vda-orb-halo {{
    position: absolute;
    inset: 0;
    border-radius: 50%;
    background: var(--vda-accent-grad);
    opacity: 0.24;
    transform: scale(1);
    animation: vda-orb-halo-breathe 4s ease-in-out infinite;
    will-change: transform, opacity;
}}
.vda-orb-core {{
    position: relative;
    width: 58px;
    height: 58px;
    border-radius: 50%;
    background: var(--vda-accent-grad);
    box-shadow: var(--vda-accent-glow);
    transform: scale(1);
    animation: vda-orb-core-breathe 4s ease-in-out infinite;
    will-change: transform, opacity;
}}
.vda-voice-instruction {{
    font-size: 16px;
    font-weight: 600;
    color: var(--vda-text);
    margin: 0 0 4px 0;
}}
.vda-voice-hint {{
    font-size: 13.5px;
    color: var(--vda-text-muted);
    margin: 8px 0 0 0;
    text-align: center;
}}

@keyframes vda-orb-core-breathe {{
    0%, 100% {{
        transform: scale(0.96);
        opacity: 0.92;
    }}
    50% {{
        transform: scale(1.06);
        opacity: 1;
    }}
}}
@keyframes vda-orb-halo-breathe {{
    0%, 100% {{
        transform: scale(0.92);
        opacity: 0.16;
    }}
    50% {{
        transform: scale(1.18);
        opacity: 0.34;
    }}
}}

/* Processing Waveform (6 vertical bars bouncing at different speeds) */
.vda-waveform-row {{
    display: inline-flex;
    align-items: center;
    gap: 12px;
    padding: 4px 0;
}}
.vda-waveform-bars {{
    display: inline-flex;
    align-items: center;
    gap: 4px;
    height: 22px;
}}
.vda-wave-bar {{
    width: 4px;
    height: 20px;
    border-radius: 999px;
    background: var(--vda-accent-grad);
    transform-origin: center;
    will-change: transform, opacity;
}}
.vda-wave-bar:nth-child(1) {{ animation: vda-wave 0.95s ease-in-out infinite 0.00s; }}
.vda-wave-bar:nth-child(2) {{ animation: vda-wave 1.15s ease-in-out infinite 0.14s; }}
.vda-wave-bar:nth-child(3) {{ animation: vda-wave 0.85s ease-in-out infinite 0.28s; }}
.vda-wave-bar:nth-child(4) {{ animation: vda-wave 1.25s ease-in-out infinite 0.08s; }}
.vda-wave-bar:nth-child(5) {{ animation: vda-wave 0.90s ease-in-out infinite 0.22s; }}
.vda-wave-bar:nth-child(6) {{ animation: vda-wave 1.10s ease-in-out infinite 0.34s; }}
.vda-waveform-label {{
    font-size: 14.5px;
    font-weight: 600;
    color: var(--vda-text);
}}

@keyframes vda-wave {{
    0%, 100% {{
        transform: scaleY(0.28);
        opacity: 0.6;
    }}
    50% {{
        transform: scaleY(1.0);
        opacity: 1;
    }}
}}

/* Speaking Equalizer (gentle 5-bar decoration inside spoken summary card) */
.vda-summary-top {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
    margin-bottom: 6px;
}}
.vda-eq {{
    display: inline-flex;
    align-items: flex-end;
    gap: 3px;
    height: 16px;
}}
.vda-eq-bar {{
    width: 3px;
    height: 14px;
    border-radius: 999px;
    background: var(--vda-accent-grad);
    transform-origin: bottom;
    will-change: transform, opacity;
}}
.vda-eq-bar:nth-child(1) {{ animation: vda-eq 1.10s ease-in-out infinite 0.00s; }}
.vda-eq-bar:nth-child(2) {{ animation: vda-eq 0.90s ease-in-out infinite 0.18s; }}
.vda-eq-bar:nth-child(3) {{ animation: vda-eq 1.25s ease-in-out infinite 0.08s; }}
.vda-eq-bar:nth-child(4) {{ animation: vda-eq 0.95s ease-in-out infinite 0.26s; }}
.vda-eq-bar:nth-child(5) {{ animation: vda-eq 1.15s ease-in-out infinite 0.12s; }}

@keyframes vda-eq {{
    0%, 100% {{
        transform: scaleY(0.32);
        opacity: 0.65;
    }}
    50% {{
        transform: scaleY(0.95);
        opacity: 1;
    }}
}}

/* Respect prefers-reduced-motion */
@media (prefers-reduced-motion: reduce) {{
    .vda-orb-halo,
    .vda-orb-core,
    .vda-wave-bar,
    .vda-eq-bar {{
        animation: none !important;
        transition: none !important;
    }}
}}

/* Audio input dark styling */
[data-testid="stAudioInput"] {{
    background: var(--vda-raised) !important;
    border: 1px solid var(--vda-border) !important;
    border-radius: var(--vda-radius);
    padding: 12px 16px;
    color: var(--vda-text) !important;
    max-width: 560px;
    margin: 0 auto;
    transition: border-color var(--vda-transition), box-shadow var(--vda-transition);
}}
[data-testid="stAudioInput"]:hover {{
    border-color: var(--vda-accent) !important;
    box-shadow: 0 0 0 1px rgba(59, 130, 246, 0.25);
}}
[data-testid="stAudioInput"] > div {{
    background: var(--vda-surface) !important;
    border: 1px solid var(--vda-border) !important;
    border-radius: var(--vda-radius-sm) !important;
    color: var(--vda-text) !important;
}}
[data-testid="stAudioInput"] button,
[data-testid="stAudioInput"] span,
[data-testid="stAudioInput"] p {{
    color: var(--vda-text) !important;
}}
[data-testid="stAudioInput"] svg {{
    fill: var(--vda-text) !important;
    color: var(--vda-text) !important;
}}

/* Example question chips: single horizontal scrollable row under input card */
[data-testid="stPills"] > div {{
    flex-wrap: nowrap !important;
    overflow-x: auto !important;
    padding-bottom: 4px;
    gap: 8px !important;
    scrollbar-width: thin;
}}
[data-testid="stPills"] button,
button[data-testid="stBaseButton-pills"] {{
    background: var(--vda-surface) !important;
    border: 1px solid var(--vda-border) !important;
    border-radius: 999px !important;
    padding: 7px 14px !important;
    font-size: 13.5px !important;
    font-weight: 500 !important;
    color: var(--vda-text) !important;
    white-space: nowrap !important;
    flex: 0 0 auto !important;
    transition: all var(--vda-transition) !important;
}}
[data-testid="stPills"] button p,
button[data-testid="stBaseButton-pills"] p {{
    color: var(--vda-text) !important;
}}
[data-testid="stPills"] button:hover,
button[data-testid="stBaseButton-pills"]:hover {{
    border-color: var(--vda-accent) !important;
    background: var(--vda-raised) !important;
    color: #FFFFFF !important;
}}
[data-testid="stPills"] button[aria-checked="true"],
[data-testid="stPills"] button[kind="pillsActive"],
button[data-testid="stBaseButton-pillsActive"] {{
    background: var(--vda-accent-tint) !important;
    border-color: var(--vda-accent) !important;
    color: #93C5FD !important;
    font-weight: 600 !important;
}}
[data-testid="stPills"] button[aria-checked="true"] p,
[data-testid="stPills"] button[kind="pillsActive"] p,
button[data-testid="stBaseButton-pillsActive"] p {{
    color: #93C5FD !important;
}}

/* Underlined Tabs with gradient highlight */
[data-testid="stTabs"] [role="tablist"] {{
    gap: 8px;
    border-bottom: 1px solid var(--vda-border);
    padding-bottom: 0;
    margin-bottom: var(--vda-space-2);
}}
[data-testid="stTabs"] button[role="tab"] {{
    padding: 10px 16px !important;
    font-size: 14.5px !important;
    font-weight: 500 !important;
    color: var(--vda-text-muted) !important;
    border-bottom: 2px solid transparent !important;
    border-radius: 0 !important;
    background: transparent !important;
    transition: color var(--vda-transition) !important;
}}
[data-testid="stTabs"] button[role="tab"] p {{
    color: var(--vda-text-muted) !important;
}}
[data-testid="stTabs"] button[role="tab"]:hover,
[data-testid="stTabs"] button[role="tab"]:hover p {{
    color: var(--vda-text) !important;
}}
[data-testid="stTabs"] button[role="tab"][aria-selected="true"],
[data-testid="stTabs"] button[role="tab"][aria-selected="true"] p {{
    color: var(--vda-text) !important;
    font-weight: 600 !important;
}}
[data-testid="stTabs"] [data-baseweb="tab-highlight"] {{
    background: var(--vda-accent-grad) !important;
    height: 3px !important;
    border-radius: 999px !important;
}}

/* Progress status block (st.status) */
[data-testid="stStatusWidget"] {{
    background: var(--vda-surface) !important;
    border: 1px solid var(--vda-border) !important;
    border-radius: var(--vda-radius) !important;
    box-shadow: var(--vda-shadow) !important;
    margin: var(--vda-space-2) 0 !important;
    color: var(--vda-text) !important;
}}
[data-testid="stStatusWidget"] summary,
[data-testid="stStatusWidget"] summary p {{
    font-weight: 600 !important;
    font-size: 14.5px !important;
    color: var(--vda-text) !important;
}}

/* Spoken summary card with audio player inside */
[data-testid="stVerticalBlockBorderWrapper"]:has(.vda-summary-marker) {{
    background: linear-gradient(135deg, rgba(59, 130, 246, 0.14) 0%, rgba(139, 92, 246, 0.12) 100%), var(--vda-surface) !important;
    border: 1px solid var(--vda-accent-border) !important;
    border-left: 4px solid var(--vda-accent) !important;
    border-radius: var(--vda-radius) !important;
    box-shadow: var(--vda-accent-glow) !important;
    padding: var(--vda-space-2) var(--vda-space-3) !important;
    margin: var(--vda-space-2) 0 var(--vda-space-3) 0 !important;
}}
.vda-summary-text {{
    font-size: 16.5px;
    font-weight: 600;
    color: var(--vda-text);
    line-height: 1.55;
    margin: 4px 0 12px 0;
}}

/* Transcript and correction diff boxes */
.vda-transcript-box {{
    background: var(--vda-surface);
    border: 1px solid var(--vda-border);
    border-radius: var(--vda-radius);
    padding: var(--vda-space-2);
    margin: var(--vda-space-1) 0 var(--vda-space-2) 0;
    font-size: 15px;
    line-height: 1.55;
    color: var(--vda-text);
}}
.vda-diff-old {{
    background: var(--vda-warning-bg);
    color: var(--vda-warning);
    border: 1px solid var(--vda-warning-border);
    padding: 1px 6px;
    border-radius: 5px;
    font-weight: 600;
}}
.vda-diff-new {{
    background: var(--vda-accent-tint);
    color: #93C5FD;
    border: 1px solid var(--vda-accent-border);
    padding: 1px 6px;
    border-radius: 5px;
    font-weight: 600;
}}

/* Routing info bar */
.vda-route-bar {{
    background: var(--vda-surface);
    border: 1px solid var(--vda-border);
    border-radius: var(--vda-radius);
    padding: 12px var(--vda-space-2);
    margin: var(--vda-space-1) 0 var(--vda-space-2) 0;
    font-size: 14px;
    color: var(--vda-text);
    display: flex;
    flex-wrap: wrap;
    gap: 8px var(--vda-space-3);
    align-items: center;
}}
.vda-route-key {{
    color: var(--vda-text-muted);
    font-weight: 600;
    margin-right: 6px;
}}
.vda-badge {{
    display: inline-block;
    background: var(--vda-accent-tint);
    color: #93C5FD;
    border: 1px solid var(--vda-accent-border);
    border-radius: 999px;
    padding: 2px 10px;
    font-size: 12px;
    font-weight: 600;
}}
.vda-badge-success {{
    display: inline-block;
    background: var(--vda-success-bg);
    color: var(--vda-success);
    border: 1px solid var(--vda-success-border);
    border-radius: 999px;
    padding: 2px 10px;
    font-size: 12px;
    font-weight: 600;
}}
.vda-badge-neutral {{
    display: inline-block;
    background: var(--vda-raised);
    color: var(--vda-text-muted);
    border: 1px solid var(--vda-border);
    border-radius: 999px;
    padding: 2px 10px;
    font-size: 12px;
    font-weight: 600;
}}

/* KPI cards: equal height, top gradient accent border */
.vda-kpi-card {{
    position: relative;
    overflow: hidden;
    background: var(--vda-surface);
    border: 1px solid var(--vda-border);
    border-radius: var(--vda-radius);
    box-shadow: var(--vda-shadow);
    padding: var(--vda-space-2);
    margin-bottom: var(--vda-space-3);
    min-height: 94px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
}}
.vda-kpi-card::before {{
    content: "";
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 3px;
    background: var(--vda-accent-grad);
}}
.vda-kpi-label {{
    font-size: 12px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--vda-text-muted);
    margin-bottom: 8px;
}}
.vda-kpi-value {{
    font-size: 24px;
    font-weight: 700;
    color: var(--vda-text);
    letter-spacing: -0.02em;
    line-height: 1.15;
    word-break: break-word;
}}

/* Warning, Refusal, and Clarification cards */
.vda-warning-card {{
    background: var(--vda-warning-bg);
    border: 1px solid var(--vda-warning-border);
    border-left: 4px solid var(--vda-warning);
    border-radius: var(--vda-radius);
    padding: var(--vda-space-2);
    margin: var(--vda-space-2) 0;
    color: var(--vda-text);
    font-size: 14.5px;
    line-height: 1.5;
}}
.vda-warning-title {{
    font-weight: 700;
    font-size: 15.5px;
    color: var(--vda-warning);
    margin-bottom: 4px;
}}
.vda-refusal-card {{
    background: var(--vda-error-bg);
    border: 1px solid var(--vda-error-border);
    border-left: 4px solid var(--vda-error);
    border-radius: var(--vda-radius);
    padding: var(--vda-space-2);
    margin: var(--vda-space-2) 0;
    color: var(--vda-text);
    font-size: 14.5px;
    line-height: 1.5;
}}
.vda-refusal-title {{
    font-weight: 700;
    font-size: 15.5px;
    color: var(--vda-error);
    margin-bottom: 4px;
}}
.vda-clarify-card {{
    background: var(--vda-accent-tint);
    border: 1px solid var(--vda-accent-border);
    border-left: 4px solid var(--vda-accent);
    border-radius: var(--vda-radius);
    padding: var(--vda-space-2);
    margin: var(--vda-space-2) 0;
    color: var(--vda-text);
    font-size: 15px;
    line-height: 1.5;
}}

/* SQL code block (darker than surface cards) */
[data-testid="stCode"] pre {{
    background-color: var(--vda-code-bg) !important;
    color: var(--vda-text) !important;
    border-radius: var(--vda-radius) !important;
    border: 1px solid var(--vda-border) !important;
    padding: var(--vda-space-2) !important;
    font-size: 13.5px !important;
}}
[data-testid="stCode"] code {{
    color: var(--vda-text) !important;
}}
[data-testid="stCode"] button {{
    color: var(--vda-text-muted) !important;
}}
.vda-sql-pills {{
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    align-items: center;
    margin-top: 8px;
    margin-bottom: 8px;
}}

/* Dataframe wrapper */
[data-testid="stDataFrame"] {{
    background: var(--vda-surface);
    border: 1px solid var(--vda-border);
    border-radius: var(--vda-radius);
    overflow: hidden;
}}

/* Performance Panel inside expander */
.vda-perf-header {{
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    flex-wrap: wrap;
    gap: var(--vda-space-2);
    padding-bottom: var(--vda-space-2);
    margin-bottom: var(--vda-space-2);
    border-bottom: 1px solid var(--vda-border);
}}
.vda-perf-value {{
    font-size: 30px;
    font-weight: 700;
    background: var(--vda-accent-grad);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    letter-spacing: -0.02em;
    line-height: 1.1;
}}
.vda-perf-table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 14px;
}}
.vda-perf-table th {{
    text-align: left;
    padding: 8px 10px;
    background: var(--vda-raised);
    color: var(--vda-text-muted);
    font-size: 12px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    border-bottom: 1px solid var(--vda-border);
}}
.vda-perf-table td {{
    padding: 8px 10px;
    border-bottom: 1px solid var(--vda-border);
    color: var(--vda-text);
    transition: background-color var(--vda-transition);
}}
.vda-perf-table tbody tr:hover td {{
    background: var(--vda-raised);
}}
.vda-perf-table tr:last-child td {{
    border-bottom: none;
}}
.vda-perf-slowest td {{
    background: var(--vda-warning-bg);
    font-weight: 600;
}}
.vda-perf-slowest:hover td {{
    background: var(--vda-warning-bg) !important;
}}
.vda-bar-track {{
    width: 100%;
    height: 6px;
    background: var(--vda-raised);
    border-radius: 999px;
    overflow: hidden;
}}
.vda-bar-fill {{
    height: 100%;
    background: var(--vda-accent-grad);
    border-radius: 999px;
}}
.vda-bar-fill-slowest {{
    height: 100%;
    background: var(--vda-warning);
    border-radius: 999px;
}}

/* Sidebar History items */
.vda-history-item {{
    background: var(--vda-raised);
    border: 1px solid var(--vda-border);
    border-radius: var(--vda-radius-sm);
    padding: 10px 12px;
    margin-bottom: 8px;
}}
.vda-history-meta {{
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 6px;
    margin-top: 6px;
    font-size: 12.5px;
    color: var(--vda-text-muted);
}}
.vda-history-sql {{
    margin-top: 6px;
}}
.vda-history-sql summary {{
    cursor: pointer;
    font-size: 12.5px;
    font-weight: 600;
    color: #93C5FD;
    user-select: none;
}}
.vda-history-sql pre {{
    background: var(--vda-code-bg);
    color: var(--vda-text);
    border: 1px solid var(--vda-border);
    border-radius: var(--vda-radius-sm);
    padding: 10px;
    margin-top: 6px;
    font-size: 12px;
    overflow-x: auto;
    white-space: pre-wrap;
    word-break: break-word;
}}

/* Empty state welcome panel with numbered tip cards (1, 2, 3) */
.vda-empty-panel {{
    background: var(--vda-surface);
    border: 1px solid var(--vda-border);
    border-radius: var(--vda-radius);
    box-shadow: var(--vda-shadow);
    padding: var(--vda-space-3);
    margin-top: var(--vda-space-2);
    margin-bottom: var(--vda-space-3);
}}
.vda-empty-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: var(--vda-space-2);
    margin-top: var(--vda-space-2);
    margin-bottom: var(--vda-space-3);
}}
.vda-tip-card {{
    background: var(--vda-raised);
    border: 1px solid var(--vda-border);
    border-radius: var(--vda-radius-sm);
    padding: var(--vda-space-2);
    display: flex;
    align-items: flex-start;
    gap: 12px;
    font-size: 14px;
    color: var(--vda-text);
    line-height: 1.45;
}}
.vda-tip-num {{
    flex: 0 0 26px;
    height: 26px;
    border-radius: 50%;
    background: var(--vda-accent-grad);
    color: #FFFFFF;
    font-size: 12.5px;
    font-weight: 700;
    display: inline-flex;
    align-items: center;
    justify-content: center;
}}
.vda-empty-sources {{
    border-top: 1px solid var(--vda-border);
    padding-top: var(--vda-space-2);
    display: flex;
    flex-direction: column;
    gap: 8px;
}}
.vda-empty-source-row {{
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px;
    font-size: 14px;
    color: var(--vda-text-muted);
}}
.vda-empty-source-row strong {{
    color: var(--vda-text);
}}

/* Buttons */
div.stButton > button {{
    border-radius: var(--vda-radius-sm) !important;
    font-family: var(--vda-font) !important;
    font-size: 14.5px !important;
    font-weight: 500 !important;
    min-height: 44px;
    transition: all var(--vda-transition) !important;
}}
div.stButton > button[kind="secondary"] {{
    background-color: var(--vda-raised) !important;
    color: var(--vda-text) !important;
    border: 1px solid var(--vda-border) !important;
}}
div.stButton > button[kind="secondary"]:hover {{
    border-color: var(--vda-accent) !important;
    color: #FFFFFF !important;
    background-color: #1F2D4D !important;
}}
div.stButton > button[kind="primary"] {{
    background: var(--vda-accent-grad) !important;
    color: #FFFFFF !important;
    border: none !important;
    font-weight: 600 !important;
    box-shadow: var(--vda-accent-glow) !important;
}}
div.stButton > button[kind="primary"]:hover {{
    filter: brightness(1.08);
    transform: translateY(-1px);
}}

/* Expander & Toast dark styling */
[data-testid="stExpander"] {{
    background: var(--vda-surface) !important;
    border: 1px solid var(--vda-border) !important;
    border-radius: var(--vda-radius) !important;
    box-shadow: var(--vda-shadow);
    color: var(--vda-text) !important;
}}
[data-testid="stExpander"] summary,
[data-testid="stExpander"] summary p {{
    color: var(--vda-text) !important;
    font-weight: 600 !important;
}}
[data-testid="stToast"] {{
    background: var(--vda-raised) !important;
    border: 1px solid var(--vda-border) !important;
    color: var(--vda-text) !important;
}}

/* Responsive adjustments for 1366x768 */
@media (max-width: 1400px) {{
    .block-container {{
        padding-left: var(--vda-space-2) !important;
        padding-right: var(--vda-space-2) !important;
    }}
    .vda-kpi-value {{
        font-size: 21px;
    }}
}}
</style>"""
