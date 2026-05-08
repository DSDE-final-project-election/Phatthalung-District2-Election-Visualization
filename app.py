import pandas as pd
import streamlit as st

from tabs import tab_anomaly, tab_heatmap, tab_map, tab_overview, tab_station, tab_votephase
from utils.loader import (
    load_anomaly_summary,
    load_constituency,
    load_phase_summary,
    load_subdistrict_summary,
)

st.set_page_config(layout="wide", page_title="Election Analytics")

constituency_df = load_constituency()
anomaly_df = load_anomaly_summary()
subdistrict_df = load_subdistrict_summary()
phase_df = load_phase_summary()

st.sidebar.title("Election Analytics")

available_districts = pd.concat(
    [
        constituency_df.get("district", pd.Series(dtype="object")),
        anomaly_df.get("district", pd.Series(dtype="object")),
        subdistrict_df.get("district", pd.Series(dtype="object")),
    ],
    ignore_index=True,
).dropna()
district_options = sorted(available_districts.unique())
selected_district = st.sidebar.selectbox("District", ["All"] + district_options)

if selected_district != "All":
    filtered_df = constituency_df[constituency_df["district"] == selected_district]
    filtered_anomaly_df = anomaly_df[anomaly_df["district"] == selected_district]
    filtered_subdistrict_df = subdistrict_df[subdistrict_df["district"] == selected_district]
else:
    filtered_df = constituency_df
    filtered_anomaly_df = anomaly_df
    filtered_subdistrict_df = subdistrict_df

st.sidebar.metric("Total Stations", len(filtered_df))
st.sidebar.metric("Total Anomalies", len(filtered_anomaly_df))

tabs = st.tabs(
    [
        "📊 Overview",
        "🚨 Anomaly",
        "🗺 Map",
        "🌡 Heatmap",
        "🔬 Station Explorer",
        "🗳 Vote Phase",
    ]
)

with tabs[0]:
    tab_overview.render(filtered_df, filtered_anomaly_df)

with tabs[1]:
    tab_anomaly.render(filtered_anomaly_df)

with tabs[2]:
    tab_map.render(filtered_df)

with tabs[3]:
    tab_heatmap.render(filtered_subdistrict_df)

with tabs[4]:
    tab_station.render(filtered_df)

with tabs[5]:
    tab_votephase.render(phase_df)
