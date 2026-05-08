import streamlit as st
import pandas as pd


def _highlight_anomaly_type(value: str) -> str:
    color_map = {
        "NORMAL": "background-color: #d9f7d9",
        "HIGH_INVALID": "background-color: #ffd6d6",
        "HIGH_WINNER_RATIO": "background-color: #fff2cc",
        "VOTE_MISMATCH": "background-color: #d9e8ff",
    }
    return color_map.get(str(value), "background-color: #f0f0f0")


def render(anomaly_df: pd.DataFrame):
    st.subheader("Anomaly")

    anomaly_types = sorted(anomaly_df["anomaly_type"].dropna().unique()) if not anomaly_df.empty else []
    selected_type = st.selectbox("Anomaly Type", ["All"] + anomaly_types)
    sort_by = st.selectbox("Sort By", ["severity_score", "integrity_score"])

    filtered_df = anomaly_df.copy()
    if selected_type != "All":
        filtered_df = filtered_df[filtered_df["anomaly_type"] == selected_type]

    if sort_by in filtered_df.columns:
        filtered_df = filtered_df.sort_values(sort_by, ascending=(sort_by == "integrity_score"))

    # TODO: Implement filtered anomaly results dataframe with color-coded anomaly_type column.
    if filtered_df.empty:
        st.dataframe(filtered_df)
    else:
        styled_df = filtered_df.style
        if hasattr(styled_df, "map"):
            st.dataframe(styled_df.map(_highlight_anomaly_type, subset=["anomaly_type"]))
        else:
            st.dataframe(styled_df.applymap(_highlight_anomaly_type, subset=["anomaly_type"]))

    # TODO: Implement anomaly chart and richer anomaly triage controls.
    st.info("Coming soon")

