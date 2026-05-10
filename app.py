from pathlib import Path

import pandas as pd
import streamlit as st

from tabs import tab_ballotBehavior, tab_candidatePartylistCompare, tab_districtOverview, tab_result, tab_strongholdArea
from utils.loader import (
    load_constituency,
    load_constituency_grouped_results,
    load_constituency_results,
    load_partylist_grouped_results,
    load_partylist_results,
    load_phase_summary,
    load_previous_66_grouped_results,
    load_subdistrict_summary,
)
from utils.theme import inject_global_theme

st.set_page_config(layout="wide", page_title="Election Analytics")
inject_global_theme()

DATA_DIR = Path(__file__).resolve().parent / "data"
NORMAL_ANOMALY = "NORMAL"


def _read_csv(filename: str) -> pd.DataFrame:
    try:
        return pd.read_csv(DATA_DIR / filename)
    except FileNotFoundError:
        return pd.DataFrame()


def _districts_from_csv(filename: str) -> pd.Series:
    try:
        return pd.read_csv(DATA_DIR / filename, usecols=["district"])["district"]
    except (FileNotFoundError, ValueError):
        return pd.Series(dtype="object")


def _station_count(df: pd.DataFrame) -> int:
    if df.empty:
        return 0

    station_df = df
    if "vote_phase" in station_df.columns:
        station_df = station_df[station_df["vote_phase"].astype(str) == "election_day"]

    key_columns = ["district", "subdistrict", "unit_index"]
    if set(key_columns).issubset(station_df.columns):
        return station_df[key_columns].dropna().drop_duplicates().shape[0]
    return len(station_df)


def _build_anomaly_df(*sources: tuple[str, pd.DataFrame]) -> pd.DataFrame:
    output_columns = [
        "source",
        "district",
        "subdistrict",
        "unit_index",
        "vote_phase",
        "anomaly_type",
        "integrity_score",
        "severity_score",
        "invalid_ratio",
        "winner_ratio",
        "vote_mismatch",
    ]
    frames = []

    for source_name, source_df in sources:
        if source_df.empty or "anomaly_type" not in source_df.columns:
            continue

        anomaly_mask = source_df["anomaly_type"].fillna(NORMAL_ANOMALY).astype(str) != NORMAL_ANOMALY
        frame = source_df.loc[anomaly_mask].copy()
        if frame.empty:
            continue

        frame["source"] = source_name
        for column in output_columns:
            if column not in frame.columns:
                frame[column] = pd.NA

        integrity = pd.to_numeric(frame["integrity_score"], errors="coerce")
        frame["severity_score"] = (100 - integrity).clip(lower=0, upper=100)
        frames.append(frame[output_columns])

    if not frames:
        return pd.DataFrame(columns=output_columns)
    return pd.concat(frames, ignore_index=True)


constituency_df = load_constituency()
constituency_result_df = load_constituency_results()
partylist_result_df = load_partylist_results()
constituency_grouped_result_df = load_constituency_grouped_results()
partylist_grouped_result_df = load_partylist_grouped_results()
previous_66_grouped_df = load_previous_66_grouped_results()
partylist_df = _read_csv("partylist_clean.csv")
subdistrict_df = load_subdistrict_summary()
phase_df = load_phase_summary()
anomaly_df = _build_anomaly_df(
    ("constituency", constituency_df),
    ("partylist", partylist_df),
)

st.sidebar.title("Election Analytics")


def election_day_rows(df: pd.DataFrame) -> pd.DataFrame:
    if "vote_phase" not in df.columns:
        return df
    return df[df["vote_phase"] == "election_day"]

available_districts = pd.concat(
    [
        _districts_from_csv("constituency_clean.csv"),
        _districts_from_csv("partylist_clean.csv"),
        constituency_df.get("district", pd.Series(dtype="object")),
        constituency_result_df.get("district", pd.Series(dtype="object")),
        partylist_result_df.get("district", pd.Series(dtype="object")),
        subdistrict_df.get("district", pd.Series(dtype="object")),
    ],
    ignore_index=True,
).dropna().astype(str)
district_options = sorted(available_districts.unique())
selected_district = st.sidebar.selectbox("District", ["All"] + district_options)

if selected_district != "All":
    filtered_df = constituency_df[constituency_df["district"].astype(str) == selected_district]
    filtered_anomaly_df = anomaly_df[anomaly_df["district"].astype(str) == selected_district]
    filtered_subdistrict_df = subdistrict_df[subdistrict_df["district"].astype(str) == selected_district]
else:
    filtered_df = constituency_df
    filtered_constituency_result_df = constituency_result_df
    filtered_partylist_result_df = partylist_result_df
    filtered_anomaly_df = anomaly_df
    filtered_subdistrict_df = subdistrict_df

st.sidebar.metric("Total Stations", _station_count(filtered_df))
st.sidebar.metric("Total Anomalies", len(filtered_anomaly_df))

tabs = st.tabs(
    [
        "📊 Overview",
        "🚨 Result",
        "🗺 Map",
        "🗺 Stronghold",
        "🔬 Station Explorer",
        "🗳 Vote Phase",
    ]
)

with tabs[0]:
    tab_districtOverview.render(filtered_df, filtered_anomaly_df, selected_district)

with tabs[1]:
    tab_result.render(
        constituency_result_df,
        partylist_result_df,
        constituency_grouped_result_df,
        partylist_grouped_result_df,
        previous_66_grouped_df,
    )

with tabs[2]:
    tab_candidatePartylistCompare.render(filtered_df)

with tabs[3]:
    tab_strongholdArea.render(filtered_constituency_result_df, filtered_partylist_result_df)

with tabs[4]:
    tab_ballotBehavior.render(filtered_df)
