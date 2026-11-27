"""
Shared design system and CSS styles for the Voice Data Analyst Streamlit app.
Defines all theme tokens as CSS custom properties (:root) and applies a calm,
modern analytics layout without emojis or em dashes.
"""

ACCENT_PRIMARY = "#2563EB"
ACCENT_DARK = "#1D4ED8"
ACCENT_SOFT = "#EFF6FF"
ACCENT_BORDER = "#BFDBFE"

TEXT_PRIMARY = "#0F172A"
TEXT_SECONDARY = "#475569"
TEXT_MUTED = "#64748B"

BG_SURFACE = "#FFFFFF"
BG_SUBTLE = "#F8FAFC"
BORDER_SUBTLE = "#E2E8F0"

WARNING_BG = "#FFFBEB"
WARNING_BORDER = "#FDE68A"
WARNING_ACCENT = "#D97706"
WARNING_TEXT = "#92400E"

ERROR_BG = "#FEF2F2"
ERROR_BORDER = "#FECACA"
ERROR_ACCENT = "#DC2626"
ERROR_TEXT = "#991B1B"

SUCCESS_BG = "#F0FDF4"
SUCCESS_BORDER = "#BBF7D0"
SUCCESS_ACCENT = "#16A34A"
SUCCESS_TEXT = "#166534"

CHART_PALETTE = [
    "#2563EB",
    "#3B82F6",
    "#0EA5E9",
    "#6366F1",
    "#1D4ED8",
    "#60A5FA",
    "#93C5FD",
]


def get_app_css() -> str:
    """Return the global stylesheet for the Streamlit interface."""
    return f"""<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

:root {{
    --vda-accent: {ACCENT_PRIMARY};
    --vda-accent-hover: {ACCENT_DARK};
    --vda-accent-tint: {ACCENT_SOFT};
    --vda-accent-border: {ACCENT_BORDER};

    --vda-bg: {BG_SUBTLE};
    --vda-surface: {BG_SURFACE};
    --vda-border: {BORDER_SUBTLE};
    --vda-text: {TEXT_PRIMARY};
    --vda-text-secondary: {TEXT_SECONDARY};
    --vda-text-muted: {TEXT_MUTED};

    --vda-success: {SUCCESS_ACCENT};
    --vda-success-bg: {SUCCESS_BG};
    --vda-success-border: {SUCCESS_BORDER};
    --vda-success-text: {SUCCESS_TEXT};

    --vda-warning: {WARNING_ACCENT};
    --vda-warning-bg: {WARNING_BG};
    --vda-warning-border: {WARNING_BORDER};
    --vda-warning-text: {WARNING_TEXT};

    --vda-error: {ERROR_ACCENT};
    --vda-error-bg: {ERROR_BG};
    --vda-error-border: {ERROR_BORDER};
    --vda-error-text: {ERROR_TEXT};

    --vda-font: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    --vda-space-1: 4px;
    --vda-space-2: 8px;
    --vda-space-3: 12px;
    --vda-space-4: 16px;
    --vda-space-6: 24px;
    --vda-space-8: 32px;

    --vda-radius: 12px;
    --vda-radius-sm: 8px;
    --vda-shadow: 0 1px 3px rgba(15, 23, 42, 0.08);
    --vda-transition: 150ms ease;
}}

/* Hide Streamlit Deploy button and default footer */
[data-testid="stAppDeployButton"],
footer,
#MainMenu {{
    display: none !important;
}}

/* Transparent/light top header bar so it never renders black over the title */
header[data-testid="stHeader"] {{
    background: var(--vda-bg) !important;
    border-bottom: none !important;
}}
header[data-testid="stHeader"] button,
header[data-testid="stHeader"] svg {{
    color: var(--vda-text-secondary) !important;
    fill: var(--vda-text-secondary) !important;
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
    padding-bottom: var(--vda-space-8) !important;
    padding-left: var(--vda-space-6) !important;
    padding-right: var(--vda-space-6) !important;
    max-width: 1280px;
}}

.stMarkdown, .stMarkdown p, .stMarkdown li, label, .stTextInput input {{
    font-family: var(--vda-font);
    font-size: 15px;
    line-height: 1.55;
}}

.stCaption {{
    color: var(--vda-text-muted) !important;
    font-size: 13.5px !important;
}}

/* Tidy scrollbar */
::-webkit-scrollbar {{
    width: 8px;
    height: 8px;
}}
::-webkit-scrollbar-track {{
    background: var(--vda-bg);
}}
::-webkit-scrollbar-thumb {{
    background: #CBD5E1;
    border-radius: 999px;
}}
::-webkit-scrollbar-thumb:hover {{
    background: #94A3B8;
}}

/* Focus rings in accent color */
button:focus-visible,
input:focus-visible,
textarea:focus-visible,
[tabindex]:focus-visible {{
    outline: 2px solid var(--vda-accent) !important;
    outline-offset: 2px !important;
    box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.18) !important;
}}

/* Compact Header Bar */
.vda-header {{
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    flex-wrap: wrap;
    gap: var(--vda-space-3) var(--vda-space-4);
    padding-bottom: var(--vda-space-4);
    margin-bottom: var(--vda-space-4);
    border-bottom: 1px solid var(--vda-border);
}}
.vda-title {{
    font-size: 28px;
    font-weight: 700;
    color: var(--vda-text);
    letter-spacing: -0.025em;
    line-height: 1.2;
    margin: 0 0 var(--vda-space-1) 0;
}}
.vda-subtitle {{
    font-size: 15px;
    color: var(--vda-text-muted);
    margin: 0;
    line-height: 1.45;
}}
.vda-status-pills {{
    display: flex;
    flex-wrap: wrap;
    gap: var(--vda-space-2);
    align-items: center;
    padding-top: var(--vda-space-1);
}}
.vda-status-pill {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: var(--vda-surface);
    border: 1px solid var(--vda-border);
    border-radius: 999px;
    padding: 4px 12px;
    font-size: 12.5px;
    font-weight: 500;
    color: var(--vda-text-secondary);
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
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

/* Small uppercase section label */
.vda-section-label {{
    font-size: 12px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: var(--vda-text-muted);
    margin: 0 0 var(--vda-space-2) 0;
}}

/* Sidebar styling (~320px wide) */
section[data-testid="stSidebar"] {{
    min-width: 320px !important;
    max-width: 320px !important;
    background-color: var(--vda-surface) !important;
    border-right: 1px solid var(--vda-border);
    color: var(--vda-text) !important;
}}
section[data-testid="stSidebar"] .block-container {{
    padding-top: var(--vda-space-6) !important;
    padding-left: var(--vda-space-4) !important;
    padding-right: var(--vda-space-4) !important;
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
section[data-testid="stSidebar"] [data-testid="stTabs"] button {{
    padding: 8px 10px !important;
    font-size: 13.5px !important;
}}

/* Explicit light styling for file uploader dropzone */
[data-testid="stFileUploader"] section[data-testid="stFileUploaderDropzone"] {{
    background-color: var(--vda-bg) !important;
    border: 1px dashed #CBD5E1 !important;
    border-radius: var(--vda-radius-sm) !important;
    color: var(--vda-text) !important;
}}
[data-testid="stFileUploaderDropzoneInstructions"],
[data-testid="stFileUploaderDropzoneInstructions"] span,
[data-testid="stFileUploaderDropzoneInstructions"] small,
[data-testid="stFileUploader"] label {{
    color: var(--vda-text-secondary) !important;
}}
[data-testid="stFileUploaderDropzone"] button {{
    background-color: var(--vda-surface) !important;
    color: var(--vda-text) !important;
    border: 1px solid var(--vda-border) !important;
}}
[data-testid="stFileUploaderDropzone"] button:hover {{
    border-color: var(--vda-accent) !important;
    color: var(--vda-accent) !important;
}}

/* Explicit light styling for text inputs */
[data-testid="stTextInput"] input {{
    background-color: var(--vda-surface) !important;
    color: var(--vda-text) !important;
    border: 1px solid var(--vda-border) !important;
    border-radius: var(--vda-radius-sm) !important;
}}
[data-testid="stTextInput"] input::placeholder {{
    color: var(--vda-text-muted) !important;
}}

/* Sidebar source cards */
.vda-source-card {{
    background: var(--vda-bg);
    border: 1px solid var(--vda-border);
    border-radius: var(--vda-radius);
    padding: var(--vda-space-3) var(--vda-space-4);
    margin-bottom: var(--vda-space-1);
    transition: border-color var(--vda-transition), box-shadow var(--vda-transition);
}}
.vda-source-card:hover {{
    border-color: #CBD5E1;
    box-shadow: var(--vda-shadow);
}}
.vda-source-header {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: var(--vda-space-2);
    margin-bottom: var(--vda-space-1);
}}
.vda-source-name {{
    font-weight: 600;
    font-size: 14.5px;
    color: var(--vda-text);
    word-break: break-word;
}}
.vda-source-desc {{
    font-size: 13.5px;
    color: var(--vda-text-secondary);
    line-height: 1.4;
    margin-bottom: var(--vda-space-1);
}}
.vda-source-tables {{
    font-size: 12.5px;
    color: var(--vda-text-muted);
    line-height: 1.35;
}}

/* Colored engine badges */
.vda-engine-badge {{
    display: inline-block;
    border-radius: 999px;
    padding: 2px 9px;
    font-size: 11.5px;
    font-weight: 600;
    letter-spacing: 0.03em;
    text-transform: uppercase;
    white-space: nowrap;
}}
.vda-engine-sqlite {{
    background: #EFF6FF;
    color: #1D4ED8;
    border: 1px solid #BFDBFE;
}}
.vda-engine-duckdb {{
    background: #ECFDF5;
    color: #047857;
    border: 1px solid #A7F3D0;
}}
.vda-engine-postgres {{
    background: #F5F3FF;
    color: #6D28D9;
    border: 1px solid #DDD6FE;
}}
.vda-engine-default {{
    background: var(--vda-bg);
    color: var(--vda-text-secondary);
    border: 1px solid var(--vda-border);
}}

/* Quiet text-style Remove button in sidebar */
section[data-testid="stSidebar"] button[kind="tertiary"] {{
    color: var(--vda-text-muted) !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    padding: 2px 6px !important;
    min-height: 28px !important;
    margin-bottom: var(--vda-space-2) !important;
    transition: color var(--vda-transition), background-color var(--vda-transition) !important;
}}
section[data-testid="stSidebar"] button[kind="tertiary"]:hover {{
    color: var(--vda-error) !important;
    background-color: var(--vda-error-bg) !important;
}}

/* Example question chips (st.pills) */
[data-testid="stPills"] button,
button[data-testid="stBaseButton-pills"] {{
    background: var(--vda-surface) !important;
    border: 1px solid var(--vda-border) !important;
    border-radius: 999px !important;
    padding: 7px 14px !important;
    font-size: 13.5px !important;
    font-weight: 500 !important;
    color: var(--vda-text) !important;
    transition: all var(--vda-transition) !important;
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04) !important;
}}
[data-testid="stPills"] button p,
button[data-testid="stBaseButton-pills"] p {{
    color: var(--vda-text) !important;
}}
[data-testid="stPills"] button:hover,
button[data-testid="stBaseButton-pills"]:hover {{
    border-color: var(--vda-accent-border) !important;
    background: var(--vda-accent-tint) !important;
    color: var(--vda-accent-hover) !important;
}}
[data-testid="stPills"] button:hover p,
button[data-testid="stBaseButton-pills"]:hover p {{
    color: var(--vda-accent-hover) !important;
}}
[data-testid="stPills"] button[aria-checked="true"],
[data-testid="stPills"] button[kind="pillsActive"],
button[data-testid="stBaseButton-pillsActive"] {{
    background: var(--vda-accent-tint) !important;
    border-color: var(--vda-accent) !important;
    color: var(--vda-accent-hover) !important;
    font-weight: 600 !important;
}}
[data-testid="stPills"] button[aria-checked="true"] p,
[data-testid="stPills"] button[kind="pillsActive"] p,
button[data-testid="stBaseButton-pillsActive"] p {{
    color: var(--vda-accent-hover) !important;
}}

/* Bordered containers styled as crisp white cards */
[data-testid="stVerticalBlockBorderWrapper"] {{
    background: var(--vda-surface) !important;
    border: 1px solid var(--vda-border) !important;
    border-radius: var(--vda-radius) !important;
    box-shadow: var(--vda-shadow);
    padding: var(--vda-space-3) var(--vda-space-4);
    margin-bottom: var(--vda-space-4);
}}

/* Prominent microphone input area (explicit light styling) */
[data-testid="stAudioInput"] {{
    background: var(--vda-accent-tint) !important;
    border: 1px dashed var(--vda-accent-border) !important;
    border-radius: var(--vda-radius);
    padding: var(--vda-space-4);
    color: var(--vda-text) !important;
    transition: border-color var(--vda-transition), background-color var(--vda-transition);
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
[data-testid="stAudioInput"]:hover {{
    border-color: var(--vda-accent) !important;
}}

/* Underlined Tabs */
[data-testid="stTabs"] [role="tablist"] {{
    gap: var(--vda-space-2);
    border-bottom: 1px solid var(--vda-border);
    padding-bottom: 0;
    margin-bottom: var(--vda-space-4);
}}
[data-testid="stTabs"] button[role="tab"] {{
    padding: 10px 16px !important;
    font-size: 14.5px !important;
    font-weight: 500 !important;
    color: var(--vda-text-secondary) !important;
    border-bottom: 2px solid transparent !important;
    border-radius: 0 !important;
    background: transparent !important;
    transition: color var(--vda-transition), border-color var(--vda-transition) !important;
}}
[data-testid="stTabs"] button[role="tab"] p {{
    color: var(--vda-text-secondary) !important;
}}
[data-testid="stTabs"] button[role="tab"]:hover,
[data-testid="stTabs"] button[role="tab"]:hover p {{
    color: var(--vda-text) !important;
}}
[data-testid="stTabs"] button[role="tab"][aria-selected="true"],
[data-testid="stTabs"] button[role="tab"][aria-selected="true"] p {{
    color: var(--vda-accent) !important;
    font-weight: 600 !important;
}}
[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {{
    border-bottom: 2px solid var(--vda-accent) !important;
}}
[data-testid="stTabs"] [data-baseweb="tab-highlight"] {{
    background-color: var(--vda-accent) !important;
    height: 2px !important;
}}

/* Progress status block (st.status) */
[data-testid="stStatusWidget"] {{
    background: var(--vda-surface) !important;
    border: 1px solid var(--vda-border) !important;
    border-radius: var(--vda-radius) !important;
    box-shadow: var(--vda-shadow) !important;
    margin: var(--vda-space-3) 0 var(--vda-space-4) 0 !important;
}}
[data-testid="stStatusWidget"] summary {{
    font-weight: 600 !important;
    font-size: 14.5px !important;
    color: var(--vda-text) !important;
    padding: var(--vda-space-3) var(--vda-space-4) !important;
}}

/* Spoken summary container with audio player inside */
[data-testid="stVerticalBlockBorderWrapper"]:has(.vda-summary-marker) {{
    background: var(--vda-accent-tint) !important;
    border: 1px solid var(--vda-accent-border) !important;
    border-left: 4px solid var(--vda-accent) !important;
    border-radius: var(--vda-radius) !important;
    box-shadow: var(--vda-shadow) !important;
    padding: var(--vda-space-4) var(--vda-space-6) !important;
    margin: var(--vda-space-4) 0 !important;
}}
.vda-summary-text {{
    font-size: 16px;
    font-weight: 600;
    color: var(--vda-text);
    line-height: 1.55;
    margin: var(--vda-space-1) 0 var(--vda-space-2) 0;
}}

/* Generic card label */
.vda-card-label {{
    font-size: 12px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--vda-text-muted);
    margin-bottom: var(--vda-space-2);
}}

/* Transcript and correction diff boxes */
.vda-transcript-box {{
    background: var(--vda-surface);
    border: 1px solid var(--vda-border);
    border-radius: var(--vda-radius);
    box-shadow: var(--vda-shadow);
    padding: var(--vda-space-3) var(--vda-space-4);
    margin: var(--vda-space-2) 0 var(--vda-space-3) 0;
    font-size: 15px;
    line-height: 1.55;
    color: var(--vda-text);
}}
.vda-diff-old {{
    background: var(--vda-warning-bg);
    color: var(--vda-warning-text);
    border: 1px solid var(--vda-warning-border);
    padding: 1px 6px;
    border-radius: 5px;
    font-weight: 600;
}}
.vda-diff-new {{
    background: var(--vda-accent-tint);
    color: var(--vda-accent-hover);
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
    box-shadow: var(--vda-shadow);
    padding: var(--vda-space-3) var(--vda-space-4);
    margin: var(--vda-space-2) 0 var(--vda-space-4) 0;
    font-size: 14px;
    color: var(--vda-text);
    display: flex;
    flex-wrap: wrap;
    gap: var(--vda-space-2) var(--vda-space-6);
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
    color: var(--vda-accent-hover);
    border: 1px solid var(--vda-accent-border);
    border-radius: 999px;
    padding: 2px 10px;
    font-size: 12px;
    font-weight: 600;
}}
.vda-badge-success {{
    display: inline-block;
    background: var(--vda-success-bg);
    color: var(--vda-success-text);
    border: 1px solid var(--vda-success-border);
    border-radius: 999px;
    padding: 2px 10px;
    font-size: 12px;
    font-weight: 600;
}}
.vda-badge-neutral {{
    display: inline-block;
    background: var(--vda-bg);
    color: var(--vda-text-secondary);
    border: 1px solid var(--vda-border);
    border-radius: 999px;
    padding: 2px 10px;
    font-size: 12px;
    font-weight: 600;
}}

/* KPI cards: equal height, top accent border */
.vda-kpi-card {{
    background: var(--vda-surface);
    border: 1px solid var(--vda-border);
    border-top: 3px solid var(--vda-accent);
    border-radius: var(--vda-radius);
    box-shadow: var(--vda-shadow);
    padding: var(--vda-space-4);
    margin-bottom: var(--vda-space-4);
    min-height: 92px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
}}
.vda-kpi-label {{
    font-size: 12px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--vda-text-muted);
    margin-bottom: var(--vda-space-2);
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
    box-shadow: var(--vda-shadow);
    padding: var(--vda-space-4);
    margin: var(--vda-space-3) 0;
    color: var(--vda-warning-text);
    font-size: 14.5px;
    line-height: 1.5;
}}
.vda-warning-title {{
    font-weight: 700;
    font-size: 15.5px;
    margin-bottom: var(--vda-space-1);
}}
.vda-refusal-card {{
    background: var(--vda-error-bg);
    border: 1px solid var(--vda-error-border);
    border-left: 4px solid var(--vda-error);
    border-radius: var(--vda-radius);
    box-shadow: var(--vda-shadow);
    padding: var(--vda-space-4);
    margin: var(--vda-space-3) 0;
    color: var(--vda-error-text);
    font-size: 14.5px;
    line-height: 1.5;
}}
.vda-refusal-title {{
    font-weight: 700;
    font-size: 15.5px;
    margin-bottom: var(--vda-space-1);
}}
.vda-clarify-card {{
    background: var(--vda-accent-tint);
    border: 1px solid var(--vda-accent-border);
    border-left: 4px solid var(--vda-accent);
    border-radius: var(--vda-radius);
    box-shadow: var(--vda-shadow);
    padding: var(--vda-space-4);
    margin: var(--vda-space-3) 0;
    color: var(--vda-text);
    font-size: 15px;
    line-height: 1.5;
}}

/* Dark SQL code block styling */
[data-testid="stCode"] pre {{
    background-color: #0F172A !important;
    color: #E2E8F0 !important;
    border-radius: var(--vda-radius) !important;
    border: 1px solid #1E293B !important;
    padding: var(--vda-space-4) !important;
    font-size: 13.5px !important;
}}
[data-testid="stCode"] code {{
    color: #E2E8F0 !important;
}}
[data-testid="stCode"] button {{
    color: #CBD5E1 !important;
}}
.vda-sql-pills {{
    display: flex;
    flex-wrap: wrap;
    gap: var(--vda-space-2);
    align-items: center;
    margin-top: var(--vda-space-2);
    margin-bottom: var(--vda-space-2);
}}

/* Data table card polish */
[data-testid="stDataFrame"] {{
    background: var(--vda-surface);
    border: 1px solid var(--vda-border);
    border-radius: var(--vda-radius);
    overflow: hidden;
    box-shadow: var(--vda-shadow);
}}

/* Compact Performance Panel card */
.vda-perf-card {{
    background: var(--vda-surface);
    border: 1px solid var(--vda-border);
    border-radius: var(--vda-radius);
    box-shadow: var(--vda-shadow);
    padding: var(--vda-space-4);
    margin-top: var(--vda-space-2);
    margin-bottom: var(--vda-space-4);
}}
.vda-perf-header {{
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    flex-wrap: wrap;
    gap: var(--vda-space-3);
    padding-bottom: var(--vda-space-3);
    margin-bottom: var(--vda-space-3);
    border-bottom: 1px solid var(--vda-border);
}}
.vda-perf-value {{
    font-size: 28px;
    font-weight: 700;
    color: var(--vda-accent);
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
    background: var(--vda-bg);
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
    background: var(--vda-bg);
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
    background: #E2E8F0;
    border-radius: 999px;
    overflow: hidden;
}}
.vda-bar-fill {{
    height: 100%;
    background: var(--vda-accent);
    border-radius: 999px;
}}
.vda-bar-fill-slowest {{
    height: 100%;
    background: var(--vda-warning);
    border-radius: 999px;
}}

/* History list items */
.vda-history-item {{
    background: var(--vda-surface);
    border: 1px solid var(--vda-border);
    border-radius: var(--vda-radius-sm);
    padding: var(--vda-space-3) var(--vda-space-4);
    margin-bottom: var(--vda-space-2);
}}
.vda-history-meta {{
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--vda-space-2);
    margin-top: var(--vda-space-1);
    font-size: 13px;
    color: var(--vda-text-muted);
}}
.vda-history-sql {{
    margin-top: var(--vda-space-2);
}}
.vda-history-sql summary {{
    cursor: pointer;
    font-size: 13px;
    font-weight: 600;
    color: var(--vda-accent);
    user-select: none;
}}
.vda-history-sql pre {{
    background: #0F172A;
    color: #E2E8F0;
    border-radius: var(--vda-radius-sm);
    padding: var(--vda-space-3);
    margin-top: var(--vda-space-2);
    font-size: 12.5px;
    overflow-x: auto;
    white-space: pre-wrap;
    word-break: break-word;
}}

/* Empty state welcome panel */
.vda-empty-panel {{
    background: var(--vda-surface);
    border: 1px solid var(--vda-border);
    border-radius: var(--vda-radius);
    box-shadow: var(--vda-shadow);
    padding: var(--vda-space-6);
    margin-top: var(--vda-space-2);
    margin-bottom: var(--vda-space-4);
}}
.vda-empty-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: var(--vda-space-3);
    margin-top: var(--vda-space-3);
    margin-bottom: var(--vda-space-4);
}}
.vda-tip-card {{
    background: var(--vda-bg);
    border: 1px solid var(--vda-border);
    border-radius: var(--vda-radius-sm);
    padding: var(--vda-space-3) var(--vda-space-4);
    font-size: 14px;
    color: var(--vda-text);
    line-height: 1.45;
}}
.vda-empty-sources {{
    border-top: 1px solid var(--vda-border);
    padding-top: var(--vda-space-3);
    display: flex;
    flex-direction: column;
    gap: var(--vda-space-2);
}}
.vda-empty-source-row {{
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--vda-space-2);
    font-size: 14px;
    color: var(--vda-text-secondary);
}}

/* Buttons */
div.stButton > button {{
    border-radius: var(--vda-radius-sm) !important;
    font-family: var(--vda-font) !important;
    font-size: 14.5px !important;
    font-weight: 500 !important;
    transition: all var(--vda-transition) !important;
}}
div.stButton > button[kind="secondary"] {{
    background-color: var(--vda-surface) !important;
    color: var(--vda-text) !important;
    border: 1px solid var(--vda-border) !important;
}}
div.stButton > button[kind="secondary"]:hover {{
    border-color: var(--vda-accent) !important;
    color: var(--vda-accent) !important;
    background-color: var(--vda-accent-tint) !important;
}}
div.stButton > button[kind="primary"] {{
    background-color: var(--vda-accent) !important;
    color: #FFFFFF !important;
    border: none !important;
    font-weight: 600 !important;
    box-shadow: 0 1px 2px rgba(37, 99, 235, 0.25) !important;
}}
div.stButton > button[kind="primary"]:hover {{
    background-color: var(--vda-accent-hover) !important;
    box-shadow: 0 2px 6px rgba(37, 99, 235, 0.3) !important;
}}

/* Expander polish */
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
}}

/* Responsive adjustments for 1366x768 and smaller laptops */
@media (max-width: 1400px) {{
    .block-container {{
        padding-left: var(--vda-space-4) !important;
        padding-right: var(--vda-space-4) !important;
    }}
    .vda-kpi-value {{
        font-size: 21px;
    }}
}}
</style>"""
