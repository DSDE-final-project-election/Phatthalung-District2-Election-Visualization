from pathlib import Path

import pandas as pd
import streamlit as st

DATA_DIR = Path(__file__).resolve().parents[1] / "data"

CONSTITUENCY_COLUMNS = [
    "district",
    "subdistrict",
    "unit_index",
    "vote_phase",
    "ballot_total",
    "ballot_valid",
    "ballot_invalid",
    "ballot_no_vote",
    "invalid_ratio",
    "no_vote_ratio",
    "turnout",
    "winner_votes",
    "winner_ratio",
    "winner_margin",
    "vote_entropy",
    "vote_mismatch",
    "integrity_score",
    "anomaly_iforest",
    "anomaly_dbscan",
    "anomaly_type",
    "validation_error",
    "has_validation_error",
    "lat",
    "lon",
]

ANOMALY_SUMMARY_COLUMNS = [
    "district",
    "subdistrict",
    "unit_index",
    "anomaly_type",
    "integrity_score",
    "severity_score",
    "invalid_ratio",
    "winner_ratio",
    "mismatch_score",
]

SUBDISTRICT_SUMMARY_COLUMNS = [
    "district",
    "subdistrict",
    "turnout",
    "integrity_score",
    "vote_mismatch",
    "invalid_ratio",
]

PHASE_SUMMARY_COLUMNS = [
    "vote_phase",
    "turnout",
    "invalid_ratio",
    "integrity_score",
    "vote_mismatch",
]


def _load_csv(filename: str, columns: list[str]) -> pd.DataFrame:
    try:
        return pd.read_csv(DATA_DIR / filename)
    except FileNotFoundError:
        return pd.DataFrame(columns=columns)


@st.cache_data
def load_constituency() -> pd.DataFrame:
    return _load_csv("constituency_clean.csv", CONSTITUENCY_COLUMNS)


@st.cache_data
def load_anomaly_summary() -> pd.DataFrame:
    return _load_csv("anomaly_summary.csv", ANOMALY_SUMMARY_COLUMNS)


@st.cache_data
def load_subdistrict_summary() -> pd.DataFrame:
    return _load_csv("subdistrict_summary.csv", SUBDISTRICT_SUMMARY_COLUMNS)


@st.cache_data
def load_phase_summary() -> pd.DataFrame:
    return _load_csv("phase_summary.csv", PHASE_SUMMARY_COLUMNS)
