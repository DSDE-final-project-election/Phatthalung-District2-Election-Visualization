import pandas as pd
import plotly.express as px
import streamlit as st


BASE_COLUMNS = {
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
}


def _score_columns(df: pd.DataFrame) -> list[str]:
    """Return candidate or party vote columns."""
    return [column for column in df.columns if column not in BASE_COLUMNS]


def _numeric_scores(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Return numeric score columns with missing values treated as zero."""
    return df[columns].apply(pd.to_numeric, errors="coerce").fillna(0)


def _entity_totals(df: pd.DataFrame, columns: list[str]) -> pd.Series:
    """Sum votes for each candidate or party."""
    if df.empty or not columns:
        return pd.Series(dtype="float64")
    return _numeric_scores(df, columns).sum().sort_values(ascending=False)


def _selected_score_columns(
    totals: pd.Series,
    result_type: str,
    party_display_mode: str,
) -> tuple[list[str], bool]:
    """Choose which score columns to draw and whether to add an other bucket."""
    nonzero_totals = totals[totals > 0]
    if result_type == "constituency":
        return list(nonzero_totals.index), False

    if party_display_mode == "Top 5":
        return list(totals.head(5).index), True
    if party_display_mode == "Top 10":
        return list(totals.head(10).index), True
    if party_display_mode == "ซ่อนพรรคคะแนน 0":
        return list(nonzero_totals.index), False
    return list(totals.index), False


def _area_label(df: pd.DataFrame) -> pd.Series:
    """Build a readable district/subdistrict label."""
    if df["district"].dropna().nunique() <= 1:
        return df["subdistrict"].fillna("ไม่ระบุ")
    return (
        df["district"].fillna("ไม่ระบุอำเภอ")
        + " / "
        + df["subdistrict"].fillna("ไม่ระบุตำบล")
    )


def _prepare_subdistrict_share(
    df: pd.DataFrame,
    all_columns: list[str],
    selected_columns: list[str],
    include_other: bool,
) -> pd.DataFrame:
    """Aggregate vote share by subdistrict for stacked bars and heatmaps."""
    if df.empty or not selected_columns:
        return pd.DataFrame()

    working = df.copy()
    working["area_label"] = _area_label(working)
    score_df = _numeric_scores(working, all_columns)
    score_df["area_label"] = working["area_label"].values
    grouped = score_df.groupby("area_label")[all_columns].sum()
    selected = grouped[selected_columns].copy()

    if include_other:
        other_columns = [column for column in all_columns if column not in selected_columns]
        selected["อื่น ๆ"] = grouped[other_columns].sum(axis=1) if other_columns else 0

    denominator = selected.sum(axis=1).replace(0, pd.NA)
    share = selected.div(denominator, axis=0).fillna(0)
    return share.reset_index()


def _subdistrict_ranking(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Rank the winning candidate or party in each subdistrict."""
    if df.empty or not columns:
        return pd.DataFrame()

    working = df.copy()
    working["area_label"] = _area_label(working)
    score_df = _numeric_scores(working, columns)
    score_df["area_label"] = working["area_label"].values
    score_df["ballot_valid"] = pd.to_numeric(
        working["ballot_valid"], errors="coerce"
    ).fillna(0)

    grouped_scores = score_df.groupby("area_label")[columns].sum()
    valid_totals = score_df.groupby("area_label")["ballot_valid"].sum()
    rows = []

    for area, scores in grouped_scores.iterrows():
        ordered = scores.sort_values(ascending=False)
        winner = ordered.index[0]
        runner_up = ordered.index[1] if len(ordered) > 1 else ""
        winner_votes = int(ordered.iloc[0])
        runner_up_votes = int(ordered.iloc[1]) if len(ordered) > 1 else 0
        valid_total = float(valid_totals.loc[area])
        winner_share = winner_votes / valid_total if valid_total else 0
        margin_votes = winner_votes - runner_up_votes
        margin_share = margin_votes / valid_total if valid_total else 0
        rows.append(
            {
                "พื้นที่": area,
                "อันดับ 1": winner,
                "คะแนนอันดับ 1": winner_votes,
                "สัดส่วนอันดับ 1": winner_share,
                "อันดับ 2": runner_up,
                "คะแนนอันดับ 2": runner_up_votes,
                "ส่วนต่างคะแนน": margin_votes,
                "ส่วนต่างสัดส่วน": margin_share,
            }
        )

    return pd.DataFrame(rows).sort_values(
        ["ส่วนต่างสัดส่วน", "คะแนนอันดับ 1"],
        ascending=[True, False],
    )


def _station_winners(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Build station-level winner data for the map."""
    if df.empty or not columns:
        return pd.DataFrame()

    station_df = df.dropna(subset=["latitude", "longitude"]).copy()
    if station_df.empty:
        return station_df

    scores = _numeric_scores(station_df, columns)
    station_df["winner"] = scores.idxmax(axis=1)
    station_df["winner_votes"] = scores.max(axis=1).astype(int)
    valid = pd.to_numeric(station_df["ballot_valid"], errors="coerce").fillna(0)
    station_df["winner_share"] = (station_df["winner_votes"] / valid.replace(0, pd.NA)).fillna(0)
    return station_df


def _format_percent_column(df: pd.DataFrame, column: str):
    """Style a table percentage column."""
    return df.style.format({column: "{:.2%}"})


def _render_insight_cards(
    df: pd.DataFrame,
    columns: list[str],
    entity_label: str,
) -> None:
    """Render compact insight metrics for the selected result type."""
    totals = _entity_totals(df, columns)
    ranking = _subdistrict_ranking(df, columns)
    if totals.empty:
        return

    winner = totals.index[0]
    winner_votes = int(totals.iloc[0])
    total_valid = pd.to_numeric(df["ballot_valid"], errors="coerce").fillna(0).sum()
    winner_share = winner_votes / total_valid if total_valid else 0

    strongest_text = "-"
    closest_text = "-"
    if not ranking.empty:
        winner_rows = ranking[ranking["อันดับ 1"] == winner].copy()
        if not winner_rows.empty:
            strongest = winner_rows.sort_values(
                "สัดส่วนอันดับ 1", ascending=False
            ).iloc[0]
            strongest_text = (
                f"{strongest['พื้นที่']} ({strongest['สัดส่วนอันดับ 1']:.1%})"
            )
        closest = ranking.iloc[0]
        closest_text = (
            f"{closest['พื้นที่']} ({closest['ส่วนต่างสัดส่วน']:.1%})"
        )

    col1, col2, col3 = st.columns(3)
    col1.metric(f"{entity_label}นำ", winner, f"{winner_votes:,.0f} votes")
    col2.metric("สัดส่วนคะแนนนำ", f"{winner_share:.2%}")
    col3.metric("พื้นที่สูสีที่สุด", closest_text)
    st.caption(f"ฐานเสียงเด่นของ {winner}: {strongest_text}")


def render(
    constituency_df: pd.DataFrame,
    partylist_df: pd.DataFrame,
) -> None:
    """Render constituency and party-list result analytics in one tab."""
    st.subheader("Election Results")

    result_label = st.radio(
        "ประเภทผล",
        ["ส.ส.เขต", "บัญชีรายชื่อ"],
        horizontal=True,
        key="result_type_toggle",
    )
    is_partylist = result_label == "บัญชีรายชื่อ"
    df = partylist_df.copy() if is_partylist else constituency_df.copy()
    result_type = "partylist" if is_partylist else "constituency"
    entity_label = "พรรค" if is_partylist else "ผู้สมัคร"

    if df.empty:
        st.warning("ไม่พบข้อมูลผลเลือกตั้งสำหรับหน้าผลลัพธ์")
        return

    score_cols = _score_columns(df)
    if not score_cols:
        st.warning("ไม่พบคอลัมน์คะแนนสำหรับทำกราฟ")
        return

    filters = st.columns([1.2, 2, 1.4])
    phase_options = sorted(df["vote_phase"].dropna().unique())
    default_phases = ["election_day"] if "election_day" in phase_options else phase_options
    selected_phases = filters[0].multiselect(
        "Vote phase",
        phase_options,
        default=default_phases,
        key=f"{result_type}_phase_filter",
    )
    if selected_phases:
        df = df[df["vote_phase"].isin(selected_phases)]

    subdistrict_options = sorted(df["subdistrict"].dropna().unique())
    selected_subdistricts = filters[1].multiselect(
        "ตำบล",
        subdistrict_options,
        default=[],
        placeholder="เลือกเฉพาะตำบลที่ต้องการ หรือปล่อยว่างเพื่อดูทั้งหมด",
        key=f"{result_type}_subdistrict_filter",
    )
    if selected_subdistricts:
        df = df[df["subdistrict"].isin(selected_subdistricts)]

    party_display_mode = "ทุกพรรค"
    if is_partylist:
        party_display_mode = filters[2].radio(
            "แสดงพรรค",
            ["Top 5", "Top 10", "ซ่อนพรรคคะแนน 0", "ทุกพรรค"],
            horizontal=False,
            key="party_display_mode",
        )
    else:
        filters[2].write("")
        filters[2].caption("ส.ส.เขตแสดงผู้สมัครทุกคนที่มีคะแนน")

    if df.empty:
        st.info("ไม่มีข้อมูลหลังจาก filter")
        return

    totals = _entity_totals(df, score_cols)
    selected_score_cols, include_other = _selected_score_columns(
        totals,
        result_type,
        party_display_mode,
    )
    if not selected_score_cols:
        st.info("ไม่มีคะแนนที่แสดงได้หลังจาก filter")
        return

    _render_insight_cards(df, score_cols, entity_label)

    total_votes_df = (
        totals.loc[selected_score_cols]
        .reset_index()
        .rename(columns={"index": entity_label, 0: "คะแนน"})
    )

    fig_total = px.bar(
        total_votes_df,
        x="คะแนน",
        y=entity_label,
        orientation="h",
        text="คะแนน",
        title=f"คะแนนรวม{entity_label}",
    )
    fig_total.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
    fig_total.update_layout(
        height=max(360, 26 * len(total_votes_df)),
        margin=dict(l=20, r=20, t=60, b=20),
        yaxis=dict(categoryorder="total ascending"),
        font=dict(family="Tahoma, Arial, sans-serif"),
    )
    st.plotly_chart(fig_total, use_container_width=True)

    share_df = _prepare_subdistrict_share(
        df,
        score_cols,
        selected_score_cols,
        include_other,
    )

    if not share_df.empty:
        share_long = share_df.melt(
            id_vars="area_label",
            var_name=entity_label,
            value_name="vote_share",
        )
        fig_stack = px.bar(
            share_long,
            x="area_label",
            y="vote_share",
            color=entity_label,
            title=f"สัดส่วนคะแนน {entity_label} แยกตามตำบล",
            labels={"area_label": "พื้นที่", "vote_share": "สัดส่วนคะแนน"},
        )
        fig_stack.update_layout(
            barmode="stack",
            yaxis_tickformat=".0%",
            height=520,
            margin=dict(l=20, r=20, t=60, b=120),
            xaxis_tickangle=-35,
            font=dict(family="Tahoma, Arial, sans-serif"),
        )
        st.plotly_chart(fig_stack, use_container_width=True)

    col_table, col_heatmap = st.columns([1.05, 1])

    with col_table:
        st.markdown("**Ranking รายตำบล**")
        ranking = _subdistrict_ranking(df, score_cols)
        if ranking.empty:
            st.info("ไม่มีข้อมูล ranking")
        else:
            st.dataframe(
                _format_percent_column(
                    ranking,
                    "สัดส่วนอันดับ 1",
                ),
                use_container_width=True,
                hide_index=True,
            )

    with col_heatmap:
        st.markdown("**Heatmap สัดส่วนคะแนน**")
        if share_df.empty:
            st.info("ไม่มีข้อมูล heatmap")
        else:
            heatmap = share_df.set_index("area_label")
            fig_heatmap = px.imshow(
                heatmap,
                aspect="auto",
                color_continuous_scale="Blues",
                labels=dict(x=entity_label, y="พื้นที่", color="Vote share"),
            )
            fig_heatmap.update_layout(
                height=max(360, 24 * len(heatmap)),
                margin=dict(l=10, r=10, t=20, b=80),
                xaxis_tickangle=-35,
                font=dict(family="Tahoma, Arial, sans-serif"),
            )
            st.plotly_chart(fig_heatmap, use_container_width=True)

    st.markdown("**Map / หน่วยเลือกตั้งที่ผู้ชนะรายหน่วย**")
    station_map_df = _station_winners(df, score_cols)
    if station_map_df.empty:
        st.info("ไม่มีพิกัดสำหรับแสดงแผนที่")
    else:
        fig_map = px.scatter_mapbox(
            station_map_df,
            lat="latitude",
            lon="longitude",
            color="winner",
            size="ballot_valid",
            hover_name="latlong_location",
            hover_data={
                "district": True,
                "subdistrict": True,
                "unit_index": True,
                "winner_votes": ":,",
                "winner_share": ":.2%",
                "latitude": False,
                "longitude": False,
            },
            zoom=8.5,
            height=560,
        )
        fig_map.update_layout(
            mapbox_style="open-street-map",
            margin=dict(l=0, r=0, t=0, b=0),
            font=dict(family="Tahoma, Arial, sans-serif"),
        )
        st.plotly_chart(fig_map, use_container_width=True)

    with st.expander("ดูข้อมูลที่ใช้ทำกราฟ"):
        preview_cols = [
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
            *selected_score_cols,
        ]
        st.dataframe(
            df[[column for column in preview_cols if column in df.columns]],
            use_container_width=True,
            hide_index=True,
        )
