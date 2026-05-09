import streamlit as st
import pandas as pd


def render(df: pd.DataFrame, anomaly_df: pd.DataFrame):
    st.subheader("Overview")

    total_stations = len(df)
    anomaly_count = len(anomaly_df)
    avg_integrity = df["integrity_score"].mean() if not df.empty else 0
    avg_invalid_ratio = df["invalid_ratio"].mean() if not df.empty else 0

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Stations", total_stations)
    col2.metric("Anomaly Count", anomaly_count)
    col3.metric("Avg Integrity Score", f"{avg_integrity:.2f}")
    col4.metric("Avg Invalid Ratio", f"{avg_invalid_ratio:.2%}")

    # TODO: Implement anomaly type breakdown bar chart.
    st.info("Coming soon")

    # TODO: Implement top 5 districts by anomaly count table.
    st.info("Coming soon")
