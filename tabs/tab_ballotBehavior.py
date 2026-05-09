import streamlit as st
import pandas as pd


def render(df: pd.DataFrame):
    st.subheader("Station Explorer")

    districts = sorted(df["district"].dropna().unique()) if not df.empty else []
    selected_district = st.selectbox("Choose District", districts) if districts else None

    district_df = df[df["district"] == selected_district] if selected_district else pd.DataFrame(columns=df.columns)
    unit_indexes = sorted(district_df["unit_index"].dropna().unique()) if not district_df.empty else []
    selected_unit = st.selectbox("Choose Unit Index", unit_indexes) if unit_indexes else None

    station_df = district_df[district_df["unit_index"] == selected_unit] if selected_unit is not None else pd.DataFrame(columns=df.columns)

    if not station_df.empty:
        station = station_df.iloc[0]
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Integrity Score", f"{station.get('integrity_score', 0):.2f}")
        col2.metric("Invalid Ratio", f"{station.get('invalid_ratio', 0):.2%}")
        col3.metric("Turnout", f"{station.get('turnout', 0):.2%}")
        col4.metric("Winner Ratio", f"{station.get('winner_ratio', 0):.2%}")
    else:
        st.write("No station selected.")

    # TODO: Implement Plotly radar chart comparing selected station vs district average.
    # TODO: Radar chart fields: invalid_ratio, winner_ratio, turnout, vote_entropy, and winner_margin.
    st.info("Coming soon")
