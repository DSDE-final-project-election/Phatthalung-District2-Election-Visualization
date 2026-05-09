import streamlit as st


APP_COLORS = {
    "app_bg": "#F1EDEC",
    "surface": "#FEFEFE",
    "surface_muted": "#F9F9F8",
    "sidebar_bg": "#404041",
    "sidebar_panel": "#FEFEFE",
    "text": "#404041",
    "text_muted": "#AA7E48",
    "text_inverse": "#FEFEFE",
    "border": "#E9E1D2",
    "accent": "#AA7E48",
    "accent_hover": "#ACAAA7",
    "accent_dark": "#8D8578",
    "accent_soft": "#E9E1D2",
    "brown-bark": "#5B3916ff",
}


def _font_face_css() -> str:
    return """
    @import url("https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Thai:wght@300;400;500;600;700&display=swap");
    """


def inject_global_theme() -> None:
    css_variables = "\n".join(
        f"--color-{name.replace('_', '-')}: {value};"
        for name, value in APP_COLORS.items()
    )

    st.markdown(
        f"""
        <style>
        {_font_face_css()}
        :root {{
            {css_variables}
            --color-divider: color-mix(in srgb, var(--color-accent-hover) 72%, var(--color-border));
            --font-sans: "IBM Plex Sans Thai", "Noto Sans Thai", Tahoma, Arial, sans-serif;
        }}

        html, body, .stApp, .stApp * {{
            font-family: var(--font-sans) !important;
            letter-spacing: 0 !important;
        }}

        .stApp {{
            background: var(--color-app-bg);
            color: var(--color-text);
        }}

        h1, h2, h3, h4, h5, h6,
        p, label, span, div {{
            color: inherit;
        }}

        section[data-testid="stSidebar"] {{
            background: var(--color-sidebar-bg);
        }}

        section[data-testid="stSidebar"] h1,
        section[data-testid="stSidebar"] h2,
        section[data-testid="stSidebar"] h3,
        section[data-testid="stSidebar"] label,
        section[data-testid="stSidebar"] [data-testid="stMetricLabel"],
        section[data-testid="stSidebar"] [data-testid="stMetricValue"] {{
            color: var(--color-text-inverse) !important;
        }}

        section[data-testid="stSidebar"] [data-baseweb="select"],
        section[data-testid="stSidebar"] [data-baseweb="select"] * {{
            color: var(--color-text) !important;
        }}

        .stTabs [data-baseweb="tab-list"] {{
            gap: 8px;
            border-bottom: 1px solid var(--color-divider);
        }}

        .stTabs [data-baseweb="tab"] {{
            color: var(--color-text);
            border-radius: 8px 8px 0 0;
            padding: 10px 14px;
        }}

        .stTabs [data-baseweb="tab"][aria-selected="true"] {{
            color: var(--color-accent-dark);
            border-bottom: 2px solid var(--color-accent);
        }}

        div[data-baseweb="select"] > div,
        div[data-baseweb="input"] > div,
        textarea,
        input {{
            background: var(--color-surface) !important;
            border-color: var(--color-border) !important;
            color: var(--color-text) !important;
        }}

        button[kind="primary"],
        button[kind="secondary"],
        .stButton > button {{
            background: var(--color-surface) !important;
            border: 1px solid var(--color-border) !important;
            color: var(--color-text) !important;
        }}

        button[kind="primary"]:hover,
        button[kind="secondary"]:hover,
        .stButton > button:hover {{
            border-color: var(--color-accent) !important;
            color: var(--color-accent-dark) !important;
        }}

        hr {{
            border-color: var(--color-divider) !important;
        }}

        div[data-testid="stMetric"],
        .element-container:has(.district-card),
        .element-container:has(.district-winner-card) {{
            font-family: var(--font-sans) !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )
