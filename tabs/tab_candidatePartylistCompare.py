import base64
import math
import mimetypes
from html import escape
from pathlib import Path
from typing import Optional

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

from utils.theme import APP_COLORS, FONT_FAMILY, font_face_css


DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DEFAULT_PARTY_COLOR = APP_COLORS["accent"]
SIGNAL_POSITIVE = APP_COLORS.get("signal_positive", "#5B7E3C")
SIGNAL_WARNING = APP_COLORS.get("signal_warning", "#FFD65A")
SIGNAL_ORANGE = APP_COLORS.get("signal_orange", "#FF9D23")
SIGNAL_NEGATIVE = APP_COLORS.get("signal_negative", "#EA5252")

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

PHASE_LABELS = {
    "election_day": "วันเลือกตั้ง",
    "in_district_advance": "ล่วงหน้าในเขต",
    "out_of_district_advance": "ล่วงหน้านอกเขต",
}


def _data_file_version(filename: str) -> float:
    path = DATA_DIR / filename
    return path.stat().st_mtime if path.exists() else 0.0


@st.cache_data
def _load_csv(filename: str, file_version: float) -> pd.DataFrame:
    path = DATA_DIR / filename
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame()


@st.cache_data
def _load_csv_with_fallback(
    primary_filename: str,
    fallback_filename: str,
    primary_version: float,
    fallback_version: float,
) -> pd.DataFrame:
    primary_path = DATA_DIR / primary_filename
    fallback_path = DATA_DIR / fallback_filename
    if primary_path.exists():
        return pd.read_csv(primary_path)
    if fallback_path.exists():
        return pd.read_csv(fallback_path)
    return pd.DataFrame()


def _load_constituency() -> pd.DataFrame:
    return _load_csv_with_fallback(
        "constituency_clean.csv",
        "constituency.csv",
        _data_file_version("constituency_clean.csv"),
        _data_file_version("constituency.csv"),
    )


def _load_candidate_mapping() -> pd.DataFrame:
    return _load_csv("candidate_party_mapping.csv", _data_file_version("candidate_party_mapping.csv"))


def _load_party_info() -> pd.DataFrame:
    return _load_csv("party_info.csv", _data_file_version("party_info.csv"))


def _load_partylist() -> pd.DataFrame:
    return _load_csv_with_fallback(
        "partylist_clean.csv",
        "partylist.csv",
        _data_file_version("partylist_clean.csv"),
        _data_file_version("partylist.csv"),
    )


def _clean_text(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def _candidate_key(value: object) -> str:
    text = _clean_text(value)
    for prefix in ["พ.ต.อ.", "พ.ต.อ", "พ.ต.ท.", "พ.ต.ท", "นาย", "นางสาว", "น.ส.", "นาง"]:
        text = text.replace(prefix, "")
    return "".join(ch for ch in text if ch.isalnum()).lower()


def _party_key(value: object) -> str:
    text = _clean_text(value)
    text = text.replace("พรรค", "")
    return "".join(ch for ch in text if ch.isalnum()).lower()


def _format_int(value: object) -> str:
    number = pd.to_numeric(value, errors="coerce")
    if pd.isna(number):
        return "-"
    return f"{float(number):,.0f}"


def _format_pct(value: object) -> str:
    number = pd.to_numeric(value, errors="coerce")
    if pd.isna(number):
        return "-"
    return f"{float(number):.1f}%"


def _format_pp(value: object) -> str:
    number = pd.to_numeric(value, errors="coerce")
    if pd.isna(number):
        return "-"
    sign = "+" if number > 0 else ""
    return f"{sign}{float(number):.1f} pp"


def _format_abs_pp(value: object) -> str:
    number = pd.to_numeric(value, errors="coerce")
    if pd.isna(number):
        return "-"
    return f"{abs(float(number)):.1f} pp"


def _safe_color(value: object, fallback: str = DEFAULT_PARTY_COLOR) -> str:
    text = _clean_text(value)
    if text.startswith("#") and len(text) in {4, 7, 9}:
        return text
    return fallback


def _soften_color(color: str, white_ratio: float = 0.16) -> str:
    color = _safe_color(color).lstrip("#")
    if len(color) == 3:
        color = "".join(ch * 2 for ch in color)
    red = int(color[0:2], 16)
    green = int(color[2:4], 16)
    blue = int(color[4:6], 16)
    red = round(red + (255 - red) * white_ratio)
    green = round(green + (255 - green) * white_ratio)
    blue = round(blue + (255 - blue) * white_ratio)
    return f"#{red:02X}{green:02X}{blue:02X}"


def _darken_color(color: str, black_ratio: float = 0.24) -> str:
    color = _safe_color(color).lstrip("#")
    if len(color) == 3:
        color = "".join(ch * 2 for ch in color)
    red = int(color[0:2], 16)
    green = int(color[2:4], 16)
    blue = int(color[4:6], 16)
    red = round(red * (1 - black_ratio))
    green = round(green * (1 - black_ratio))
    blue = round(blue * (1 - black_ratio))
    return f"#{red:02X}{green:02X}{blue:02X}"


def _hex_to_rgb(color: str) -> tuple[int, int, int]:
    color = _safe_color(color).lstrip("#")
    if len(color) == 3:
        color = "".join(ch * 2 for ch in color)
    return int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)


def _rgb_to_hex(red: float, green: float, blue: float) -> str:
    return f"#{round(red):02X}{round(green):02X}{round(blue):02X}"


def _blend_color(first_color: str, second_color: str, second_ratio: float = 0.5) -> str:
    first_red, first_green, first_blue = _hex_to_rgb(first_color)
    second_red, second_green, second_blue = _hex_to_rgb(second_color)
    first_ratio = 1 - second_ratio
    return _rgb_to_hex(
        (first_red * first_ratio) + (second_red * second_ratio),
        (first_green * first_ratio) + (second_green * second_ratio),
        (first_blue * first_ratio) + (second_blue * second_ratio),
    )


def _relative_luminance(color: str) -> float:
    channels = []
    for channel in _hex_to_rgb(color):
        value = channel / 255
        channels.append(value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4)
    return (0.2126 * channels[0]) + (0.7152 * channels[1]) + (0.0722 * channels[2])


def _card_ink_for_bg(color: str) -> str:
    bg_luminance = _relative_luminance(color)
    text_luminance = _relative_luminance(APP_COLORS["text"])
    inverse_luminance = _relative_luminance(APP_COLORS["text_inverse"])
    dark_contrast = (max(bg_luminance, text_luminance) + 0.05) / (min(bg_luminance, text_luminance) + 0.05)
    light_contrast = (max(bg_luminance, inverse_luminance) + 0.05) / (min(bg_luminance, inverse_luminance) + 0.05)
    return APP_COLORS["text"] if dark_contrast >= light_contrast else APP_COLORS["text_inverse"]


def _vote_columns(df: pd.DataFrame) -> list[str]:
    if df.empty:
        return []

    columns = []
    for column in df.columns:
        if column in NON_VOTE_COLUMNS:
            continue
        numeric = pd.to_numeric(df[column], errors="coerce")
        if numeric.notna().any():
            columns.append(column)
    return columns


def _column_total(df: pd.DataFrame, column: str) -> float:
    if column not in df.columns:
        return 0.0
    return float(pd.to_numeric(df[column], errors="coerce").fillna(0).sum())


def _valid_total(df: pd.DataFrame, vote_columns: list[str]) -> float:
    if "ballot_valid" in df.columns:
        total = _column_total(df, "ballot_valid")
        if total > 0:
            return total
    if not vote_columns:
        return 0.0
    return float(df[vote_columns].apply(pd.to_numeric, errors="coerce").fillna(0).sum().sum())


def _image_src_from_ref(image_ref: object) -> str:
    text = _clean_text(image_ref)
    if not text:
        return ""
    for scheme in ["https://", "http://", "data:"]:
        scheme_index = text.find(scheme)
        if scheme_index > 0:
            text = text[scheme_index:]
            break
    if text.startswith(("http://", "https://", "data:")):
        return text

    path = Path(text)
    if not path.is_absolute():
        path = DATA_DIR / text
    if not path.exists() or not path.is_file():
        return ""

    mime_type = mimetypes.guess_type(path.name)[0] or "image/png"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def _compact_name(value: object, max_chars: int = 22) -> str:
    text = _clean_text(value)
    if len(text) <= max_chars:
        return text
    return f"{text[: max_chars - 3]}..."


def _candidate_meta(candidate_name: str, mapping_df: pd.DataFrame) -> dict[str, str]:
    if mapping_df.empty or "candidate_display_name" not in mapping_df.columns:
        return {}

    target_key = _candidate_key(candidate_name)
    lookup_df = mapping_df.copy()
    lookup_df["candidate_key"] = lookup_df["candidate_display_name"].map(_candidate_key)
    matched = lookup_df[lookup_df["candidate_key"] == target_key]

    if matched.empty:
        matched = lookup_df[
            lookup_df["candidate_key"].map(
                lambda key: bool(key) and (key in target_key or target_key in key)
            )
        ]
    if matched.empty:
        return {}

    row = matched.iloc[0]
    return {
        "candidate_display_name": _clean_text(row.get("candidate_display_name", candidate_name)),
        "candidate_number": _clean_text(row.get("candidate_number", "")),
        "party_name": _clean_text(row.get("party_name", "")),
        "image_ref": _clean_text(row.get("image_ref", "")),
    }


def _first_existing_text(row: pd.Series, columns: list[str]) -> str:
    for column in columns:
        if column in row.index:
            text = _clean_text(row.get(column, ""))
            if text:
                return text
    return ""


def _party_lookup(party_info_df: pd.DataFrame) -> dict[str, dict[str, str]]:
    if party_info_df.empty or "party_name" not in party_info_df.columns:
        return {}

    lookup = {}
    for _, row in party_info_df.iterrows():
        party_name = _clean_text(row.get("party_name", ""))
        if not party_name:
            continue
        lookup[_party_key(party_name)] = {
            "party_name": party_name,
            "party_color": _safe_color(row.get("party_color", DEFAULT_PARTY_COLOR)),
            "party_image_ref": _clean_text(row.get("party_image_ref", "")),
            "pm_candidate_image_ref": _first_existing_text(
                row,
                [
                    "pm_candidate_image_ref",
                    "prime_minister_candidate_image_ref",
                    "prime_candidate_image_ref",
                    "candidate_pm_image_ref",
                    "leader_image_ref",
                ],
            ),
        }
    return lookup


def _party_column_lookup(party_columns: list[str]) -> dict[str, str]:
    return {_party_key(column): column for column in party_columns}


def _phase_options(constituency_df: pd.DataFrame, partylist_df: pd.DataFrame) -> list[str]:
    phases = []
    for frame in [constituency_df, partylist_df]:
        if "vote_phase" in frame.columns:
            phases.extend(frame["vote_phase"].dropna().astype(str).unique().tolist())
    return ["All"] + sorted(set(phases))


def _is_all_option(value: object) -> bool:
    text = _clean_text(value).casefold()
    return text in {"", "all", "ทั้งหมด"}


def _filter_scope(df: pd.DataFrame, vote_phase: str, subdistrict: str) -> pd.DataFrame:
    scoped_df = df.copy()
    if not _is_all_option(vote_phase) and "vote_phase" in scoped_df.columns:
        scoped_df = scoped_df[scoped_df["vote_phase"].astype(str) == vote_phase]
    if not _is_all_option(subdistrict) and "subdistrict" in scoped_df.columns:
        scoped_df = scoped_df[scoped_df["subdistrict"].astype(str) == subdistrict]
    return scoped_df


def _is_advance_phase(vote_phase: str) -> bool:
    return vote_phase in {"in_district_advance", "out_of_district_advance"}


def _area_label_df(df: pd.DataFrame) -> pd.DataFrame:
    labeled_df = df.copy()
    if labeled_df.empty:
        labeled_df["_compare_area"] = pd.Series(dtype="object")
        return labeled_df

    subdistrict = (
        labeled_df["subdistrict"]
        if "subdistrict" in labeled_df.columns
        else pd.Series(pd.NA, index=labeled_df.index)
    )
    phase = (
        labeled_df["vote_phase"].astype(str)
        if "vote_phase" in labeled_df.columns
        else pd.Series("", index=labeled_df.index)
    )
    unit = (
        labeled_df["unit_index"]
        if "unit_index" in labeled_df.columns
        else pd.Series(pd.NA, index=labeled_df.index)
    )

    phase_label = phase.map(lambda value: PHASE_LABELS.get(value, value or "พื้นที่ไม่ระบุ"))
    unit_label = unit.map(lambda value: "" if pd.isna(value) else f" #{_format_int(value)}")
    fallback = phase_label + unit_label
    valid_subdistrict = subdistrict.notna() & subdistrict.astype(str).str.strip().ne("")
    labeled_df["_compare_area"] = subdistrict.astype(str).where(valid_subdistrict, fallback)
    return labeled_df


def _align_partylist_to_constituency(partylist_df: pd.DataFrame, constituency_df: pd.DataFrame) -> pd.DataFrame:
    if partylist_df.empty or constituency_df.empty:
        return partylist_df.iloc[0:0]
    if "district" not in partylist_df.columns or "district" not in constituency_df.columns:
        return partylist_df

    constituency_district = constituency_df["district"]
    districts = constituency_district.dropna().astype(str).unique().tolist()
    partylist_district = partylist_df["district"]
    mask = partylist_district.astype(str).isin(districts) if districts else pd.Series(False, index=partylist_df.index)

    if constituency_district.isna().any():
        mask = mask | partylist_district.isna()

    if not mask.any():
        return partylist_df.iloc[0:0]
    return partylist_df[mask]


def _comparison_df(
    constituency_df: pd.DataFrame,
    partylist_df: pd.DataFrame,
    mapping_df: pd.DataFrame,
    party_info_df: pd.DataFrame,
) -> pd.DataFrame:
    candidate_columns = _vote_columns(constituency_df)
    party_columns = _vote_columns(partylist_df)
    if not candidate_columns or not party_columns:
        return pd.DataFrame()

    party_columns_by_key = _party_column_lookup(party_columns)
    party_info_by_key = _party_lookup(party_info_df)
    candidate_valid = _valid_total(constituency_df, candidate_columns)
    party_valid = _valid_total(partylist_df, party_columns)
    rows = []

    for candidate_column in candidate_columns:
        meta = _candidate_meta(candidate_column, mapping_df)
        display_name = meta.get("candidate_display_name") or candidate_column
        party_name = meta.get("party_name", "")
        party_key = _party_key(party_name)
        party_column = party_columns_by_key.get(party_key)

        if not party_column:
            continue

        party_meta = party_info_by_key.get(party_key, {})
        party_color = party_meta.get("party_color", DEFAULT_PARTY_COLOR)
        candidate_votes = _column_total(constituency_df, candidate_column)
        party_votes = _column_total(partylist_df, party_column)
        candidate_share = (candidate_votes / candidate_valid * 100) if candidate_valid else 0
        party_share = (party_votes / party_valid * 100) if party_valid else 0
        gap_pp = candidate_share - party_share

        rows.append(
            {
                "candidate_column": candidate_column,
                "candidate_name": display_name,
                "candidate_number": meta.get("candidate_number", ""),
                "party_name": party_name or party_column,
                "party_column": party_column,
                "image_ref": meta.get("image_ref", ""),
                "pm_candidate_image_ref": party_meta.get("pm_candidate_image_ref", ""),
                "party_color": party_color,
                "candidate_votes": candidate_votes,
                "party_votes": party_votes,
                "candidate_share": candidate_share,
                "party_share": party_share,
                "gap_pp": gap_pp,
                "abs_gap_pp": abs(gap_pp),
                "insight_type": _gap_label(gap_pp),
            }
        )

    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values("candidate_share", ascending=False).reset_index(drop=True)


def _gap_label(gap_pp: float) -> str:
    if gap_pp >= 5:
        return "Candidate effect"
    if gap_pp <= -5:
        return "Party brand strong"
    return "Aligned"


def _gap_text(gap_pp: float) -> str:
    if gap_pp >= 5:
        return "คนเด่นกว่าพรรค"
    if gap_pp <= -5:
        return "พรรคเด่นกว่าคน"
    return "คะแนนคน/พรรคใกล้กัน"


def _gap_tone(gap_pp: float) -> str:
    if gap_pp >= 5:
        return "positive"
    if gap_pp <= -5:
        return "negative"
    if abs(gap_pp) >= 1:
        return "orange"
    return "warning"


def _gap_color(gap_pp: float) -> str:
    return {
        "positive": SIGNAL_POSITIVE,
        "negative": SIGNAL_NEGATIVE,
        "orange": SIGNAL_ORANGE,
        "warning": SIGNAL_WARNING,
    }[_gap_tone(gap_pp)]


def _inject_styles() -> None:
    st.markdown(
        """
        <style>
        .compare-page-title {
            color: var(--color-text);
            font-size: 1.8rem;
            font-weight: 780;
            line-height: 1.18;
            margin: 0 0 0.25rem;
        }
        .compare-page-subtitle {
            color: var(--color-text-muted);
            font-size: 0.94rem;
            margin-bottom: 1rem;
        }
        .compare-card {
            --card-accent: var(--color-accent);
            --card-accent-secondary: var(--card-accent);
            --card-bg: var(--color-surface-muted);
            --card-blend: var(--card-bg);
            --card-border: var(--color-border);
            --card-line: color-mix(in srgb, var(--card-ink) 28%, transparent);
            --card-rule: var(--card-accent);
            --card-ink: var(--color-text-inverse);
            --card-muted: rgba(255, 255, 255, 0.9);
            min-height: 176px;
            height: 100%;
            border: 1px solid var(--card-border);
            border-radius: 8px;
            background: var(--card-bg);
            padding: 17px 18px 16px;
            display: flex;
            flex-direction: column;
            overflow: hidden;
            color: var(--card-ink);
            position: relative;
            isolation: isolate;
            box-shadow: 0 14px 30px rgba(64, 64, 65, 0.10);
        }
        .compare-card::before {
            content: "";
            position: absolute;
            inset: 0 0 auto 0;
            height: 3px;
            background: var(--card-rule);
            z-index: 1;
        }
        .compare-card::after {
            content: none;
        }
        .compare-card > * {
            position: relative;
            z-index: 2;
        }
        .compare-card.blend-card {
            background: var(--card-blend);
        }
        .compare-card-label {
            align-self: flex-start;
            color: var(--card-muted);
            background: transparent;
            border-bottom: 1px solid var(--card-line);
            border-radius: 0;
            font-size: 0.78rem;
            font-weight: 820;
            line-height: 1.2;
            margin-bottom: 13px;
            padding: 0 0 8px;
            max-width: 100%;
        }
        .compare-card-value {
            color: var(--card-ink);
            font-size: 1.56rem;
            font-weight: 900;
            line-height: 1.12;
            min-height: 48px;
            overflow-wrap: anywhere;
            text-align: center;
        }
        .compare-card.large .compare-card-value {
            font-size: 1.76rem;
            font-weight: 920;
            letter-spacing: 0;
            min-height: 56px;
        }
        .compare-card-note {
            color: var(--card-muted);
            font-size: 0.86rem;
            font-weight: 780;
            margin-top: 10px;
            line-height: 1.32;
            overflow-wrap: anywhere;
            text-align: center;
        }
        .compare-card.large .compare-card-note {
            font-size: 0.9rem;
            font-weight: 780;
            line-height: 1.35;
        }
        .compare-card-note.muted {
            color: var(--card-muted);
            font-size: 0.74rem;
            font-weight: 720;
            line-height: 1.28;
            margin-top: 4px;
        }
        .compare-card.large .compare-card-note.muted {
            font-size: 0.66rem;
            font-weight: 620;
            line-height: 1.25;
            opacity: 0.82;
        }
        .compare-card .compare-card-note.positive,
        .compare-card .compare-card-note.negative,
        .compare-card .compare-card-note.orange,
        .compare-card .compare-card-note.warning {
            color: var(--card-muted);
        }
        .compare-card-note.positive,
        .tower-gap.positive {
            color: var(--color-signal-positive);
        }
        .compare-card-note.negative,
        .tower-gap.negative {
            color: var(--color-signal-negative);
        }
        .compare-card-note.orange,
        .tower-gap.orange {
            color: var(--color-signal-orange);
        }
        .compare-card-note.warning,
        .tower-gap.warning {
            color: color-mix(in srgb, var(--color-signal-warning) 72%, var(--color-text));
        }
        .compare-section-title {
            color: var(--color-text);
            font-size: 1.1rem;
            font-weight: 780;
            margin: 1.3rem 0 0.7rem;
        }
        .compare-hint {
            color: var(--color-text-muted);
            font-size: 0.86rem;
            margin-top: -0.25rem;
            margin-bottom: 0.75rem;
        }
        .compare-disclaimer {
            color: color-mix(in srgb, var(--color-text-muted) 68%, var(--color-text));
            background: color-mix(in srgb, var(--color-surface-muted) 78%, var(--color-accent-soft));
            border: 1px solid color-mix(in srgb, var(--color-border) 78%, var(--color-accent));
            border-left: 4px solid var(--color-accent);
            border-radius: 10px;
            font-size: 0.78rem;
            font-weight: 560;
            line-height: 1.45;
            margin: 0.55rem 0 0.9rem;
            padding: 8px 11px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _metric_card(
    label: str,
    value: str,
    note: str = "",
    tone: str = "",
    accent_color: object = "",
    accent_color_secondary: object = "",
    size: str = "",
    variant: str = "",
) -> None:
    note_class = f" {tone}" if tone else ""
    classes = ["compare-card"]
    if accent_color:
        classes.append("party-accent")
    if size == "large":
        classes.append("large")
    if variant:
        classes.append(variant)

    safe_accent = _safe_color(accent_color, APP_COLORS["accent"])
    safe_secondary = _safe_color(accent_color_secondary, safe_accent) if accent_color_secondary else safe_accent
    is_blended = bool(accent_color_secondary) and safe_secondary.lower() != safe_accent.lower()
    if is_blended:
        classes.append("blend-card")

    card_bg = _soften_color(safe_accent, 0.14)
    card_bg_secondary = _soften_color(safe_secondary, 0.14)
    card_blend = _blend_color(card_bg, card_bg_secondary, 0.5)
    readable_bg = card_blend if is_blended else card_bg
    readable_ink = _card_ink_for_bg(readable_bg)
    mixed_accent = _blend_color(safe_accent, safe_secondary, 0.5)
    app_bg_red, app_bg_green, app_bg_blue = _hex_to_rgb(APP_COLORS["app_bg"])
    card_ink = APP_COLORS["app_bg"]
    card_muted = f"rgba({app_bg_red}, {app_bg_green}, {app_bg_blue}, 0.86)"
    card_line = f"rgba({app_bg_red}, {app_bg_green}, {app_bg_blue}, 0.34)"
    card_rule = card_line

    if readable_ink == APP_COLORS["text_inverse"]:
        card_border = "rgba(255, 255, 255, 0.24)"
    else:
        card_border = _soften_color(mixed_accent, 0.44)

    class_name = " ".join(classes)
    st.markdown(
        f"""
        <div class="{class_name}" style="--card-accent:{safe_accent}; --card-accent-secondary:{safe_secondary}; --card-bg:{card_bg}; --card-bg-secondary:{card_bg_secondary}; --card-blend:{card_blend}; --card-border:{card_border}; --card-line:{card_line}; --card-rule:{card_rule}; --card-ink:{card_ink}; --card-muted:{card_muted};">
            <div class="compare-card-label">{escape(label)}</div>
            <div class="compare-card-value">{escape(value)}</div>
            {f'<div class="compare-card-note{note_class}">{escape(note)}</div>' if note else ''}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_insight_cards(comparison_df: pd.DataFrame) -> None:
    if comparison_df.empty:
        return

    winner_candidate = comparison_df.sort_values("candidate_votes", ascending=False).iloc[0]
    winner_party = comparison_df.sort_values("party_votes", ascending=False).iloc[0]
    split_ticket = _party_key(winner_candidate["party_name"]) != _party_key(winner_party["party_name"])
    avg_gap = comparison_df["abs_gap_pp"].mean()
    signal_primary_color = _safe_color(winner_candidate.get("party_color", APP_COLORS["accent"]))
    signal_secondary_color = (
        _safe_color(winner_party.get("party_color", signal_primary_color), signal_primary_color)
        if split_ticket
        else ""
    )
    signal_value = "เลือกแยกพรรค" if split_ticket else "แนวโน้มเดียวกัน"
    signal_tone = "orange" if split_ticket else "muted"

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        _metric_card(
            "ส.ส.เขตนำ",
            str(winner_candidate["candidate_name"]),
            f"{_format_pct(winner_candidate['candidate_share'])} / gap {_format_pp(winner_candidate['gap_pp'])}",
            _gap_tone(float(winner_candidate["gap_pp"])),
            accent_color=winner_candidate["party_color"],
        )
    with col2:
        _metric_card(
            "Party-list นำ",
            str(winner_party["party_name"]),
            f"{_format_pct(winner_party['party_share'])} / เขตคู่พรรค: {winner_party['candidate_name']}",
            _gap_tone(float(winner_party["gap_pp"])),
            accent_color=winner_party["party_color"],
        )
    with col3:
        _metric_card(
            "สัญญาณเลือกแยกพรรค",
            signal_value,
            f"เขตนำ: {winner_candidate['party_name']} | บัญชีรายชื่อนำ: {winner_party['party_name']}",
            signal_tone,
            accent_color=signal_primary_color,
            accent_color_secondary=signal_secondary_color,
            size="large",
            variant="signal-card",
        )
    with col4:
        _metric_card(
            "ความต่างเฉลี่ย คน-พรรค",
            _format_abs_pp(avg_gap),
            "* ยิ่งสูง = คะแนนคนกับพรรคแยกกันมาก",
            "muted",
            accent_color=APP_COLORS["brown-bark"],
            size="large",
            variant="signal-card",
        )


def _render_candidate_tower(comparison_df: pd.DataFrame) -> None:
    if comparison_df.empty:
        return

    max_share = max(float(comparison_df[["candidate_share", "party_share"]].max().max()), 1)
    cards_html = []
    for _, row in comparison_df.sort_values("candidate_share", ascending=False).iterrows():
        color = _soften_color(row["party_color"], 0.08)
        party_color = _soften_color(row["party_color"], 0.42)
        image_src = _image_src_from_ref(row["image_ref"])
        image_html = (
            f'<img src="{escape(image_src, quote=True)}" alt="{escape(row["candidate_name"], quote=True)}" />'
            if image_src
            else f'<div class="tower-initial">{escape(str(row["candidate_name"])[:2])}</div>'
        )
        pm_image_src = _image_src_from_ref(row.get("pm_candidate_image_ref", ""))
        safe_pm_image_src = escape(pm_image_src.replace("'", "%27"), quote=True)
        pm_image_value = f"url('{safe_pm_image_src}')" if pm_image_src else "none"
        candidate_scale = (float(row["candidate_share"]) / max_share) if max_share else 0
        party_scale = (float(row["party_share"]) / max_share) if max_share else 0
        candidate_height_px = 44 + (candidate_scale ** 1.1 * 270)
        party_height_px = 44 + (party_scale ** 1.1 * 270)
        gap_tone = _gap_tone(float(row["gap_pp"]))
        cards_html.append(
            f"""
            <div class="tower-card" style="--party-color:{color}; --party-list-color:{party_color}; --candidate-height:{candidate_height_px:.1f}px; --party-height:{party_height_px:.1f}px; --pm-image:{pm_image_value};">
                <div class="tower-stage">
                    <div class="party-bar">
                        <span>{_format_pct(row["party_share"])}</span>
                    </div>
                    <div class="tower-person">
                        <div class="tower-photo">{image_html}</div>
                        <div class="tower-score">{_format_pct(row["candidate_share"])}</div>
                    </div>
                </div>
                <div class="tower-name">{escape(_compact_name(row["candidate_name"], 18))}</div>
                <div class="tower-party">เบอร์ {escape(str(row["candidate_number"]) or "-")} · {escape(str(row["party_name"]))}</div>
                <div class="tower-gap {gap_tone}">
                    <div class="tower-gap-number">{escape(_format_pp(row["gap_pp"]))}</div>
                    <div class="tower-gap-label">{escape(_gap_text(float(row["gap_pp"])))}</div>
                </div>
            </div>
            """
        )

    component_html = f"""
        <!doctype html>
        <html>
        <head>
            <meta charset="utf-8" />
            <style>
                {font_face_css()}
                * {{
                    box-sizing: border-box;
                }}
                html, body {{
                    width: 100%;
                    margin: 0;
                    background: transparent;
                    color: {APP_COLORS["text"]};
                    font-family: {FONT_FAMILY};
                    overflow: hidden;
                }}
                .tower-wrap {{
                    display: grid;
                    grid-template-columns: repeat(7, minmax(112px, 1fr));
                    gap: 12px;
                    width: 100%;
                }}
                .tower-card {{
                    min-width: 0;
                    border: 1px solid {APP_COLORS["border"]};
                    border-radius: 10px;
                    background: {APP_COLORS["surface"]};
                    padding: 12px 10px 13px;
                    display: flex;
                    flex-direction: column;
                    text-align: center;
                }}
                .tower-stage {{
                    position: relative;
                    height: 326px;
                    display: flex;
                    align-items: flex-end;
                    justify-content: center;
                    border-bottom: 1px solid color-mix(in srgb, {APP_COLORS["accent_hover"]} 72%, {APP_COLORS["border"]});
                    margin-bottom: 10px;
                }}
                .party-bar {{
                    position: absolute;
                    left: 50%;
                    transform: translateX(-50%);
                    bottom: 0;
                    width: 104px;
                    height: var(--party-height);
                    border-radius: 999px 999px 12px 12px;
                    background: var(--party-list-color);
                    overflow: hidden;
                    box-shadow: inset 0 0 0 1px rgba(255,255,255,0.38);
                    z-index: 1;
                }}
                .party-bar::before {{
                    content: "";
                    position: absolute;
                    inset: 0;
                    background-image: var(--pm-image);
                    background-size: cover;
                    background-position: center top;
                    background-repeat: no-repeat;
                    opacity: 0.46;
                    filter: grayscale(18%);
                    z-index: 1;
                }}
                .party-bar::after {{
                    content: "";
                    position: absolute;
                    inset: 0;
                    background:
                        linear-gradient(
                            180deg,
                            color-mix(in srgb, var(--party-list-color) 48%, white),
                            var(--party-list-color)
                        );
                    opacity: 0.54;
                    z-index: 2;
                }}
                .party-bar span {{
                    position: absolute;
                    right: 6px;
                    top: -17px;
                    color: {APP_COLORS["text"]};
                    font-size: 10px;
                    font-weight: 820;
                    line-height: 1;
                    white-space: nowrap;
                    z-index: 3;
                }}
                .tower-person {{
                    width: 90px;
                    height: var(--candidate-height);
                    min-height: 44px;
                    border-radius: 999px 999px 2px 2px;
                    background: transparent;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: flex-end;
                    padding-top: 0;
                    overflow: hidden;
                    box-shadow: none;
                    z-index: 2;
                }}
                .tower-photo {{
                    width: 100%;
                    height: 100%;
                    min-height: 36px;
                    border-radius: 999px 999px 3px 3px;
                    overflow: hidden;
                    background: transparent;
                    border: 0;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }}
                .tower-photo img {{
                    width: 100%;
                    height: 100%;
                    object-fit: fill;
                    display: block;
                }}
                .tower-initial {{
                    color: {APP_COLORS["text"]};
                    font-weight: 800;
                }}
                .tower-score {{
                    position: absolute;
                    bottom: 8px;
                    left: 50%;
                    transform: translateX(-50%);
                    color: {APP_COLORS["text_inverse"]};
                    font-weight: 850;
                    font-size: 13px;
                    background: rgba(0, 0, 0, 0.28);
                    border-radius: 999px;
                    padding: 2px 7px;
                    text-shadow: 0 1px 1px rgba(0,0,0,0.2);
                    white-space: nowrap;
                }}
                .tower-name {{
                    color: {APP_COLORS["text"]};
                    font-size: 15px;
                    font-weight: 860;
                    line-height: 1.2;
                    min-height: 40px;
                    letter-spacing: 0;
                    text-align: center;
                }}
                .tower-party {{
                    color: {APP_COLORS["accent"]};
                    font-size: 12.5px;
                    font-weight: 650;
                    line-height: 1.25;
                    margin-top: 5px;
                    min-height: 30px;
                    overflow: hidden;
                    text-overflow: ellipsis;
                    text-align: center;
                }}
                .tower-gap {{
                    color: {APP_COLORS["text"]};
                    margin-top: 7px;
                    line-height: 1.1;
                    min-height: 50px;
                    border-radius: 9px;
                    padding: 6px 7px;
                    background: color-mix(in srgb, currentColor 9%, white);
                    text-align: center;
                }}
                .tower-gap-number {{
                    font-size: 17px;
                    font-weight: 900;
                    white-space: nowrap;
                }}
                .tower-gap-label {{
                    font-size: 13.5px;
                    font-weight: 820;
                    margin-top: 4px;
                }}
                .tower-gap.positive {{
                    color: {SIGNAL_POSITIVE};
                }}
                .tower-gap.negative {{
                    color: {SIGNAL_NEGATIVE};
                }}
                .tower-gap.orange {{
                    color: {SIGNAL_ORANGE};
                }}
                .tower-gap.warning {{
                    color: color-mix(in srgb, {SIGNAL_WARNING} 72%, {APP_COLORS["text"]});
                }}
            </style>
        </head>
        <body>
            <div class="tower-wrap">{''.join(cards_html)}</div>
        </body>
        </html>
    """
    components.html(component_html, height=528, scrolling=False)


def _scatter_chart(comparison_df: pd.DataFrame) -> None:
    if comparison_df.empty:
        return

    plot_df = comparison_df.copy()
    max_share = max(float(comparison_df[["candidate_share", "party_share"]].max().max()), 1)
    axis_max = max(60, math.ceil(max_share * 1.16 / 5) * 5)
    axis_min = -max(1.4, axis_max * 0.03)
    plot_df["_plot_party_share"] = plot_df["party_share"].clip(lower=0, upper=axis_max)
    plot_df["_plot_candidate_share"] = plot_df["candidate_share"].clip(lower=0, upper=axis_max)
    plot_df["_marker_share"] = plot_df[["candidate_share", "party_share"]].max(axis=1).clip(lower=0.05)
    plot_df["_marker_size"] = plot_df["_marker_share"].map(
        lambda value: 6 + (math.sqrt(float(value) / axis_max) * 32)
    )
    plot_df["_text_position"] = plot_df.apply(
        lambda row: "middle left"
        if row["party_share"] > axis_max * 0.78
        else ("bottom center" if row["candidate_share"] > axis_max * 0.78 else ("middle right" if row["candidate_share"] < axis_max * 0.08 else "top center")),
        axis=1,
    )
    tick_step = 5 if axis_max <= 80 else 10

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=[0, axis_max],
            y=[0, axis_max],
            mode="lines",
            line=dict(color=APP_COLORS["accent_hover"], width=1, dash="dash"),
            hoverinfo="skip",
            showlegend=False,
        )
    )
    fig.add_trace(
        go.Scatter(
            x=plot_df["_plot_party_share"],
            y=plot_df["_plot_candidate_share"],
            mode="markers+text",
            text=plot_df["candidate_name"].map(lambda name: _compact_name(name, 12)),
            textposition=plot_df["_text_position"],
            textfont=dict(size=11, color=APP_COLORS["text"]),
            cliponaxis=True,
            marker=dict(
                size=plot_df["_marker_size"],
                color=plot_df["party_color"].map(lambda value: _soften_color(value, 0.12)),
                opacity=0.9,
                line=dict(color=APP_COLORS["surface"], width=2),
            ),
            customdata=plot_df[
                [
                    "candidate_name",
                    "party_name",
                    "gap_pp",
                    "candidate_votes",
                    "party_votes",
                    "candidate_share",
                    "party_share",
                ]
            ],
            hovertemplate=(
                "%{customdata[0]}<br>"
                "พรรค: %{customdata[1]}<br>"
                "Candidate share: %{customdata[5]:.1f}%<br>"
                "Party-list share: %{customdata[6]:.1f}%<br>"
                "Gap: %{customdata[2]:+.1f} pp<br>"
                "Votes: %{customdata[3]:,.0f} / %{customdata[4]:,.0f}<extra></extra>"
            ),
            showlegend=False,
        )
    )
    fig.update_layout(
        height=520,
        margin=dict(l=64, r=34, t=18, b=64),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor=APP_COLORS["surface"],
        font=dict(family=FONT_FAMILY, color=APP_COLORS["text"]),
        xaxis=dict(
            title="Party-list vote share (%)",
            type="linear",
            range=[axis_min, axis_max],
            tickmode="linear",
            tick0=0,
            dtick=tick_step,
            gridcolor=APP_COLORS["border"],
            minor=dict(dtick=1, showgrid=True, gridcolor="rgba(233, 225, 210, 0.16)"),
            zeroline=True,
            zerolinecolor=APP_COLORS["accent_hover"],
        ),
        yaxis=dict(
            title="Candidate vote share (%)",
            type="linear",
            range=[axis_min, axis_max],
            tickmode="linear",
            tick0=0,
            dtick=tick_step,
            gridcolor=APP_COLORS["border"],
            minor=dict(dtick=1, showgrid=True, gridcolor="rgba(233, 225, 210, 0.16)"),
            zeroline=True,
            zerolinecolor=APP_COLORS["accent_hover"],
        ),
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def _slope_chart(comparison_df: pd.DataFrame) -> None:
    if comparison_df.empty:
        return

    plot_df = comparison_df.sort_values("candidate_share", ascending=False)
    fig = go.Figure()
    for _, row in plot_df.iterrows():
        color = _soften_color(row["party_color"], 0.10)
        fig.add_trace(
            go.Scatter(
                x=["ผู้สมัครเขต", "Party-list"],
                y=[row["candidate_share"], row["party_share"]],
                mode="lines+markers+text",
                text=[_compact_name(row["candidate_name"], 14), _compact_name(row["party_name"], 14)],
                textposition=["middle left", "middle right"],
                line=dict(color=color, width=2),
                marker=dict(size=9, color=color),
                hovertemplate=f"{escape(row['candidate_name'])}<br>%{{x}}: %{{y:.1f}}%<extra></extra>",
                showlegend=False,
            )
        )

    fig.update_layout(
        height=420,
        margin=dict(l=76, r=84, t=18, b=44),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor=APP_COLORS["surface"],
        font=dict(family=FONT_FAMILY, color=APP_COLORS["text"]),
        yaxis=dict(title="Vote share (%)", gridcolor=APP_COLORS["border"], zerolinecolor=APP_COLORS["accent_hover"]),
        xaxis=dict(title="", showgrid=False),
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def _subdistrict_gap_df(
    constituency_df: pd.DataFrame,
    partylist_df: pd.DataFrame,
    selected_row: pd.Series,
) -> pd.DataFrame:
    candidate_column = selected_row["candidate_column"]
    party_column = selected_row["party_column"]
    if candidate_column not in constituency_df.columns or party_column not in partylist_df.columns:
        return pd.DataFrame()

    constituency_area_df = _area_label_df(constituency_df)
    partylist_area_df = _area_label_df(partylist_df)
    const_group = (
        constituency_area_df.groupby("_compare_area", dropna=False)
        .agg(candidate_votes=(candidate_column, "sum"), candidate_valid=("ballot_valid", "sum"))
        .reset_index()
    )
    party_group = (
        partylist_area_df.groupby("_compare_area", dropna=False)
        .agg(party_votes=(party_column, "sum"), party_valid=("ballot_valid", "sum"))
        .reset_index()
    )
    merged = const_group.merge(party_group, on="_compare_area", how="inner")
    if merged.empty:
        return merged

    merged["candidate_share"] = merged.apply(
        lambda row: (row["candidate_votes"] / row["candidate_valid"] * 100) if row["candidate_valid"] else 0,
        axis=1,
    )
    merged["party_share"] = merged.apply(
        lambda row: (row["party_votes"] / row["party_valid"] * 100) if row["party_valid"] else 0,
        axis=1,
    )
    merged["gap_pp"] = merged["candidate_share"] - merged["party_share"]
    merged["abs_gap_pp"] = merged["gap_pp"].abs()
    merged = merged.rename(columns={"_compare_area": "area_label"})
    return merged.sort_values("abs_gap_pp", ascending=False)


def _gap_by_subdistrict_chart(
    constituency_df: pd.DataFrame,
    partylist_df: pd.DataFrame,
    comparison_df: pd.DataFrame,
) -> None:
    if comparison_df.empty:
        return

    candidate_options = comparison_df["candidate_name"].tolist()
    selected_name = st.selectbox("เลือกผู้สมัครเพื่อดู gap รายตำบล", candidate_options)
    selected_row = comparison_df[comparison_df["candidate_name"] == selected_name].iloc[0]
    gap_df = _subdistrict_gap_df(constituency_df, partylist_df, selected_row)
    if gap_df.empty:
        st.info("ยังไม่มีข้อมูลตำบลสำหรับคำนวณ candidate-party gap")
        return

    plot_df = gap_df.head(12).sort_values("gap_pp")
    colors = [_gap_color(float(value)) for value in plot_df["gap_pp"]]
    fig = go.Figure(
        go.Bar(
            x=plot_df["gap_pp"],
            y=plot_df["area_label"],
            orientation="h",
            marker=dict(color=colors, line=dict(color=APP_COLORS["surface"], width=1)),
            text=plot_df["gap_pp"].map(_format_pp),
            textposition="outside",
            hovertemplate=(
                "%{y}<br>"
                "Gap: %{x:+.1f} pp<br>"
                "Candidate: %{customdata[0]:.1f}%<br>"
                "Party-list: %{customdata[1]:.1f}%<extra></extra>"
            ),
            customdata=plot_df[["candidate_share", "party_share"]],
        )
    )
    fig.update_layout(
        height=420,
        margin=dict(l=112, r=48, t=14, b=48),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor=APP_COLORS["surface"],
        font=dict(family=FONT_FAMILY, color=APP_COLORS["text"]),
        xaxis=dict(title="Candidate share - Party-list share (pp)", gridcolor=APP_COLORS["border"]),
        yaxis=dict(title="", tickfont=dict(color=APP_COLORS["text_muted"])),
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def render(df: pd.DataFrame, selected_district: str = "All"):
    _inject_styles()

    st.markdown('<div class="compare-page-title">เลือกคนหรือเลือกพรรค?</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="compare-page-subtitle"></div>',
        unsafe_allow_html=True,
    )

    source_df = df.copy()
    if source_df.empty:
        source_df = _load_constituency()
        if selected_district != "All" and "district" in source_df.columns:
            source_df = source_df[source_df["district"].astype(str) == selected_district]

    if source_df.empty:
        st.info("ยังไม่มีข้อมูล `constituency_clean.csv` สำหรับหน้า Candidate vs Party-list")
        return

    partylist_df = _align_partylist_to_constituency(_load_partylist(), source_df)
    mapping_df = _load_candidate_mapping()
    party_info_df = _load_party_info()

    if partylist_df.empty:
        st.info("ยังไม่มีข้อมูล `partylist_clean.csv` สำหรับเปรียบเทียบกับคะแนนผู้สมัคร")
        return
    if mapping_df.empty:
        st.info("ต้องมี `data/candidate_party_mapping.csv` เพื่อ map ผู้สมัครกับพรรค")
        return

    phase_options = _phase_options(source_df, partylist_df)
    subdistrict_options = ["All"]
    if "subdistrict" in source_df.columns:
        subdistrict_options += sorted(source_df["subdistrict"].dropna().astype(str).unique().tolist())

    filter_col1, filter_col2 = st.columns([1, 1.35])
    with filter_col1:
        selected_phase = st.selectbox(
            "ประเภทการลงคะแนน",
            phase_options,
            format_func=lambda value: "ทั้งหมด" if _is_all_option(value) else PHASE_LABELS.get(value, value),
        )
    disable_subdistrict = _is_advance_phase(selected_phase)
    if disable_subdistrict:
        subdistrict_options = ["All"]
    with filter_col2:
        selected_subdistrict = st.selectbox(
            "ตำบล",
            subdistrict_options,
            format_func=lambda value: "ทั้งหมด" if _is_all_option(value) else value,
            disabled=disable_subdistrict,
            help="ข้อมูลเลือกตั้งล่วงหน้าไม่มีตำบล จึงเปรียบเทียบตามชุด/หน่วยล่วงหน้าแทน" if disable_subdistrict else None,
        )

    scoped_constituency_df = _filter_scope(source_df, selected_phase, selected_subdistrict)
    scoped_partylist_df = _filter_scope(partylist_df, selected_phase, selected_subdistrict)
    comparison_df = _comparison_df(scoped_constituency_df, scoped_partylist_df, mapping_df, party_info_df)

    if comparison_df.empty:
        st.info("ยังจับคู่คะแนนผู้สมัครกับคะแนน party-list ไม่ได้ ตรวจสอบชื่อพรรคใน mapping และคอลัมน์พรรคใน partylist_clean.csv")
        return

    st.markdown(
        '<div class="compare-disclaimer">* ค่า pp = percentage point หรือ จุดเปอร์เซ็นต์ ใช้วัดส่วนต่างของเปอร์เซ็นต์ เช่น ผู้สมัคร 50% และพรรค 45% แปลว่าต่างกัน 5 pp</div>',
        unsafe_allow_html=True,
    )
    _render_insight_cards(comparison_df)

    st.markdown('<div class="compare-section-title">Candidate height chart</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="compare-hint">* ความสูงของผู้สมัครตามคะแนน ส.ส.เขต และกราฟซ้อนด้านหลังแทนคะแนน party-list ของพรรคเดียวกัน</div>',
        unsafe_allow_html=True,
    )
    _render_candidate_tower(comparison_df)

    st.markdown('<div class="compare-section-title">Candidate share vs Party-list share</div>', unsafe_allow_html=True)
    _scatter_chart(comparison_df)
