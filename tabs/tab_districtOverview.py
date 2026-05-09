import base64
import mimetypes
from html import escape
from pathlib import Path
from typing import Optional

import pandas as pd
import plotly.express as px
import streamlit as st
import streamlit.components.v1 as components


DATA_DIR = Path(__file__).resolve().parents[1] / "data"
ALL_DISTRICTS_LABEL = "All"
NO_DATA_LABEL = "ไม่มีข้อมูล"
ALL_FILTER_LABEL = "ทั้งหมด"
VOTE_DAY_LABEL = "วันเลือกตั้ง"
PHASE_LABELS = {
    "election_day": VOTE_DAY_LABEL,
    "in_district_advance": "ล่วงหน้าในเขต",
    "out_of_district_advance": "ล่วงหน้านอกเขต",
}
LABEL_TO_PHASE = {label: phase for phase, label in PHASE_LABELS.items()}
ADVANCE_PHASE_LABELS = {
    PHASE_LABELS["in_district_advance"],
    PHASE_LABELS["out_of_district_advance"],
}
PARTYLIST_NUMBER_LOOKUP = {
    "ประชาธิปัตย์": "27",
}
THEME_ACCENT = "#AA7E48"
THEME_ACCENT_HOVER = "#ACAAA7"
THEME_ACCENT_DARK = "#8D8578"
THEME_ACCENT_SOFT = "#E9E1D2"
THEME_APP_BG = "#F1EDEC"
THEME_SURFACE = "#FEFEFE"
THEME_SURFACE_MUTED = "#F9F9F8"
THEME_TEXT = "#404041"
THEME_TEXT_MUTED = THEME_ACCENT
THEME_TEXT_INVERSE = "#FEFEFE"
THEME_BORDER = "#E9E1D2"
DEFAULT_PARTY_COLOR = THEME_ACCENT

NON_VOTE_COLUMNS = {
    "district",
    "subdistrict",
    "unit_index",
    "form_type",
    "vote_phase",
    "ballot_total",
    "ballot_valid",
    "ballot_invalid",
    "ballot_no_vote",
    "vote_sum",
    "vote_mismatch",
    "invalid_ratio",
    "no_vote_ratio",
    "turnout",
    "winner_votes",
    "winner_ratio",
    "winner_margin",
    "vote_entropy",
    "validation_error",
    "has_validation_error",
    "integrity_score",
    "anomaly_iforest",
    "anomaly_dbscan",
    "anomaly_type",
    "severity_score",
    "mismatch_score",
    "lat",
    "lon",
}


@st.cache_data
def _load_csv_with_fallback(primary_filename: str, fallback_filename: str) -> pd.DataFrame:
    primary_path = DATA_DIR / primary_filename
    fallback_path = DATA_DIR / fallback_filename

    if primary_path.exists():
        return pd.read_csv(primary_path)
    if fallback_path.exists():
        return pd.read_csv(fallback_path)
    return pd.DataFrame()


@st.cache_data
def _load_constituency_votes() -> pd.DataFrame:
    return _load_csv_with_fallback("constituency_clean.csv", "constituency.csv")


@st.cache_data
def _load_partylist_votes() -> pd.DataFrame:
    return _load_csv_with_fallback("partylist_clean.csv", "partylist.csv")


@st.cache_data
def _load_candidate_party_mapping(file_version: float) -> pd.DataFrame:
    mapping_path = DATA_DIR / "candidate_party_mapping.csv"
    if mapping_path.exists():
        return pd.read_csv(mapping_path)
    return pd.DataFrame()


@st.cache_data
def _load_party_info(file_version: float) -> pd.DataFrame:
    party_path = DATA_DIR / "party_info.csv"
    if party_path.exists():
        return pd.read_csv(party_path)
    return pd.DataFrame(columns=["party_name", "party_color", "party_image_ref"])


@st.cache_data
def _load_constituency_quality() -> pd.DataFrame:
    quality_path = DATA_DIR / "constituency_clean.csv"
    if quality_path.exists():
        return pd.read_csv(quality_path)
    return pd.DataFrame()


def _sum_column(df: pd.DataFrame, column: str) -> float:
    if column not in df.columns or df.empty:
        return 0
    return pd.to_numeric(df[column], errors="coerce").fillna(0).sum()


def _data_file_version(filename: str) -> float:
    path = DATA_DIR / filename
    return path.stat().st_mtime if path.exists() else 0.0


def _mean_column(df: pd.DataFrame, column: str) -> float:
    if column not in df.columns or df.empty:
        return 0
    value = pd.to_numeric(df[column], errors="coerce").mean()
    return 0 if pd.isna(value) else value


def _has_numeric_column_data(df: pd.DataFrame, column: str) -> bool:
    if column not in df.columns or df.empty:
        return False
    return pd.to_numeric(df[column], errors="coerce").notna().any()


def _format_int(value: float) -> str:
    return f"{int(round(value)):,}"


def _format_percent(value: float) -> str:
    return f"{value:.1%}"


def _format_name_list(values: list[str], max_items: int = 5) -> str:
    clean_values = [str(value) for value in values if pd.notna(value) and str(value).strip()]
    unique_values = sorted(set(clean_values))
    if not unique_values:
        return "-"

    visible_values = unique_values[:max_items]
    remaining_count = len(unique_values) - len(visible_values)
    name_text = ", ".join(visible_values)
    if remaining_count > 0:
        name_text = f"{name_text} + อีก {remaining_count}"
    return name_text


def _district_values(df: pd.DataFrame) -> set[str]:
    if df.empty or "district" not in df.columns:
        return set()
    return set(df["district"].dropna().astype(str).unique())


def _vote_columns(df: pd.DataFrame) -> list[str]:
    columns = []
    for column in df.columns:
        if column in NON_VOTE_COLUMNS:
            continue
        numeric_values = pd.to_numeric(df[column], errors="coerce")
        if numeric_values.notna().any():
            columns.append(column)
    return columns


def _vote_totals(df: pd.DataFrame, columns: list[str]) -> pd.Series:
    if df.empty or not columns:
        return pd.Series(dtype="float64")
    totals = df[columns].apply(pd.to_numeric, errors="coerce").fillna(0).sum()
    return totals[totals > 0].sort_values(ascending=False)


def _candidate_join_key(value: object) -> str:
    return str(value).replace("พ.ต.อ.", "").replace(" ", "").strip()


def _party_join_key(value: object) -> str:
    text = str(value).replace(" ", "").strip()
    if text.startswith("พรรค"):
        text = text.removeprefix("พรรค")
    return text


def _clean_optional_text(value: object) -> str:
    if pd.isna(value):
        return ""
    text = str(value).strip()
    return "" if text.lower() == "nan" else text


def _safe_color(value: object, fallback: str = DEFAULT_PARTY_COLOR) -> str:
    color = _clean_optional_text(value)
    if color.startswith("#") and len(color) in {4, 7}:
        return color
    return fallback


def _soften_color(color: str, white_ratio: float = 0.22) -> str:
    color = _safe_color(color)
    if len(color) == 4:
        color = "#" + "".join(channel * 2 for channel in color[1:])

    try:
        red = int(color[1:3], 16)
        green = int(color[3:5], 16)
        blue = int(color[5:7], 16)
    except ValueError:
        return DEFAULT_PARTY_COLOR

    mixed = [
        round(channel * (1 - white_ratio) + 255 * white_ratio)
        for channel in (red, green, blue)
    ]
    return f"#{mixed[0]:02X}{mixed[1]:02X}{mixed[2]:02X}"


def _image_src_from_ref(image_ref: object) -> str:
    ref = _clean_optional_text(image_ref)
    if not ref:
        return ""
    if ref.startswith(("http://", "https://", "data:image")):
        return ref

    raw_path = Path(ref)
    candidate_paths = [
        raw_path,
        DATA_DIR.parent / raw_path,
        DATA_DIR / raw_path,
    ]
    for path in candidate_paths:
        if path.exists() and path.is_file():
            mime_type = mimetypes.guess_type(path.name)[0] or "image/png"
            image_data = base64.b64encode(path.read_bytes()).decode("ascii")
            return f"data:{mime_type};base64,{image_data}"
    return ""


def _scope_to_sidebar_selection(vote_df: pd.DataFrame, sidebar_df: pd.DataFrame) -> pd.DataFrame:
    vote_districts = _district_values(vote_df)
    sidebar_districts = _district_values(sidebar_df)

    if not vote_districts or not sidebar_districts:
        return vote_df
    if sidebar_districts == vote_districts:
        return vote_df
    return vote_df[vote_df["district"].astype(str).isin(sidebar_districts)]


def _is_sidebar_district_selected(scoped_df: pd.DataFrame, full_df: pd.DataFrame) -> bool:
    scoped_districts = _district_values(scoped_df)
    full_districts = _district_values(full_df)
    return bool(scoped_districts and full_districts and scoped_districts != full_districts)


def _select_overview_filters(scoped_df: pd.DataFrame, full_df: pd.DataFrame) -> tuple[str, str]:
    district_is_selected = _is_sidebar_district_selected(scoped_df, full_df)

    if district_is_selected:
        phase_options = [VOTE_DAY_LABEL]
    else:
        existing_phases = set(scoped_df.get("vote_phase", pd.Series(dtype="object")).dropna().astype(str))
        phase_options = [ALL_FILTER_LABEL]
        phase_options.extend(
            label
            for phase, label in PHASE_LABELS.items()
            if phase in existing_phases
        )

    if st.session_state.get("district_overview_vote_phase") not in phase_options:
        st.session_state["district_overview_vote_phase"] = phase_options[0]

    phase_col, subdistrict_col = st.columns([1, 1.6])
    with phase_col:
        selected_phase = st.selectbox(
            "ช่วงเวลาเลือกตั้ง",
            phase_options,
            index=0,
            key="district_overview_vote_phase",
        )

    phase_filtered_df = _apply_phase_filter(scoped_df, selected_phase)
    subdistrict_disabled = selected_phase in ADVANCE_PHASE_LABELS
    subdistrict_options = [ALL_FILTER_LABEL]
    if not subdistrict_disabled and "subdistrict" in phase_filtered_df.columns:
        subdistrict_options.extend(sorted(phase_filtered_df["subdistrict"].dropna().astype(str).unique()))

    if st.session_state.get("district_overview_subdistrict") not in subdistrict_options:
        st.session_state["district_overview_subdistrict"] = subdistrict_options[0]

    with subdistrict_col:
        selected_subdistrict = st.selectbox(
            "ตำบล",
            subdistrict_options,
            index=0,
            key="district_overview_subdistrict",
            disabled=subdistrict_disabled,
        )
    if subdistrict_disabled:
        selected_subdistrict = ALL_FILTER_LABEL

    return selected_phase, selected_subdistrict


def _apply_phase_filter(df: pd.DataFrame, selected_phase: str) -> pd.DataFrame:
    if df.empty or selected_phase == ALL_FILTER_LABEL:
        return df
    if "vote_phase" not in df.columns or selected_phase not in LABEL_TO_PHASE:
        return pd.DataFrame(columns=df.columns)
    return df[df["vote_phase"].astype(str) == LABEL_TO_PHASE[selected_phase]]


def _apply_subdistrict_filter(df: pd.DataFrame, selected_subdistrict: str) -> pd.DataFrame:
    if df.empty or selected_subdistrict == ALL_FILTER_LABEL:
        return df
    if "subdistrict" not in df.columns:
        return pd.DataFrame(columns=df.columns)
    return df[df["subdistrict"].astype(str) == selected_subdistrict]


def _apply_overview_filters(
    df: pd.DataFrame,
    selected_phase: str,
    selected_subdistrict: str,
) -> pd.DataFrame:
    filtered_df = _apply_phase_filter(df, selected_phase)
    return _apply_subdistrict_filter(filtered_df, selected_subdistrict)


def _filter_by_area(vote_df: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    if vote_df.empty:
        return vote_df, NO_DATA_LABEL

    districts = sorted(vote_df["district"].dropna().astype(str).unique()) if "district" in vote_df.columns else []
    phases = []
    if "vote_phase" in vote_df.columns:
        existing_phases = set(vote_df["vote_phase"].dropna().astype(str).unique())
        phases = [label for phase, label in PHASE_LABELS.items() if phase in existing_phases]

    if not districts and not phases:
        return vote_df, NO_DATA_LABEL

    if len(districts) == 1 and not phases:
        return vote_df, districts[0]

    selected_area = st.selectbox(
        "เลือกอำเภอ / ประเภทล่วงหน้า",
        [ALL_DISTRICTS_LABEL] + districts + phases,
        key="district_overview_selected_area",
    )
    if selected_area == ALL_DISTRICTS_LABEL:
        return vote_df, selected_area
    if selected_area in LABEL_TO_PHASE:
        return vote_df[vote_df["vote_phase"].astype(str) == LABEL_TO_PHASE[selected_area]], selected_area
    return vote_df[vote_df["district"].astype(str) == selected_area], selected_area


def _filter_optional_area(df: pd.DataFrame, selected_area: str) -> pd.DataFrame:
    if df.empty:
        return df
    if selected_area in {ALL_DISTRICTS_LABEL, NO_DATA_LABEL}:
        return df
    if selected_area in LABEL_TO_PHASE:
        if "vote_phase" not in df.columns:
            return pd.DataFrame(columns=df.columns)
        return df[df["vote_phase"].astype(str) == LABEL_TO_PHASE[selected_area]]
    if "district" not in df.columns:
        return pd.DataFrame(columns=df.columns)
    return df[df["district"].astype(str) == selected_area]


def _metric_card(label: str, value: str, note: Optional[str] = None, variant: str = "default"):
    extra_class = " district-card-dark" if variant == "dark" else ""
    st.markdown(
        f"""
        <div class="district-card{extra_class}">
            <div class="district-card-label">{label}</div>
            <div class="district-card-value">{value}</div>
            {f'<div class="district-card-note">{note}</div>' if note else ''}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _lookup_candidate_mapping(candidate_name: str, mapping_df: Optional[pd.DataFrame]) -> dict[str, str]:
    if mapping_df is None or mapping_df.empty:
        return {}

    required_columns = {"candidate_display_name", "candidate_number", "party_name"}
    if not required_columns.issubset(mapping_df.columns):
        return {}

    join_key = _candidate_join_key(candidate_name)
    mapping_join_df = mapping_df.copy()
    mapping_join_df["candidate_join_key"] = mapping_join_df["candidate_display_name"].map(_candidate_join_key)
    matched_rows = mapping_join_df[mapping_join_df["candidate_join_key"] == join_key]
    if matched_rows.empty:
        return {}

    matched = matched_rows.iloc[0]
    return {
        "number": _clean_optional_text(matched["candidate_number"]),
        "party": _clean_optional_text(matched["party_name"]),
        "image_ref": _clean_optional_text(matched["image_ref"]) if "image_ref" in matched else "",
    }


def _lookup_party_info(party_name: str, party_info_df: Optional[pd.DataFrame]) -> dict[str, str]:
    if party_info_df is None or party_info_df.empty or "party_name" not in party_info_df.columns:
        return {}

    lookup_key = _party_join_key(party_name)
    party_lookup_df = party_info_df.copy()
    party_lookup_df["party_join_key"] = party_lookup_df["party_name"].map(_party_join_key)
    matched_rows = party_lookup_df[party_lookup_df["party_join_key"] == lookup_key]
    if matched_rows.empty:
        return {}

    matched = matched_rows.iloc[0]
    return {
        "color": _safe_color(matched["party_color"]) if "party_color" in matched else DEFAULT_PARTY_COLOR,
        "image_ref": _clean_optional_text(matched["party_image_ref"]) if "party_image_ref" in matched else "",
        "number": _clean_optional_text(matched["party_number"]) if "party_number" in matched else "",
    }


def _party_color_for_name(
    value: object,
    name_label: str,
    mapping_df: Optional[pd.DataFrame],
    party_info_df: Optional[pd.DataFrame],
) -> str:
    if name_label == "candidate":
        candidate_meta = _lookup_candidate_mapping(str(value), mapping_df)
        party_name = candidate_meta.get("party", "")
    else:
        party_name = str(value)

    party_meta = _lookup_party_info(party_name, party_info_df)
    return _safe_color(party_meta.get("color"), DEFAULT_PARTY_COLOR)


def _winner_visual(name: str, card_type: str, accent_color: str, image_ref: str = "") -> str:
    image_src = _image_src_from_ref(image_ref)
    if image_src:
        fit_class = "winner-media-fit-cover" if card_type == "candidate" else "winner-media-fit-contain"
        return (
            f'<div class="winner-media winner-media-image {fit_class}" style="--winner-accent:{accent_color};">'
            f'<img src="{escape(image_src, quote=True)}" alt="{escape(name, quote=True)}" />'
            "</div>"
        )

    if card_type == "party":
        short_name = escape(name[:8] if name and name != "-" else "Party")
        return (
            f'<div class="winner-media winner-media-party" style="--winner-accent:{accent_color};">'
            f'<div class="party-card-label">{short_name}</div>'
            '<div class="party-card-seal">กกต.</div>'
            "</div>"
        )

    initials = "".join(str(name).split())[:2] if name and name != "-" else "ผู้"
    return (
        f'<div class="winner-media winner-media-candidate" style="--winner-accent:{accent_color};">'
        f'<div class="winner-initials">{escape(initials)}</div>'
        "</div>"
    )


def _winner_card(
    totals: pd.Series,
    card_type: str,
    mapping_df: Optional[pd.DataFrame] = None,
    party_info_df: Optional[pd.DataFrame] = None,
    accent_color: str = THEME_ACCENT,
):
    if totals.empty:
        name = "-"
        votes = 0
        share = 0
    else:
        name = str(totals.index[0])
        votes = float(totals.iloc[0])
        total_votes = float(totals.sum())
        share = (votes / total_votes * 100) if total_votes else 0

    candidate_meta = _lookup_candidate_mapping(name, mapping_df) if card_type == "candidate" else {}
    if card_type == "candidate":
        number = candidate_meta.get("number")
        party_name = candidate_meta.get("party")
        party_meta = _lookup_party_info(party_name or "", party_info_df)
        image_ref = candidate_meta.get("image_ref", "")
    else:
        party_name = None
        party_meta = _lookup_party_info(name, party_info_df)
        number = party_meta.get("number") or PARTYLIST_NUMBER_LOOKUP.get(name)
        image_ref = party_meta.get("image_ref", "")

    card_accent_color = _safe_color(party_meta.get("color"), accent_color)

    number_badge = f'<span class="winner-number-pill">เบอร์ {escape(number)}</span>' if number else ""
    party_badge = f'<span class="winner-party-text">{escape(party_name)}</span>' if party_name else ""
    empty_note = '<div class="district-card-note">ไม่มีคอลัมน์คะแนน</div>' if totals.empty else ""
    winner_html = (
        f'<div class="district-winner-card" style="--winner-accent:{card_accent_color};">'
        f'{_winner_visual(name, card_type, card_accent_color, image_ref)}'
        '<div class="winner-content">'
        '<div class="winner-card-topline">'
        '<span class="winner-rank-badge">อันดับ 1</span>'
        "</div>"
        f'<div class="district-winner-name">{escape(name)}</div>'
        '<div class="winner-meta-row">'
        f"{number_badge}"
        f"{party_badge}"
        "</div>"
        f'<div class="winner-votes">{_format_int(votes)}</div>'
        f'<div class="winner-share">คิดเป็น <strong>{share:.2f}%</strong></div>'
        f"{empty_note}"
        "</div>"
        "</div>"
    )

    st.markdown(winner_html, unsafe_allow_html=True)


def _top_table(
    title: str,
    totals: pd.Series,
    name_label: str,
    mapping_df: Optional[pd.DataFrame] = None,
    party_info_df: Optional[pd.DataFrame] = None,
):
    st.markdown(f"#### {title}")
    if totals.empty:
        st.info(f"ยังไม่มีข้อมูลสำหรับ {title}")
        return

    top_df = totals.head(5).reset_index()
    top_df.columns = [name_label, "votes"]
    total_votes = totals.sum()
    top_df["share"] = (top_df["votes"] / total_votes * 100) if total_votes else 0
    top_df.insert(0, "rank", range(1, len(top_df) + 1))

    if mapping_df is not None and not mapping_df.empty and name_label == "candidate":
        top_df["candidate_join_key"] = top_df["candidate"].map(_candidate_join_key)
        mapping_join_df = mapping_df.copy()
        mapping_join_df["candidate_join_key"] = mapping_join_df["candidate_display_name"].map(_candidate_join_key)
        top_df = top_df.merge(
            mapping_join_df[
                [
                    "candidate_join_key",
                    "candidate_display_name",
                    "candidate_number",
                    "party_name",
                ]
            ],
            on="candidate_join_key",
            how="left",
        )
        top_df["candidate"] = top_df["candidate_display_name"].fillna(top_df["candidate"])
        top_df = top_df[
            [
                "rank",
                "candidate_number",
                "candidate",
                "party_name",
                "votes",
                "share",
            ]
        ]

    if name_label == "candidate":
        header_cells = ["#", "เบอร์", "candidate", "party", "votes", "share"]
    else:
        header_cells = ["#", "party", "votes", "share"]

    header_html = "".join(f"<th>{escape(header)}</th>" for header in header_cells)
    row_html = []
    for _, row in top_df.iterrows():
        display_name = str(row[name_label])
        party_name = str(row["party_name"]) if "party_name" in top_df.columns and pd.notna(row["party_name"]) else display_name
        color = _party_color_for_name(display_name, name_label, mapping_df, party_info_df)
        bar_color = _soften_color(color, 0.16)
        bar_bg = _soften_color(color, 0.88)
        share = float(row["share"]) if pd.notna(row["share"]) else 0

        if name_label == "candidate":
            cells = [
                _format_int(row["rank"]),
                _format_int(row["candidate_number"]) if pd.notna(row.get("candidate_number")) else "-",
                escape(display_name),
                escape(party_name),
                _format_int(row["votes"]),
            ]
        else:
            cells = [
                _format_int(row["rank"]),
                escape(display_name),
                _format_int(row["votes"]),
            ]

        cells_html = "".join(f"<td>{cell}</td>" for cell in cells)
        share_html = (
            '<td class="share-cell">'
            f'<div class="party-progress" style="--party-color:{bar_color}; --party-track:{bar_bg};">'
            f'<div class="party-progress-fill" style="width:{share:.2f}%;"></div>'
            "</div>"
            f'<span class="share-text">{share:.1f}%</span>'
            "</td>"
        )
        row_html.append(f"<tr>{cells_html}{share_html}</tr>")

    table_html = (
        '<div class="party-table-wrap">'
        '<table class="party-table">'
        f"<thead><tr>{header_html}</tr></thead>"
        f"<tbody>{''.join(row_html)}</tbody>"
        "</table>"
        "</div>"
    )
    st.markdown(table_html, unsafe_allow_html=True)


def _compact_axis_label(value: object, max_chars: int = 18) -> str:
    text = str(value)
    if len(text) <= max_chars:
        return text
    return f"{text[: max_chars - 3]}..."


def _nice_tick_step(max_value: float) -> int:
    if max_value <= 1000:
        return 200
    if max_value <= 5000:
        return 1000
    if max_value <= 20000:
        return 5000
    return 10000


def _format_axis_tick(value: float) -> str:
    if value >= 1000:
        return f"{value / 1000:g}k"
    return _format_int(value)


def _bar_chart(
    title: str,
    totals: pd.Series,
    color: str,
    name_label: str,
    mapping_df: Optional[pd.DataFrame] = None,
    party_info_df: Optional[pd.DataFrame] = None,
):
    if totals.empty:
        st.info(f"ยังไม่มีข้อมูลสำหรับกราฟ {title}")
        return

    chart_df = totals.head(10).reset_index()
    chart_df.columns = ["name", "votes"]
    max_votes = float(chart_df["votes"].max()) if not chart_df.empty else 0
    tick_step = _nice_tick_step(max_votes)
    axis_max = max(max_votes * 1.08, tick_step)
    last_tick = int(axis_max // tick_step) * tick_step
    tick_values = list(range(0, last_tick + 1, tick_step))

    rows_html = []
    for _, row in chart_df.iterrows():
        name = str(row["name"])
        votes = float(row["votes"])
        bar_width = (votes / axis_max * 100) if axis_max else 0
        raw_color = _party_color_for_name(name, name_label, mapping_df, party_info_df)
        bar_color = _soften_color(raw_color, 0.10)
        value_text = _format_int(votes)
        is_inside = bar_width >= 18
        inside_value = f'<span class="bar-value bar-value-inside">{value_text}</span>' if is_inside else ""
        outside_value = f'<span class="bar-value bar-value-outside">{value_text}</span>' if not is_inside else ""
        min_width = "6px" if votes > 0 else "0"
        rows_html.append(
            f"""
            <div class="chart-row" title="{escape(name, quote=True)}: {value_text}">
                <div class="chart-name">{escape(_compact_axis_label(name, 20))}</div>
                <div class="bar-track" style="--bar-width:{bar_width:.4f}%; --bar-color:{bar_color};">
                    <div class="bar-fill" style="min-width:{min_width};">
                        {inside_value}
                    </div>
                    {outside_value}
                </div>
            </div>
            """
        )

    tick_html = "".join(
        f'<span class="axis-tick" style="left:{(tick / axis_max * 100) if axis_max else 0:.4f}%;">{_format_axis_tick(tick)}</span>'
        for tick in tick_values
    )
    component_height = min(470, max(330, 102 + len(chart_df) * 36))
    component_html = f"""
        <!doctype html>
        <html>
        <head>
            <meta charset="utf-8" />
            <style>
                * {{
                    box-sizing: border-box;
                }}
                html, body {{
                    width: 100%;
                    height: 100%;
                    margin: 0;
                    font-family: "IBM Plex Sans Thai", "Noto Sans Thai", Tahoma, Arial, sans-serif;
                    color: {THEME_TEXT};
                    background: transparent;
                    overflow: hidden;
                }}
                .chart {{
                    width: 100%;
                    height: 100%;
                    padding: 2px 8px 0 0;
                }}
                .chart-title {{
                    color: {THEME_TEXT};
                    font-size: 18px;
                    font-weight: 760;
                    line-height: 1.25;
                    margin: 0 0 16px;
                }}
                .chart-rows {{
                    display: flex;
                    flex-direction: column;
                    gap: 8px;
                }}
                .chart-row {{
                    display: grid;
                    grid-template-columns: 128px minmax(0, 1fr);
                    gap: 10px;
                    align-items: center;
                    min-height: 28px;
                }}
                .chart-name {{
                    color: {THEME_TEXT_MUTED};
                    font-size: 12px;
                    line-height: 1.2;
                    text-align: right;
                    white-space: nowrap;
                    overflow: hidden;
                    text-overflow: ellipsis;
                }}
                .bar-track {{
                    position: relative;
                    height: 24px;
                    border-radius: 999px;
                    background: transparent;
                    overflow: visible;
                }}
                .bar-fill {{
                    width: var(--bar-width);
                    height: 100%;
                    border-radius: 999px;
                    background: var(--bar-color);
                    display: flex;
                    align-items: center;
                    justify-content: flex-end;
                    padding: 0 10px;
                }}
                .bar-value {{
                    font-size: 12px;
                    line-height: 1;
                    white-space: nowrap;
                    font-variant-numeric: tabular-nums;
                }}
                .bar-value-inside {{
                    color: {THEME_TEXT_INVERSE};
                    font-weight: 820;
                    text-shadow: 0 1px 1px rgba(0, 0, 0, 0.18);
                }}
                .bar-value-outside {{
                    position: absolute;
                    left: calc(var(--bar-width) + 8px);
                    top: 50%;
                    transform: translateY(-50%);
                    color: {THEME_TEXT};
                    font-weight: 760;
                }}
                .axis {{
                    margin-left: 138px;
                    margin-top: 16px;
                    padding-right: 8px;
                }}
                .axis-ticks {{
                    position: relative;
                    height: 18px;
                }}
                .axis-tick {{
                    position: absolute;
                    top: 0;
                    transform: translateX(-50%);
                    color: {THEME_TEXT_MUTED};
                    font-size: 12px;
                    font-variant-numeric: tabular-nums;
                }}
                .axis-title {{
                    color: {THEME_TEXT_MUTED};
                    font-size: 12px;
                    font-weight: 650;
                    text-align: center;
                    margin-top: 18px;
                }}
            </style>
        </head>
        <body>
            <div class="chart">
                <div class="chart-title">{escape(title)}</div>
                <div class="chart-rows">
                    {''.join(rows_html)}
                </div>
                <div class="axis">
                    <div class="axis-ticks">{tick_html}</div>
                    <div class="axis-title">คะแนนรวม</div>
                </div>
            </div>
        </body>
        </html>
    """
    components.html(component_html, height=component_height, scrolling=False)


def _ballot_chart(title: str, valid_votes: float, invalid_votes: float, no_vote: float):
    total = valid_votes + invalid_votes + no_vote
    if total <= 0:
        st.info("ยังไม่มีข้อมูลบัตรดี / บัตรเสีย / ไม่ประสงค์ลงคะแนน")
        return

    segments = [
        ("บัตรดี", valid_votes, THEME_ACCENT_DARK),
        ("บัตรเสีย", invalid_votes, THEME_ACCENT),
        ("ไม่ประสงค์ลงคะแนน", no_vote, THEME_ACCENT_SOFT),
    ]
    segment_html = []
    legend_html = []
    for label, count, color in segments:
        share = count / total * 100
        min_width = "2px" if share > 0 else "0"
        segment_html.append(
            f"""
            <div
                class="segment"
                style="width:{share:.4f}%; min-width:{min_width}; background:{color};"
                title="{escape(label)} {share:.1f}% ({_format_int(count)})"
            ></div>
            """
        )
        legend_html.append(
            f"""
            <div class="legend-item">
                <span class="dot" style="background:{color};"></span>
                <span>{escape(label)}</span>
                <strong>{share:.1f}%</strong>
                <span class="count">{_format_int(count)}</span>
            </div>
            """
        )

    component_html = f"""
        <!doctype html>
        <html>
        <head>
            <meta charset="utf-8" />
            <style>
                * {{
                    box-sizing: border-box;
                }}
                html, body {{
                    width: 100%;
                    height: 100%;
                    margin: 0;
                    font-family: "IBM Plex Sans Thai", "Noto Sans Thai", Tahoma, Arial, sans-serif;
                    color: {THEME_TEXT};
                    background: transparent;
                    overflow: hidden;
                }}
                .card {{
                    width: 100%;
                    height: 100%;
                    border: 1px solid {THEME_BORDER};
                    border-radius: 10px;
                    background: {THEME_SURFACE};
                    padding: 12px 16px 10px;
                }}
                .heading {{
                    font-size: 14px;
                    font-weight: 760;
                    margin-bottom: 10px;
                }}
                .bar-row {{
                    width: 100%;
                    margin: 0;
                }}
                .track {{
                    display: flex;
                    width: 100%;
                    height: 16px;
                    overflow: hidden;
                    border-radius: 999px;
                    background: {THEME_SURFACE_MUTED};
                }}
                .segment {{
                    height: 100%;
                }}
                .caption {{
                    display: flex;
                    justify-content: flex-end;
                    color: {THEME_TEXT_MUTED};
                    font-size: 12px;
                    margin-top: 6px;
                    white-space: nowrap;
                }}
                .caption strong {{
                    color: {THEME_TEXT};
                    font-weight: 700;
                }}
                .legend {{
                    display: flex;
                    flex-wrap: wrap;
                    justify-content: flex-start;
                    gap: 6px 12px;
                    margin-top: 10px;
                }}
                .legend-item {{
                    display: inline-flex;
                    align-items: center;
                    gap: 6px;
                    color: {THEME_TEXT};
                    font-size: 12px;
                    white-space: nowrap;
                }}
                .dot {{
                    width: 8px;
                    height: 8px;
                    border-radius: 999px;
                    display: inline-block;
                }}
                .count {{
                    color: {THEME_TEXT_MUTED};
                }}
            </style>
        </head>
                <body>
        <div class="card">
            <div class="heading">สัดส่วนบัตรเลือกตั้ง: {escape(title)}</div>
            <div class="bar-row">
                <div class="track">
                    {''.join(segment_html)}
                </div>
                <div class="caption">
                    <span>รวม <strong>{_format_int(total)}</strong> ใบ</span>
                </div>
            </div>
            <div class="legend">
                {''.join(legend_html)}
            </div>
        </div>
        </body>
        </html>
    """
    components.html(
        component_html,
        height=118,
        scrolling=False,
    )


def _anomaly_count(clean_df: pd.DataFrame, anomaly_df: pd.DataFrame, selected_area: str) -> int:
    scoped_anomaly_df = _filter_optional_area(anomaly_df, selected_area)
    if not scoped_anomaly_df.empty:
        return len(scoped_anomaly_df)

    scoped_clean_df = _filter_optional_area(clean_df, selected_area)
    if scoped_clean_df.empty or "anomaly_type" not in scoped_clean_df.columns:
        return 0
    anomaly_type = scoped_clean_df["anomaly_type"].fillna("NORMAL").astype(str)
    return int((anomaly_type != "NORMAL").sum())


def _inject_styles():
    st.markdown(
        """
        <style>
        .district-card, .district-winner-card {
            background: var(--color-surface-muted);
            border: 1px solid var(--color-border);
            border-radius: 10px;
            padding: 16px 18px;
            box-sizing: border-box;
            display: flex;
            flex-direction: column;
            justify-content: center;
            margin-bottom: 10px;
        }
        .district-card {
            height: 106px;
        }
        .district-card-dark {
            background: var(--color-text);
            border-color: color-mix(in srgb, var(--color-text) 82%, var(--color-border));
        }
        .district-card-dark .district-card-label {
            color: color-mix(in srgb, var(--color-surface) 76%, var(--color-accent-soft));
        }
        .district-card-dark .district-card-value {
            color: var(--color-surface);
        }
        .district-card-dark .district-card-note {
            color: color-mix(in srgb, var(--color-surface) 70%, var(--color-text-muted));
        }
        .district-winner-card {
            background: var(--color-surface);
            min-height: 176px;
            justify-content: flex-start;
            align-items: center;
            flex-direction: row;
            gap: 14px;
            padding: 14px 16px;
        }
        .district-card-label {
            color: var(--color-text-muted);
            font-size: 0.86rem;
            font-weight: 650;
            margin-bottom: 8px;
        }
        .district-card-value {
            color: var(--color-accent-dark);
            font-size: 1.85rem;
            font-weight: 780;
            line-height: 1.1;
        }
        .district-card-note {
            color: var(--color-text-muted);
            font-size: 0.82rem;
            margin-top: 8px;
            min-height: 18px;
        }
        .winner-media {
            width: 96px;
            height: 112px;
            border-radius: 9px;
            flex: 0 0 96px;
            overflow: hidden;
            border: 2px solid color-mix(in srgb, var(--winner-accent) 72%, var(--color-surface));
            background: color-mix(in srgb, var(--winner-accent) 12%, var(--color-surface));
            display: flex;
            align-items: center;
            justify-content: center;
            box-shadow: inset 0 0 0 1px var(--color-surface);
        }
        .winner-media-candidate {
            background:
                linear-gradient(145deg, var(--color-surface), transparent 42%),
                linear-gradient(160deg, color-mix(in srgb, var(--winner-accent) 78%, var(--color-surface)), var(--winner-accent));
        }
        .winner-media-party {
            height: 144px;
            color: var(--color-text-inverse);
            flex-direction: column;
            gap: 10px;
            background:
                radial-gradient(circle at 18px 28px, var(--color-surface) 0 2px, transparent 3px),
                linear-gradient(155deg, color-mix(in srgb, var(--winner-accent) 42%, var(--color-surface)), var(--winner-accent));
        }
        .winner-media-image {
            background:
                linear-gradient(145deg, color-mix(in srgb, var(--winner-accent) 16%, var(--color-surface)), var(--color-surface) 62%),
                var(--winner-accent);
            padding: 6px;
        }
        .winner-media-fit-cover {
            width: 90px;
            height: 144px;
            flex-basis: 90px;
            padding: 0;
        }
        .winner-media-image img {
            width: 100%;
            height: 100%;
            object-position: center;
            display: block;
            border-radius: 6px;
        }
        .winner-media-fit-cover img {
            object-fit: cover;
            border-radius: 0;
        }
        .winner-media-fit-contain img {
            object-fit: contain;
        }
        .winner-media-fit-contain {
            height: 144px;
            flex-basis: 96px;
        }
        .winner-initials {
            width: 58px;
            height: 58px;
            border-radius: 999px;
            background: var(--color-surface);
            color: color-mix(in srgb, var(--winner-accent) 84%, var(--color-text));
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 800;
            font-size: 1.25rem;
            line-height: 1;
        }
        .party-card-label {
            max-width: 68px;
            border: 1px solid var(--color-surface);
            border-radius: 999px;
            padding: 3px 8px;
            font-size: 0.68rem;
            line-height: 1.1;
            text-align: center;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .party-card-seal {
            width: 46px;
            height: 46px;
            border-radius: 999px;
            background: var(--color-surface);
            color: color-mix(in srgb, var(--winner-accent) 84%, var(--color-text));
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 0.82rem;
            font-weight: 800;
        }
        .winner-content {
            min-width: 0;
            flex: 1;
        }
        .winner-card-topline {
            display: flex;
            align-items: center;
            gap: 8px;
            flex-wrap: wrap;
            margin-bottom: 5px;
        }
        .winner-card-topline .district-card-label {
            margin-bottom: 0;
            color: var(--color-text-muted);
        }
        .winner-rank-badge {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            min-height: 23px;
            border-radius: 999px;
            background: var(--color-accent);
            color: var(--color-text-inverse);
            font-size: 0.78rem;
            font-weight: 800;
            padding: 2px 9px;
            line-height: 1;
        }
        .winner-meta-row {
            min-height: 25px;
            display: flex;
            align-items: center;
            gap: 7px;
            flex-wrap: wrap;
            margin-top: 3px;
        }
        .winner-number-pill {
            border: 1px solid var(--color-accent-hover);
            border-radius: 999px;
            color: var(--color-accent-dark);
            background: var(--color-accent-soft);
            font-size: 0.75rem;
            line-height: 1;
            padding: 4px 10px;
        }
        .winner-party-text {
            color: var(--color-text-muted);
            font-size: 0.83rem;
            line-height: 1.2;
        }
        .district-winner-name {
            color: var(--color-text);
            font-size: 1.24rem;
            font-weight: 760;
            line-height: 1.25;
            word-break: break-word;
        }
        .winner-votes {
            color: color-mix(in srgb, var(--winner-accent) 86%, var(--color-text));
            font-size: 1.52rem;
            font-weight: 820;
            line-height: 1.1;
            margin-top: 9px;
        }
        .winner-share {
            color: var(--color-text-muted);
            font-size: 0.88rem;
            margin-top: 3px;
        }
        .district-vertical-divider {
            border-left: 1px solid var(--color-divider);
            min-height: 1220px;
            width: 1px;
            margin: 38px auto 0;
        }
        .party-table-wrap {
            overflow: hidden;
            border: 1px solid var(--color-border);
            border-radius: 8px;
            background: var(--color-surface);
            margin-bottom: 20px;
        }
        .party-table {
            width: 100%;
            border-collapse: collapse;
            color: var(--color-text);
            font-size: 0.86rem;
        }
        .party-table th {
            background: var(--color-surface-muted);
            color: var(--color-text-muted);
            font-weight: 520;
            text-align: left;
            padding: 8px 10px;
            border-bottom: 1px solid var(--color-border);
        }
        .party-table td {
            padding: 8px 10px;
            border-bottom: 1px solid var(--color-border);
            vertical-align: middle;
        }
        .party-table tr:last-child td {
            border-bottom: 0;
        }
        .party-table td:first-child,
        .party-table th:first-child {
            width: 48px;
            text-align: center;
            color: var(--color-text-muted);
        }
        .share-cell {
            min-width: 150px;
        }
        .party-progress {
            display: inline-flex;
            width: 92px;
            height: 7px;
            overflow: hidden;
            border-radius: 999px;
            background: var(--party-track);
            vertical-align: middle;
            margin-right: 8px;
        }
        .party-progress-fill {
            height: 100%;
            border-radius: 999px;
            background: var(--party-color);
        }
        .share-text {
            color: var(--color-text-muted);
            font-size: 0.78rem;
            white-space: nowrap;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render(
    df: pd.DataFrame,
    anomaly_df: pd.DataFrame,
    selected_sidebar_district: str = ALL_DISTRICTS_LABEL,
):
    _inject_styles()
    st.subheader("ผลการเลือก 69 พัทลุง เขต 2")

    full_constituency_votes_df = _load_constituency_votes()
    if selected_sidebar_district != ALL_DISTRICTS_LABEL and "district" in full_constituency_votes_df.columns:
        constituency_votes_df = full_constituency_votes_df[
            full_constituency_votes_df["district"].astype(str) == selected_sidebar_district
        ]
    else:
        constituency_votes_df = full_constituency_votes_df

    candidate_party_mapping_df = _load_candidate_party_mapping(
        _data_file_version("candidate_party_mapping.csv")
    )
    party_info_df = _load_party_info(_data_file_version("party_info.csv"))
    selected_phase, selected_subdistrict = _select_overview_filters(
        constituency_votes_df,
        full_constituency_votes_df,
    )
    district_df = _apply_overview_filters(
        constituency_votes_df,
        selected_phase,
        selected_subdistrict,
    )
    partylist_source_df = _load_partylist_votes()
    if selected_sidebar_district != ALL_DISTRICTS_LABEL and "district" in partylist_source_df.columns:
        partylist_source_df = partylist_source_df[
            partylist_source_df["district"].astype(str) == selected_sidebar_district
        ]
    partylist_df = _apply_overview_filters(
        partylist_source_df,
        selected_phase,
        selected_subdistrict,
    )
    quality_source_df = _load_constituency_quality()
    if quality_source_df.empty:
        quality_source_df = df
    elif selected_sidebar_district != ALL_DISTRICTS_LABEL and "district" in quality_source_df.columns:
        quality_source_df = quality_source_df[
            quality_source_df["district"].astype(str) == selected_sidebar_district
        ]
    clean_metric_df = _apply_overview_filters(
        quality_source_df,
        selected_phase,
        selected_subdistrict,
    )
    scoped_anomaly_df = _apply_overview_filters(
        anomaly_df,
        selected_phase,
        selected_subdistrict,
    )

    if district_df.empty:
        st.warning("ยังไม่มีข้อมูล `data/constituency_clean.csv` สำหรับแสดง District Overview")
        return

    candidate_columns = _vote_columns(district_df)
    party_columns = _vote_columns(partylist_df)
    candidate_totals = _vote_totals(district_df, candidate_columns)
    party_totals = _vote_totals(partylist_df, party_columns)

    spatial_df = (
        district_df[district_df["vote_phase"].astype(str) == "election_day"]
        if "vote_phase" in district_df.columns
        else district_df
    )
    total_units = (
        spatial_df[["district", "subdistrict", "unit_index"]].drop_duplicates().shape[0]
        if {"district", "subdistrict", "unit_index"}.issubset(spatial_df.columns)
        else len(spatial_df)
    )
    total_districts = (
        spatial_df["district"].dropna().astype(str).nunique()
        if "district" in spatial_df.columns
        else 0
    )
    total_subdistricts = (
        spatial_df[["district", "subdistrict"]].dropna().drop_duplicates().shape[0]
        if {"district", "subdistrict"}.issubset(spatial_df.columns)
        else 0
    )

    constituency_total_ballots = _sum_column(district_df, "ballot_total")
    constituency_valid_votes = _sum_column(district_df, "ballot_valid")
    constituency_invalid_votes = _sum_column(district_df, "ballot_invalid")
    constituency_no_vote = _sum_column(district_df, "ballot_no_vote")
    partylist_total_ballots = _sum_column(partylist_df, "ballot_total")
    partylist_valid_votes = _sum_column(partylist_df, "ballot_valid")
    partylist_invalid_votes = _sum_column(partylist_df, "ballot_invalid")
    partylist_no_vote = _sum_column(partylist_df, "ballot_no_vote")
    avg_integrity = _mean_column(clean_metric_df, "integrity_score")
    avg_integrity_display = (
        f"{avg_integrity:.1f}"
        if _has_numeric_column_data(clean_metric_df, "integrity_score")
        else "-"
    )
    anomaly_total = len(scoped_anomaly_df)
    is_advance_selection = selected_phase in ADVANCE_PHASE_LABELS
    total_units_display = "-" if is_advance_selection else _format_int(total_units)
    total_districts_display = "-" if is_advance_selection else _format_int(total_districts)
    total_subdistricts_display = "-" if is_advance_selection else _format_int(total_subdistricts)

    st.divider()

    # st.caption(f"ภาพรวม: {selected_phase} / {selected_subdistrict} | คะแนนหลักจาก data/constituency_clean.csv และ data/partylist_clean.csv")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        _metric_card("หน่วยเลือกตั้งทั้งหมด", total_units_display, variant="dark")
    with col2:
        _metric_card("อำเภอ", total_districts_display, variant="dark")
    with col3:
        _metric_card("ตำบล", total_subdistricts_display, variant="dark")
    with col4:
        _metric_card("Integrity เฉลี่ย", avg_integrity_display, f"Anomaly: {_format_int(anomaly_total)}", variant="dark")

    constituency_col, divider_col, partylist_col = st.columns([1, 0.035, 1])
    with constituency_col:
        st.markdown("#### สส.เขต")
        _winner_card(
            candidate_totals,
            "candidate",
            candidate_party_mapping_df,
            party_info_df,
            THEME_ACCENT,
        )
        row1_col1, row1_col2 = st.columns(2)
        with row1_col1:
            _metric_card("บัตรทั้งหมด", _format_int(constituency_total_ballots))
        with row1_col2:
            _metric_card("บัตรดี", _format_int(constituency_valid_votes), _format_percent(constituency_valid_votes / constituency_total_ballots) if constituency_total_ballots else None)
        row2_col1, row2_col2 = st.columns(2)
        with row2_col1:
            _metric_card("บัตรเสีย", _format_int(constituency_invalid_votes), _format_percent(constituency_invalid_votes / constituency_total_ballots) if constituency_total_ballots else None)
        with row2_col2:
            _metric_card("ไม่ประสงค์ลงคะแนน", _format_int(constituency_no_vote), _format_percent(constituency_no_vote / constituency_total_ballots) if constituency_total_ballots else None)
        _ballot_chart("สส.เขต", constituency_valid_votes, constituency_invalid_votes, constituency_no_vote)
        _top_table("Top 5 Candidates", candidate_totals, "candidate", candidate_party_mapping_df, party_info_df)
        _bar_chart(
            "คะแนนผู้สมัครรวม",
            candidate_totals,
            THEME_ACCENT_DARK,
            "candidate",
            candidate_party_mapping_df,
            party_info_df,
        )

    with divider_col:
        st.markdown('<div class="district-vertical-divider"></div>', unsafe_allow_html=True)

    with partylist_col:
        st.markdown("#### สส.บัญชีรายชื่อ")
        _winner_card(
            party_totals,
            "party",
            party_info_df=party_info_df,
            accent_color=THEME_ACCENT,
        )
        row1_col1, row1_col2 = st.columns(2)
        with row1_col1:
            _metric_card("บัตรทั้งหมด", _format_int(partylist_total_ballots))
        with row1_col2:
            _metric_card("บัตรดี", _format_int(partylist_valid_votes), _format_percent(partylist_valid_votes / partylist_total_ballots) if partylist_total_ballots else None)
        row2_col1, row2_col2 = st.columns(2)
        with row2_col1:
            _metric_card("บัตรเสีย", _format_int(partylist_invalid_votes), _format_percent(partylist_invalid_votes / partylist_total_ballots) if partylist_total_ballots else None)
        with row2_col2:
            _metric_card("ไม่ประสงค์ลงคะแนน", _format_int(partylist_no_vote), _format_percent(partylist_no_vote / partylist_total_ballots) if partylist_total_ballots else None)
        _ballot_chart("บัญชีรายชื่อ", partylist_valid_votes, partylist_invalid_votes, partylist_no_vote)
        _top_table("Top 5 Parties", party_totals, "party", party_info_df=party_info_df)
        _bar_chart(
            "คะแนน Party-list รวม",
            party_totals,
            THEME_ACCENT,
            "party",
            party_info_df=party_info_df,
        )

    missing_notes = []
    if candidate_totals.empty:
        missing_notes.append("คะแนนผู้สมัคร: ต้องมีคอลัมน์ชื่อผู้สมัครใน `data/constituency_clean.csv`")
    if party_totals.empty:
        missing_notes.append("คะแนน party-list: ต้องมีคอลัมน์ชื่อพรรคใน `data/partylist_clean.csv`")
    if avg_integrity_display == "-":
        missing_notes.append("Integrity/anomaly ต้องใช้ `data/constituency_clean.csv`")
    if missing_notes:
        st.info(" / ".join(missing_notes))
