import copy
import base64
import json
import re
import unicodedata
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
GEOJSON_DIRS = [DATA_DIR / "jsonGeo", ROOT_DIR / "jsonGeo"]
MARK_IMAGE_PATH = ROOT_DIR / "assets" / "mark_strong.png"

TARGET_DISTRICTS = [
    "ศรีบรรพต",
    "ศรีนครินทร์",
    "ป่าพะยอม",
    "ควนขนุน",
    "กงหรา",
]

TARGET_PARTIES = [
    "ภูมิใจไทย",
    "ประชาธิปัตย์",
    "ประชาชน",
    "เพื่อไทย",
]

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
    "พรรคพลวัต": "#56bd36",
    "อื่นๆ": "#ADB5BD",
    "อื่น ๆ": "#ADB5BD",
}

CANDIDATE_PARTY_MAP = {
    "วรท เทอดวีระพงศ์": "ภูมิใจไทย",
    "ศุภกร ขุนชิต": "ประชาชน",
    "พ.ต.อ.พงศ์พสิษฐ์ ทองด้วง": "กล้าธรรม",
    "อธิคม ขุนแก้ว": "ไทยก้าวใหม่",
    "ภพเอกอัคร อินทรโม": "ประชาธิปัตย์",
    "สมเสริม ชูรักษ์": "พลวัต",
    "นิติศักดิ์ ธรรมเพชร": "เพื่อไทย",
}

CATEGORY_ORDER = [
    "แข็งแกร่ง",
    "เฝ้าระวัง",
    "แพ้สูสี",
    "แพ้ขาด",
]


def _normalize_area_name(value: object) -> str:
    """Normalize Thai area labels so CSV and GeoJSON names can be joined."""
    if pd.isna(value):
        return ""

    text = unicodedata.normalize("NFC", str(value).strip())
    text = re.sub(r"\s+", "", text)
    text = re.sub(r"\(.*?\)", "", text)
    text = re.sub(r"\d+$", "", text)
    text = text.replace("ลำสินธ์ุ", "ลำสินธุ์")
    return text


def _display_area_name(value: object) -> str:
    if pd.isna(value):
        return "ไม่ระบุ"
    text = unicodedata.normalize("NFC", str(value).strip())
    text = re.sub(r"\(.*?\)", "", text).strip()
    text = re.sub(r"\d+$", "", text).strip()
    text = text.replace("ลำสินธ์ุ", "ลำสินธุ์")
    return text or "ไม่ระบุ"


def _score_columns(df: pd.DataFrame) -> list[str]:
    return [column for column in df.columns if column not in BASE_COLUMNS]


def _numeric_scores(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    if not columns:
        return pd.DataFrame(index=df.index)
    return df[columns].apply(pd.to_numeric, errors="coerce").fillna(0)


def _party_color(party: str) -> str:
    return PARTY_COLORS.get(party) or PARTY_COLORS.get(f"พรรค{party}") or "#6B7280"


def _lighten_hex(hex_color: str, amount: float) -> str:
    raw = hex_color.lstrip("#")
    red, green, blue = (int(raw[i : i + 2], 16) for i in (0, 2, 4))
    red = round(red + (255 - red) * amount)
    green = round(green + (255 - green) * amount)
    blue = round(blue + (255 - blue) * amount)
    return f"#{red:02X}{green:02X}{blue:02X}"


def _category_colors(selected_party: str) -> dict[str, str]:
    party_color = _party_color(selected_party)
    return {
        "แข็งแกร่ง": "#60d274",
        "เฝ้าระวัง": "#ca8a04",
        "แพ้สูสี": "#ea580c",
        "แพ้ขาด": "#b91c1c", 
    }


def _geojson_filename(area_level: str, target: bool) -> str:
    suffix = "_phatthalung_target" if target else ""
    admin_level = "2" if area_level == "district" else "3"
    return f"tha_admin{admin_level}{suffix}.geojson"


def _geojson_paths(area_level: str) -> list[Path]:
    return [
        geojson_dir / _geojson_filename(area_level, target)
        for target in (True, False)
        for geojson_dir in GEOJSON_DIRS
    ]


def _read_geojson(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def _feature_district_key(feature: dict) -> str:
    properties = feature.get("properties", {})
    return _normalize_area_name(properties.get("adm2_name1") or properties.get("adm2_name"))


def _feature_subdistrict_key(feature: dict) -> str:
    properties = feature.get("properties", {})
    district_key = _feature_district_key(feature)
    subdistrict_key = _normalize_area_name(
        properties.get("adm3_name1") or properties.get("adm3_name")
    )
    return f"{district_key}|{subdistrict_key}"


def _decorate_feature(feature: dict, area_level: str) -> dict:
    decorated = copy.deepcopy(feature)
    properties = decorated.setdefault("properties", {})
    district_name = _display_area_name(
        properties.get("adm2_name1") or properties.get("adm2_name")
    )

    if area_level == "district":
        properties["area_key"] = _feature_district_key(decorated)
        properties["area_name"] = district_name
    else:
        subdistrict_name = _display_area_name(
            properties.get("adm3_name1") or properties.get("adm3_name")
        )
        properties["area_key"] = _feature_subdistrict_key(decorated)
        properties["area_name"] = f"{district_name} / {subdistrict_name}"

    return decorated


def _filtered_geojson(
    geojson_data: dict,
    area_level: str,
    keep_keys: set[str] | None = None,
) -> dict:
    target_districts = {_normalize_area_name(district) for district in TARGET_DISTRICTS}
    features = []

    for feature in geojson_data.get("features", []):
        district_key = _feature_district_key(feature)
        if district_key not in target_districts:
            continue

        decorated = _decorate_feature(feature, area_level)
        area_key = decorated["properties"].get("area_key", "")
        if keep_keys is not None and area_key not in keep_keys:
            continue
        features.append(decorated)

    return {"type": "FeatureCollection", "features": features}


@st.cache_data(show_spinner=False)
def load_area_geojson(area_level: str) -> dict:
    """Load target GeoJSON first, then fall back to the larger province file."""
    for path in _geojson_paths(area_level):
        if not path.exists():
            continue

        try:
            geojson_data = _read_geojson(path)
        except (OSError, json.JSONDecodeError):
            continue

        filtered = _filtered_geojson(geojson_data, area_level)
        if filtered["features"]:
            return filtered

    return {"type": "FeatureCollection", "features": []}


def _party_vote_table(df: pd.DataFrame, result_type: str) -> pd.DataFrame:
    score_cols = _score_columns(df)
    numeric_scores = _numeric_scores(df, score_cols)
    party_scores = pd.DataFrame(index=df.index)

    for column in numeric_scores.columns:
        party = CANDIDATE_PARTY_MAP.get(column, column) if result_type == "constituency" else column
        if party in party_scores:
            party_scores[party] = party_scores[party] + numeric_scores[column]
        else:
            party_scores[party] = numeric_scores[column]

    for party in TARGET_PARTIES:
        if party not in party_scores:
            party_scores[party] = 0

    return party_scores


def _area_key_columns(df: pd.DataFrame, area_level: str) -> pd.DataFrame:
    area_df = pd.DataFrame(index=df.index)
    district_display = df["district"].map(_display_area_name)
    district_key = df["district"].map(_normalize_area_name)

    if area_level == "district":
        area_df["area_key"] = district_key
        area_df["พื้นที่"] = district_display
        return area_df

    subdistrict_display = df["subdistrict"].map(_display_area_name)
    subdistrict_key = df["subdistrict"].map(_normalize_area_name)
    area_df["area_key"] = district_key + "|" + subdistrict_key
    area_df["พื้นที่"] = district_display + " / " + subdistrict_display
    return area_df


def _classify_margin(won: bool, gap_share: float) -> str:
    gap_percent = gap_share * 100

    if won:
        if gap_percent <= 15:
            return "เฝ้าระวัง"
        return "แข็งแกร่ง"

    if gap_percent <= 15:
        return "แพ้สูสี"
    return "แพ้ขาด"


def _map_color_key(row: pd.Series) -> str:
    if row["ผลลัพธ์"] == "ชนะ":
        return f"ชนะ:{row['หมวดหมู่']}"
    return f"{row['หมวดหมู่']}:{row['พรรคที่ชนะ']}"


def _map_color_map(stronghold_df: pd.DataFrame, selected_party: str) -> dict[str, str]:
    color_map = {
        "ชนะ:แข็งแกร่ง": _party_color(selected_party),
        "ชนะ:เฝ้าระวัง": _lighten_hex(_party_color(selected_party), 0.45),
    }

    losing_rows = stronghold_df.loc[
        stronghold_df["ผลลัพธ์"] == "แพ้", ["หมวดหมู่", "พรรคที่ชนะ"]
    ].dropna()
    for _, row in losing_rows.iterrows():
        category = str(row["หมวดหมู่"])
        winner_party = str(row["พรรคที่ชนะ"])
        winner_color = _party_color(winner_party)
        if category == "แพ้สูสี":
            color_map[f"{category}:{winner_party}"] = _lighten_hex(winner_color, 0.45)
        else:
            color_map[f"{category}:{winner_party}"] = winner_color
    return color_map


def prepare_stronghold_data(
    df: pd.DataFrame,
    selected_party: str,
    result_type: str,
    area_level: str,
) -> pd.DataFrame:
    """Aggregate votes by map section and classify selected-party strength."""
    if df.empty or "district" not in df.columns:
        return pd.DataFrame()

    working = df.copy()
    working["district_key"] = working["district"].map(_normalize_area_name)
    target_districts = {_normalize_area_name(district) for district in TARGET_DISTRICTS}
    working = working[working["district_key"].isin(target_districts)].copy()
    working = working[working["district_key"] != ""]

    if area_level == "subdistrict" and "subdistrict" in working.columns:
        working["subdistrict_key"] = working["subdistrict"].map(_normalize_area_name)
        working = working[working["subdistrict_key"] != ""]

    if working.empty:
        return pd.DataFrame()

    party_scores = _party_vote_table(working, result_type)
    area_columns = _area_key_columns(working, area_level)
    valid_votes = pd.to_numeric(working["ballot_valid"], errors="coerce").fillna(0)

    score_df = pd.concat(
        [
            area_columns,
            valid_votes.rename("บัตรดี"),
            party_scores,
        ],
        axis=1,
    )

    grouped_scores = score_df.groupby("area_key")[party_scores.columns].sum()
    grouped_valid = score_df.groupby("area_key")["บัตรดี"].sum()
    area_names = score_df.groupby("area_key")["พื้นที่"].first()
    rows = []

    for area_key, scores in grouped_scores.iterrows():
        ordered = scores.sort_values(ascending=False)
        total_valid = float(grouped_valid.loc[area_key])
        total_votes = float(scores.sum())
        denominator = total_valid if total_valid else total_votes

        if denominator <= 0 or ordered.empty:
            continue

        selected_votes = float(scores.get(selected_party, 0))
        winner = str(ordered.index[0])
        winner_votes = float(ordered.iloc[0])
        runner_up = str(ordered.index[1]) if len(ordered) > 1 else ""
        runner_up_votes = float(ordered.iloc[1]) if len(ordered) > 1 else 0
        won = selected_party == winner

        if won:
            compare_party = runner_up
            compare_votes = runner_up_votes
            gap_votes = selected_votes - runner_up_votes
            result_label = "ชนะ"
            comparison_label = "นำอันดับ 2"
        else:
            compare_party = winner
            compare_votes = winner_votes
            gap_votes = winner_votes - selected_votes
            result_label = "แพ้"
            comparison_label = "ตามผู้ชนะ"

        gap_share = max(gap_votes, 0) / denominator if denominator else 0
        rows.append(
            {
                "area_key": area_key,
                "พื้นที่": area_names.loc[area_key],
                "ผลลัพธ์": result_label,
                "หมวดหมู่": _classify_margin(won, gap_share),
                "พรรคที่เลือก": selected_party,
                "คะแนนพรรคที่เลือก": int(selected_votes),
                "สัดส่วนพรรคที่เลือก": selected_votes / denominator,
                "พรรคที่ชนะ": winner,
                "คะแนนพรรคที่ชนะ": int(winner_votes),
                "สัดส่วนพรรคที่ชนะ": winner_votes / denominator,
                "พรรคที่เทียบ": compare_party,
                "คะแนนพรรคที่เทียบ": int(compare_votes),
                "สัดส่วนพรรคที่เทียบ": compare_votes / denominator,
                "รูปแบบส่วนต่าง": comparison_label,
                "ส่วนต่างคะแนน": int(max(gap_votes, 0)),
                "ส่วนต่างเปอร์เซ็นต์": gap_share,
                "บัตรดี": int(total_valid),
            }
        )

    result = pd.DataFrame(rows)
    if result.empty:
        return result

    result["result_sort"] = (result["ผลลัพธ์"] == "ชนะ").astype(int)
    result["category_sort"] = result["หมวดหมู่"].map(
        {category: index for index, category in enumerate(CATEGORY_ORDER)}
    )
    return (
        result.sort_values(
            ["result_sort", "category_sort", "ส่วนต่างเปอร์เซ็นต์", "คะแนนพรรคที่เลือก"],
            ascending=[False, True, False, False],
        )
        .drop(columns=["result_sort", "category_sort"])
        .reset_index(drop=True)
    )


def _geojson_center(geojson_data: dict) -> dict[str, float]:
    latitudes = []
    longitudes = []

    for feature in geojson_data.get("features", []):
        properties = feature.get("properties", {})
        lat = pd.to_numeric(properties.get("center_lat"), errors="coerce")
        lon = pd.to_numeric(properties.get("center_lon"), errors="coerce")
        if pd.notna(lat) and pd.notna(lon):
            latitudes.append(float(lat))
            longitudes.append(float(lon))

    if latitudes and longitudes:
        return {"lat": sum(latitudes) / len(latitudes), "lon": sum(longitudes) / len(longitudes)}

    return {"lat": 7.62, "lon": 99.96}


@st.cache_data(show_spinner=False)
def _mark_image_data_url() -> str:
    if not MARK_IMAGE_PATH.exists():
        return ""

    image_bytes = MARK_IMAGE_PATH.read_bytes()
    encoded = base64.b64encode(image_bytes).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def _iter_lng_lat_points(geometry: dict) -> list[tuple[float, float]]:
    geometry_type = geometry.get("type")
    coords = geometry.get("coordinates", [])
    points: list[tuple[float, float]] = []

    if geometry_type == "Polygon":
        for ring in coords:
            for point in ring:
                if len(point) >= 2:
                    points.append((float(point[0]), float(point[1])))
    elif geometry_type == "MultiPolygon":
        for polygon in coords:
            for ring in polygon:
                for point in ring:
                    if len(point) >= 2:
                        points.append((float(point[0]), float(point[1])))

    return points


def _feature_bounds(feature: dict) -> tuple[float, float, float, float] | None:
    geometry = feature.get("geometry")
    if not geometry:
        return None

    points = _iter_lng_lat_points(geometry)
    if not points:
        return None

    longitudes = [point[0] for point in points]
    latitudes = [point[1] for point in points]
    return (min(longitudes), min(latitudes), max(longitudes), max(latitudes))


def _democrat_strong_overlay_layers(map_df: pd.DataFrame, geojson_data: dict) -> list[dict]:
    image_url = _mark_image_data_url()
    if not image_url:
        return []

    target_rows = map_df[
        (
            (map_df["พรรคที่เลือก"] == "ประชาธิปัตย์")
            & (map_df["ผลลัพธ์"] == "ชนะ")
            & (map_df["หมวดหมู่"] == "แข็งแกร่ง")
        )
        | (
            (map_df["ผลลัพธ์"] == "แพ้")
            & (map_df["หมวดหมู่"] == "แพ้ขาด")
            & (map_df["พรรคที่ชนะ"] == "ประชาธิปัตย์")
        )
    ]
    if target_rows.empty:
        return []

    feature_lookup: dict[str, dict] = {}
    for feature in geojson_data.get("features", []):
        area_key = str(feature.get("properties", {}).get("area_key", ""))
        if area_key:
            feature_lookup[area_key] = feature

    layers = []
    for area_key in target_rows["area_key"].dropna().tolist():
        feature = feature_lookup.get(str(area_key))
        if not feature:
            continue

        bounds = _feature_bounds(feature)
        if not bounds:
            continue

        min_lon, min_lat, max_lon, max_lat = bounds
        center_lon = (min_lon + max_lon) / 2
        center_lat = (min_lat + max_lat) / 2
        half_lon = max((max_lon - min_lon) * 0.18, 0.0045)
        half_lat = max((max_lat - min_lat) * 0.18, 0.0038)
        layers.append(
            {
                "sourcetype": "image",
                "source": image_url,
                "coordinates": [
                    [center_lon - half_lon, center_lat + half_lat],
                    [center_lon + half_lon, center_lat + half_lat],
                    [center_lon + half_lon, center_lat - half_lat],
                    [center_lon - half_lon, center_lat - half_lat],
                ],
                "type": "raster",
                "opacity": 0.92,
            }
        )

    return layers


def render_stronghold_section_map(
    stronghold_df: pd.DataFrame,
    area_level: str,
    selected_party: str,
    height: int = 620,
) -> None:
    """Render a reusable GeoJSON section map for selected-party strongholds."""
    if stronghold_df.empty:
        st.info("ไม่มีข้อมูลพื้นที่สำหรับแสดงแผนที่")
        return

    keep_keys = set(stronghold_df["area_key"].dropna())
    geojson_data = _filtered_geojson(load_area_geojson(area_level), area_level, keep_keys)

    if not geojson_data["features"]:
        st.warning("ไม่พบ boundary ใน GeoJSON ที่ตรงกับข้อมูลคะแนน")
        return
    map_df = stronghold_df.copy()
    map_df["สีแผนที่"] = map_df.apply(_map_color_key, axis=1)
    map_color_map = _map_color_map(map_df, selected_party)

    fig = px.choropleth_mapbox(
        map_df,
        geojson=geojson_data,
        locations="area_key",
        featureidkey="properties.area_key",
        color="สีแผนที่",
        color_discrete_map=map_color_map,
        hover_name=None,
        hover_data={
            "สีแผนที่": False,
            "area_key": False,
            "พื้นที่": True,
            "ผลลัพธ์": True,
            "หมวดหมู่": True,
            "ส่วนต่างเปอร์เซ็นต์": ":.2%",
            "พรรคที่เลือก": False,
            "คะแนนพรรคที่เลือก": False,
            "สัดส่วนพรรคที่เลือก": False,
            "พรรคที่ชนะ": False,
            "คะแนนพรรคที่ชนะ": False,
            "สัดส่วนพรรคที่ชนะ": False,
            "พรรคที่เทียบ": False,
            "คะแนนพรรคที่เทียบ": False,
            "สัดส่วนพรรคที่เทียบ": False,
            "รูปแบบส่วนต่าง": False,
            "ส่วนต่างคะแนน": False,
            "บัตรดี": False,
        },
        opacity=0.78,
        center=_geojson_center(geojson_data),
        zoom=9.0 if area_level == "district" else 9.4,
        height=height,
    )
    fig.update_layout(
        mapbox_style="carto-positron",
        legend_title_text="สีบนแผนที่",
        margin=dict(l=0, r=0, t=0, b=0),
        font=dict(family="Tahoma, Arial, sans-serif"),
    )
    overlay_layers = _democrat_strong_overlay_layers(map_df, geojson_data)
    if overlay_layers:
        fig.update_layout(mapbox_layers=overlay_layers)
    fig.update_traces(marker_line_width=1.4, marker_line_color="#FFFFFF")
    st.plotly_chart(fig, use_container_width=True)


def _render_summary(stronghold_df: pd.DataFrame, selected_party: str) -> None:
    if stronghold_df.empty:
        return

    win_df = stronghold_df[stronghold_df["ผลลัพธ์"] == "ชนะ"]
    lose_df = stronghold_df[stronghold_df["ผลลัพธ์"] == "แพ้"]
    strongest = "-"
    if not win_df.empty:
        row = win_df.sort_values("ส่วนต่างเปอร์เซ็นต์", ascending=False).iloc[0]
        strongest = f"{row['พื้นที่']} ({row['ส่วนต่างเปอร์เซ็นต์']:.1%})"

    col1, col2, col3 = st.columns(3)
    col1.metric("พื้นที่ทั้งหมด", f"{len(stronghold_df):,}")
    col2.metric("ชนะ", f"{len(win_df):,}")
    col3.metric("แพ้", f"{len(lose_df):,}")
    st.caption(f"ฐานเสียงแข็งที่สุดของ {selected_party}: {strongest}")


def _styled_table(stronghold_df: pd.DataFrame):
    table_columns = [
        "พื้นที่",
        "ผลลัพธ์",
        "หมวดหมู่",
        "สัดส่วนพรรคที่เลือก",
        "พรรคที่เทียบ",
        "สัดส่วนพรรคที่เทียบ",
        "ส่วนต่างเปอร์เซ็นต์",
        "บัตรดี",
    ]
    return (
        stronghold_df[table_columns]
        .style.format(
            {
                "สัดส่วนพรรคที่เลือก": "{:.2%}",
                "สัดส่วนพรรคที่เทียบ": "{:.2%}",
                "ส่วนต่างเปอร์เซ็นต์": "{:.2%}",
                "บัตรดี": "{:,.0f}",
            }
        )
    )


def render(
    constituency_df: pd.DataFrame,
    partylist_df: pd.DataFrame | None = None,
) -> None:
    st.subheader("Stronghold Area")

    if partylist_df is None:
        partylist_df = pd.DataFrame()

    controls = st.columns([1.1, 1.1, 1.4])
    result_label = controls[0].radio(
        "ประเภทคะแนน",
        ["ส.ส.เขต", "บัญชีรายชื่อ"],
        horizontal=False,
        key="stronghold_result_type",
    )
    area_label = controls[1].radio(
        "ระดับแผนที่",
        ["อำเภอ", "ตำบล/เขต"],
        horizontal=False,
        key="stronghold_area_level",
    )
    selected_party = controls[2].selectbox(
        "เลือกพรรค",
        TARGET_PARTIES,
        key="stronghold_party",
    )

    result_type = "partylist" if result_label == "บัญชีรายชื่อ" else "constituency"
    area_level = "district" if area_label == "อำเภอ" else "subdistrict"
    df = partylist_df.copy() if result_type == "partylist" else constituency_df.copy()

    if df.empty:
        st.warning("ไม่พบข้อมูลคะแนนสำหรับทำ Stronghold map")
        return

    if "vote_phase" in df.columns and (df["vote_phase"] == "election_day").any():
        df = df[df["vote_phase"] == "election_day"].copy()

    stronghold_df = prepare_stronghold_data(
        df=df,
        selected_party=selected_party,
        result_type=result_type,
        area_level=area_level,
    )

    if stronghold_df.empty:
        st.info("ไม่มีข้อมูลใน 5 อำเภอเป้าหมายหลังจาก filter")
        return

    _render_summary(stronghold_df, selected_party)
    render_stronghold_section_map(stronghold_df, area_level, selected_party)

    category_counts = (
        stronghold_df["หมวดหมู่"]
        .value_counts()
        .reindex(CATEGORY_ORDER)
        .dropna()
        .reset_index()
    )
    category_counts.columns = ["หมวดหมู่", "จำนวนพื้นที่"]
    category_counts["จำนวนพื้นที่"] = category_counts["จำนวนพื้นที่"].astype(int)
    fig_counts = px.bar(
        category_counts,
        x="หมวดหมู่",
        y="จำนวนพื้นที่",
        color="หมวดหมู่",
        color_discrete_map=_category_colors(selected_party),
        category_orders={"หมวดหมู่": CATEGORY_ORDER},
        text="จำนวนพื้นที่",
        title="จำนวนพื้นที่ตามระดับความแข็งแรง",
    )
    fig_counts.update_layout(
        showlegend=False,
        height=320,
        margin=dict(l=20, r=20, t=60, b=20),
        font=dict(family="Tahoma, Arial, sans-serif"),
    )
    st.plotly_chart(fig_counts, use_container_width=True)

    with st.expander("ดูรายละเอียดแต่ละพื้นที่", expanded=True):
        st.dataframe(
            _styled_table(stronghold_df),
            use_container_width=True,
            hide_index=True,
        )
