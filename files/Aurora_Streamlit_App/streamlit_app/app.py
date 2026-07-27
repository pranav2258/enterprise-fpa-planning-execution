"""
Aurora Dynamics — Enterprise FP&A Planning & Executive Decision Intelligence Platform
=======================================================================================
Streamlit self-service dashboard.

Run locally with:
    streamlit run app.py

Requires: streamlit, pandas, plotly, numpy  (pip install streamlit pandas plotly numpy)
Expects the SQLite database `aurora_fpa.db` and the derived CSVs produced by
scripts/01_generate_data.py, 03_forecast_variance_scenario.py, and
04_nlp_commentary.py to sit in a sibling `data/` folder (see DATA_DIR below).
"""
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ------------------------------------------------------------------
# CONFIG
# ------------------------------------------------------------------
APP_DIR = Path(__file__).parent
DATA_DIR = APP_DIR / "data"
DB_PATH = DATA_DIR / "aurora_fpa.db"

st.set_page_config(
    page_title="Aurora Dynamics | FP&A Decision Intelligence",
    page_icon="📊",
    layout="wide",
)

NAVY = "#1E2761"
GOLD = "#D4A94C"
SLATE = "#44506B"
GREEN = "#1E8A5F"
RED = "#C0392B"
ICE = "#CADCFC"

PALETTE = [NAVY, GOLD, SLATE, "#3A56B4", "#9AA6C4", GREEN]

# ------------------------------------------------------------------
# DATA LOADING (cached)
# ------------------------------------------------------------------
@st.cache_data
def load_data():
    conn = sqlite3.connect(DB_PATH)
    d = {}
    d["revenue"] = pd.read_sql("SELECT * FROM fact_revenue_actuals", conn, parse_dates=["period"])
    d["opex"] = pd.read_sql("SELECT * FROM fact_opex_actuals", conn, parse_dates=["period"])
    d["headcount"] = pd.read_sql("SELECT * FROM fact_headcount_actuals", conn, parse_dates=["period"])
    d["segments"] = pd.read_sql("SELECT * FROM dim_segments", conn)
    d["entities"] = pd.read_sql("SELECT * FROM dim_entities", conn)
    d["cost_centers"] = pd.read_sql("SELECT * FROM dim_cost_centers", conn)
    d["calendar"] = pd.read_sql("SELECT * FROM dim_calendar", conn, parse_dates=["period"])
    conn.close()

    d["pnl_monthly"] = pd.read_csv(DATA_DIR / "pnl_monthly_actuals.csv", parse_dates=["period"])
    d["var_budget"] = pd.read_csv(DATA_DIR / "variance_actual_vs_budget.csv", parse_dates=["period"])
    d["var_forecast"] = pd.read_csv(DATA_DIR / "variance_actual_vs_forecast.csv", parse_dates=["period"])
    d["exec_var_budget"] = pd.read_csv(DATA_DIR / "variance_summary_exec_budget.csv", parse_dates=["period"])
    d["exec_var_forecast"] = pd.read_csv(DATA_DIR / "variance_summary_exec_forecast.csv", parse_dates=["period"])
    d["accuracy"] = pd.read_csv(DATA_DIR / "ml_model_accuracy_comparison.csv")
    d["ml_preds_holdout"] = pd.read_csv(DATA_DIR / "ml_model_predictions_holdout.csv", parse_dates=["period"])
    d["ml_future"] = pd.read_csv(DATA_DIR / "ml_revenue_forecast_fy26_remainder.csv", parse_dates=["period"])
    d["scenario_pnl"] = pd.read_csv(DATA_DIR / "scenario_pnl_fy26_remainder.csv", parse_dates=["period"])
    d["lrp"] = pd.read_csv(DATA_DIR / "fact_lrp.csv")
    d["lrp_scenario"] = pd.read_csv(DATA_DIR / "lrp_scenario_flexed.csv")
    d["scenario_assump"] = pd.read_csv(DATA_DIR / "dim_scenario_assumptions.csv")
    d["driver_revenue"] = pd.read_csv(DATA_DIR / "driver_model_revenue.csv", parse_dates=["period"])
    d["commentary"] = pd.read_csv(DATA_DIR / "commentary_nlp_scored.csv")
    d["commentary_clusters"] = pd.read_csv(DATA_DIR / "commentary_topic_clusters.csv")
    d["commentary_link"] = pd.read_csv(DATA_DIR / "commentary_vs_variance_link.csv")
    return d


data = load_data()
seg_names = dict(zip(data["segments"]["profit_center"], data["segments"]["segment_name"]))

# ------------------------------------------------------------------
# SIDEBAR — GLOBAL FILTERS
# ------------------------------------------------------------------
st.sidebar.markdown("## 📊 Aurora Dynamics")
st.sidebar.caption("Enterprise FP&A Decision Intelligence Platform")
page = st.sidebar.radio(
    "Navigate",
    ["Executive Overview", "Actuals & Variance", "Driver-Based Model", "Forecasting (ML vs Statistical)",
     "Scenario Planning", "3-Year LRP", "Management Commentary (NLP)", "Data Explorer"],
)
st.sidebar.markdown("---")
fy_options = sorted(data["pnl_monthly"]["period"].dt.year.unique())
fy_filter = st.sidebar.multiselect("Fiscal Year", fy_options, default=fy_options)
st.sidebar.caption("Filters apply to the Actuals, Variance, and Driver Model pages.")
st.sidebar.markdown("---")
st.sidebar.caption("Synthetic SAP-style dataset · illustrative only, not real financials.")


def fmt_millions(x):
    return f"${x/1e6:,.2f}M"


# ==========================================================================
# PAGE 1 — EXECUTIVE OVERVIEW
# ==========================================================================
if page == "Executive Overview":
    st.title("Executive Overview")
    st.caption("Company-wide KPIs across the full modeled history (FY2023 – FY2026 latest close)")

    pnl = data["pnl_monthly"][data["pnl_monthly"]["period"].dt.year.isin(fy_filter)]
    latest = pnl.iloc[-1]
    prior_year_same_month = pnl[pnl["period"] == latest["period"] - pd.DateOffset(years=1)]

    c1, c2, c3, c4 = st.columns(4)
    yoy_rev = (latest["total_revenue"] / prior_year_same_month["total_revenue"].values[0] - 1) if len(prior_year_same_month) else np.nan
    c1.metric("Latest Month Revenue", fmt_millions(latest["total_revenue"]), f"{yoy_rev:+.1%} YoY" if not np.isnan(yoy_rev) else "n/a")
    c2.metric("Gross Margin", f"{latest['gross_margin_pct']:.1%}")
    c3.metric("EBITDA Margin", f"{latest['ebitda_margin_pct']:.1%}")
    c4.metric("EBITDA", fmt_millions(latest["ebitda"]))

    col1, col2 = st.columns([2, 1])
    with col1:
        fig = go.Figure()
        fig.add_bar(x=pnl["period"], y=pnl["total_revenue"], name="Revenue", marker_color=NAVY)
        fig.add_scatter(x=pnl["period"], y=pnl["ebitda"], name="EBITDA", yaxis="y2", line=dict(color=GOLD, width=3))
        fig.update_layout(
            title="Monthly Revenue & EBITDA",
            yaxis=dict(title="Revenue ($)"),
            yaxis2=dict(title="EBITDA ($)", overlaying="y", side="right"),
            legend=dict(orientation="h", y=-0.2),
            height=420, margin=dict(t=50, l=10, r=10, b=10),
        )
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        seg_rev = data["revenue"][data["revenue"]["period"].dt.year.isin(fy_filter)].groupby("profit_center")["revenue"].sum().reset_index()
        seg_rev["segment"] = seg_rev["profit_center"].map(seg_names)
        fig2 = px.pie(seg_rev, names="segment", values="revenue", hole=0.5, color_discrete_sequence=PALETTE,
                      title="Revenue Mix by Segment")
        fig2.update_layout(height=420, margin=dict(t=50, l=10, r=10, b=10))
        st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Margin Trend")
    fig3 = go.Figure()
    fig3.add_scatter(x=pnl["period"], y=pnl["gross_margin_pct"], name="Gross Margin %", line=dict(color=NAVY))
    fig3.add_scatter(x=pnl["period"], y=pnl["ebitda_margin_pct"], name="EBITDA Margin %", line=dict(color=GOLD))
    fig3.update_layout(yaxis_tickformat=".0%", height=320, margin=dict(t=10, l=10, r=10, b=10),
                        legend=dict(orientation="h", y=-0.25))
    st.plotly_chart(fig3, use_container_width=True)

# ==========================================================================
# PAGE 2 — ACTUALS & VARIANCE
# ==========================================================================
elif page == "Actuals & Variance":
    st.title("Actual vs. Budget / Forecast Variance")
    tab1, tab2 = st.tabs(["Actual vs Budget", "Actual vs Forecast"])

    with tab1:
        vb = data["exec_var_budget"]
        vb = vb[vb["period"].dt.year.isin(fy_filter)]
        line_pick = st.selectbox("Line Type", vb["line_type"].unique(), key="vb_line")
        vb_f = vb[vb["line_type"] == line_pick]
        fig = go.Figure()
        fig.add_bar(x=vb_f["period"], y=vb_f["budget_amount"], name="Budget", marker_color=SLATE)
        fig.add_bar(x=vb_f["period"], y=vb_f["actual_amount"], name="Actual", marker_color=NAVY)
        fig.update_layout(barmode="group", height=400, title=f"{line_pick}: Budget vs Actual",
                           margin=dict(t=50, l=10, r=10, b=10), legend=dict(orientation="h", y=-0.2))
        st.plotly_chart(fig, use_container_width=True)

        fig_v = px.bar(vb_f, x="period", y="variance_pct", color=vb_f["variance_pct"] > 0,
                        color_discrete_map={True: GREEN, False: RED}, title="Variance % (Actual vs Budget)")
        fig_v.update_layout(yaxis_tickformat=".0%", showlegend=False, height=320, margin=dict(t=50, l=10, r=10, b=10))
        st.plotly_chart(fig_v, use_container_width=True)
        st.dataframe(vb_f.style.format({"budget_amount": "${:,.0f}", "actual_amount": "${:,.0f}",
                                          "variance_abs": "${:,.0f}", "variance_pct": "{:.1%}"}), use_container_width=True)

    with tab2:
        vf = data["exec_var_forecast"]
        line_pick2 = st.selectbox("Line Type", vf["line_type"].unique(), key="vf_line")
        vf_f = vf[vf["line_type"] == line_pick2]
        fig = go.Figure()
        fig.add_bar(x=vf_f["period"], y=vf_f["forecast_amount"], name="Forecast", marker_color=SLATE)
        fig.add_bar(x=vf_f["period"], y=vf_f["actual_amount"], name="Actual", marker_color=GOLD)
        fig.update_layout(barmode="group", height=400, title=f"{line_pick2}: Forecast vs Actual",
                           margin=dict(t=50, l=10, r=10, b=10), legend=dict(orientation="h", y=-0.2))
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(vf_f.style.format({"forecast_amount": "${:,.0f}", "actual_amount": "${:,.0f}",
                                          "variance_abs": "${:,.0f}", "variance_pct": "{:.1%}"}), use_container_width=True)

# ==========================================================================
# PAGE 3 — DRIVER-BASED MODEL
# ==========================================================================
elif page == "Driver-Based Model":
    st.title("Driver-Based Revenue Model")
    st.caption("Revenue = Customers × ARPU, rebuilt bottoms-up by segment — adjust drivers to see what-if impact")

    drv = data["driver_revenue"][data["driver_revenue"]["period"].dt.year.isin(fy_filter)]
    seg_pick = st.selectbox("Segment", sorted(drv["profit_center"].unique()), format_func=lambda x: seg_names.get(x, x))
    drv_f = drv[drv["profit_center"] == seg_pick].sort_values("period")

    col1, col2 = st.columns(2)
    with col1:
        arpu_adj = st.slider("ARPU adjustment (%)", -20, 20, 0, step=1)
    with col2:
        churn_adj = st.slider("Churn rate adjustment (pp)", -5.0, 5.0, 0.0, step=0.5)

    drv_f = drv_f.copy()
    drv_f["arpu_adjusted"] = drv_f["arpu_implied"] * (1 + arpu_adj / 100)
    drv_f["churn_rate_adjusted"] = (drv_f["churn_rate_implied"] + churn_adj / 100).clip(lower=0)
    drv_f["customers_adjusted"] = drv_f["customers"] * (1 - (drv_f["churn_rate_adjusted"] - drv_f["churn_rate_implied"]))
    drv_f["revenue_adjusted"] = drv_f["customers_adjusted"] * drv_f["arpu_adjusted"]

    fig = go.Figure()
    fig.add_scatter(x=drv_f["period"], y=drv_f["revenue"], name="Revenue (actual driver model)", line=dict(color=NAVY))
    fig.add_scatter(x=drv_f["period"], y=drv_f["revenue_adjusted"], name="Revenue (what-if)", line=dict(color=GOLD, dash="dash"))
    fig.update_layout(height=420, title=f"{seg_names.get(seg_pick, seg_pick)} — Revenue: Actual vs What-If",
                       margin=dict(t=50, l=10, r=10, b=10), legend=dict(orientation="h", y=-0.2))
    st.plotly_chart(fig, use_container_width=True)

    delta = drv_f["revenue_adjusted"].sum() - drv_f["revenue"].sum()
    st.metric("Cumulative revenue impact of adjustments", fmt_millions(delta), delta=f"{delta/drv_f['revenue'].sum():+.1%}")

    st.subheader("Underlying driver data")
    st.dataframe(drv_f[["period", "customers", "arpu_implied", "revenue", "new_logos", "churned", "churn_rate_implied"]]
                 .style.format({"customers": "{:,.0f}", "arpu_implied": "${:,.0f}", "revenue": "${:,.0f}",
                                 "new_logos": "{:,.1f}", "churned": "{:,.1f}", "churn_rate_implied": "{:.2%}"}),
                 use_container_width=True)

# ==========================================================================
# PAGE 4 — FORECASTING (ML vs STATISTICAL)
# ==========================================================================
elif page == "Forecasting (ML vs Statistical)":
    st.title("Forecast Model Accuracy: ML vs. Statistical Baselines")
    st.caption("Trained on FY23-FY25 monthly revenue with lag/rolling-mean features; evaluated on trailing 6 actual months")

    acc = data["accuracy"].sort_values("MAPE")
    fig = px.bar(acc, x="model", y="MAPE", color="model", color_discrete_sequence=PALETTE,
                 title="Mean Absolute Percentage Error by Model (lower = better)")
    fig.update_layout(yaxis_tickformat=".1%", showlegend=False, height=380, margin=dict(t=50, l=10, r=10, b=10))
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(acc.style.format({"MAPE": "{:.2%}", "RMSE": "${:,.0f}", "MAE": "${:,.0f}"}), use_container_width=True)

    st.subheader("Holdout Predictions vs Actuals")
    preds = data["ml_preds_holdout"]
    fig2 = go.Figure()
    fig2.add_scatter(x=preds["period"], y=preds["actual"], name="Actual", line=dict(color="black", width=3))
    for col in preds.columns:
        if col not in ("period", "actual"):
            fig2.add_scatter(x=preds["period"], y=preds[col], name=col, line=dict(dash="dot"))
    fig2.update_layout(height=420, margin=dict(t=20, l=10, r=10, b=10), legend=dict(orientation="h", y=-0.3))
    st.plotly_chart(fig2, use_container_width=True)

    st.subheader("ML Revenue Forecast — Remainder of FY2026")
    future = data["ml_future"]
    fig3 = px.line(future, x="period", y="ml_revenue_forecast", markers=True,
                    color_discrete_sequence=[GOLD], title="Best-Model Recursive Forecast (Gradient Boosting)")
    fig3.update_layout(height=350, margin=dict(t=50, l=10, r=10, b=10))
    st.plotly_chart(fig3, use_container_width=True)

# ==========================================================================
# PAGE 5 — SCENARIO PLANNING
# ==========================================================================
elif page == "Scenario Planning":
    st.title("Scenario Planning: Base / Upside / Downside")

    st.subheader("Scenario Assumptions")
    st.dataframe(data["scenario_assump"].style.format({"rev_growth_delta": "{:+.1%}", "churn_delta": "{:+.1%}",
                                                         "opex_growth_delta": "{:+.1%}"}), use_container_width=True)

    st.subheader("H2 FY26 Scenario-Flexed P&L")
    scen = data["scenario_pnl"]
    scen_summary = scen.groupby("scenario").agg(revenue=("revenue", "sum"), opex=("opex", "sum"),
                                                  ebitda_proxy=("ebitda_proxy", "sum")).reset_index()
    order = ["Downside", "Base", "Upside"]
    scen_summary["scenario"] = pd.Categorical(scen_summary["scenario"], categories=order, ordered=True)
    scen_summary = scen_summary.sort_values("scenario")

    col1, col2 = st.columns(2)
    with col1:
        fig = px.bar(scen_summary, x="scenario", y="revenue", color="scenario",
                     color_discrete_map={"Base": SLATE, "Upside": GREEN, "Downside": RED},
                     title="H2 FY26 Revenue by Scenario")
        fig.update_layout(showlegend=False, height=380, margin=dict(t=50, l=10, r=10, b=10))
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        fig2 = px.bar(scen_summary, x="scenario", y="ebitda_proxy", color="scenario",
                      color_discrete_map={"Base": SLATE, "Upside": GREEN, "Downside": RED},
                      title="H2 FY26 EBITDA Proxy by Scenario")
        fig2.update_layout(showlegend=False, height=380, margin=dict(t=50, l=10, r=10, b=10))
        st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Monthly Scenario Trajectory")
    fig3 = px.line(scen, x="period", y="ebitda_proxy", color="scenario",
                    color_discrete_map={"Base": SLATE, "Upside": GREEN, "Downside": RED}, markers=True)
    fig3.update_layout(height=380, margin=dict(t=20, l=10, r=10, b=10), legend=dict(orientation="h", y=-0.25))
    st.plotly_chart(fig3, use_container_width=True)

# ==========================================================================
# PAGE 6 — 3-YEAR LRP
# ==========================================================================
elif page == "3-Year LRP":
    st.title("Three-Year Long-Range Plan (FY2027 – FY2029)")

    lrp_scen = data["lrp_scenario"]
    scenario_pick = st.radio("Scenario", ["Base", "Upside", "Downside"], horizontal=True)
    lrp_f = lrp_scen[lrp_scen["scenario"] == scenario_pick].sort_values("fiscal_year")

    col1, col2, col3 = st.columns(3)
    col1.metric("FY29 Plan Revenue", fmt_millions(lrp_f.iloc[-1]["plan_revenue"]))
    col2.metric("FY29 Plan EBITDA", fmt_millions(lrp_f.iloc[-1]["plan_ebitda"]))
    col3.metric("FY29 EBITDA Margin", f"{lrp_f.iloc[-1]['plan_ebitda_margin']:.1%}")

    fig = go.Figure()
    fig.add_bar(x=lrp_f["fiscal_year"], y=lrp_f["plan_revenue"], name="Plan Revenue", marker_color=NAVY)
    fig.add_bar(x=lrp_f["fiscal_year"], y=lrp_f["plan_opex"], name="Plan Opex", marker_color=SLATE)
    fig.add_scatter(x=lrp_f["fiscal_year"], y=lrp_f["plan_ebitda_margin"], name="EBITDA Margin %",
                     yaxis="y2", line=dict(color=GOLD, width=3))
    fig.update_layout(barmode="group", height=450,
                       yaxis2=dict(title="EBITDA Margin %", overlaying="y", side="right", tickformat=".0%"),
                       margin=dict(t=30, l=10, r=10, b=10), legend=dict(orientation="h", y=-0.2))
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("All Scenarios Compared")
    st.dataframe(lrp_scen.sort_values(["fiscal_year", "scenario"])
                 .style.format({"plan_revenue": "${:,.0f}", "plan_opex": "${:,.0f}", "plan_ebitda": "${:,.0f}",
                                 "plan_ebitda_margin": "{:.1%}"}), use_container_width=True)

# ==========================================================================
# PAGE 7 — MANAGEMENT COMMENTARY (NLP)
# ==========================================================================
elif page == "Management Commentary (NLP)":
    st.title("Management Commentary — NLP Analysis")
    st.caption("Lexicon-based sentiment scoring + TF-IDF/K-Means topic clustering over quarterly narratives")

    commentary = data["commentary"]
    dept_pick = st.multiselect("Department", commentary["department"].unique(), default=list(commentary["department"].unique()))
    commentary_f = commentary[commentary["department"].isin(dept_pick)]

    col1, col2 = st.columns([1, 1])
    with col1:
        tone_counts = commentary_f["predicted_tone"].value_counts().reset_index()
        tone_counts.columns = ["tone", "count"]
        fig = px.pie(tone_counts, names="tone", values="count", hole=0.5,
                     color="tone", color_discrete_map={"Positive": GREEN, "Neutral": SLATE, "Negative": RED},
                     title="Commentary Tone Distribution")
        fig.update_layout(height=380, margin=dict(t=50, l=10, r=10, b=10))
        st.plotly_chart(fig, use_container_width=True)
    with col2:
        clusters = data["commentary_clusters"]
        fig2 = px.bar(clusters, x="topic_cluster_label", y="comment_count", color="avg_sentiment",
                      color_continuous_scale=[RED, "#FFEB84", GREEN], title="Topic Clusters (TF-IDF + KMeans)")
        fig2.update_layout(height=380, margin=dict(t=50, l=10, r=10, b=10), xaxis_title=None)
        st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Sentiment vs. Opex Variance Linkage")
    link = data["commentary_link"]
    fig3 = px.scatter(link, x="avg_sentiment", y="variance_pct", color="cost_center", size=[10]*len(link),
                       trendline="ols" if len(link) > 3 else None,
                       title="Quarterly Commentary Sentiment vs. Opex Budget Variance %")
    fig3.update_layout(height=420, yaxis_tickformat=".0%", margin=dict(t=50, l=10, r=10, b=10))
    st.plotly_chart(fig3, use_container_width=True)

    st.subheader("Commentary Detail")
    st.dataframe(commentary_f[["fiscal_quarter", "department", "commentary_text", "sentiment_score",
                                 "predicted_tone", "top_keywords"]], use_container_width=True, height=400)

# ==========================================================================
# PAGE 8 — DATA EXPLORER (self-service, raw tables)
# ==========================================================================
elif page == "Data Explorer":
    st.title("Data Explorer")
    st.caption("Self-service access to the underlying fact and dimension tables")

    table_options = {
        "Revenue Actuals": data["revenue"],
        "Opex Actuals": data["opex"],
        "Headcount Actuals": data["headcount"],
        "Monthly P&L": data["pnl_monthly"],
        "Variance vs Budget (detail)": data["var_budget"],
        "Variance vs Forecast (detail)": data["var_forecast"],
        "Driver Model - Revenue": data["driver_revenue"],
        "Commentary (NLP scored)": data["commentary"],
    }
    tbl_pick = st.selectbox("Choose a table", list(table_options.keys()))
    df = table_options[tbl_pick]
    st.write(f"{len(df):,} rows × {len(df.columns)} columns")
    st.dataframe(df, use_container_width=True, height=500)
    st.download_button("Download as CSV", df.to_csv(index=False).encode("utf-8"),
                        file_name=f"{tbl_pick.replace(' ', '_').lower()}.csv", mime="text/csv")
