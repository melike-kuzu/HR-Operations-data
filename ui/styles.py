"""Global styling for the HR Decision Support Platform."""

from __future__ import annotations

import streamlit as st


COMPANY_TURQUOISE = "#00A7A5"
TEXT_PRIMARY = "#111111"
TEXT_SECONDARY = "#626262"
BORDER_COLOR = "#E3E7E7"
BACKGROUND = "#F7F8F8"
SURFACE = "#FFFFFF"
SURFACE_HOVER = "#F1F6F6"


def apply_global_styles() -> None:
    """Apply the shared visual system across the application."""

    st.markdown(
        f"""
<style>
:root {{
    --company-turquoise: {COMPANY_TURQUOISE};
    --text-primary: {TEXT_PRIMARY};
    --text-secondary: {TEXT_SECONDARY};
    --border-color: {BORDER_COLOR};
    --background: {BACKGROUND};
    --surface: {SURFACE};
    --surface-hover: {SURFACE_HOVER};
}}

/* ---------------------------------------------------------
   GLOBAL
--------------------------------------------------------- */

html,
body,
[data-testid="stAppViewContainer"],
[data-testid="stSidebar"],
[class*="css"] {{
    font-family:
        Inter,
        -apple-system,
        BlinkMacSystemFont,
        "Segoe UI",
        Arial,
        sans-serif;
}}

html,
body {{
    color: var(--text-primary);
}}

.stApp {{
    background: var(--background);
    color: var(--text-primary);
}}

#MainMenu,
footer {{
    visibility: hidden;
}}

header[data-testid="stHeader"] {{
    background: transparent;
}}

[data-testid="stToolbar"] {{
    visibility: visible;
}}

[data-testid="stDecoration"] {{
    display: none;
}}

.block-container {{
    width: 100%;
    max-width: 1500px;
    padding-top: 1.25rem;
    padding-right: 2rem;
    padding-bottom: 3rem;
    padding-left: 2rem;
}}

/* ---------------------------------------------------------
   SIDEBAR
--------------------------------------------------------- */

section[data-testid="stSidebar"] {{
    background: var(--surface);
    border-right: 1px solid var(--border-color);
}}

section[data-testid="stSidebar"] > div {{
    padding-top: 1.2rem;
}}

section[data-testid="stSidebar"] [data-testid="stSidebarNav"] {{
    padding-top: 0.25rem;
}}

section[data-testid="stSidebar"] [data-testid="stSidebarNavItems"] {{
    gap: 0.25rem;
}}

section[data-testid="stSidebar"] a {{
    color: var(--text-primary);
    text-decoration: none;
    border-radius: 8px;
}}

section[data-testid="stSidebar"] a:hover {{
    background: var(--surface-hover);
    color: var(--company-turquoise);
}}

section[data-testid="stSidebar"] a[aria-current="page"] {{
    background: var(--surface-hover);
    color: var(--company-turquoise);
    font-weight: 600;
}}

section[data-testid="stSidebar"] svg {{
    color: currentColor;
    fill: none;
}}

.sidebar-workspace {{
    padding: 3px 5px 18px;
    margin-bottom: 4px;
}}

.sidebar-workspace__label {{
    color: #777777;
    font-size: 11px;
    font-weight: 650;
    letter-spacing: 0.1em;
    text-transform: uppercase;
}}

.sidebar-workspace__title {{
    margin-top: 7px;
    color: var(--text-primary);
    font-size: 15px;
    font-weight: 650;
    letter-spacing: -0.01em;
}}

/* ---------------------------------------------------------
   TOP HEADER
--------------------------------------------------------- */

.platform-header {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    min-height: 84px;
    padding: 16px 22px;
    margin-bottom: 24px;
    background: var(--surface);
    border: 1px solid var(--border-color);
    border-radius: 12px;
}}

.platform-header__left {{
    display: flex;
    align-items: center;
    gap: 18px;
    min-width: 0;
}}

.platform-header__logo {{
    display: block;
    width: auto;
    max-width: 220px;
    height: 42px;
    object-fit: contain;
}}

.platform-header__logo-fallback {{
    color: var(--text-primary);
    font-size: 15px;
    font-weight: 700;
    letter-spacing: 0.08em;
}}

.platform-header__divider {{
    flex: 0 0 auto;
    width: 1px;
    height: 38px;
    background: var(--border-color);
}}

.platform-header__content {{
    min-width: 0;
}}

.platform-header__title {{
    margin: 0;
    color: var(--text-primary);
    font-size: 20px;
    font-weight: 650;
    letter-spacing: -0.025em;
    line-height: 1.2;
}}

.platform-header__subtitle {{
    margin-top: 5px;
    color: var(--text-secondary);
    font-size: 13px;
    line-height: 1.4;
}}


/* ---------------------------------------------------------
   PAGE HEADINGS
--------------------------------------------------------- */

.page-heading {{
    margin-bottom: 24px;
}}

.page-heading h1 {{
    margin: 0;
    color: var(--text-primary);
    font-size: 28px;
    font-weight: 650;
    letter-spacing: -0.035em;
    line-height: 1.15;
}}

.page-heading p {{
    max-width: 780px;
    margin: 8px 0 0;
    color: var(--text-secondary);
    font-size: 14px;
    line-height: 1.65;
}}

.section-title {{
    margin: 30px 0 14px;
    color: var(--text-primary);
    font-size: 17px;
    font-weight: 650;
    letter-spacing: -0.015em;
}}

/* ---------------------------------------------------------
   KPI CARDS
--------------------------------------------------------- */

.metric-card {{
    min-height: 132px;
    padding: 20px;
    background: var(--surface);
    border: 1px solid var(--border-color);
    border-radius: 12px;
}}

.metric-card__accent {{
    width: 34px;
    height: 3px;
    margin-bottom: 20px;
    background: var(--company-turquoise);
    border-radius: 999px;
}}

.metric-card__label {{
    color: var(--text-secondary);
    font-size: 13px;
    font-weight: 500;
}}

.metric-card__value {{
    margin-top: 8px;
    color: var(--text-primary);
    font-size: 30px;
    font-weight: 650;
    letter-spacing: -0.045em;
    line-height: 1.1;
}}

.metric-card__caption {{
    margin-top: 8px;
    color: var(--text-secondary);
    font-size: 12px;
    line-height: 1.45;
}}

/* ---------------------------------------------------------
   REPORT CARDS
--------------------------------------------------------- */

.report-card-link {{
    display: block;
    color: inherit;
    text-decoration: none !important;
    border-radius: 12px;
}}

.report-card-link:hover,
.report-card-link:visited,
.report-card-link:active {{
    color: inherit;
    text-decoration: none !important;
}}

.report-card-link:focus-visible {{
    border-radius: 12px;
    outline: 2px solid var(--company-turquoise);
    outline-offset: 3px;
}}

.report-card {{
    position: relative;
    min-height: 220px;
    padding: 22px;
    cursor: pointer;
    background: var(--surface);
    border: 1px solid var(--border-color);
    border-radius: 12px;
    transition:
        border-color 150ms ease,
        transform 150ms ease,
        background 150ms ease;
}}

.report-card-link:hover .report-card {{
    background: #FCFEFE;
    border-color: var(--company-turquoise);
    transform: translateY(-2px);
}}

.report-card__top {{
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
}}

.report-card__icon {{
    display: flex;
    align-items: center;
    justify-content: center;
    width: 38px;
    height: 38px;
    margin-bottom: 22px;
    color: var(--company-turquoise);
    background: #FAFDFD;
    border: 1px solid #CDE8E7;
    border-radius: 9px;
    font-size: 15px;
    font-weight: 650;
    letter-spacing: -0.02em;
}}

.report-card__external {{
    color: var(--text-secondary);
    font-size: 19px;
    line-height: 1;
    transition:
        color 150ms ease,
        transform 150ms ease;
}}

.report-card-link:hover .report-card__external {{
    color: var(--company-turquoise);
    transform: translate(2px, -2px);
}}

.report-card__title {{
    color: var(--text-primary);
    font-size: 16px;
    font-weight: 650;
    letter-spacing: -0.015em;
}}

.report-card__description {{
    min-height: 62px;
    margin-top: 8px;
    color: var(--text-secondary);
    font-size: 13px;
    line-height: 1.55;
}}

.report-card__footer {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-top: 20px;
    padding-top: 15px;
    color: var(--text-secondary);
    border-top: 1px solid var(--border-color);
    font-size: 12px;
}}

.report-card__status {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
}}

.report-card__status::before {{
    display: inline-block;
    width: 7px;
    height: 7px;
    flex: 0 0 auto;
    border-radius: 50%;
    content: "";
}}

.report-card__status--available::before {{
    background: var(--company-turquoise);
}}

.report-card__status--unavailable::before {{
    background: #9A9A9A;
}}

/* ---------------------------------------------------------
   GENERIC PANELS
--------------------------------------------------------- */

.empty-panel {{
    padding: 34px;
    background: var(--surface);
    border: 1px solid var(--border-color);
    border-radius: 12px;
    text-align: center;
}}

.empty-panel h3 {{
    margin: 0;
    color: var(--text-primary);
    font-size: 17px;
    font-weight: 650;
    letter-spacing: -0.015em;
}}

.empty-panel p {{
    max-width: 580px;
    margin: 10px auto 0;
    color: var(--text-secondary);
    font-size: 13px;
    line-height: 1.65;
}}

/* ---------------------------------------------------------
   STANDARD BUTTONS
--------------------------------------------------------- */

.stButton > button {{
    min-height: 40px;
    color: var(--text-primary);
    background: var(--surface);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    box-shadow: none;
    font-weight: 500;
    transition:
        border-color 150ms ease,
        color 150ms ease,
        background 150ms ease;
}}

.stButton > button:hover {{
    color: var(--company-turquoise);
    background: #FAFDFD;
    border-color: var(--company-turquoise);
}}

.stButton > button:focus {{
    border-color: var(--company-turquoise);
    box-shadow: 0 0 0 2px rgba(0, 167, 165, 0.12);
}}

/* ---------------------------------------------------------
   LINK BUTTONS
--------------------------------------------------------- */

div[data-testid="stLinkButton"] a {{
    min-height: 40px;
    color: var(--text-primary);
    background: var(--surface);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    box-shadow: none;
    font-weight: 500;
    text-decoration: none;
}}

div[data-testid="stLinkButton"] a:hover {{
    color: var(--company-turquoise);
    background: #FAFDFD;
    border-color: var(--company-turquoise);
}}

/* ---------------------------------------------------------
   DOWNLOAD BUTTONS
--------------------------------------------------------- */

[data-testid="stDownloadButton"] > button {{
    width: 100%;
    min-height: 40px;
    color: var(--text-primary);
    background: var(--surface);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    box-shadow: none;
    font-weight: 500;
    transition:
        border-color 150ms ease,
        color 150ms ease,
        background 150ms ease;
}}

[data-testid="stDownloadButton"] > button:hover {{
    color: var(--company-turquoise);
    background: #FAFDFD;
    border-color: var(--company-turquoise);
}}

[data-testid="stDownloadButton"] > button:focus {{
    border-color: var(--company-turquoise);
    box-shadow: 0 0 0 2px rgba(0, 167, 165, 0.12);
}}

/* ---------------------------------------------------------
   INPUTS
--------------------------------------------------------- */

[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input,
[data-testid="stSelectbox"] > div > div,
[data-testid="stMultiSelect"] > div > div {{
    background: var(--surface);
    border-color: var(--border-color);
    border-radius: 8px;
}}

[data-testid="stTextInput"] input:focus,
[data-testid="stNumberInput"] input:focus {{
    border-color: var(--company-turquoise);
    box-shadow: 0 0 0 1px var(--company-turquoise);
}}

/* ---------------------------------------------------------
   ALERTS
--------------------------------------------------------- */

[data-testid="stAlert"] {{
    color: var(--text-primary);
    background: var(--surface);
    border: 1px solid var(--border-color);
    border-radius: 10px;
}}

/* ---------------------------------------------------------
   DATAFRAME / TABLE AREA
--------------------------------------------------------- */

[data-testid="stDataFrame"] {{
    overflow: hidden;
    background: var(--surface);
    border: 1px solid var(--border-color);
    border-radius: 10px;
}}

[data-testid="stDataFrame"] iframe {{
    border-radius: 10px;
}}

/* ---------------------------------------------------------
   CAPTIONS
--------------------------------------------------------- */

[data-testid="stCaptionContainer"] {{
    color: var(--text-secondary);
}}

/* ---------------------------------------------------------
   SPINNERS
--------------------------------------------------------- */

[data-testid="stSpinner"] {{
    color: var(--text-secondary);
}}

/* ---------------------------------------------------------
   DIVIDERS
--------------------------------------------------------- */

hr {{
    border: 0;
    border-top: 1px solid var(--border-color);
}}

/* ---------------------------------------------------------
   RESPONSIVE
--------------------------------------------------------- */



@media (max-width: 850px) {{
    .block-container {{
        padding-right: 1rem;
        padding-left: 1rem;
    }}

    .platform-header {{
        min-height: auto;
        padding: 15px 16px;
    }}

    .platform-header__left {{
        gap: 12px;
    }}

    .platform-header__divider {{
        display: none;
    }}

    .platform-header__logo {{
        max-width: 155px;
        height: 34px;
    }}

    .platform-header__title {{
        font-size: 17px;
    }}

    .platform-header__subtitle {{
        font-size: 12px;
    }}

    .page-heading h1 {{
        font-size: 24px;
    }}

    .report-card {{
        min-height: auto;
    }}

    .report-card__description {{
        min-height: auto;
    }}
}}
/* ---------------------------------------------------------
   SIDEBAR DATA INFORMATION
--------------------------------------------------------- */

.sidebar-data-info {{
    margin-top: 28px;
    padding: 18px 4px 8px;
    border-top: 1px solid var(--border-color);
}}

.sidebar-data-info__label {{
    color: #858585;
    font-size: 10px;
    font-weight: 650;
    letter-spacing: 0.1em;
    text-transform: uppercase;
}}

.sidebar-data-info__value {{
    margin-top: 7px;
    color: var(--text-primary);
    font-size: 13px;
    font-weight: 600;
    line-height: 1.45;
}}

.sidebar-data-info__caption {{
    margin-top: 4px;
    color: var(--text-secondary);
    font-size: 11px;
    line-height: 1.45;
}}
</style>
        """,
        unsafe_allow_html=True,
    )