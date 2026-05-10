import base64
import mimetypes
from functools import lru_cache
from pathlib import Path

import streamlit as st


ROOT_DIR = Path(__file__).resolve().parents[1]
FONT_DIR = ROOT_DIR / "assets" / "fonts"
LOCAL_FONT_NAME = "Election Local"
FONT_FAMILY = f'"IBM Plex Sans Thai", "{LOCAL_FONT_NAME}", "Noto Sans Thai", Tahoma, Arial, sans-serif'


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
    "signal_positive": "#5B7E3C",
    "signal_warning": "#FFD65A",
    "signal_orange": "#FF9D23",
    "signal_negative": "#EA5252",
}


def _font_weight_from_name(name: str) -> str:
    lower_name = name.lower()
    if "variable" in lower_name or "vf" in lower_name:
        return "300 900"
    if "black" in lower_name:
        return "900"
    if "extrabold" in lower_name or "extra-bold" in lower_name:
        return "800"
    if "bold" in lower_name:
        return "700"
    if "semibold" in lower_name or "semi-bold" in lower_name:
        return "600"
    if "medium" in lower_name:
        return "500"
    if "light" in lower_name:
        return "300"
    return "400"


def _font_format(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".woff2":
        return "woff2"
    if suffix == ".woff":
        return "woff"
    if suffix == ".otf":
        return "opentype"
    return "truetype"


@lru_cache(maxsize=1)
def font_face_css() -> str:
    font_files = []
    for pattern in ("*.woff2", "*.woff", "*.otf", "*.ttf"):
        font_files.extend(FONT_DIR.glob(pattern))

    if not font_files:
        return ""

    rules = []
    for path in sorted(font_files):
        mime_type = mimetypes.guess_type(path.name)[0] or "font/woff2"
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        style = "italic" if "italic" in path.stem.lower() else "normal"
        weight = _font_weight_from_name(path.stem)
        rules.append(
            f"""
            @font-face {{
                font-family: "{LOCAL_FONT_NAME}";
                src: url("data:{mime_type};base64,{encoded}") format("{_font_format(path)}");
                font-style: {style};
                font-weight: {weight};
                font-display: swap;
            }}
            """
        )
    return "\n".join(rules)


def inject_global_theme() -> None:
    css_variables = "\n".join(
        f"--color-{name.replace('_', '-')}: {value};"
        for name, value in APP_COLORS.items()
    )

    st.markdown(
        f"""
        <style>
        {font_face_css()}
        :root {{
            {css_variables}
            --color-divider: color-mix(in srgb, var(--color-accent-hover) 72%, var(--color-border));
            --font-sans: {FONT_FAMILY};
        }}

        html, body, .stApp, .stApp * {{
            font-family: var(--font-sans) !important;
            letter-spacing: 0 !important;
        }}

        .stApp [class*="material-icons"],
        .stApp [class*="material-symbols"],
        .stApp [data-testid="stIconMaterial"],
        .stApp [data-testid="stIconMaterial"] * {{
            font-family: "Material Symbols Rounded", "Material Symbols Outlined", "Material Icons" !important;
            font-weight: normal !important;
            font-style: normal !important;
            font-size: inherit;
            line-height: 1;
            letter-spacing: normal !important;
            text-transform: none;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            white-space: nowrap;
            direction: ltr;
            -webkit-font-feature-settings: "liga";
            -webkit-font-smoothing: antialiased;
            font-feature-settings: "liga";
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
            border-bottom: 0 !important;
        }}

        .stTabs [data-baseweb="tab-highlight"] {{
            background-color: transparent !important;
            height: 0 !important;
        }}

        .stTabs [data-baseweb="tab-border"] {{
            background-color: var(--color-divider) !important;
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
