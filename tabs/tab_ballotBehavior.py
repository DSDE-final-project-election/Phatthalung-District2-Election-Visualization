from __future__ import annotations

from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from utils.theme import APP_COLORS, FONT_FAMILY


DATA_DIR = Path(__file__).resolve().parents[1] / "data"

ISSUE_TYPES = {
    "INCOMPLETE_DOCUMENT",
    "SCORE_BALLOT_MISMATCH",
    "UNUSUAL_VOTING_PATTERN",
    "HIGH_INVALID",
}

ISSUE_LABELS = {
    "NORMAL": "ไม่พบประเด็นจาก rule/model",
    "UNUSUAL_VOTING_PATTERN": "ลักษณะการลงคะแนนผิดปกติ",
    "INCOMPLETE_DOCUMENT": "เอกสารผิดพลาด",
    "SCORE_BALLOT_MISMATCH": "ผลรวมคะแนนไม่เท่าบัตรดี",
    "HIGH_INVALID": "สัดส่วนบัตรเสียสูง",
    "ADVANCE_VOTING_EXCLUDED": "เลือกตั้งล่วงหน้า วิเคราะห์แยก",
    "CROSS_FORM_MISMATCH": "บัตรรวม ส.ส.เขต/บัญชีรายชื่อไม่ตรงกัน",
}

ISSUE_COLORS = {
    "ไม่พบประเด็นจาก rule/model": APP_COLORS["accent_hover"],
    "ลักษณะการลงคะแนนผิดปกติ": APP_COLORS["signal_orange"],
    "เอกสารผิดพลาด": APP_COLORS["signal_warning"],
    "ผลรวมคะแนนไม่เท่าบัตรดี": APP_COLORS["signal_negative"],
    "สัดส่วนบัตรเสียสูง": "#C2410C",
    "เลือกตั้งล่วงหน้า วิเคราะห์แยก": APP_COLORS["accent"],
    "บัตรรวม ส.ส.เขต/บัญชีรายชื่อไม่ตรงกัน": "#7C3AED",
}

FORM_FILES = {
    "constituency": {
        "label": "ส.ส.เขต",
        "clean": "constituency_clean.csv",
        "spatial": "constituency_spatial_clusters.csv",
        "cluster_summary": "constituency_mixed_cluster_summary.csv",
        "issues": "constituency_clustered_issues.csv",
    },
    "partylist": {
        "label": "บัญชีรายชื่อ",
        "clean": "partylist_clean.csv",
        "spatial": "partylist_spatial_clusters.csv",
        "cluster_summary": "partylist_mixed_cluster_summary.csv",
        "issues": "partylist_clustered_issues.csv",
    },
}

FORM_SCOPE_LABELS = {
    "combined": "ทั้งหมด",
    "constituency": "ส.ส.เขต",
    "partylist": "บัญชีรายชื่อ",
}

METRIC_CONFIG = {
    "invalid_ratio": {
        "label": "Invalid ratio",
        "thai": "สัดส่วนบัตรเสีย",
        "color": APP_COLORS["signal_negative"],
        "scale": "OrRd",
    },
    "no_vote_ratio": {
        "label": "No vote ratio",
        "thai": "สัดส่วนไม่เลือกผู้ใด",
        "color": APP_COLORS["signal_orange"],
        "scale": "YlOrBr",
    },
    "valid_ratio": {
        "label": "Valid ratio",
        "thai": "สัดส่วนบัตรดี",
        "color": APP_COLORS["signal_positive"],
        "scale": "Greens",
    },
    "integrity_score": {
        "label": "Integrity score",
        "thai": "คะแนน integrity",
        "color": APP_COLORS["accent"],
        "scale": "Teal",
    },
    "issue_rate": {
        "label": "Review rate",
        "thai": "สัดส่วนพื้นที่ที่ควรตรวจต่อ",
        "color": APP_COLORS["accent_dark"],
        "scale": "Burg",
    },
}


def _csv_version(filename: str) -> float:
    path = DATA_DIR / filename
    return path.stat().st_mtime if path.exists() else 0.0


@st.cache_data(show_spinner=False)
def _read_csv(filename: str, file_version: float) -> pd.DataFrame:
    path = DATA_DIR / filename
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def _load_csv(filename: str) -> pd.DataFrame:
    return _read_csv(filename, _csv_version(filename))


def _format_percent(value: object) -> str:
    number = pd.to_numeric(value, errors="coerce")
    if pd.isna(number):
        return "-"
    return f"{float(number):.2%}"


def _format_pp(value: object) -> str:
    number = pd.to_numeric(value, errors="coerce")
    if pd.isna(number):
        return "-"
    return f"{float(number) * 100:+.2f} pp"


def _format_number(value: object) -> str:
    number = pd.to_numeric(value, errors="coerce")
    if pd.isna(number):
        return "-"
    return f"{float(number):,.0f}"


def _plotly_color(color: str) -> str:
    if isinstance(color, str) and color.startswith("#") and len(color) == 9:
        return color[:7]
    return color


def _safe_numeric(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series, errors="coerce").fillna(0)


def _safe_ratio(num: pd.Series, den: pd.Series) -> pd.Series:
    denominator = _safe_numeric(den).replace(0, pd.NA)
    return (_safe_numeric(num) / denominator).fillna(0)


def _with_ballot_features(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df.copy()

    working = df.copy()
    for column in ["ballot_total", "ballot_valid", "ballot_invalid", "ballot_no_vote"]:
        if column in working.columns:
            working[column] = _safe_numeric(working[column])

    if "ballot_total" in working.columns and "ballot_valid" in working.columns:
        working["valid_ratio"] = _safe_ratio(working["ballot_valid"], working["ballot_total"])
    elif "valid_ratio" not in working.columns:
        working["valid_ratio"] = 0

    if "invalid_ratio" not in working.columns and {"ballot_invalid", "ballot_total"}.issubset(working.columns):
        working["invalid_ratio"] = _safe_ratio(working["ballot_invalid"], working["ballot_total"])
    if "no_vote_ratio" not in working.columns and {"ballot_no_vote", "ballot_total"}.issubset(working.columns):
        working["no_vote_ratio"] = _safe_ratio(working["ballot_no_vote"], working["ballot_total"])

    if "anomaly_type" not in working.columns:
        working["anomaly_type"] = "NORMAL"
    working["anomaly_type"] = working["anomaly_type"].fillna("NORMAL").astype(str)
    working["issue_label"] = working["anomaly_type"].map(ISSUE_LABELS).fillna(working["anomaly_type"])
    working["is_review_unit"] = working["anomaly_type"].isin(ISSUE_TYPES)

    if "integrity_score" in working.columns:
        working["integrity_score"] = pd.to_numeric(working["integrity_score"], errors="coerce")
    else:
        working["integrity_score"] = pd.NA

    if "vote_mismatch" in working.columns:
        working["vote_mismatch"] = _safe_numeric(working["vote_mismatch"])
    else:
        working["vote_mismatch"] = 0

    return working


def _valid_coordinate_rows(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or not {"latitude", "longitude"}.issubset(df.columns):
        return pd.DataFrame(columns=df.columns)
    working = df.copy()
    working["latitude"] = pd.to_numeric(working["latitude"], errors="coerce")
    working["longitude"] = pd.to_numeric(working["longitude"], errors="coerce")
    return working[
        working["latitude"].between(6.5, 8.5)
        & working["longitude"].between(99.0, 101.0)
    ].copy()


def _district_options(*frames: pd.DataFrame) -> list[str]:
    values: list[str] = []
    for frame in frames:
        if not frame.empty and "district" in frame.columns:
            values.extend(frame["district"].dropna().astype(str).tolist())
    return sorted(pd.Series(values, dtype="object").dropna().unique().tolist())


def _filter_district(df: pd.DataFrame, district: str) -> pd.DataFrame:
    if district == "All" or df.empty or "district" not in df.columns:
        return df.copy()
    return df[df["district"].astype(str) == district].copy()


def _filter_dataset(df: pd.DataFrame, dataset_key: str) -> pd.DataFrame:
    if dataset_key == "combined" or df.empty or "dataset" not in df.columns:
        return df.copy()
    return df[df["dataset"].astype(str) == dataset_key].copy()


def _election_day(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "vote_phase" not in df.columns:
        return df.copy()
    return df[df["vote_phase"].astype(str) == "election_day"].copy()


def _infer_sidebar_district(df: pd.DataFrame, selected_district: str | None) -> str:
    if selected_district:
        return selected_district
    if df.empty or "district" not in df.columns:
        return "All"
    districts = df["district"].dropna().astype(str).unique()
    return districts[0] if len(districts) == 1 else "All"


def _review_score(df: pd.DataFrame) -> pd.Series:
    integrity_component = (100 - pd.to_numeric(df.get("integrity_score", 100), errors="coerce")).clip(0, 100).fillna(0)
    mismatch_ratio = _safe_ratio(df.get("vote_mismatch", pd.Series(0, index=df.index)), df.get("ballot_valid", pd.Series(0, index=df.index)))
    return (
        integrity_component
        + _safe_numeric(df.get("invalid_ratio", pd.Series(0, index=df.index))) * 100
        + _safe_numeric(df.get("no_vote_ratio", pd.Series(0, index=df.index))) * 60
        + mismatch_ratio * 100
        + df.get("is_review_unit", pd.Series(False, index=df.index)).astype(int) * 15
    )


def _aggregate_area(df: pd.DataFrame, area_level: str) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()

    group_cols = ["district"] if area_level == "district" else ["district", "subdistrict"]
    working = _election_day(df)
    working = working.dropna(subset=[column for column in group_cols if column in working.columns]).copy()
    if working.empty:
        return pd.DataFrame()

    grouped = (
        working.groupby(group_cols, dropna=False)
        .agg(
            ballot_total=("ballot_total", "sum"),
            ballot_valid=("ballot_valid", "sum"),
            ballot_invalid=("ballot_invalid", "sum"),
            ballot_no_vote=("ballot_no_vote", "sum"),
            issue_units=("is_review_unit", "sum"),
            unit_count=("unit_index", "count"),
            integrity_score=("integrity_score", "mean"),
        )
        .reset_index()
    )
    grouped["invalid_ratio"] = _safe_ratio(grouped["ballot_invalid"], grouped["ballot_total"])
    grouped["no_vote_ratio"] = _safe_ratio(grouped["ballot_no_vote"], grouped["ballot_total"])
    grouped["valid_ratio"] = _safe_ratio(grouped["ballot_valid"], grouped["ballot_total"])
    grouped["issue_rate"] = _safe_ratio(grouped["issue_units"], grouped["unit_count"])
    grouped["area_label"] = grouped[group_cols].astype(str).agg(" / ".join, axis=1)
    return grouped


def _metric_card(label: str, value: str, caption: str = "") -> None:
    st.markdown(
        f"""
        <div style="background:var(--color-surface);border:1px solid var(--color-border);
        border-radius:8px;padding:14px 16px;min-height:104px;">
            <div style="font-size:13px;font-weight:800;color:var(--color-text-muted);">{label}</div>
            <div style="font-size:clamp(22px,2.2vw,30px);font-weight:950;color:var(--color-text);
            line-height:1.05;margin-top:8px;white-space:nowrap;">{value}</div>
            <div style="font-size:12px;color:var(--color-text-muted);line-height:1.3;margin-top:8px;">{caption}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _colored_metric_card(label: str, value: str, caption: str, bg_var: str) -> None:
    bg_css = f"var({bg_var})" if bg_var.startswith("--") else bg_var
    caption_html = (
        f'<div style="font-size:12px;font-weight:700;color:rgba(254,254,254,.82);'
        f'line-height:1.35;margin-top:9px;">{caption}</div>'
        if caption
        else ""
    )
    html = (
        f'<div style="background:{bg_css};border:1px solid rgba(255,255,255,.28);'
        f'border-radius:8px;padding:15px 17px;min-height:126px;box-shadow:0 8px 18px rgba(64,64,65,.08);">'
        f'<div style="font-size:12px;font-weight:900;color:rgba(254,254,254,.82);line-height:1.25;">{label}</div>'
        f'<div style="font-size:clamp(27px,2.6vw,38px);font-weight:950;color:var(--color-text-inverse);'
        f'line-height:1;margin-top:9px;white-space:nowrap;">{value}</div>'
        f'{caption_html}</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def _cluster_metric_card(label: str, value: str, caption: str, accent: str) -> None:
    st.markdown(
        f"""
        <div style="background:var(--color-surface);border:1px solid var(--color-border);
        border-top:4px solid {accent};border-radius:8px;padding:13px 15px;height:124px;
        display:flex;flex-direction:column;justify-content:space-between;">
            <div style="font-size:12px;font-weight:900;color:var(--color-accent);
            line-height:1.35;min-height:34px;">{label}</div>
            <div style="font-size:clamp(26px,2.3vw,34px);font-weight:950;
            color:var(--color-text);line-height:1;white-space:nowrap;">{value}</div>
            <div style="font-size:12px;color:var(--color-text-muted);
            line-height:1.3;white-space:nowrap;">{caption}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_overview_cards(df: pd.DataFrame) -> None:
    election_df = _election_day(df)
    if election_df.empty:
        st.info("ยังไม่มีข้อมูลวันเลือกตั้งจริงสำหรับสรุปพฤติกรรมบัตร")
        return

    total = election_df["ballot_total"].sum()
    invalid_ratio = election_df["ballot_invalid"].sum() / total if total else 0
    no_vote_ratio = election_df["ballot_no_vote"].sum() / total if total else 0
    valid_ratio = election_df["ballot_valid"].sum() / total if total else 0
    review_units = int(election_df["is_review_unit"].sum())
    unit_count = len(election_df)

    cols = st.columns(5)
    with cols[0]:
        _metric_card("บัตรทั้งหมด", _format_number(total), "เฉพาะวันเลือกตั้งจริง")
    with cols[1]:
        _metric_card("Valid ratio", _format_percent(valid_ratio), "บัตรดี / บัตรทั้งหมด")
    with cols[2]:
        _metric_card("Invalid ratio", _format_percent(invalid_ratio), "บัตรเสีย / บัตรทั้งหมด")
    with cols[3]:
        _metric_card("No vote ratio", _format_percent(no_vote_ratio), "ไม่เลือกผู้ใด / บัตรทั้งหมด")
    with cols[4]:
        _metric_card("พื้นที่ที่ควรตรวจต่อ", f"{review_units}/{unit_count}", "ไม่ใช่ข้อกล่าวหา")


def _plot_area_metric(area_df: pd.DataFrame, metric: str, title: str) -> None:
    if area_df.empty:
        st.info("ไม่มีข้อมูลสำหรับกราฟพื้นที่")
        return
    config = METRIC_CONFIG[metric]
    plot_df = area_df.sort_values(metric, ascending=False).head(24).copy()
    fig = px.bar(
        plot_df,
        x=metric,
        y="area_label",
        orientation="h",
        color=metric,
        color_continuous_scale=config["scale"],
        hover_data={
            metric: ":.2%",
            "ballot_total": ":,",
            "issue_units": ":,",
            "unit_count": ":,",
            "area_label": False,
        },
        title=title,
        height=max(360, min(720, 26 * len(plot_df) + 110)),
    )
    fig.update_layout(
        yaxis_title="",
        xaxis_title=config["thai"],
        coloraxis_showscale=False,
        margin=dict(l=0, r=0, t=48, b=0),
        font=dict(family=FONT_FAMILY),
    )
    fig.update_xaxes(tickformat=".0%")
    fig.update_yaxes(autorange="reversed")
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def _render_metric_bars(area_df: pd.DataFrame) -> None:
    st.markdown("**Invalid / No vote / Valid ratio by area**")
    metric_tabs = st.tabs(["Invalid ratio", "No vote ratio", "Valid ratio", "Review rate"])
    with metric_tabs[0]:
        _plot_area_metric(area_df, "invalid_ratio", "สัดส่วนบัตรเสียตามพื้นที่")
    with metric_tabs[1]:
        _plot_area_metric(area_df, "no_vote_ratio", "สัดส่วนไม่เลือกผู้ใดตามพื้นที่")
    with metric_tabs[2]:
        _plot_area_metric(area_df, "valid_ratio", "สัดส่วนบัตรดีตามพื้นที่")
    with metric_tabs[3]:
        _plot_area_metric(area_df, "issue_rate", "สัดส่วนหน่วยที่ควรตรวจสอบเพิ่มเติม")


def _render_behavior_map(spatial_df: pd.DataFrame, metric: str, title_suffix: str) -> None:
    map_df = _valid_coordinate_rows(_election_day(spatial_df))
    if map_df.empty:
        st.info("ยังไม่มีข้อมูลพิกัดสำหรับแผนที่พฤติกรรมบัตร")
        return

    map_df = _with_ballot_features(map_df)
    map_df["review_status"] = map_df["is_integrity_or_anomaly_issue"].map(
        {True: "ควรตรวจสอบเพิ่มเติม", False: "ไม่พบประเด็นจาก rule/model"}
    ) if "is_integrity_or_anomaly_issue" in map_df.columns else map_df["is_review_unit"].map(
        {True: "ควรตรวจสอบเพิ่มเติม", False: "ไม่พบประเด็นจาก rule/model"}
    )
    map_df["display_unit"] = map_df["unit_index"].map(lambda value: f"หน่วย {value}")

    if metric == "mixed_kmeans_cluster" and metric in map_df.columns:
        map_df[metric] = map_df[metric].astype(str)
        fig = px.scatter_mapbox(
            map_df,
            lat="latitude",
            lon="longitude",
            color=metric,
            size="ballot_total",
            hover_name="display_unit",
            hover_data={
                "district": True,
                "subdistrict": True,
                "review_status": True,
                "invalid_ratio": ":.2%",
                "no_vote_ratio": ":.2%",
                "valid_ratio": ":.2%",
                "integrity_score": ":.2f",
                "latitude": False,
                "longitude": False,
            },
            zoom=8.6,
            height=560,
            title=f"แผนที่ cluster พฤติกรรมบัตร ({title_suffix})",
        )
        fig.update_layout(legend_title_text="Cluster")
    else:
        config = METRIC_CONFIG.get(metric, METRIC_CONFIG["invalid_ratio"])
        fig = px.scatter_mapbox(
            map_df,
            lat="latitude",
            lon="longitude",
            color=metric,
            size="ballot_total",
            color_continuous_scale=config["scale"],
            hover_name="display_unit",
            hover_data={
                "district": True,
                "subdistrict": True,
                "review_status": True,
                "invalid_ratio": ":.2%",
                "no_vote_ratio": ":.2%",
                "valid_ratio": ":.2%",
                "integrity_score": ":.2f",
                "latitude": False,
                "longitude": False,
            },
            zoom=8.6,
            height=560,
            title=f"แผนที่ {config['thai']} ({title_suffix})",
        )
        fig.update_layout(coloraxis_colorbar=dict(title=config["label"]))

    fig.update_layout(
        mapbox_style="carto-positron",
        margin=dict(l=0, r=0, t=48, b=0),
        font=dict(family=FONT_FAMILY),
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def _render_issue_breakdown(df: pd.DataFrame, cross_df: pd.DataFrame) -> None:
    election_df = _election_day(df)
    issue_counts = (
        election_df["issue_label"].value_counts().rename_axis("issue_label").reset_index(name="units")
        if not election_df.empty
        else pd.DataFrame(columns=["issue_label", "units"])
    )
    if not cross_df.empty and "cross_mismatch" in cross_df.columns:
        cross_count = int(pd.to_numeric(cross_df["cross_mismatch"], errors="coerce").fillna(0).gt(0).sum())
        if cross_count:
            issue_counts = pd.concat(
                [
                    issue_counts,
                    pd.DataFrame(
                        [{"issue_label": ISSUE_LABELS["CROSS_FORM_MISMATCH"], "units": cross_count}]
                    ),
                ],
                ignore_index=True,
            )

    issue_counts = issue_counts[issue_counts["issue_label"] != ISSUE_LABELS["NORMAL"]].copy()
    if issue_counts.empty:
        st.info("ยังไม่พบพื้นที่ที่ควรตรวจสอบเพิ่มเติมจาก rule/model ใน filter นี้")
        return

    fig = px.bar(
        issue_counts.sort_values("units", ascending=False),
        x="units",
        y="issue_label",
        orientation="h",
        color="issue_label",
        color_discrete_map=ISSUE_COLORS,
        title="Abnormal type ในความหมายของงานตรวจสอบ",
        height=max(300, 70 * len(issue_counts) + 110),
    )
    fig.update_layout(
        showlegend=False,
        xaxis_title="จำนวนหน่วย/รายการ",
        yaxis_title="",
        margin=dict(l=0, r=0, t=48, b=0),
        font=dict(family=FONT_FAMILY),
    )
    fig.update_yaxes(autorange="reversed")
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def _top_review_units(df: pd.DataFrame, limit: int = 15) -> pd.DataFrame:
    election_df = _election_day(df)
    if election_df.empty:
        return pd.DataFrame()
    working = election_df.copy()
    working["review_score"] = _review_score(working)
    working = working[working["is_review_unit"]].copy()
    if working.empty:
        return pd.DataFrame()
    columns = [
        "district",
        "subdistrict",
        "unit_index",
        "issue_label",
        "integrity_score",
        "invalid_ratio",
        "no_vote_ratio",
        "valid_ratio",
        "vote_mismatch",
        "review_score",
    ]
    return working.sort_values("review_score", ascending=False)[columns].head(limit)


def _render_review_table(df: pd.DataFrame) -> None:
    top_df = _top_review_units(df)
    if top_df.empty:
        st.info("ไม่มีรายการพื้นที่ที่ควรตรวจสอบเพิ่มเติมใน filter นี้")
        return
    display_df = top_df.rename(
        columns={
            "district": "อำเภอ",
            "subdistrict": "ตำบล",
            "unit_index": "หน่วย",
            "issue_label": "เหตุผลที่ควรตรวจต่อ",
            "integrity_score": "Integrity",
            "invalid_ratio": "Invalid",
            "no_vote_ratio": "No vote",
            "valid_ratio": "Valid",
            "vote_mismatch": "Mismatch",
            "review_score": "Review score",
        }
    )
    st.dataframe(
        display_df.style.format(
            {
                "Integrity": "{:.2f}",
                "Invalid": "{:.2%}",
                "No vote": "{:.2%}",
                "Valid": "{:.2%}",
                "Mismatch": "{:,.0f}",
                "Review score": "{:.2f}",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )


def _render_cluster_summary(summary_df: pd.DataFrame) -> None:
    if summary_df.empty:
        st.info("ยังไม่มีไฟล์ cluster summary ใน data/")
        return
    working = summary_df.copy()
    working["cluster_id"] = working["cluster_id"].astype(str)
    if "dataset" in working.columns and working["dataset"].nunique() > 1:
        working["cluster_label"] = working["dataset"].astype(str) + " / C" + working["cluster_id"]
    else:
        working["cluster_label"] = "C" + working["cluster_id"]

    top_clusters = working.sort_values(["issue_rate", "unit_count"], ascending=[False, False]).head(3)
    if not top_clusters.empty:
        cards = st.columns(len(top_clusters))
        for card, (_, row) in zip(cards, top_clusters.iterrows()):
            with card:
                _metric_card(
                    f"Cluster {row['cluster_label']}",
                    _format_percent(row.get("issue_rate")),
                    f"{_format_number(row.get('issue_count'))}/{_format_number(row.get('unit_count'))} units ควรตรวจต่อ",
                )

    fig = px.bar(
        working.sort_values("issue_rate", ascending=False),
        x="cluster_label",
        y="issue_rate",
        color="unit_count",
        color_continuous_scale="YlOrBr",
        hover_data={
            "unit_count": ":,",
            "issue_count": ":,",
            "issue_rate": ":.2%",
            "integrity_score_mean": ":.2f" if "integrity_score_mean" in working.columns else False,
        },
        title="Cluster ที่มีสัดส่วนพื้นที่ควรตรวจต่อสูง",
        height=360,
    )
    fig.update_layout(
        xaxis_title="Mixed KMeans anomaly cluster",
        yaxis_title="Issue rate",
        coloraxis_colorbar=dict(title="จำนวนหน่วย"),
        margin=dict(l=0, r=0, t=48, b=0),
        font=dict(family=FONT_FAMILY),
    )
    fig.update_yaxes(tickformat=".0%")
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    table_cols = [
        column
        for column in [
            "dataset",
            "cluster_label",
            "cluster_id",
            "unit_count",
            "issue_count",
            "issue_rate",
            "invalid_ratio_mean",
            "no_vote_ratio_mean",
            "turnout_mean",
            "integrity_score_mean",
            "subdistricts",
        ]
        if column in working.columns
    ]
    st.dataframe(
        working[table_cols].style.format(
            {
                "issue_rate": "{:.2%}",
                "invalid_ratio_mean": "{:.2%}",
                "no_vote_ratio_mean": "{:.2%}",
                "turnout_mean": "{:.2%}",
                "integrity_score_mean": "{:.2f}",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )


def _cluster_label_series(df: pd.DataFrame) -> pd.Series:
    if "mixed_kmeans_cluster" not in df.columns:
        return pd.Series("ไม่พบ cluster", index=df.index)
    cluster = "C" + df["mixed_kmeans_cluster"].astype(str)
    if "dataset" in df.columns and df["dataset"].nunique() > 1:
        return df["dataset"].astype(str) + " / " + cluster
    return cluster


def _semantic_cluster_label_map(df: pd.DataFrame, issue_col: str) -> dict[tuple[str, str], str]:
    if df.empty or "mixed_kmeans_cluster" not in df.columns:
        return {}

    working = df.copy()
    if "dataset" not in working.columns:
        working["dataset"] = "combined"
    working[issue_col] = working[issue_col].astype(bool)
    group_cols = ["dataset", "mixed_kmeans_cluster"]
    stats = (
        working.groupby(group_cols, dropna=False)
        .agg(
            issue_rate=(issue_col, "mean"),
            unit_count=("unit_index", "count"),
            invalid_ratio=("invalid_ratio", "mean"),
            no_vote_ratio=("no_vote_ratio", "mean"),
        )
        .reset_index()
    )

    names = [
        "กลุ่มควรตรวจสูง",
        "กลุ่มรูปแบบต่างเด่น",
        "กลุ่มเฝ้าระวัง",
        "กลุ่มฐานเปรียบเทียบ",
        "กลุ่มย่อยเพิ่มเติม",
    ]
    label_map: dict[tuple[str, str], str] = {}
    for dataset, group in stats.groupby("dataset", dropna=False):
        ranked = group.sort_values(
            ["issue_rate", "invalid_ratio", "no_vote_ratio", "unit_count"],
            ascending=[False, False, False, False],
        ).reset_index(drop=True)
        for rank, row in ranked.iterrows():
            label = names[rank] if rank < len(names) else f"กลุ่มย่อย {rank + 1}"
            key = (str(dataset), str(row["mixed_kmeans_cluster"]))
            label_map[key] = f"{_dataset_display(dataset)} · {label}"
    return label_map


def _cluster_palette(labels: Iterable[str]) -> dict[str, str]:
    palette = [
        APP_COLORS["signal_negative"],
        APP_COLORS["signal_orange"],
        APP_COLORS["signal_positive"],
        APP_COLORS["accent"],
        APP_COLORS["accent_dark"],
        APP_COLORS["brown-bark"],
        APP_COLORS["signal_warning"],
    ]
    ordered = list(dict.fromkeys(labels))
    return {label: _plotly_color(palette[index % len(palette)]) for index, label in enumerate(ordered)}


def _semantic_summary_cluster_labels(summary_df: pd.DataFrame) -> pd.Series:
    if summary_df.empty or "cluster_id" not in summary_df.columns:
        return pd.Series("กลุ่มคลัสเตอร์", index=summary_df.index)

    names = [
        "กลุ่มควรตรวจสูง",
        "กลุ่มรูปแบบต่างเด่น",
        "กลุ่มเฝ้าระวัง",
        "กลุ่มฐานเปรียบเทียบ",
        "กลุ่มย่อยเพิ่มเติม",
    ]
    working = summary_df.copy()
    if "dataset" not in working.columns:
        working["dataset"] = "combined"
    labels = pd.Series(index=working.index, dtype="object")
    for dataset, group in working.groupby("dataset", dropna=False):
        ranked = group.sort_values(
            ["issue_rate", "unit_count"],
            ascending=[False, False],
        )
        for rank, index in enumerate(ranked.index):
            label = names[rank] if rank < len(names) else f"กลุ่มย่อย {rank + 1}"
            labels.loc[index] = f"{_dataset_display(dataset)} · {label}"
    return labels.fillna("กลุ่มคลัสเตอร์")


def _render_anomaly_cluster_map(spatial_df: pd.DataFrame, review_only: bool = False) -> None:
    map_df = _valid_coordinate_rows(_election_day(spatial_df))
    if map_df.empty:
        st.info("ยังไม่มีข้อมูลพิกัดสำหรับ anomaly clustering map")
        return
    if "mixed_kmeans_cluster" not in map_df.columns:
        st.info("ยังไม่มีคอลัมน์ mixed_kmeans_cluster ในไฟล์ spatial clusters")
        return

    map_df = _with_ballot_features(map_df)
    issue_col = (
        "is_integrity_or_anomaly_issue"
        if "is_integrity_or_anomaly_issue" in map_df.columns
        else "is_review_unit"
    )
    map_df[issue_col] = map_df[issue_col].astype(bool)
    label_map = _semantic_cluster_label_map(map_df, issue_col)
    if review_only:
        map_df = map_df[map_df[issue_col]].copy()
        if map_df.empty:
            st.info("ไม่มีจุดที่ควรตรวจสอบเพิ่มเติมในพื้นที่นี้")
            return

    if "dataset" not in map_df.columns:
        map_df["dataset"] = "combined"
    map_df["cluster_label"] = map_df.apply(
        lambda row: label_map.get(
            (str(row.get("dataset", "combined")), str(row.get("mixed_kmeans_cluster"))),
            f"{_dataset_display(row.get('dataset', 'combined'))} · กลุ่มคลัสเตอร์",
        ),
        axis=1,
    )
    cluster_order = list(dict.fromkeys(label_map.values()))
    color_map = _cluster_palette(cluster_order)
    map_df["review_status"] = map_df[issue_col].map(
        {True: "พื้นที่ที่ควรตรวจสอบเพิ่มเติม", False: "ไม่พบประเด็นจาก rule/model"}
    )
    map_df["point_size"] = map_df[issue_col].map({True: 18, False: 7})
    map_df["display_unit"] = map_df["unit_index"].map(lambda value: f"หน่วย {value}")

    fig = px.scatter_mapbox(
        map_df,
        lat="latitude",
        lon="longitude",
        color="cluster_label",
        size="point_size",
        hover_name="display_unit",
        color_discrete_map=color_map,
        category_orders={"cluster_label": cluster_order},
        hover_data={
            "dataset": True if "dataset" in map_df.columns else False,
            "district": True,
            "subdistrict": True,
            "review_status": True,
            "anomaly_type": True if "anomaly_type" in map_df.columns else False,
            "invalid_ratio": ":.2%",
            "no_vote_ratio": ":.2%",
            "valid_ratio": ":.2%",
            "integrity_score": ":.2f",
            "latitude": False,
            "longitude": False,
            "point_size": False,
        },
        zoom=8.6,
        height=590,
    )
    fig.update_layout(
        mapbox_style="carto-positron",
        legend_title_text="กลุ่มคลัสเตอร์",
        margin=dict(l=0, r=0, t=48, b=0),
        font=dict(family=FONT_FAMILY),
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def _render_anomaly_heatmap(spatial_df: pd.DataFrame) -> None:
    heat_df = _valid_coordinate_rows(_election_day(spatial_df))
    if heat_df.empty:
        st.info("ยังไม่มีพิกัดสำหรับทำ heatmap ความกระจุกของ anomaly")
        return

    heat_df = _with_ballot_features(heat_df)
    issue_col = (
        "is_integrity_or_anomaly_issue"
        if "is_integrity_or_anomaly_issue" in heat_df.columns
        else "is_review_unit"
    )
    heat_df[issue_col] = heat_df[issue_col].astype(bool)
    heat_df = heat_df[heat_df[issue_col]].copy()
    if heat_df.empty:
        st.info("ยังไม่มีจุดที่ควรตรวจสอบเพิ่มเติมสำหรับทำ heatmap ในตัวกรองนี้")
        return

    heat_df["density_weight"] = 1
    hover_df = _add_simple_issue_group(heat_df)
    hover_df["dataset_label"] = hover_df.get("dataset", pd.Series("combined", index=hover_df.index)).map(
        {"constituency": "ส.ส.เขต", "partylist": "บัญชีรายชื่อ"}
    ).fillna(hover_df.get("dataset", ""))
    hover_df["unit_display"] = hover_df.get("unit_index", pd.Series("-", index=hover_df.index)).map(
        lambda value: f"หน่วย {value}"
    )
    for column, default in {
        "district": "-",
        "subdistrict": "-",
        "issue_group": "-",
        "invalid_ratio": 0,
        "no_vote_ratio": 0,
        "turnout": 0,
    }.items():
        if column not in hover_df.columns:
            hover_df[column] = default
    fig = px.density_mapbox(
        heat_df,
        lat="latitude",
        lon="longitude",
        z="density_weight",
        radius=28,
        center={"lat": float(heat_df["latitude"].mean()), "lon": float(heat_df["longitude"].mean())},
        zoom=8.6,
        height=520,
        color_continuous_scale=[
            _plotly_color(APP_COLORS["accent_soft"]),
            _plotly_color(APP_COLORS["signal_warning"]),
            _plotly_color(APP_COLORS["signal_orange"]),
            _plotly_color(APP_COLORS["signal_negative"]),
        ],
    )
    fig.add_trace(
        go.Scattermapbox(
            lat=hover_df["latitude"],
            lon=hover_df["longitude"],
            mode="markers",
            marker=dict(size=18, color="rgba(64,64,65,0.06)"),
            customdata=hover_df[
                [
                    "dataset_label",
                    "district",
                    "subdistrict",
                    "unit_display",
                    "issue_group",
                    "invalid_ratio",
                    "no_vote_ratio",
                    "turnout",
                ]
            ],
            hovertemplate=(
                "<b>%{customdata[1]} / %{customdata[2]}</b><br>"
                "%{customdata[0]} · %{customdata[3]}<br>"
                "%{customdata[4]}<br>"
                "บัตรเสีย %{customdata[5]:.2%} · No vote %{customdata[6]:.2%}<br>"
                "Turnout %{customdata[7]:.2%}<extra></extra>"
            ),
            showlegend=False,
        )
    )
    fig.update_layout(
        mapbox_style="carto-positron",
        coloraxis_colorbar=dict(title="ความหนาแน่น"),
        margin=dict(l=0, r=0, t=48, b=0),
        font=dict(family=FONT_FAMILY),
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def _semantic_issue_cluster_labels(issues_df: pd.DataFrame, spatial_df: pd.DataFrame | None) -> pd.Series:
    if issues_df.empty or "mixed_kmeans_cluster" not in issues_df.columns:
        return pd.Series("ไม่พบ cluster", index=issues_df.index)

    label_map: dict[tuple[str, str], str] = {}
    if spatial_df is not None and not spatial_df.empty:
        spatial_working = _valid_coordinate_rows(_election_day(spatial_df))
        if not spatial_working.empty and "mixed_kmeans_cluster" in spatial_working.columns:
            spatial_working = _with_ballot_features(spatial_working)
            spatial_issue_col = (
                "is_integrity_or_anomaly_issue"
                if "is_integrity_or_anomaly_issue" in spatial_working.columns
                else "is_review_unit"
            )
            spatial_working[spatial_issue_col] = spatial_working[spatial_issue_col].astype(bool)
            label_map = _semantic_cluster_label_map(spatial_working, spatial_issue_col)

    working = issues_df.copy()
    if "dataset" not in working.columns:
        working["dataset"] = "combined"
    if not label_map:
        fallback = _with_ballot_features(working)
        fallback_issue_col = "is_integrity_or_anomaly_issue" if "is_integrity_or_anomaly_issue" in fallback.columns else "is_review_unit"
        fallback[fallback_issue_col] = fallback[fallback_issue_col].astype(bool)
        label_map = _semantic_cluster_label_map(fallback, fallback_issue_col)

    return working.apply(
        lambda row: label_map.get(
            (str(row.get("dataset", "combined")), str(row.get("mixed_kmeans_cluster"))),
            f"{_dataset_display(row.get('dataset', 'combined'))} - cluster C{row.get('mixed_kmeans_cluster')}",
        ),
        axis=1,
    )


def _issue_card_color(row: pd.Series) -> str:
    anomaly_type = str(row.get("anomaly_type", "") or "")
    mismatch = _as_float(row.get("vote_mismatch", 0))
    if anomaly_type == "INCOMPLETE_DOCUMENT":
        return APP_COLORS["signal_orange"]
    if anomaly_type == "SCORE_BALLOT_MISMATCH" or (np.isfinite(mismatch) and mismatch != 0):
        return APP_COLORS["signal_negative"]
    if anomaly_type == "UNUSUAL_VOTING_PATTERN":
        return APP_COLORS["accent"]
    if anomaly_type == "HIGH_INVALID":
        return APP_COLORS["signal_warning"]
    return APP_COLORS["accent_dark"]


def _render_cluster_issue_selector(issues_df: pd.DataFrame, spatial_df: pd.DataFrame | None = None) -> None:
    if issues_df.empty:
        st.info("ไม่มี issue rows ที่ถูกจัดเข้า anomaly cluster ใน filter นี้")
        return

    working = _add_simple_issue_group(issues_df)
    if "dataset" not in working.columns:
        working["dataset"] = "combined"
    working["dataset_label"] = working["dataset"].map(
        {"constituency": "ส.ส.เขต", "partylist": "บัญชีรายชื่อ"}
    ).fillna(working["dataset"])
    working["cluster_label"] = _semantic_issue_cluster_labels(working, spatial_df)
    working["review_score"] = _review_score(working)

    anomaly_type = working.get("anomaly_type", pd.Series("", index=working.index)).fillna("").astype(str)
    mismatch = _safe_numeric(working.get("vote_mismatch", pd.Series(0, index=working.index))).ne(0)
    working["issue_order"] = 9
    working.loc[anomaly_type.eq("INCOMPLETE_DOCUMENT"), "issue_order"] = 0
    working.loc[anomaly_type.eq("SCORE_BALLOT_MISMATCH") | (mismatch & ~anomaly_type.eq("INCOMPLETE_DOCUMENT")), "issue_order"] = 1
    working.loc[anomaly_type.eq("UNUSUAL_VOTING_PATTERN"), "issue_order"] = 2
    working.loc[anomaly_type.eq("HIGH_INVALID"), "issue_order"] = 3
    working["display_unit"] = working.apply(_unit_label, axis=1)
    working["evidence"] = working.apply(_issue_evidence_text, axis=1)
    working["next_action"] = working.apply(_next_review_action, axis=1)
    working["issue_color"] = working.apply(_issue_card_color, axis=1)

    cluster_counts = (
        working.groupby("cluster_label", dropna=False)
        .agg(
            units=("unit_index", "count"),
            issue_order=("issue_order", "min"),
            review_score=("review_score", "max"),
        )
        .reset_index()
        .sort_values(["issue_order", "units", "review_score"], ascending=[True, False, False])
    )
    options = cluster_counts["cluster_label"].tolist()
    count_lookup = dict(zip(cluster_counts["cluster_label"], cluster_counts["units"]))
    selected_cluster = st.selectbox(
        "เลือก cluster ที่อยากดูรายการหน่วย",
        options,
        format_func=lambda label: f"{label} ({int(count_lookup.get(label, 0)):,} หน่วย)",
        key="ballot_behavior_cluster_select",
    )
    display_df = (
        working[working["cluster_label"].eq(selected_cluster)]
        .sort_values(["issue_order", "review_score"], ascending=[True, False])
        .copy()
    )
    st.caption(f"แสดง {len(display_df):,} หน่วยใน {selected_cluster}")

    rows = list(display_df.iterrows())
    for start in range(0, len(rows), 2):
        cols = st.columns(2)
        for col, (_, row) in zip(cols, rows[start : start + 2]):
            with col:
                color = row.get("issue_color", APP_COLORS["accent"])
                st.markdown(
                    f"""
                    <div style="background:var(--color-surface);border:1px solid var(--color-border);
                    border-left:5px solid {color};border-radius:8px;padding:13px 15px;
                    margin-bottom:10px;min-height:154px;">
                        <div style="font-size:11px;font-weight:900;color:var(--color-text-muted);
                        line-height:1.3;">
                            {row.get('cluster_label', '-')}
                        </div>
                        <div style="font-size:16px;font-weight:950;color:var(--color-text);margin-top:5px;
                        line-height:1.35;">
                            {row.get('display_unit', '-')}
                        </div>
                        <div style="display:inline-block;background:color-mix(in srgb, {color} 14%, white);
                        color:{color};border-radius:999px;padding:4px 9px;font-size:12px;font-weight:950;
                        margin-top:8px;line-height:1.2;">
                            {row.get('issue_group', '-')}
                        </div>
                        <div style="font-size:13px;color:var(--color-text);line-height:1.4;margin-top:8px;">
                            {row.get('evidence', '-')}
                        </div>
                        <div style="font-size:12px;color:var(--color-text-muted);line-height:1.35;margin-top:6px;">
                            ตรวจต่อ: {row.get('next_action', '-')}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


def _render_cluster_issue_list(issues_df: pd.DataFrame, spatial_df: pd.DataFrame | None = None) -> None:
    _render_cluster_issue_selector(issues_df, spatial_df)


def _as_float(value: object) -> float:
    number = pd.to_numeric(value, errors="coerce")
    if pd.isna(number):
        return float("nan")
    return float(number)


def _unit_label(row: pd.Series) -> str:
    district = str(row.get("district", "") or "-")
    subdistrict = str(row.get("subdistrict", "") or "-")
    unit = str(row.get("unit_index", "") or "-")
    return f"{district} / {subdistrict} / หน่วย {unit}"


def _issue_evidence_text(row: pd.Series) -> str:
    anomaly_type = str(row.get("anomaly_type", "") or "")
    mismatch = _as_float(row.get("vote_mismatch", 0))
    ballot_valid = _as_float(row.get("ballot_valid", float("nan")))
    vote_sum = _as_float(row.get("vote_sum", float("nan")))

    if anomaly_type == "INCOMPLETE_DOCUMENT":
        return "ภาพสแกน/เอกสารไม่ชัด ควรเปิดต้นฉบับก่อนสรุป"

    if anomaly_type == "SCORE_BALLOT_MISMATCH" or (np.isfinite(mismatch) and mismatch != 0):
        if np.isfinite(ballot_valid) and np.isfinite(vote_sum):
            return f"บัตรดี {_format_number(ballot_valid)} / คะแนนรวม {_format_number(vote_sum)} ต่าง {mismatch:+.0f}"
        return f"คะแนนรวมต่างจากบัตรดี {mismatch:+.0f}"

    if anomaly_type == "UNUSUAL_VOTING_PATTERN":
        return (
            f"บัตรเสีย {_format_percent(row.get('invalid_ratio'))} / "
            f"No vote {_format_percent(row.get('no_vote_ratio'))} / "
            f"Turnout {_format_percent(row.get('turnout'))}"
        )

    if anomaly_type == "HIGH_INVALID":
        return f"สัดส่วนบัตรเสีย {_format_percent(row.get('invalid_ratio'))}"

    return (
        f"Integrity {_format_number(row.get('integrity_score'))} / "
        f"บัตรเสีย {_format_percent(row.get('invalid_ratio'))} / "
        f"No vote {_format_percent(row.get('no_vote_ratio'))}"
    )


def _next_review_action(row: pd.Series) -> str:
    anomaly_type = str(row.get("anomaly_type", "") or "")
    mismatch = _as_float(row.get("vote_mismatch", 0))
    if anomaly_type == "INCOMPLETE_DOCUMENT":
        return "เปิดเอกสารต้นฉบับ"
    if anomaly_type == "SCORE_BALLOT_MISMATCH" or (np.isfinite(mismatch) and mismatch != 0):
        return "เช็กผลรวมคะแนน"
    if anomaly_type == "UNUSUAL_VOTING_PATTERN":
        return "เทียบหน่วยใกล้เคียง"
    if anomaly_type == "HIGH_INVALID":
        return "ตรวจเหตุผลบัตรเสีย"
    return "ตรวจรายละเอียดหน่วย"


def _add_simple_issue_group(df: pd.DataFrame) -> pd.DataFrame:
    working = _with_ballot_features(df.copy())
    anomaly_type = working.get("anomaly_type", pd.Series("NORMAL", index=working.index)).fillna("NORMAL").astype(str)
    mismatch = _safe_numeric(working.get("vote_mismatch", pd.Series(0, index=working.index))).ne(0)

    issue_group = working.get("issue_label", pd.Series("ควรตรวจสอบเพิ่มเติม", index=working.index)).astype(str)
    issue_group.loc[anomaly_type.eq("UNUSUAL_VOTING_PATTERN")] = "ลักษณะการลงคะแนนผิดปกติ"
    issue_group.loc[anomaly_type.eq("HIGH_INVALID")] = "บัตรเสียสูง"
    issue_group.loc[anomaly_type.eq("SCORE_BALLOT_MISMATCH") | (mismatch & ~anomaly_type.eq("INCOMPLETE_DOCUMENT"))] = (
        "ผลรวมคะแนนไม่เท่าบัตรดี"
    )
    issue_group.loc[anomaly_type.eq("INCOMPLETE_DOCUMENT")] = "เอกสารผิดพลาด"
    working["issue_group"] = issue_group
    return working


def _render_simple_issue_overview(
    clean_df: pd.DataFrame,
    spatial_df: pd.DataFrame,
    issues_df: pd.DataFrame,
    cluster_summary_df: pd.DataFrame,
) -> None:
    issues = _add_simple_issue_group(issues_df)
    election_df = _election_day(clean_df)
    spatial_points = len(_valid_coordinate_rows(_election_day(spatial_df)))
    cluster_count = len(cluster_summary_df) if not cluster_summary_df.empty else 0
    if "dataset" in cluster_summary_df.columns and "cluster_id" in cluster_summary_df.columns:
        cluster_count = cluster_summary_df[["dataset", "cluster_id"]].drop_duplicates().shape[0]

    anomaly_type = issues.get("anomaly_type", pd.Series(index=issues.index, dtype=object)).fillna("").astype(str)
    doc_count = int(anomaly_type.eq("INCOMPLETE_DOCUMENT").sum())
    mismatch_count = int(
        (
            anomaly_type.eq("SCORE_BALLOT_MISMATCH")
            | (_safe_numeric(issues.get("vote_mismatch", pd.Series(0, index=issues.index))).ne(0) & ~anomaly_type.eq("INCOMPLETE_DOCUMENT"))
        ).sum()
    )
    model_count = int(anomaly_type.eq("UNUSUAL_VOTING_PATTERN").sum())
    constituency_issue_count = int(
        issues.get("dataset", pd.Series(index=issues.index, dtype=object)).astype(str).eq("constituency").sum()
    )
    partylist_issue_count = int(
        issues.get("dataset", pd.Series(index=issues.index, dtype=object)).astype(str).eq("partylist").sum()
    )
    dataset_values = set(issues.get("dataset", pd.Series(index=issues.index, dtype=object)).dropna().astype(str))
    if dataset_values == {"constituency"}:
        issue_caption = f"เฉพาะ ส.ส.เขต<br>{constituency_issue_count:,} หน่วยที่ควรตรวจสอบ"
    elif dataset_values == {"partylist"}:
        issue_caption = f"เฉพาะบัญชีรายชื่อ<br>{partylist_issue_count:,} หน่วยที่ควรตรวจสอบ"
    else:
        issue_caption = (
            f"รวม ส.ส.เขต + ปาร์ตี้ลิสต์<br>"
            f"เขต {constituency_issue_count:,} / ปาร์ตี้ลิสต์ {partylist_issue_count:,}"
        )

    cols = st.columns([1.38, 1, 1, 1, 1])
    with cols[0]:
        _colored_metric_card(
            "จำนวนหน่วยเลือกตั้ง<br>ที่มีความผิดปกติ",
            f"{len(issues):,}",
            issue_caption,
            "--color-signal-negative",
        )
    with cols[1]:
        _colored_metric_card(
            "เอกสารผิดพลาด",
            f"{doc_count:,}",
            "",
            "color-mix(in srgb, var(--color-signal-negative) 78%, white)",
        )
    with cols[2]:
        _colored_metric_card(
            "ผลรวมคะแนนไม่เท่าบัตรดี",
            f"{mismatch_count:,}",
            "",
            "color-mix(in srgb, var(--color-signal-negative) 70%, white)",
        )
    with cols[3]:
        _colored_metric_card(
            "ลักษณะการลงคะแนนผิดปกติ",
            f"{model_count:,}",
            "",
            "color-mix(in srgb, var(--color-signal-negative) 62%, white)",
        )
    with cols[4]:
        _colored_metric_card(
            "Clusters",
            f"{cluster_count:,}",
            "",
            "--color-sidebar-bg",
        )


def _render_simple_issue_breakdown(issues_df: pd.DataFrame) -> None:
    if issues_df.empty:
        st.info("ไม่มีรายการที่ควรตรวจสอบเพิ่มเติม")
        return
    working = _add_simple_issue_group(issues_df)
    counts = (
        working["issue_group"]
        .value_counts()
        .rename_axis("issue_group")
        .reset_index(name="units")
        .sort_values("units", ascending=True)
    )
    issue_color_map = {
        "เอกสารผิดพลาด": _plotly_color(APP_COLORS["signal_negative"]),
        "ผลรวมคะแนนไม่เท่าบัตรดี": _plotly_color(APP_COLORS["signal_orange"]),
        "ลักษณะการลงคะแนนผิดปกติ": _plotly_color(APP_COLORS["brown-bark"]),
        "บัตรเสียสูง": _plotly_color(APP_COLORS["signal_warning"]),
    }
    fig = px.bar(
        counts,
        x="units",
        y="issue_group",
        orientation="h",
        color="issue_group",
        color_discrete_map=issue_color_map,
        text="units",
        height=max(240, 46 * len(counts) + 72),
    )
    fig.update_traces(marker_line_width=0, textposition="outside", cliponaxis=False, width=0.56)
    fig.update_layout(
        showlegend=False,
        xaxis_title="จำนวนหน่วย",
        yaxis_title="",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        bargap=0.42,
        margin=dict(l=0, r=8, t=10, b=8),
        font=dict(family=FONT_FAMILY),
    )
    fig.update_xaxes(showgrid=True, gridcolor="rgba(64,64,65,.12)", zeroline=False)
    fig.update_yaxes(showgrid=False, ticks="", automargin=True)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def _cluster_summary_for_view(spatial_df: pd.DataFrame) -> pd.DataFrame:
    working = _valid_coordinate_rows(_election_day(spatial_df))
    if working.empty or "mixed_kmeans_cluster" not in working.columns:
        return pd.DataFrame()
    working = _with_ballot_features(working)
    issue_col = "is_integrity_or_anomaly_issue" if "is_integrity_or_anomaly_issue" in working.columns else "is_review_unit"
    working[issue_col] = working[issue_col].astype(bool)
    group_cols = ["mixed_kmeans_cluster"]
    if "dataset" in working.columns:
        group_cols = ["dataset", "mixed_kmeans_cluster"]
    grouped = (
        working.groupby(group_cols, dropna=False)
        .agg(
            unit_count=("unit_index", "count"),
            issue_count=(issue_col, "sum"),
            invalid_ratio_mean=("invalid_ratio", "mean"),
            no_vote_ratio_mean=("no_vote_ratio", "mean"),
            integrity_score_mean=("integrity_score", "mean"),
        )
        .reset_index()
    )
    grouped["cluster_id"] = grouped["mixed_kmeans_cluster"]
    grouped["issue_rate"] = _safe_ratio(grouped["issue_count"], grouped["unit_count"])
    return grouped.sort_values(["issue_rate", "unit_count"], ascending=[False, False])


def _render_simple_cluster_summary(summary_df: pd.DataFrame) -> None:
    if summary_df.empty:
        st.info("ยังไม่มีข้อมูล cluster summary สำหรับพื้นที่นี้")
        return
    working = summary_df.copy()
    working["cluster_id"] = working["cluster_id"].astype(str)
    working["cluster_label"] = _semantic_summary_cluster_labels(working)
    color_map = _cluster_palette(working["cluster_label"])

    top_clusters = working.sort_values(["issue_rate", "unit_count"], ascending=[False, False]).head(3)
    cards = st.columns(len(top_clusters))
    for card, (_, row) in zip(cards, top_clusters.iterrows()):
        with card:
            _cluster_metric_card(
                row["cluster_label"],
                _format_percent(row.get("issue_rate")),
                f"{_format_number(row.get('issue_count'))}/{_format_number(row.get('unit_count'))} จุดตรวจ",
                color_map.get(row["cluster_label"], APP_COLORS["accent"]),
            )

    plot_df = working.sort_values("issue_rate", ascending=False).head(8).sort_values("issue_rate", ascending=True).copy()
    plot_df["issue_rate_label"] = plot_df["issue_rate"].map(_format_percent)
    fig = px.bar(
        plot_df,
        x="issue_rate",
        y="cluster_label",
        orientation="h",
        color="cluster_label",
        color_discrete_map=color_map,
        text="issue_rate_label",
        height=max(260, 42 * len(plot_df) + 78),
    )
    fig.update_traces(marker_line_width=0, textposition="outside", cliponaxis=False, width=0.55)
    fig.update_layout(
        showlegend=False,
        xaxis_title="สัดส่วนจุดตรวจ",
        yaxis_title="",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        bargap=0.4,
        margin=dict(l=0, r=34, t=12, b=8),
        font=dict(family=FONT_FAMILY),
    )
    range_max = min(1.35, max(0.12, float(plot_df["issue_rate"].max()) * 1.28))
    fig.update_xaxes(tickformat=".0%", showgrid=True, gridcolor="rgba(64,64,65,.12)", zeroline=False, range=[0, range_max])
    fig.update_yaxes(showgrid=False, ticks="", automargin=True)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def _dataset_display(value: object) -> str:
    return {
        "constituency": "ส.ส.เขต",
        "partylist": "บัญชีรายชื่อ",
        "cross_form": "เทียบสองบัตร",
    }.get(str(value), str(value))


def _candidate_party_lookup() -> dict[str, str]:
    mapping = _load_csv("candidate_party_mapping.csv")
    if mapping.empty or not {"candidate_display_name", "party_name"}.issubset(mapping.columns):
        return {}
    names = mapping["candidate_display_name"].fillna("").astype(str).str.strip()
    parties = mapping["party_name"].fillna("").astype(str).str.strip()
    return dict(zip(names, parties))


def _vote_name_with_party(dataset: str, name: object, party_lookup: dict[str, str]) -> str:
    display_name = str(name or "-").strip()
    if dataset != "constituency":
        return display_name
    party = party_lookup.get(display_name, "")
    return f"{display_name} ({party})" if party else display_name


def _format_pp_value(value: object) -> str:
    number = _as_float(value)
    if not np.isfinite(number):
        return "-"
    return f"{number:+.2f} pp"


def _render_special_voting_signal(panel_df: pd.DataFrame, top_shares_df: pd.DataFrame) -> None:
    if panel_df.empty:
        st.info("ยังไม่มีไฟล์ special_voting_panel.csv สำหรับสรุปเลือกตั้งล่วงหน้า")
        return

    out_df = panel_df[panel_df["segment"].astype(str).eq("out_of_district_advance_aggregated")].copy()
    if out_df.empty:
        st.info("ยังไม่มีข้อมูลเลือกตั้งล่วงหน้านอกเขตแบบรวม")
        return

    st.markdown("**การเลือกตั้งล่วงหน้านอกเขต**")

    party_lookup = _candidate_party_lookup()
    cols = st.columns(len(out_df))
    for col, (_, row) in zip(cols, out_df.iterrows()):
        dataset = str(row.get("dataset", ""))
        top_df = (
            top_shares_df[
                top_shares_df.get("dataset", pd.Series(dtype=object)).astype(str).eq(dataset)
                & top_shares_df.get("segment", pd.Series(dtype=object)).astype(str).eq("out_of_district_advance_aggregated")
            ]
            .copy()
            .head(3)
        )
        top_lines = []
        for _, top in top_df.iterrows():
            diff = _as_float(top.get("share_diff_vs_election_day"))
            diff_color = "--color-signal-positive" if np.isfinite(diff) and diff >= 0 else "--color-signal-negative"
            top_name = _vote_name_with_party(dataset, top.get("name", "-"), party_lookup)
            top_lines.append(
                f'<div style="display:flex;justify-content:space-between;gap:8px;line-height:1.45;">'
                f'<span>{int(_as_float(top.get("rank", 0)))}. {top_name}</span>'
                f'<span style="white-space:nowrap;color:var({diff_color});font-weight:900;">'
                f'{_format_percent(top.get("vote_share"))} ({_format_pp(top.get("share_diff_vs_election_day"))})'
                f'</span></div>'
            )
        top_text = "".join(top_lines) if top_lines else "-"
        status = str(row.get("special_voting_status", ""))
        is_unusual = status == "UNUSUAL_SPECIAL_VOTING_PATTERN"
        status_label = "ควรตรวจสอบเพิ่มเติม" if is_unusual else "ใช้เป็นบริบท"
        badge_color = "--color-signal-negative" if is_unusual else "--color-accent-dark"
        shift_name = _vote_name_with_party(dataset, row.get("largest_share_shift_name", "-"), party_lookup)

        with col:
            html = (
                f'<div style="background:var(--color-surface);border:1px solid var(--color-border);'
                f'border-left:6px solid var({badge_color});border-radius:8px;padding:16px;min-height:238px;">'
                f'<div style="display:flex;align-items:center;justify-content:space-between;gap:10px;">'
                f'<div style="font-size:14px;font-weight:950;color:var(--color-accent);">{_dataset_display(dataset)}</div>'
                f'<div style="background:var({badge_color});color:var(--color-text-inverse);border-radius:999px;'
                f'padding:4px 10px;font-size:12px;font-weight:900;">{status_label}</div></div>'
                f'<div style="display:flex;align-items:flex-end;gap:8px;margin-top:10px;">'
                f'<div style="font-size:34px;font-weight:950;color:var(--color-text);line-height:1;">{_format_number(row.get("ballot_total"))}</div>'
                f'<div style="font-size:12px;color:var(--color-text-muted);font-weight:800;">บัตร</div></div>'
                f'<div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:12px;">'
                f'<span style="background:color-mix(in srgb, var(--color-signal-negative) 14%, white);color:var(--color-signal-negative);'
                f'border-radius:999px;padding:5px 9px;font-size:12px;font-weight:900;">ต่างจากวันจริง {_format_percent(row.get("vote_share_tvd_vs_election_day"))}</span>'
                f'<span style="background:color-mix(in srgb, var(--color-signal-warning) 28%, white);color:var(--color-brown-bark);'
                f'border-radius:999px;padding:5px 9px;font-size:12px;font-weight:900;">No vote {_format_percent(row.get("no_vote_ratio"))}</span>'
                f'<span style="background:color-mix(in srgb, var(--color-signal-positive) 16%, white);color:var(--color-signal-positive);'
                f'border-radius:999px;padding:5px 9px;font-size:12px;font-weight:900;">Turnout {_format_percent(row.get("turnout"))}</span></div>'
                f'<div style="font-size:14px;line-height:1.45;color:var(--color-text);margin-top:12px;">'
                f'เพิ่มเด่น: <b style="color:var(--color-signal-orange);">{shift_name}</b> '
                f'<b style="color:var(--color-signal-orange);">{_format_pp_value(row.get("largest_share_shift_pp"))}</b></div>'
                f'<div style="height:1px;background:var(--color-border);margin:12px 0 10px;"></div>'
                f'<div style="font-size:12px;color:var(--color-text);font-weight:850;margin-bottom:4px;">Top 3</div>'
                f'<div style="font-size:12px;color:var(--color-text-muted);">{top_text}</div></div>'
            )
            st.markdown(html, unsafe_allow_html=True)


def _render_cross_form(cross_df: pd.DataFrame) -> None:
    if cross_df.empty:
        st.info("ยังไม่มีข้อมูล cross-form validation")
        return
    working = cross_df.copy()
    if "cross_mismatch" not in working.columns:
        st.info("ไฟล์ cross-form ไม่มีคอลัมน์ cross_mismatch")
        return
    working["cross_mismatch"] = _safe_numeric(working["cross_mismatch"])
    mismatch_df = working[working["cross_mismatch"] > 0].copy()
    col1, col2, col3 = st.columns(3)
    col1.metric("Cross-form mismatch rows", f"{len(mismatch_df):,}")
    col2.metric("Total mismatch", f"{working['cross_mismatch'].sum():,.0f}")
    col3.metric("Max mismatch", f"{working['cross_mismatch'].max():,.0f}")

    if mismatch_df.empty:
        st.caption("ไม่พบ mismatch ระหว่างบัตรรวม ส.ส.เขต และบัญชีรายชื่อใน filter นี้")
        return

    columns = [
        column
        for column in [
            "district",
            "subdistrict",
            "unit_index",
            "vote_phase",
            "ballot_total_const",
            "ballot_total_party",
            "cross_mismatch",
            "ballot_valid_cross_mismatch",
            "ballot_invalid_cross_mismatch",
            "ballot_no_vote_cross_mismatch",
        ]
        if column in mismatch_df.columns
    ]
    st.dataframe(
        mismatch_df.sort_values("cross_mismatch", ascending=False)[columns],
        use_container_width=True,
        hide_index=True,
    )


def _render_special_voting(panel_df: pd.DataFrame, selected_form: str) -> None:
    if panel_df.empty:
        st.info("ยังไม่มีไฟล์ special_voting_panel.csv ใน data/")
        return
    working = panel_df.copy()
    if selected_form != "combined" and "dataset" in working.columns:
        working = working[working["dataset"] == selected_form].copy()
    if working.empty:
        st.info("ไม่มีข้อมูล special voting ใน filter นี้")
        return

    fig = px.bar(
        working[working["segment"] != "election_day_baseline"],
        x="segment",
        y="vote_share_tvd_vs_election_day",
        color="special_voting_status",
        color_discrete_map={
            "UNUSUAL_SPECIAL_VOTING_PATTERN": APP_COLORS["signal_orange"],
            "LOW_SAMPLE_REFERENCE_ONLY": APP_COLORS["accent_hover"],
            "NORMAL_SPECIAL_VOTING_PATTERN": APP_COLORS["signal_positive"],
        },
        facet_col="dataset" if selected_form == "combined" and working["dataset"].nunique() > 1 else None,
        hover_data={
            "ballot_total": ":,",
            "turnout": ":.2%",
            "winner_name": True,
            "winner_ratio": ":.2%",
            "largest_share_shift_name": True,
            "largest_share_shift_pp": ":.2f",
        },
        title="Advance voting behavior เทียบกับ election-day baseline",
        height=390,
    )
    fig.update_layout(
        xaxis_title="Special voting segment",
        yaxis_title="Vote-share distance from election day",
        legend_title_text="Status",
        margin=dict(l=0, r=0, t=54, b=0),
        font=dict(family=FONT_FAMILY),
    )
    fig.update_yaxes(tickformat=".0%")
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    display_cols = [
        "dataset",
        "segment",
        "ballot_total",
        "turnout",
        "winner_name",
        "winner_ratio",
        "vote_share_tvd_vs_election_day",
        "largest_share_shift_name",
        "largest_share_shift_pp",
        "special_voting_status",
        "interpretation_note",
    ]
    display_cols = [column for column in display_cols if column in working.columns]
    st.dataframe(
        working[display_cols].style.format(
            {
                "ballot_total": "{:,.0f}",
                "turnout": "{:.2%}",
                "winner_ratio": "{:.2%}",
                "vote_share_tvd_vs_election_day": "{:.2%}",
                "largest_share_shift_pp": "{:+.2f}",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )


def _merge_forms(frames: Iterable[pd.DataFrame]) -> pd.DataFrame:
    output = []
    for frame in frames:
        if not frame.empty:
            output.append(frame)
    if not output:
        return pd.DataFrame()
    return pd.concat(output, ignore_index=True, sort=False)


def _load_form_data(form_key: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if form_key == "combined":
        clean_frames = []
        spatial_frames = []
        issue_frames = []
        summary_frames = []
        for key, config in FORM_FILES.items():
            clean = _with_ballot_features(_load_csv(config["clean"]))
            clean["dataset"] = key
            spatial = _with_ballot_features(_load_csv(config["spatial"]))
            spatial["dataset"] = key
            issues = _with_ballot_features(_load_csv(config["issues"]))
            issues["dataset"] = key
            summary = _load_csv(config["cluster_summary"])
            summary["dataset"] = key
            clean_frames.append(clean)
            spatial_frames.append(spatial)
            issue_frames.append(issues)
            summary_frames.append(summary)
        return (
            _merge_forms(clean_frames),
            _merge_forms(spatial_frames),
            _merge_forms(issue_frames),
            _merge_forms(summary_frames),
        )

    config = FORM_FILES[form_key]
    clean = _with_ballot_features(_load_csv(config["clean"]))
    clean["dataset"] = form_key
    spatial = _with_ballot_features(_load_csv(config["spatial"]))
    spatial["dataset"] = form_key
    issues = _with_ballot_features(_load_csv(config["issues"]))
    issues["dataset"] = form_key
    summary = _load_csv(config["cluster_summary"])
    summary["dataset"] = form_key
    return clean, spatial, issues, summary


def render(df: pd.DataFrame, selected_district: str | None = None):
    st.subheader("Ballot behavior signals")

    clean_df, spatial_df, issues_df, cluster_summary_df = _load_form_data("combined")
    district_filter = _infer_sidebar_district(df, selected_district)
    if district_filter not in ["All", * _district_options(clean_df, spatial_df)]:
        district_filter = "All"

    clean_df = _filter_district(clean_df, district_filter)
    spatial_df = _filter_district(spatial_df, district_filter)
    issues_df = _filter_district(issues_df, district_filter)
    special_panel_df = _load_csv("special_voting_panel.csv")
    special_top_df = _load_csv("special_voting_top_vote_shares.csv")

    if clean_df.empty:
        st.warning("ยังไม่มีข้อมูล ballot behavior ใน data/ กรุณาเพิ่มไฟล์ cleaned และ clustering ก่อน")
        return

    if district_filter != "All":
        st.caption(f"กำลังแสดงเฉพาะอำเภอ: {district_filter}")

    _render_special_voting_signal(special_panel_df, special_top_df)

    st.markdown("---")

    selected_form_scope = st.radio(
        "เลือกชุดข้อมูลที่ต้องการดู",
        ["combined", "constituency", "partylist"],
        format_func=lambda value: FORM_SCOPE_LABELS.get(value, value),
        horizontal=True,
        key="ballot_behavior_form_scope",
    )

    clean_df = _filter_dataset(clean_df, selected_form_scope)
    spatial_df = _filter_dataset(spatial_df, selected_form_scope)
    issues_df = _filter_dataset(issues_df, selected_form_scope)
    cluster_summary_df = _filter_dataset(cluster_summary_df, selected_form_scope)

    view_cluster_summary = _cluster_summary_for_view(spatial_df)
    if view_cluster_summary.empty:
        view_cluster_summary = cluster_summary_df

    _render_simple_issue_overview(clean_df, spatial_df, issues_df, view_cluster_summary)
    st.markdown("---")

    st.markdown("**จุดที่ควรตรวจสอบเพิ่มเติมตาม Anomaly cluster**")
    
    _render_anomaly_cluster_map(spatial_df, review_only=True)
    st.markdown("**ความกระจุกของ Anomaly**")
    _render_anomaly_heatmap(spatial_df)

    st.markdown("**รายการจุดที่ควรตรวจสอบเพิ่มเติม**")
    _render_cluster_issue_list(issues_df, spatial_df)
