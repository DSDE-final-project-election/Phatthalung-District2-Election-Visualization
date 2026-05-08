import streamlit as st
import pandas as pd


def render(phase_df: pd.DataFrame):
    st.subheader("Vote Phase")

    if not phase_df.empty:
        cols = st.columns(len(phase_df))
        for col, (_, row) in zip(cols, phase_df.iterrows()):
            phase = row.get("vote_phase", "Unknown")
            integrity_score = row.get("integrity_score", 0)
            col.metric(f"{phase} Integrity", f"{integrity_score:.2f}")

    # TODO: Implement grouped bar chart showing turnout and invalid_ratio by vote_phase.
    # TODO: Vote phase values are expected to be election_day and advance.
    st.info("Coming soon")
