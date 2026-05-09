import base64
import copy
import html
import json
import mimetypes
import re
import unicodedata
import urllib.error
import urllib.request
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
GEOJSON_DIRS = [DATA_DIR / "jsonGeo", ROOT_DIR / "jsonGeo"]

TARGET_DISTRICTS = ["ศรีบรรพต", "ศรีนครินทร์", "ป่าพะยอม", "ควนขนุน", "กงหรา"]
PARTY_LOGOS = {
    "ภูมิใจไทย": "https://election69-assets.thaipbs.or.th/party-logos/webp-250/PARTY-0037.webp",
    "รวมไทยสร้างชาติ": "https://election69-assets.thaipbs.or.th/party-logos/webp-250/PARTY-0006.webp",
    "ประชาธิปัตย์": "https://election69-assets.thaipbs.or.th/party-logos/webp-250/PARTY-0027.webp",
}
CANDIDATE_PROFILES = {
    "วรท เทอดวีระพงศ์": {
        "number": "1",
        "party": "ภูมิใจไทย",
        "image": "https://election69-assets.thaipbs.or.th/candidate_img/v2/normalized-face-portrait-webp-300x480/93/2/1.webp",
    },
    "นิติศักดิ์ ธรรมเพชร": {
        "number": "7",
        "party": "เพื่อไทย",
        "image": "https://election69-assets.thaipbs.or.th/candidate_img/v2/normalized-face-square-webp-192x192/93/2/7.webp",
    },
}
PARTYLIST_MAP_ICONS = {
    "ประชาธิปัตย์": "asset:democrat_cutout.png",
    "รวมไทยสร้างชาติ": "asset:prayut_chan_ocha.png",
    "ก้าวไกล": "asset:move_forward_cutout.png",
}
PARTYLIST_CANDIDATE_NAMES = {
    "ประชาธิปัตย์": "อภิสิทธิ์ เวชชาชีวะ",
    "รวมไทยสร้างชาติ": "พล.อ.ประยุทธ์ จันทร์โอชา",
}
MAP_ICON_SETTINGS = {
    "constituency": {"lon_radius": 0.030, "lat_radius": 0.046, "lon_offset": 0.0, "lat_offset": 0.0},
    "partylist": {"lon_radius": 0.034, "lat_radius": 0.052, "lon_offset": 0.0, "lat_offset": 0.0},
}
DISTRICT_ICON_OFFSETS = {
    # ตัวอย่างถ้าอยากขยับรายอำเภอ:
    "ควนขนุน": {"lon_offset": 0.010, "lat_offset": 0.030},
    "กงหรา": {"lon_offset": -0.05, "lat_offset": -0.04},
    "ศรีนครินทร์": {"lon_offset": -0.025, "lat_offset": 0.000},
    "ป่าพะยอม": {"lon_offset": -0.025, "lat_offset": 0.000},
}
PREVIOUS_66_CONSTITUENCY_CANDIDATES_BY_PARTY = {
    "ภูมิใจไทย": "วรท เทอดวีระพงศ์",
    "รวมไทยสร้างชาติ": "นิติศักดิ์ ธรรมเพชร",
}
PREVIOUS_66_CONSTITUENCY_CANDIDATE_PARTIES = {
    "วรท เทอดวีระพงศ์": "ภูมิใจไทย",
    "นิติศักดิ์ ธรรมเพชร": "รวมไทยสร้างชาติ",
}
VOTE_PHASE_LABELS = {
    "election_day": "วันเลือกตั้ง",
    "out_of_district_advance": "เลือกตั้งล่วงหน้านอกเขต",
    "in_district_advance": "เลือกตั้งล่วงหน้าในเขต",
}
NON_PARTY_SCORE_LABELS = {
    "บัตรเสีย",
    "ผู้มาใช้สิทธิ์",
    "ผู้มีสิทธิ์",
    "ไม่เลือกผู้ใด",
}
SUMMARY_META_COLUMNS = {
    "district_key",
    "district",
    "year",
    "winner",
    "winner_votes",
    "winner_share",
    "runner_up",
    "margin_votes",
    "margin_share",
    "valid_votes",
}


def normalize_area_name(value: object) -> str:
    """Normalize Thai area labels so CSV and GeoJSON names can be joined."""
    if pd.isna(value):
        return ""

    text = unicodedata.normalize("NFC", str(value).strip())
    text = re.sub(r"\s+", "", text)
    text = re.sub(r"\(.*?\)", "", text)
    text = re.sub(r"\d+$", "", text)
    text = text.replace("ลำสินธ์ุ", "ลำสินธุ์")
    return text


def display_area_name(value: object) -> str:
    """Return a cleaned display label for a district or subdistrict."""
    text = normalize_area_name(value)
    return text or "ไม่ระบุ"


def party_key(value: object) -> str:
    """Normalize party labels without merging historical party names."""
    text = unicodedata.normalize("NFC", str(value).strip())
    if text.startswith("พรรค"):
        text = text[len("พรรค") :]
    text = "".join(text.split())
    return text


def party_color(value: object, party_colors: dict[str, str]) -> str | None:
    """Resolve a stable party color from labels with or without พรรค prefix."""
    party = party_key(value)
    return party_colors.get(party) or party_colors.get(f"พรรค{party}")


def party_color_map(
    parties: list[str],
    party_colors: dict[str, str],
    fallback_colors: list[str],
) -> dict[str, str]:
    """Build a Plotly color map for party labels."""
    color_map: dict[str, str] = {}
    fallback_index = 0
    for party in parties:
        color = party_color(party, party_colors)
        if not color:
            color = fallback_colors[fallback_index % len(fallback_colors)]
            fallback_index += 1
        color_map[str(party)] = color
    return color_map


@st.cache_data(show_spinner=False)
def local_image_data_url(filename: str) -> str | None:
    """Read a local image asset as a data URL for map overlays."""
    path = DATA_DIR / "assets" / filename
    if not path.exists():
        return None

    mime_type = mimetypes.guess_type(path.name)[0] or "image/png"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


@st.cache_data(show_spinner=False)
def remote_image_data_url(url: str) -> str:
    """Fetch a remote image as a data URL, falling back to the URL if blocked."""
    try:
        request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(request, timeout=6) as response:
            content_type = response.headers.get_content_type() or "image/jpeg"
            encoded = base64.b64encode(response.read()).decode("ascii")
            return f"data:{content_type};base64,{encoded}"
    except (OSError, urllib.error.URLError, TimeoutError):
        return url


def resolve_map_icon_source(source: str | None) -> str | None:
    """Resolve local and remote map icon sources to browser-friendly image data."""
    if not source:
        return None
    if source.startswith("asset:"):
        return local_image_data_url(source.removeprefix("asset:"))
    if source.startswith("http://") or source.startswith("https://"):
        return remote_image_data_url(source)
    return source


def valid_coordinate_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Keep rows with plausible Phatthalung latitude/longitude values."""
    if df.empty or not {"latitude", "longitude"}.issubset(df.columns):
        return pd.DataFrame(columns=df.columns)

    working = df.copy()
    working["latitude"] = pd.to_numeric(working["latitude"], errors="coerce")
    working["longitude"] = pd.to_numeric(working["longitude"], errors="coerce")
    return working[
        working["latitude"].between(6.5, 8.5)
        & working["longitude"].between(99.0, 101.0)
    ].copy()


def current_score_columns(df: pd.DataFrame, base_columns: set[str]) -> list[str]:
    """Return current-year candidate or party vote columns."""
    helper_columns = {"district_key", "subdistrict_key", "area_label"}
    return [
        column
        for column in df.columns
        if column not in base_columns and column not in helper_columns
    ]


def current_entity_scores(df: pd.DataFrame, base_columns: set[str]) -> pd.DataFrame:
    """Return current-year score columns as numeric entity-level scores."""
    score_columns = current_score_columns(df, base_columns)
    if not score_columns:
        return pd.DataFrame(index=df.index)

    return df[score_columns].apply(pd.to_numeric, errors="coerce").fillna(0)


def current_party_scores(
    df: pd.DataFrame,
    result_type: str,
    base_columns: set[str],
    candidate_party_map: dict[str, str],
) -> pd.DataFrame:
    """Return current-year scores aggregated to party labels."""
    score_columns = current_score_columns(df, base_columns)
    if not score_columns:
        return pd.DataFrame(index=df.index)

    numeric = df[score_columns].apply(pd.to_numeric, errors="coerce").fillna(0)
    party_scores = pd.DataFrame(index=df.index)

    for column in numeric.columns:
        party = candidate_party_map.get(column, column) if result_type == "constituency" else column
        party = party_key(party)
        if party in party_scores:
            party_scores[party] = party_scores[party] + numeric[column]
        else:
            party_scores[party] = numeric[column]

    return party_scores


def previous_party_scores(df: pd.DataFrame, result_type: str) -> pd.DataFrame:
    """Return 2566 scores aggregated to party labels."""
    prefix = "บช_" if result_type == "partylist" else "เขต_"
    party_scores = pd.DataFrame(index=df.index)

    for column in df.columns:
        if not str(column).startswith(prefix):
            continue

        party = str(column).removeprefix(prefix)
        if party in NON_PARTY_SCORE_LABELS:
            continue

        party = party_key(party)
        values = pd.to_numeric(df[column], errors="coerce").fillna(0)
        if party in party_scores:
            party_scores[party] = party_scores[party] + values
        else:
            party_scores[party] = values

    return party_scores


def district_centroids(station_df: pd.DataFrame) -> pd.DataFrame:
    """Compute district centroids from current station coordinates."""
    if "vote_phase" in station_df.columns:
        station_df = station_df[station_df["vote_phase"] == "election_day"].copy()

    working = valid_coordinate_rows(station_df)
    if working.empty:
        return pd.DataFrame(columns=["district_key", "latitude", "longitude"])

    working["district_key"] = working["district"].map(normalize_area_name)
    return (
        working.groupby("district_key", as_index=False)[["latitude", "longitude"]]
        .mean()
        .reset_index(drop=True)
    )


def area_geojson_filename(area_level: str, target: bool) -> str:
    """Return expected GeoJSON filename for district or subdistrict boundaries."""
    suffix = "_phatthalung_target" if target else ""
    admin_level = "2" if area_level == "district" else "3"
    return f"tha_admin{admin_level}{suffix}.geojson"


def feature_district_key(feature: dict) -> str:
    """Return normalized district key from a GeoJSON feature."""
    properties = feature.get("properties", {})
    return normalize_area_name(properties.get("adm2_name1") or properties.get("adm2_name"))


def decorate_district_feature(feature: dict) -> dict:
    """Copy a GeoJSON feature and add join/display properties."""
    decorated = copy.deepcopy(feature)
    properties = decorated.setdefault("properties", {})
    properties["area_key"] = feature_district_key(decorated)
    properties["area_name"] = display_area_name(
        properties.get("adm2_name1") or properties.get("adm2_name")
    )
    return decorated


@st.cache_data(show_spinner=False)
def load_district_geojson() -> dict:
    """Load district GeoJSON boundaries if they exist in the project."""
    target_keys = {normalize_area_name(district) for district in TARGET_DISTRICTS}
    paths = [
        geojson_dir / area_geojson_filename("district", target)
        for target in (True, False)
        for geojson_dir in GEOJSON_DIRS
    ]

    for path in paths:
        if not path.exists():
            continue

        try:
            with path.open("r", encoding="utf-8") as file:
                geojson_data = json.load(file)
        except (OSError, json.JSONDecodeError):
            continue

        features = []
        for feature in geojson_data.get("features", []):
            district_key = feature_district_key(feature)
            if district_key in target_keys:
                features.append(decorate_district_feature(feature))

        if features:
            return {"type": "FeatureCollection", "features": features}

    return {"type": "FeatureCollection", "features": []}


def geojson_center(geojson_data: dict) -> dict[str, float]:
    """Return a map center from GeoJSON properties when available."""
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


def district_summary(
    df: pd.DataFrame,
    result_type: str,
    year_label: str,
    base_columns: set[str],
    candidate_party_map: dict[str, str],
) -> pd.DataFrame:
    """Aggregate a result dataset to district-level winner rows."""
    if df.empty or "district" not in df.columns:
        return pd.DataFrame()

    working = df.copy()
    if year_label != "2566" and "vote_phase" in working.columns:
        working = working[working["vote_phase"] == "election_day"].copy()

    working["district_key"] = working["district"].map(normalize_area_name)
    target_keys = {normalize_area_name(district) for district in TARGET_DISTRICTS}
    working = working[working["district_key"].isin(target_keys)].copy()
    if working.empty:
        return pd.DataFrame()

    party_scores = (
        previous_party_scores(working, result_type)
        if year_label == "2566"
        else current_party_scores(working, result_type, base_columns, candidate_party_map)
    )
    if party_scores.empty:
        return pd.DataFrame()

    score_df = pd.concat([working[["district_key"]], party_scores], axis=1)
    grouped_scores = score_df.groupby("district_key")[party_scores.columns].sum()
    rows = []

    for district_key, scores in grouped_scores.iterrows():
        total_votes = float(scores.sum())
        if total_votes <= 0:
            continue

        ordered = scores.sort_values(ascending=False)
        winner = str(ordered.index[0])
        runner_up = str(ordered.index[1]) if len(ordered) > 1 else ""
        winner_votes = float(ordered.iloc[0])
        runner_up_votes = float(ordered.iloc[1]) if len(ordered) > 1 else 0
        rows.append(
            {
                "district_key": district_key,
                "district": display_area_name(district_key),
                "year": year_label,
                "winner": winner,
                "winner_votes": int(winner_votes),
                "winner_share": winner_votes / total_votes,
                "runner_up": runner_up,
                "margin_votes": int(winner_votes - runner_up_votes),
                "margin_share": (winner_votes - runner_up_votes) / total_votes,
                "valid_votes": int(total_votes),
                **{party: float(scores.get(party, 0)) / total_votes for party in scores.index},
            }
        )

    return pd.DataFrame(rows)


def summary_party_columns(summary_df: pd.DataFrame) -> list[str]:
    """Return party-share columns in a district summary table."""
    return [column for column in summary_df.columns if column not in SUMMARY_META_COLUMNS]


def constituency_map_icon_source(party: object) -> str | None:
    """Return the constituency candidate portrait for a winning party."""
    normalized_party = party_key(party)
    if normalized_party == "ภูมิใจไทย":
        return CANDIDATE_PROFILES["วรท เทอดวีระพงศ์"]["image"]
    if normalized_party in {"เพื่อไทย", "รวมไทยสร้างชาติ"}:
        return CANDIDATE_PROFILES["นิติศักดิ์ ธรรมเพชร"]["image"]
    return party_logo_url(normalized_party)


def partylist_map_icon_source(party: object) -> str | None:
    """Return the party-list portrait/icon source for a winning party."""
    normalized_party = party_key(party)
    return PARTYLIST_MAP_ICONS.get(normalized_party) or party_logo_url(normalized_party)


def winner_map_icon_source(party: object, result_type: str) -> str | None:
    """Return a resolved image source for a district winner marker."""
    source = (
        partylist_map_icon_source(party)
        if result_type == "partylist"
        else constituency_map_icon_source(party)
    )
    return resolve_map_icon_source(source)


def image_marker_coordinates(
    latitude: float,
    longitude: float,
    result_type: str,
    district_key: object | None = None,
) -> list[list[float]]:
    """Build a small image box around a map centroid."""
    settings = MAP_ICON_SETTINGS.get(result_type, MAP_ICON_SETTINGS["constituency"])
    district_offsets = DISTRICT_ICON_OFFSETS.get(normalize_area_name(district_key), {})
    lon_radius = float(settings["lon_radius"])
    lat_radius = float(settings["lat_radius"])
    longitude = longitude + float(settings["lon_offset"]) + float(
        district_offsets.get("lon_offset", 0)
    )
    latitude = latitude + float(settings["lat_offset"]) + float(
        district_offsets.get("lat_offset", 0)
    )
    return [
        [longitude - lon_radius, latitude + lat_radius],
        [longitude + lon_radius, latitude + lat_radius],
        [longitude + lon_radius, latitude - lat_radius],
        [longitude - lon_radius, latitude - lat_radius],
    ]


def district_winner_icon_layers(
    summary_df: pd.DataFrame,
    centroids_df: pd.DataFrame,
    result_type: str,
) -> list[dict[str, object]]:
    """Create Mapbox image layers for district winner portraits."""
    if summary_df.empty or centroids_df.empty:
        return []

    plot_df = summary_df.merge(centroids_df, on="district_key", how="left")
    plot_df = valid_coordinate_rows(plot_df)
    layers = []

    for _, row in plot_df.iterrows():
        source = winner_map_icon_source(row.get("winner"), result_type)
        if not source:
            continue

        layers.append(
            {
                "sourcetype": "image",
                "source": source,
                "coordinates": image_marker_coordinates(
                    float(row["latitude"]),
                    float(row["longitude"]),
                    result_type,
                    row.get("district_key"),
                ),
                "opacity": 0.96,
                "below": "",
            }
        )

    return layers


def overall_summary(
    df: pd.DataFrame,
    result_type: str,
    year_label: str,
    base_columns: set[str],
    candidate_party_map: dict[str, str],
) -> dict[str, object] | None:
    """Summarize the winner for the whole district-2 dataset."""
    if df.empty or "district" not in df.columns:
        return None

    working = df.copy()
    if year_label != "2566" and "vote_phase" in working.columns:
        working = working[working["vote_phase"] == "election_day"].copy()

    working["district_key"] = working["district"].map(normalize_area_name)
    target_keys = {normalize_area_name(district) for district in TARGET_DISTRICTS}
    working = working[working["district_key"].isin(target_keys)].copy()
    if working.empty:
        return None

    party_scores = (
        previous_party_scores(working, result_type)
        if year_label == "2566"
        else current_party_scores(working, result_type, base_columns, candidate_party_map)
    )
    if party_scores.empty:
        return None

    totals = party_scores.sum().sort_values(ascending=False)
    total_votes = float(totals.sum())
    if total_votes <= 0 or totals.empty:
        return None

    winner = str(totals.index[0])
    runner_up = str(totals.index[1]) if len(totals) > 1 else ""
    winner_votes = float(totals.iloc[0])
    runner_up_votes = float(totals.iloc[1]) if len(totals) > 1 else 0
    winner_party = winner
    runner_up_party = runner_up
    winner_display = winner
    runner_up_display = runner_up
    winner_number = ""
    runner_up_number = ""

    if result_type == "constituency":
        if year_label == "2566":
            winner_display = PREVIOUS_66_CONSTITUENCY_CANDIDATES_BY_PARTY.get(
                winner_party, winner_party
            )
            runner_up_display = PREVIOUS_66_CONSTITUENCY_CANDIDATES_BY_PARTY.get(
                runner_up_party, runner_up_party
            )
            winner_party = PREVIOUS_66_CONSTITUENCY_CANDIDATE_PARTIES.get(
                winner_display, winner_party
            )
            runner_up_party = PREVIOUS_66_CONSTITUENCY_CANDIDATE_PARTIES.get(
                runner_up_display, runner_up_party
            )
        else:
            candidate_scores = current_entity_scores(working, base_columns)
            if not candidate_scores.empty:
                candidate_totals = candidate_scores.sum().sort_values(ascending=False)
                winner_display = str(candidate_totals.index[0])
                runner_up_display = (
                    str(candidate_totals.index[1]) if len(candidate_totals) > 1 else ""
                )
                winner_votes = float(candidate_totals.iloc[0])
                runner_up_votes = (
                    float(candidate_totals.iloc[1]) if len(candidate_totals) > 1 else 0
                )
                winner_party = party_key(
                    candidate_party_map.get(winner_display, winner_display)
                )
                runner_up_party = (
                    party_key(candidate_party_map.get(runner_up_display, runner_up_display))
                    if runner_up_display
                    else ""
                )
                winner = winner_party
                runner_up = runner_up_party

        winner_profile = CANDIDATE_PROFILES.get(winner_display, {})
        runner_up_profile = CANDIDATE_PROFILES.get(runner_up_display, {})
        winner_number = str(winner_profile.get("number", ""))
        runner_up_number = str(runner_up_profile.get("number", ""))
    else:
        winner_profile = {}
        runner_up_profile = {}

    return {
        "year": year_label,
        "result_type": result_type,
        "winner": winner,
        "winner_display": winner_display,
        "winner_party": winner_party,
        "winner_number": winner_number,
        "winner_image": winner_profile.get("image") or party_logo_url(winner_party),
        "winner_votes": int(winner_votes),
        "winner_share": winner_votes / total_votes,
        "runner_up": runner_up,
        "runner_up_display": runner_up_display,
        "runner_up_party": runner_up_party,
        "runner_up_number": runner_up_number,
        "runner_up_image": runner_up_profile.get("image") or party_logo_url(runner_up_party),
        "runner_up_votes": int(runner_up_votes),
        "runner_up_share": runner_up_votes / total_votes if total_votes else 0,
        "margin_votes": int(winner_votes - runner_up_votes),
        "margin_share": (winner_votes - runner_up_votes) / total_votes,
        "valid_votes": int(total_votes),
        "comparison_key": winner_party,
        "party_shares": {str(party): float(votes) / total_votes for party, votes in totals.items()},
    }


def render_district_winner_map(
    summary_df: pd.DataFrame,
    centroids_df: pd.DataFrame,
    title: str,
    result_type: str,
    party_colors: dict[str, str],
    fallback_colors: list[str],
) -> None:
    """Render a reusable district winner map with GeoJSON or centroid fallback."""
    if summary_df.empty:
        st.info("ไม่มีข้อมูลรายอำเภอสำหรับแสดงแผนที่")
        return

    geojson_data = load_district_geojson()
    color_map = party_color_map(
        sorted(summary_df["winner"].dropna().unique()),
        party_colors,
        fallback_colors,
    )

    if geojson_data["features"]:
        fig = px.choropleth_mapbox(
            summary_df,
            geojson=geojson_data,
            locations="district_key",
            featureidkey="properties.area_key",
            color="winner",
            color_discrete_map=color_map,
            hover_name="district",
            hover_data={
                "district_key": False,
                "winner": True,
                "winner_votes": ":,",
                "winner_share": ":.2%",
                "runner_up": True,
                "margin_votes": ":,",
                "margin_share": ":.2%",
                "valid_votes": ":,",
            },
            opacity=0.78,
            center=geojson_center(geojson_data),
            zoom=8.2,
            height=430,
            title=title,
        )
        fig.update_traces(marker_line_width=1.4, marker_line_color="#FFFFFF")
    else:
        plot_df = summary_df.merge(centroids_df, on="district_key", how="left")
        plot_df = valid_coordinate_rows(plot_df)
        if plot_df.empty:
            st.warning("ยังไม่พบ GeoJSON boundary และไม่มีพิกัด centroid สำหรับแสดงแผนที่")
            return

        fig = px.scatter_mapbox(
            plot_df,
            lat="latitude",
            lon="longitude",
            color="winner",
            size="valid_votes",
            color_discrete_map=color_map,
            hover_name="district",
            hover_data={
                "winner": True,
                "winner_votes": ":,",
                "winner_share": ":.2%",
                "runner_up": True,
                "margin_votes": ":,",
                "margin_share": ":.2%",
                "valid_votes": ":,",
                "latitude": False,
                "longitude": False,
            },
            zoom=8.2,
            height=430,
            title=title,
        )

    icon_layers = district_winner_icon_layers(summary_df, centroids_df, result_type)
    fig.update_layout(
        mapbox_style="carto-positron",
        mapbox_layers=icon_layers,
        legend_title_text="ผู้ชนะ",
        margin=dict(l=0, r=0, t=48, b=0),
        font=dict(family="Tahoma, Arial, sans-serif"),
    )
    st.plotly_chart(fig, width="stretch")


def party_logo_url(value: object) -> str | None:
    """Return a known party logo URL for winner summary cards."""
    return PARTY_LOGOS.get(party_key(value))


def comparison_badge(
    label: str,
    summary: dict[str, object],
    comparison_summary: dict[str, object] | None,
) -> tuple[str, str, str]:
    """Return badge text and colors for overall winner cards."""
    if label != "ปีนี้" or not comparison_summary:
        return f"{summary['winner_share']:.2%}", "#EEF2FF", "#3730A3"

    previous_party_shares = comparison_summary.get("party_shares", {})
    comparison_key = str(summary.get("comparison_key", summary["winner"]))
    previous_share = float(previous_party_shares.get(comparison_key, 0))
    delta = float(summary["winner_share"]) - previous_share
    delta_points = abs(delta) * 100
    if delta > 0:
        return f"เพิ่มขึ้นจากปีที่แล้ว {delta_points:.2f}%", "#DCFCE7", "#166534"
    if delta < 0:
        return f"ลดลงจากปีที่แล้ว {delta_points:.2f}%", "#FEE2E2", "#991B1B"
    return "เท่ากับปีที่แล้ว", "#F3F4F6", "#374151"


def render_overall_card(
    label: str,
    summary: dict[str, object],
    comparison_summary: dict[str, object] | None,
    party_colors: dict[str, str],
) -> None:
    """Render one large overall winner card."""
    is_constituency = summary.get("result_type") == "constituency"
    winner_party = str(summary.get("winner_party", summary["winner"]))
    runner_up_party = str(summary.get("runner_up_party", summary.get("runner_up", "")))
    winner_display = str(summary.get("winner_display", summary["winner"]))
    runner_up_display = str(summary.get("runner_up_display", summary.get("runner_up", "")))
    color = party_color(winner_party, party_colors) or "#111827"
    winner_asset = str(summary.get("winner_image") or party_logo_url(winner_party) or "")
    winner_image_style = (
        "width:82px;height:96px;object-fit:cover;border-radius:12px;flex:0 0 82px;"
        if is_constituency
        else "width:72px;height:72px;object-fit:contain;flex:0 0 72px;"
    )
    logo_html = (
        f'<img src="{html.escape(winner_asset)}" style="{winner_image_style}">'
        if winner_asset
        else ""
    )
    badge_text, badge_bg, badge_fg = comparison_badge(label, summary, comparison_summary)
    if is_constituency:
        party_line = html.escape(winner_party)
    else:
        party_line = html.escape(
            PARTYLIST_CANDIDATE_NAMES.get(party_key(winner_party), winner_party)
        )

    runner_up_html = ""
    if is_constituency and runner_up_display:
        runner_asset = str(summary.get("runner_up_image") or party_logo_url(runner_up_party) or "")
        runner_image_html = (
            f'<img src="{html.escape(runner_asset)}" '
            'style="width:42px;height:42px;object-fit:cover;border-radius:9px;flex:0 0 42px;">'
            if runner_asset
            else ""
        )
        runner_meta_bits = []
        if runner_up_party:
            runner_meta_bits.append(html.escape(runner_up_party))
        runner_meta = " | ".join(runner_meta_bits)
        runner_up_html = f"""
        <div style="display:flex;align-items:center;gap:10px;margin:12px 0 2px 0;">
            <div style="font-size:13px;font-weight:900;color:#374151;min-width:54px;">อันดับ 2</div>
            {runner_image_html}
            <div>
                <div style="font-size:15px;font-weight:850;color:#111827;line-height:1.2;">
                    {html.escape(runner_up_display)}
                </div>
                <div style="font-size:13px;color:#6B7280;line-height:1.25;">
                    {runner_meta} | คะแนน {summary['runner_up_votes']:,} ({summary['runner_up_share']:.2%})
                </div>
            </div>
        </div>
        """

    runner_up_text = (
        ""
        if is_constituency
        else f"อันดับ 2: {html.escape(runner_up_display)} |"
    )
    st.markdown(
        f"""
        <div style="display:flex;align-items:center;gap:16px;margin:4px 0 10px 0;">
            {logo_html}
            <div>
                <div style="font-size:25px;font-weight:800;color:#111827;line-height:1.15;">
                    {label}
                </div>
                <div style="font-size:36px;font-weight:900;color:{color};line-height:1.05;margin-top:2px;">
                    {html.escape(winner_display)}
                </div>
                <div style="font-size:15px;font-weight:800;color:{color};line-height:1.25;margin-top:3px;">
                    {party_line}
                </div>
                <div style="
                    display:inline-block;margin-top:9px;padding:4px 11px;border-radius:999px;
                    background:{badge_bg};color:{badge_fg};font-size:15px;font-weight:800;">
                    {html.escape(badge_text)}
                </div>
            </div>
        </div>
        {runner_up_html}
        <div style="color:#6B7280;font-size:14px;margin-top:4px;">
            {runner_up_text}
            ส่วนต่าง {summary['margin_votes']:,} ({summary['margin_share']:.2%})
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_overall_summary(
    current_overall: dict[str, object] | None,
    previous_overall: dict[str, object] | None,
    party_colors: dict[str, str],
) -> None:
    """Render whole-constituency winner cards for current and previous results."""
    st.markdown("**ผลรวมทั้งเขต 2**")
    columns = st.columns(2)
    summaries = [
        ("ปีนี้", current_overall),
        ("ปีที่แล้ว (66)", previous_overall),
    ]
    for column, (label, summary) in zip(columns, summaries):
        with column:
            if not summary:
                st.info(f"ไม่มีข้อมูลผลรวม {label}")
                continue
            comparison_summary = previous_overall if label == "ปีนี้" else None
            render_overall_card(
                label,
                summary,
                comparison_summary,
                party_colors,
            )


def station_winners(
    df: pd.DataFrame,
    result_type: str,
    selected_phases: list[str],
    base_columns: set[str],
    candidate_party_map: dict[str, str],
) -> pd.DataFrame:
    """Build current-year station-level winner rows."""
    if df.empty:
        return pd.DataFrame()

    working = df.copy()
    if selected_phases and "vote_phase" in working.columns:
        working = working[working["vote_phase"].isin(selected_phases)].copy()

    working = valid_coordinate_rows(working)
    if working.empty:
        return pd.DataFrame()

    score_columns = current_score_columns(working, base_columns)
    if not score_columns:
        return pd.DataFrame()

    scores = working[score_columns].apply(pd.to_numeric, errors="coerce").fillna(0)
    station_df = working[
        [
            "district",
            "subdistrict",
            "unit_index",
            "vote_phase",
            "latitude",
            "longitude",
            "ballot_valid",
        ]
    ].copy()
    station_df["winner_entity"] = scores.idxmax(axis=1)
    station_df["winner_votes"] = scores.max(axis=1).astype(int)
    station_df["winner_party"] = station_df["winner_entity"].map(
        lambda value: party_key(candidate_party_map.get(value, value))
        if result_type == "constituency"
        else party_key(value)
    )
    station_df["winner_display"] = station_df.apply(
        lambda row: f"{row['winner_entity']} ({row['winner_party']})"
        if result_type == "constituency"
        else row["winner_party"],
        axis=1,
    )
    valid = pd.to_numeric(station_df["ballot_valid"], errors="coerce").fillna(0)
    station_df["winner_share"] = (station_df["winner_votes"] / valid.replace(0, pd.NA)).fillna(0)
    station_df["vote_phase_label"] = station_df["vote_phase"].map(
        lambda value: VOTE_PHASE_LABELS.get(str(value), str(value))
    )
    return station_df


def render_station_map(
    station_df: pd.DataFrame,
    party_colors: dict[str, str],
    fallback_colors: list[str],
) -> None:
    """Render station-level winner points."""
    if station_df.empty:
        st.info("ไม่มีข้อมูลพิกัดรายหน่วยหลังจาก filter")
        return

    fig = px.scatter_mapbox(
        station_df,
        lat="latitude",
        lon="longitude",
        color="winner_party",
        size="winner_votes",
        color_discrete_map=party_color_map(
            sorted(station_df["winner_party"].dropna().unique()),
            party_colors,
            fallback_colors,
        ),
        hover_name="winner_display",
        hover_data={
            "district": True,
            "subdistrict": True,
            "unit_index": True,
            "vote_phase_label": True,
            "winner_votes": ":,",
            "winner_share": ":.2%",
            "latitude": False,
            "longitude": False,
        },
        zoom=8.6,
        height=560,
        title="ผู้ชนะรายหน่วยเลือกตั้ง",
    )
    fig.update_layout(
        mapbox_style="carto-positron",
        legend_title_text="พรรคของผู้ชนะ",
        margin=dict(l=0, r=0, t=48, b=0),
        font=dict(family="Tahoma, Arial, sans-serif"),
    )
    st.plotly_chart(fig, width="stretch")


def heatmap_share(
    df: pd.DataFrame,
    result_type: str,
    area_level: str,
    top_n: int,
    selected_phases: list[str],
    base_columns: set[str],
    candidate_party_map: dict[str, str],
) -> pd.DataFrame:
    """Build current-year vote-share heatmap data."""
    if df.empty:
        return pd.DataFrame()

    working = df.copy()
    if selected_phases and "vote_phase" in working.columns:
        working = working[working["vote_phase"].isin(selected_phases)].copy()
    if working.empty:
        return pd.DataFrame()

    if area_level == "district":
        working["area_label"] = working.apply(
            lambda row: display_area_name(row.get("district"))
            if normalize_area_name(row.get("district"))
            else VOTE_PHASE_LABELS.get(str(row.get("vote_phase")), str(row.get("vote_phase"))),
            axis=1,
        )
    else:
        working["area_label"] = working.apply(
            lambda row: (
                f"{display_area_name(row.get('district'))} / {display_area_name(row.get('subdistrict'))}"
                if normalize_area_name(row.get("district")) or normalize_area_name(row.get("subdistrict"))
                else VOTE_PHASE_LABELS.get(str(row.get("vote_phase")), str(row.get("vote_phase")))
            ),
            axis=1,
        )

    party_scores = current_party_scores(working, result_type, base_columns, candidate_party_map)
    if party_scores.empty:
        return pd.DataFrame()

    score_df = pd.concat([working[["area_label"]], party_scores], axis=1)
    grouped = score_df.groupby("area_label")[party_scores.columns].sum()
    selected = list(grouped.sum().sort_values(ascending=False).head(top_n).index)
    denominator = grouped[selected].sum(axis=1).replace(0, pd.NA)
    return grouped[selected].div(denominator, axis=0).fillna(0)


def render_heatmap(share_df: pd.DataFrame) -> None:
    """Render a vote-share heatmap."""
    if share_df.empty:
        st.info("ไม่มีข้อมูล heatmap")
        return

    fig = px.imshow(
        share_df,
        aspect="auto",
        color_continuous_scale="Blues",
        labels=dict(x="พรรค", y="พื้นที่", color="Vote share"),
        text_auto=".0%",
    )
    fig.update_layout(
        height=max(420, 24 * len(share_df)),
        margin=dict(l=20, r=20, t=20, b=20),
        font=dict(family="Tahoma, Arial, sans-serif"),
    )
    st.plotly_chart(fig, width="stretch")


def render_result_map_sections(
    current_raw_df: pd.DataFrame,
    current_grouped_df: pd.DataFrame,
    constituency_raw_df: pd.DataFrame,
    partylist_raw_df: pd.DataFrame,
    previous_66_df: pd.DataFrame,
    result_type: str,
    base_columns: set[str],
    candidate_party_map: dict[str, str],
    party_colors: dict[str, str],
    fallback_colors: list[str],
) -> None:
    """Render comparison maps, station map, and vote-share heatmap."""
    if current_grouped_df.empty:
        current_grouped_df = current_raw_df.copy()

    current_summary = district_summary(
        current_grouped_df,
        result_type,
        "current",
        base_columns,
        candidate_party_map,
    )
    previous_summary = district_summary(
        previous_66_df,
        result_type,
        "2566",
        base_columns,
        candidate_party_map,
    )
    centroids_df = district_centroids(current_raw_df)

    if not load_district_geojson()["features"]:
        st.caption(
            "ยังไม่พบ GeoJSON boundary ใน `data/jsonGeo`; ภาพรวมรายอำเภอจะแสดงเป็น bubble map จาก centroid ไปก่อน"
        )
    render_overall_summary(
        overall_summary(
            current_grouped_df,
            result_type,
            "current",
            base_columns,
            candidate_party_map,
        ),
        overall_summary(
            previous_66_df,
            result_type,
            "2566",
            base_columns,
            candidate_party_map,
        ),
        party_colors,
    )

    col_current, col_previous = st.columns(2)
    with col_current:
        render_district_winner_map(
            current_summary,
            centroids_df,
            "ปีนี้: ผู้ชนะรายอำเภอ",
            result_type,
            party_colors,
            fallback_colors,
        )
    with col_previous:
        render_district_winner_map(
            previous_summary,
            centroids_df,
            "ปีที่แล้ว (66): ผู้ชนะรายอำเภอ",
            result_type,
            party_colors,
            fallback_colors,
        )

    station_section, heatmap_section = st.tabs(["Map รายหน่วยเลือกตั้ง", "Heatmap สัดส่วนคะแนน"])
    with station_section:
        station_result_label = st.radio(
            "ประเภทคะแนนใน map รายหน่วย",
            ["ส.ส.เขต", "บัญชีรายชื่อ"],
            horizontal=True,
            index=1 if result_type == "partylist" else 0,
            key=f"result_map_station_type_{result_type}",
        )
        station_result_type = "partylist" if station_result_label == "บัญชีรายชื่อ" else "constituency"
        station_raw_df = partylist_raw_df.copy() if station_result_type == "partylist" else constituency_raw_df.copy()
        phase_options = (
            sorted(station_raw_df["vote_phase"].dropna().unique())
            if "vote_phase" in station_raw_df.columns
            else []
        )
        default_phases = ["election_day"] if "election_day" in phase_options else phase_options
        selected_phases = st.multiselect(
            "Vote phase",
            phase_options,
            default=default_phases,
            key=f"result_map_phase_{result_type}_{station_result_type}",
        )
        render_station_map(
            station_winners(
                station_raw_df,
                station_result_type,
                selected_phases,
                base_columns,
                candidate_party_map,
            ),
            party_colors,
            fallback_colors,
        )

    with heatmap_section:
        controls = st.columns([1, 1, 1.7])
        area_label = controls[0].radio(
            "ระดับพื้นที่",
            ["อำเภอ", "ตำบล"],
            horizontal=True,
            key=f"result_map_heatmap_area_{result_type}",
        )
        top_n = controls[1].slider(
            "จำนวนพรรคใน heatmap",
            min_value=3,
            max_value=15,
            value=8,
            key=f"result_map_heatmap_top_n_{result_type}",
        )
        heatmap_phase_options = (
            sorted(current_raw_df["vote_phase"].dropna().unique())
            if "vote_phase" in current_raw_df.columns
            else []
        )
        default_heatmap_phases = (
            ["election_day"] if "election_day" in heatmap_phase_options else heatmap_phase_options
        )
        selected_heatmap_phases = controls[2].multiselect(
            "Vote phase ใน heatmap",
            heatmap_phase_options,
            default=default_heatmap_phases,
            key=f"result_map_heatmap_phase_{result_type}",
        )
        area_level = "district" if area_label == "อำเภอ" else "subdistrict"
        render_heatmap(
            heatmap_share(
                current_raw_df,
                result_type,
                area_level,
                top_n,
                selected_heatmap_phases,
                base_columns,
                candidate_party_map,
            )
        )
