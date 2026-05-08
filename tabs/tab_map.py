import streamlit as st
import pandas as pd


def render(df: pd.DataFrame):
    st.subheader("Map")

    # TODO: Implement Folium map centered on Thailand at (13.7, 100.5), zoom level 6.
    # TODO: Add dot markers using lat/lon columns, colored red for anomalies and green for normal stations.
    # TODO: Add marker popups showing unit_index, district, anomaly_type, and integrity_score.
    # TODO: Render the map with streamlit-folium st_folium().
    st.info("Coming soon")
