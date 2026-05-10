from pathlib import Path

import pandas as pd
import streamlit as st

DATA_DIR = Path(__file__).resolve().parents[1] / "data"

CONSTITUENCY_COLUMNS = [
    "district",
    "subdistrict",
    "unit_index",
    "form_type",
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
]

PARTYLIST_COLUMNS = [
    "district",
    "subdistrict",
    "unit_index",
    "form_type",
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
]

CROSS_FORM_COLUMNS = [
    "district",
    "subdistrict",
    "unit_index",
    "vote_phase",
    "ballot_total_const",
    "ballot_total_party",
    "cross_mismatch",
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

RESULT_BASE_COLUMNS = [
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
def load_partylist() -> pd.DataFrame:
    return _load_csv("partylist_clean.csv", PARTYLIST_COLUMNS)


@st.cache_data
def load_cross_form_validation() -> pd.DataFrame:
    return _load_csv("cross_form_validation.csv", CROSS_FORM_COLUMNS)


@st.cache_data
def load_subdistrict_summary() -> pd.DataFrame:
    return _load_csv("subdistrict_summary.csv", SUBDISTRICT_SUMMARY_COLUMNS)


@st.cache_data
def load_phase_summary() -> pd.DataFrame:
    return _load_csv("phase_summary.csv", PHASE_SUMMARY_COLUMNS)


@st.cache_data
def load_constituency_results() -> pd.DataFrame:
    return _load_csv("constituency_with_latlong_minimal.csv", RESULT_BASE_COLUMNS)


@st.cache_data
def load_partylist_results() -> pd.DataFrame:
    return _load_csv("partylist_with_latlong_minimal.csv", RESULT_BASE_COLUMNS)


@st.cache_data
def load_constituency_grouped_results() -> pd.DataFrame:
    return _load_csv("constituency_with_latlong_minimal_grouped.csv", RESULT_BASE_COLUMNS)


@st.cache_data
def load_partylist_grouped_results() -> pd.DataFrame:
    return _load_csv("partylist_with_latlong_minimal_grouped.csv", RESULT_BASE_COLUMNS)


@st.cache_data
def load_previous_66_grouped_results() -> pd.DataFrame:
    return _load_csv("phatthalung_2_grouped_66.csv", ["district", "subdistrict"])
