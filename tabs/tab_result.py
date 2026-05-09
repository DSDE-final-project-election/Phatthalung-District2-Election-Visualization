import pandas as pd
import plotly.express as px
import streamlit as st

from utils.result_maps import render_result_map_sections


BASE_COLUMNS = {
    "district",
    "subdistrict",
    "unit_index",
    "form_type",
    "vote_phase",
    "latitude",
    "longitude",
    "latlong_location",
    "ballot_total",
    "ballot_valid",
    "ballot_invalid",
    "ballot_no_vote",
}

PARTY_COLORS = {
    "พรรคกล้า": "#003E72",
    "พรรคกล้าธรรม": "#4dc26d",
    "พรรคก้าวไกล": "#EF771E",
    "พรรคความหวังใหม่": "#FFF04F",
    "พรรคคอมมิวนิสต์แห่งประเทศไทย": "#FF0000",
    "พรรคชาติไทยพัฒนา": "#E90080",
    "พรรคชาติไทย": "#E90080",
    "พรรคชาติพัฒนากล้า": "#FFA500",
    "ชาติพัฒนากล้า": "#FFA500",
    "ชาติพัฒนาเพื่อแผ่นดิน": "#FFAE41",
    "พรรครวมใจไทยชาติพัฒนา": "#FFAE41",
    "พรรครวมชาติพัฒนา": "#FFAE41",
    "พรรคท้องที่ไทย": "#008C45",
    "พรรคไทยภักดี": "#006400",
    "พรรคไทยก้าวใหม่": "#FEFF00",
    "พรรคไทยสร้างไทย": "#6841D0",
    "พรรคไทยรักไทย": "#E30613",
    "พรรคไทยรักษาชาติ": "#2D308F",
    "พรรคไทยทรพย์ทวี": "#6816a4",
    "พรรคประชากรไทย": "#00CED1",
    "พรรคประชาชน": "#FF6413",
    "พรรคประชาชาติ": "#BA810D",
    "พรรคประชาธิปไตยใหม่": "#EF5E17",
    "พรรคประชาธิปัตย์": "#15A5F5",
    "พรรคเป็นธรรม": "#0C4CA3",
    "พรรคเปลี่ยน": "#BD1F2E",
    "พรรคเพื่อไทย": "#E30613",
    "พรรคพลังประชาชน": "#FE4E01",
    "พรรคพลังประชารัฐ": "#006536",
    "พรรคพลังบูรพา": "#00FFFF",
    "พรรคพลังชล": "#00FFFF",
    "พรรคพลังท้องถิ่นไท": "#32CD32",
    "พรรคพลังธรรมใหม่": "#175294",
    "พรรคพลังธรรม": "#175294",
    "พรรคพลังสังคมใหม่": "#A91B35",
    "พรรคภูมิใจไทย": "#312682",
    "พรรครวมไทยสร้างชาติ": "#121F91",
    "พรรครวมพลังประชาชาติไทย": "#A611E1",
    "พรรครวมพลัง": "#A611E1",
    "พรรคแรงงานสร้างชาติ": "#995CE2",
    "พรรครักษ์ผืนป่าประเทศไทย": "#8CC63F",
    "พรรครักษ์ผืนป่า": "#8CC63F",
    "พรรคเศรษฐกิจไทย": "#4EC86F",
    "พรรคเศรษฐกิจ": "#FEBD00",
    "พรรคเศรษฐกิจใหม่": "#7B00FF",
    "พรรคเสรีรวมไทย": "#D8B720",
    "พรรคอนาคตใหม่": "#F57A36",
    "พรรคโอกาสไทย": "#8B5BFD",
    "พรรคพลวัต" : "#56bd36",
    "อื่นๆ" : "#ADB5BD",
    "อื่น ๆ": "#ADB5BD",
}

FALLBACK_COLORS = [
    "#4E79A7",
    "#F28E2B",
    "#E15759",
    "#76B7B2",
    "#59A14F",
    "#EDC948",
    "#B07AA1",
    "#FF9DA7",
    "#9C755F",
    "#BAB0AC",
    "#1F77B4",
    "#FF7F0E",
    "#2CA02C",
    "#D62728",
    "#9467BD",
    "#8C564B",
    "#E377C2",
    "#7F7F7F",
    "#BCBD22",
    "#17BECF",
]

CANDIDATE_PARTY_MAP = {
    "วรท เทอดวีระพงศ์": "ภูมิใจไทย",
    "ศุภกร ขุนชิต": "ประชาชน",
    "พ.ต.อ.พงศ์พสิษฐ์ ทองด้วง": "กล้าธรรม",
    "อธิคม ขุนแก้ว": "ไทยก้าวใหม่",
    "ภพเอกอัคร อินทรโม": "ประชาธิปัตย์",
    "สมเสริม ชูรักษ์": "พลวัต",
    "นิติศักดิ์ ธรรมเพชร": "เพื่อไทย",
}

VOTE_PHASE_LABELS = {
    "election_day": "วันเลือกตั้ง",
    "out_of_district_advance": "เลือกตั้งล่วงหน้านอกเขต",
    "in_district_advance": "เลือกตั้งล่วงหน้าในเขต",
}


def _normalize_party_name(value: str) -> str:
    """Normalize party labels for color matching."""
    text = str(value).strip()
    if text.startswith("พรรค"):
        text = text[len("พรรค") :]
    return "".join(text.split())


PARTY_COLOR_LOOKUP = {}
for _party_name, _party_color in PARTY_COLORS.items():
    PARTY_COLOR_LOOKUP[_normalize_party_name(_party_name)] = _party_color


def _party_color(value: str) -> str | None:
    """Resolve a party color from a party label with or without พรรค prefix."""
    return PARTY_COLOR_LOOKUP.get(_normalize_party_name(value))


def _entity_color_map(entities: list[str], result_type: str) -> dict[str, str]:
    """Build a Plotly color map for parties or candidate party affiliations."""
    color_map = {}
    fallback_index = 0
    for entity in entities:
        color = None
        if result_type == "partylist":
            color = _party_color(entity)
        else:
            party_name = CANDIDATE_PARTY_MAP.get(entity)
            if party_name:
                color = _party_color(party_name)
        if not color and entity != "อื่น ๆ":
            color = FALLBACK_COLORS[fallback_index % len(FALLBACK_COLORS)]
            fallback_index += 1
        if color:
            color_map[str(entity)] = color
            color_map[_entity_display_label(entity, result_type)] = color
    color_map["อื่น ๆ"] = PARTY_COLORS["อื่น ๆ"]
    return color_map


def _entity_display_label(entity: str, result_type: str) -> str:
    """Display candidate-party mapping when viewing constituency results."""
    if entity == "อื่น ๆ":
        return entity
    if result_type == "constituency":
        party_name = CANDIDATE_PARTY_MAP.get(entity)
        if party_name:
            return f"{entity} ({party_name})"
    return str(entity)


def _phase_label(value: object) -> str:
    """Return a Thai label for a vote phase."""
    if pd.isna(value):
        return "ไม่ระบุประเภทการลงคะแนน"
    return VOTE_PHASE_LABELS.get(str(value), str(value))


def _clean_area_value(value: object) -> str | None:
    """Return a usable area value, or None for missing placeholders."""
    if pd.isna(value):
        return None
    text = str(value).strip()
    missing_values = {
        "",
        "nan",
        "none",
        "null",
        "ไม่ระบุ",
        "ไม่ระบุอำเภอ",
        "ไม่ระบุตำบล",
        "ไม่ระบุหน่วย",
    }
    if text.lower() in missing_values:
        return None
    return text


def _score_columns(df: pd.DataFrame) -> list[str]:
    """Return candidate or party vote columns."""
    return [column for column in df.columns if column not in BASE_COLUMNS]


def _numeric_scores(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Return numeric score columns with missing values treated as zero."""
    return df[columns].apply(pd.to_numeric, errors="coerce").fillna(0)


def _entity_totals(df: pd.DataFrame, columns: list[str]) -> pd.Series:
    """Sum votes for each candidate or party."""
    if df.empty or not columns:
        return pd.Series(dtype="float64")
    return _numeric_scores(df, columns).sum().sort_values(ascending=False)


def _selected_score_columns(
    totals: pd.Series,
    result_type: str,
    party_display_mode: str,
) -> tuple[list[str], bool]:
    """Choose which score columns to draw and whether to add an other bucket."""
    nonzero_totals = totals[totals > 0]
    if result_type == "constituency":
        return list(nonzero_totals.index), False

    if party_display_mode == "Top 5":
        return list(totals.head(5).index), True
    if party_display_mode == "Top 10":
        return list(totals.head(10).index), True
    if party_display_mode == "ซ่อนพรรคคะแนน 0":
        return list(nonzero_totals.index), False
    return list(totals.index), False


def _area_label(df: pd.DataFrame) -> pd.Series:
    """Build a readable district/subdistrict label."""
    clean_districts = df["district"].map(_clean_area_value)
    one_district = clean_districts.dropna().nunique() <= 1

    def build_label(row: pd.Series) -> str:
        district = _clean_area_value(row.get("district"))
        subdistrict = _clean_area_value(row.get("subdistrict"))
        phase = _phase_label(row.get("vote_phase"))

        if not district and not subdistrict:
            return phase
        if one_district:
            return subdistrict or phase
        if district and subdistrict:
            return f"{district} / {subdistrict}"
        if district:
            return f"{district} / {phase}"
        return subdistrict or phase

    return df.apply(build_label, axis=1)


def _prepare_subdistrict_share(
    df: pd.DataFrame,
    all_columns: list[str],
    selected_columns: list[str],
    include_other: bool,
) -> pd.DataFrame:
    """Aggregate vote share by subdistrict for stacked bars and heatmaps."""
    if df.empty or not selected_columns:
        return pd.DataFrame()

    working = df.copy()
    working["area_label"] = _area_label(working)
    score_df = _numeric_scores(working, all_columns)
    score_df["area_label"] = working["area_label"].values
    grouped = score_df.groupby("area_label")[all_columns].sum()
    selected = grouped[selected_columns].copy()

    if include_other:
        other_columns = [column for column in all_columns if column not in selected_columns]
        selected["อื่น ๆ"] = grouped[other_columns].sum(axis=1) if other_columns else 0

    denominator = selected.sum(axis=1).replace(0, pd.NA)
    share = selected.div(denominator, axis=0).fillna(0)
    return share.reset_index()


def _subdistrict_ranking(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Rank the winning candidate or party in each subdistrict."""
    if df.empty or not columns:
        return pd.DataFrame()

    working = df.copy()
    working["area_label"] = _area_label(working)
    score_df = _numeric_scores(working, columns)
    score_df["area_label"] = working["area_label"].values
    score_df["ballot_valid"] = pd.to_numeric(
        working["ballot_valid"], errors="coerce"
    ).fillna(0)

    grouped_scores = score_df.groupby("area_label")[columns].sum()
    valid_totals = score_df.groupby("area_label")["ballot_valid"].sum()
    rows = []

    for area, scores in grouped_scores.iterrows():
        ordered = scores.sort_values(ascending=False)
        winner = ordered.index[0]
        runner_up = ordered.index[1] if len(ordered) > 1 else ""
        winner_votes = int(ordered.iloc[0])
        runner_up_votes = int(ordered.iloc[1]) if len(ordered) > 1 else 0
        valid_total = float(valid_totals.loc[area])
        winner_share = winner_votes / valid_total if valid_total else 0
        margin_votes = winner_votes - runner_up_votes
        margin_share = margin_votes / valid_total if valid_total else 0
        rows.append(
            {
                "พื้นที่": area,
                "อันดับ 1": winner,
                "คะแนนอันดับ 1": winner_votes,
                "สัดส่วนอันดับ 1": winner_share,
                "อันดับ 2": runner_up,
                "คะแนนอันดับ 2": runner_up_votes,
                "ส่วนต่างคะแนน": margin_votes,
                "ส่วนต่างสัดส่วน": margin_share,
            }
        )

    return pd.DataFrame(rows).sort_values(
        ["ส่วนต่างสัดส่วน", "คะแนนอันดับ 1"],
        ascending=[True, False],
    )


def _station_winners(
    df: pd.DataFrame,
    columns: list[str],
    result_type: str,
) -> pd.DataFrame:
    """Build station-level winner data for the map."""
    if df.empty or not columns:
        return pd.DataFrame()

    station_df = df.dropna(subset=["latitude", "longitude"]).copy()
    if station_df.empty:
        return station_df

    scores = _numeric_scores(station_df, columns)
    station_df["winner"] = scores.idxmax(axis=1)
    station_df["winner_display"] = station_df["winner"].map(
        lambda value: _entity_display_label(value, result_type)
    )
    station_df["winner_votes"] = scores.max(axis=1).astype(int)
    valid = pd.to_numeric(station_df["ballot_valid"], errors="coerce").fillna(0)
    station_df["winner_share"] = (station_df["winner_votes"] / valid.replace(0, pd.NA)).fillna(0)
    return station_df


def _format_percent_column(df: pd.DataFrame, column: str):
    """Style a table percentage column."""
    return df.style.format({column: "{:.2%}"})


def _render_insight_cards(
    df: pd.DataFrame,
    columns: list[str],
    entity_label: str,
) -> None:
    """Render compact insight metrics for the selected result type."""
    totals = _entity_totals(df, columns)
    ranking = _subdistrict_ranking(df, columns)
    if totals.empty:
        return

    winner = totals.index[0]
    winner_votes = int(totals.iloc[0])
    total_valid = pd.to_numeric(df["ballot_valid"], errors="coerce").fillna(0).sum()
    winner_share = winner_votes / total_valid if total_valid else 0

    strongest_text = "-"
    closest_text = "-"
    if not ranking.empty:
        winner_rows = ranking[ranking["อันดับ 1"] == winner].copy()
        if not winner_rows.empty:
            strongest = winner_rows.sort_values(
                "สัดส่วนอันดับ 1", ascending=False
            ).iloc[0]
            strongest_text = (
                f"{strongest['พื้นที่']} ({strongest['สัดส่วนอันดับ 1']:.1%})"
            )
        closest = ranking.iloc[0]
        closest_text = (
            f"{closest['พื้นที่']} ({closest['ส่วนต่างสัดส่วน']:.1%})"
        )

    col1, col2 = st.columns(2)
    col1.metric(f"{entity_label}นำ", winner, f"{winner_votes:,.0f} votes")
    col2.metric("สัดส่วนคะแนนนำ", f"{winner_share:.2%}")
    st.caption(f"ฐานเสียงเด่นของ {winner}: {strongest_text}")


def render(
    constituency_df: pd.DataFrame,
    partylist_df: pd.DataFrame,
    constituency_grouped_df: pd.DataFrame | None = None,
    partylist_grouped_df: pd.DataFrame | None = None,
    previous_66_df: pd.DataFrame | None = None,
) -> None:
    """Render map-focused constituency and party-list result analytics."""
    st.subheader("Election Results")

    result_label = st.radio(
        "ประเภทผล",
        ["ส.ส.เขต", "บัญชีรายชื่อ"],
        horizontal=True,
        key="result_type_toggle",
    )
    is_partylist = result_label == "บัญชีรายชื่อ"
    result_type = "partylist" if is_partylist else "constituency"

    current_raw_df = partylist_df.copy() if is_partylist else constituency_df.copy()
    current_grouped_df = (
        partylist_grouped_df.copy()
        if is_partylist and partylist_grouped_df is not None
        else constituency_grouped_df.copy()
        if not is_partylist and constituency_grouped_df is not None
        else pd.DataFrame()
    )
    previous_df = previous_66_df.copy() if previous_66_df is not None else pd.DataFrame()

    if current_raw_df.empty and current_grouped_df.empty:
        st.warning("ไม่พบข้อมูลผลเลือกตั้งสำหรับหน้าผลลัพธ์")
        return

    render_result_map_sections(
        current_raw_df=current_raw_df,
        current_grouped_df=current_grouped_df,
        constituency_raw_df=constituency_df,
        partylist_raw_df=partylist_df,
        previous_66_df=previous_df,
        result_type=result_type,
        base_columns=BASE_COLUMNS,
        candidate_party_map=CANDIDATE_PARTY_MAP,
        party_colors=PARTY_COLORS,
        fallback_colors=FALLBACK_COLORS,
    )
