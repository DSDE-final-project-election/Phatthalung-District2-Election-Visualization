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


def _data_file_version(filename: str) -> float:
    path = DATA_DIR / filename
    return path.stat().st_mtime if path.exists() else 0.0


@st.cache_data
def _load_csv_cached(
    filename: str,
    fallback_filename: str,
    columns: tuple[str, ...],
    file_version: float,
    fallback_version: float,
) -> pd.DataFrame:
    primary_path = DATA_DIR / filename
    fallback_path = DATA_DIR / fallback_filename if fallback_filename else None

    if primary_path.exists():
        return pd.read_csv(primary_path)
    if fallback_path and fallback_path.exists():
        return pd.read_csv(fallback_path)
    return pd.DataFrame(columns=list(columns))


def load_constituency() -> pd.DataFrame:
    return _load_csv_cached(
        "constituency_clean.csv",
        "constituency.csv",
        tuple(CONSTITUENCY_COLUMNS),
        _data_file_version("constituency_clean.csv"),
        _data_file_version("constituency.csv"),
    )


def load_partylist() -> pd.DataFrame:
    return _load_csv_cached(
        "partylist_clean.csv",
        "partylist.csv",
        tuple(PARTYLIST_COLUMNS),
        _data_file_version("partylist_clean.csv"),
        _data_file_version("partylist.csv"),
    )


def load_cross_form_validation() -> pd.DataFrame:
    return _load_csv_cached(
        "cross_form_validation.csv",
        "",
        tuple(CROSS_FORM_COLUMNS),
        _data_file_version("cross_form_validation.csv"),
        0.0,
    )


def load_subdistrict_summary() -> pd.DataFrame:
    return _load_csv_cached(
        "subdistrict_summary.csv",
        "",
        tuple(SUBDISTRICT_SUMMARY_COLUMNS),
        _data_file_version("subdistrict_summary.csv"),
        0.0,
    )


def load_phase_summary() -> pd.DataFrame:
    return _load_csv_cached(
        "phase_summary.csv",
        "",
        tuple(PHASE_SUMMARY_COLUMNS),
        _data_file_version("phase_summary.csv"),
        0.0,
    )


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
