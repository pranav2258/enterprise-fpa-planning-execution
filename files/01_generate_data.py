"""
Aurora Dynamics Inc. — Synthetic SAP-style FP&A dataset generator
===================================================================
Generates a multi-year (FY2023-FY2026) general ledger, revenue, opex,
headcount, and operational dataset styled after SAP ECC/S4 tables
(BSEG/BKPF-like GL, COEP-like cost center actuals, PA-like headcount),
plus budget, forecast, long-range-plan, and management-commentary text.

Output: /home/claude/fpa_project/data/aurora_fpa.db  (SQLite)
        + mirrored CSVs for convenience
"""
import sqlite3
import numpy as np
import pandas as pd
from datetime import date
import random

np.random.seed(42)
random.seed(42)

DB_PATH = "/home/claude/fpa_project/data/aurora_fpa.db"
CSV_DIR = "/home/claude/fpa_project/data"

# ----------------------------------------------------------------------
# 1. MASTER DATA (SAP-style dimensions)
# ----------------------------------------------------------------------

# Company code / legal entities (SAP: BUKRS)
entities = pd.DataFrame([
    {"company_code": "1000", "entity_name": "Aurora Dynamics US",   "region": "Americas", "currency": "USD"},
    {"company_code": "2000", "entity_name": "Aurora Dynamics EMEA", "region": "EMEA",      "currency": "USD"},
    {"company_code": "3000", "entity_name": "Aurora Dynamics APAC", "region": "APAC",      "currency": "USD"},
])

# Business segments / profit centers (SAP: PRCTR)
segments = pd.DataFrame([
    {"profit_center": "PC10", "segment_name": "Cloud Platform",     "segment_type": "Subscription"},
    {"profit_center": "PC20", "segment_name": "Data Analytics",     "segment_type": "Subscription"},
    {"profit_center": "PC30", "segment_name": "Professional Svcs",  "segment_type": "Services"},
    {"profit_center": "PC40", "segment_name": "Hardware & IoT",     "segment_type": "Product"},
])

# Cost centers (SAP: KOSTL)
cost_centers = pd.DataFrame([
    {"cost_center": "CC100", "department": "Sales & Marketing",        "function": "S&M"},
    {"cost_center": "CC200", "department": "Research & Development",   "function": "R&D"},
    {"cost_center": "CC300", "department": "General & Administrative", "function": "G&A"},
    {"cost_center": "CC400", "department": "Customer Success",         "function": "S&M"},
    {"cost_center": "CC500", "department": "Cloud Operations (COGS)",  "function": "COGS"},
])

# GL account chart of accounts (SAP: SAKNR) — condensed but realistic
gl_accounts = pd.DataFrame([
    {"gl_account": "400000", "account_name": "Subscription Revenue",         "account_group": "Revenue",  "pnl_category": "Revenue", "normal_balance": "C"},
    {"gl_account": "400100", "account_name": "Services Revenue",             "account_group": "Revenue",  "pnl_category": "Revenue", "normal_balance": "C"},
    {"gl_account": "400200", "account_name": "Hardware Revenue",             "account_group": "Revenue",  "pnl_category": "Revenue", "normal_balance": "C"},
    {"gl_account": "500000", "account_name": "Hosting & Cloud Infra Cost",   "account_group": "COGS",     "pnl_category": "COGS",    "normal_balance": "D"},
    {"gl_account": "500100", "account_name": "Third-Party License COGS",     "account_group": "COGS",     "pnl_category": "COGS",    "normal_balance": "D"},
    {"gl_account": "500200", "account_name": "Support & Success Labor COGS", "account_group": "COGS",     "pnl_category": "COGS",    "normal_balance": "D"},
    {"gl_account": "600000", "account_name": "Salaries & Wages",             "account_group": "Opex",     "pnl_category": "Opex",    "normal_balance": "D"},
    {"gl_account": "600100", "account_name": "Employee Benefits",            "account_group": "Opex",     "pnl_category": "Opex",    "normal_balance": "D"},
    {"gl_account": "600200", "account_name": "Stock-Based Compensation",     "account_group": "Opex",     "pnl_category": "Opex",    "normal_balance": "D"},
    {"gl_account": "610000", "account_name": "Marketing Programs",          "account_group": "Opex",     "pnl_category": "Opex",    "normal_balance": "D"},
    {"gl_account": "620000", "account_name": "Travel & Entertainment",      "account_group": "Opex",     "pnl_category": "Opex",    "normal_balance": "D"},
    {"gl_account": "630000", "account_name": "Software & IT Subscriptions", "account_group": "Opex",     "pnl_category": "Opex",    "normal_balance": "D"},
    {"gl_account": "640000", "account_name": "Facilities & Occupancy",      "account_group": "Opex",     "pnl_category": "Opex",    "normal_balance": "D"},
    {"gl_account": "650000", "account_name": "Professional Fees",          "account_group": "Opex",     "pnl_category": "Opex",    "normal_balance": "D"},
    {"gl_account": "660000", "account_name": "Depreciation & Amortization", "account_group": "Opex",     "pnl_category": "Opex",    "normal_balance": "D"},
])

entities.to_csv(f"{CSV_DIR}/dim_entities.csv", index=False)
segments.to_csv(f"{CSV_DIR}/dim_segments.csv", index=False)
cost_centers.to_csv(f"{CSV_DIR}/dim_cost_centers.csv", index=False)
gl_accounts.to_csv(f"{CSV_DIR}/dim_gl_accounts.csv", index=False)

# ----------------------------------------------------------------------
# 2. TIME DIMENSION
# ----------------------------------------------------------------------
# Actuals available Jan-2023 through Jun-2026 ("today" = Jul 27 2026 -> last closed month = Jun-2026)
all_months = pd.date_range("2023-01-01", "2026-12-01", freq="MS")
actual_cutoff = pd.Timestamp("2026-06-01")

fiscal = pd.DataFrame({"period": all_months})
fiscal["fiscal_year"] = fiscal["period"].dt.year
fiscal["fiscal_quarter"] = "Q" + fiscal["period"].dt.quarter.astype(str)
fiscal["month_name"] = fiscal["period"].dt.strftime("%b-%Y")
fiscal["is_actual"] = fiscal["period"] <= actual_cutoff
fiscal.to_csv(f"{CSV_DIR}/dim_calendar.csv", index=False)

# ----------------------------------------------------------------------
# 3. DRIVER-BASED REVENUE MODEL (bottoms-up, per segment x entity x month)
# ----------------------------------------------------------------------
# Drivers: beginning customers, new logos, churn rate, ARPU (average revenue per unit),
# services attach rate, hardware unit sell-through.

segment_growth = {
    "PC10": {"base_customers": 1200, "monthly_new_logo_mean": 55, "monthly_churn_rate": 0.018, "arpu": 850,  "arpu_growth_m": 0.004},
    "PC20": {"base_customers": 640,  "monthly_new_logo_mean": 28, "monthly_churn_rate": 0.020, "arpu": 1150, "arpu_growth_m": 0.005},
    "PC30": {"base_customers": 0,    "monthly_new_logo_mean": 0,  "monthly_churn_rate": 0.0,   "arpu": 0,    "arpu_growth_m": 0.0},  # services driven off subscription base
    "PC40": {"base_customers": 300,  "monthly_new_logo_mean": 10, "monthly_churn_rate": 0.03,  "arpu": 2200, "arpu_growth_m": 0.001},
}
entity_mix = {"1000": 0.55, "2000": 0.30, "3000": 0.15}  # revenue split across entities

records = []
cust_state = {seg: params["base_customers"] for seg, params in segment_growth.items()}
arpu_state = {seg: params["arpu"] for seg, params in segment_growth.items()}

# macro seasonality index (Q4 budget flush + Q1 renewal dip), applied to new logos
season_index = {1: 0.90, 2: 1.00, 3: 1.00, 4: 1.05, 5: 1.00, 6: 1.05,
                 7: 0.85, 8: 0.85, 9: 1.05, 10: 1.10, 11: 1.10, 12: 1.25}

for m in all_months:
    month_num = m.month
    seasonal = season_index[month_num]
    # subscription segments
    for seg in ["PC10", "PC20", "PC40"]:
        p = segment_growth[seg]
        new_logo = max(0, np.random.normal(p["monthly_new_logo_mean"] * seasonal, p["monthly_new_logo_mean"] * 0.18))
        churned = cust_state[seg] * p["monthly_churn_rate"] * np.random.normal(1.0, 0.15)
        cust_state[seg] = max(0, cust_state[seg] + new_logo - churned)
        arpu_state[seg] = arpu_state[seg] * (1 + p["arpu_growth_m"] + np.random.normal(0, 0.006))
        revenue = cust_state[seg] * arpu_state[seg]
        gl_map = {"PC10": "400000", "PC20": "400000", "PC40": "400200"}
        for ent, share in entity_mix.items():
            records.append({
                "period": m, "profit_center": seg, "company_code": ent,
                "gl_account": gl_map[seg], "customers": cust_state[seg] * share,
                "arpu": arpu_state[seg], "revenue": revenue * share,
                "new_logos": new_logo * share, "churned_customers": churned * share,
            })
    # professional services: ~11% of combined subscription revenue that month, own GL
    sub_rev_month = sum(r["revenue"] for r in records if r["period"] == m and r["profit_center"] in ["PC10", "PC20"])
    svc_rev = sub_rev_month * np.random.normal(0.11, 0.015)
    for ent, share in entity_mix.items():
        records.append({
            "period": m, "profit_center": "PC30", "company_code": ent,
            "gl_account": "400100", "customers": np.nan, "arpu": np.nan,
            "revenue": svc_rev * share, "new_logos": np.nan, "churned_customers": np.nan,
        })

revenue_df = pd.DataFrame(records)
revenue_df["revenue"] = revenue_df["revenue"].round(2)
revenue_df.to_csv(f"{CSV_DIR}/fact_revenue_actuals.csv", index=False)

# ----------------------------------------------------------------------
# 4. HEADCOUNT (SAP HR-style, per cost center x entity x month)
# ----------------------------------------------------------------------
hc_base = {"CC100": 42, "CC200": 58, "CC300": 19, "CC400": 26, "CC500": 14}
hc_growth_m = {"CC100": 0.009, "CC200": 0.012, "CC300": 0.003, "CC400": 0.011, "CC500": 0.010}
avg_fully_loaded_salary = {"CC100": 118000, "CC200": 152000, "CC300": 105000, "CC400": 98000, "CC500": 122000}

hc_records = []
hc_state = dict(hc_base)
for m in all_months:
    for cc in hc_base:
        hc_state[cc] = hc_state[cc] * (1 + hc_growth_m[cc] + np.random.normal(0, 0.006))
        for ent, share in entity_mix.items():
            hc_records.append({
                "period": m, "cost_center": cc, "company_code": ent,
                "headcount": round(hc_state[cc] * share, 1),
                "avg_fully_loaded_cost": avg_fully_loaded_salary[cc] * (1 + 0.028 * ((m.year - 2023) + m.month/12)),
            })
headcount_df = pd.DataFrame(hc_records)
headcount_df.to_csv(f"{CSV_DIR}/fact_headcount_actuals.csv", index=False)

# ----------------------------------------------------------------------
# 5. OPEX (GL postings driven off headcount + non-headcount programs)
# ----------------------------------------------------------------------
opex_records = []
non_hc_opex_pct_of_payroll = {  # ratio applied on top of comp costs, by department
    "CC100": {"610000": 0.35, "620000": 0.05, "630000": 0.04, "640000": 0.03},
    "CC200": {"630000": 0.07, "640000": 0.03, "620000": 0.015},
    "CC300": {"650000": 0.15, "630000": 0.04, "640000": 0.03},
    "CC400": {"630000": 0.05, "620000": 0.02, "640000": 0.03},
    "CC500": {"500000": 3.50, "500100": 1.50},  # COGS-heavy cost center, tuned for ~72-75% gross margin
}
for _, row in headcount_df.iterrows():
    cc, ent, period = row["cost_center"], row["company_code"], row["period"]
    monthly_comp = row["headcount"] * row["avg_fully_loaded_cost"] / 12
    salaries = monthly_comp * 0.78
    benefits = monthly_comp * 0.16
    sbc = monthly_comp * 0.06
    for gl, amt in [("600000", salaries), ("600100", benefits), ("600200", sbc)]:
        opex_records.append({"period": period, "cost_center": cc, "company_code": ent, "gl_account": gl,
                              "amount": round(amt * np.random.normal(1.0, 0.02), 2)})
    for gl, ratio in non_hc_opex_pct_of_payroll.get(cc, {}).items():
        amt = monthly_comp * ratio * np.random.normal(1.0, 0.10)
        opex_records.append({"period": period, "cost_center": cc, "company_code": ent, "gl_account": gl,
                              "amount": round(amt, 2)})
    # D&A flat-ish add-on for R&D/G&A capex amortization
    if cc in ["CC200", "CC300"]:
        opex_records.append({"period": period, "cost_center": cc, "company_code": ent, "gl_account": "660000",
                              "amount": round(monthly_comp * 0.03 * np.random.normal(1.0, 0.05), 2)})

opex_df = pd.DataFrame(opex_records)
opex_df.to_csv(f"{CSV_DIR}/fact_opex_actuals.csv", index=False)

# ----------------------------------------------------------------------
# 6. GENERAL LEDGER — SAP BSEG/BKPF style unified journal (revenue + opex, double-entry flavored)
# ----------------------------------------------------------------------
gl_records = []
doc_no = 4900000001
for _, r in revenue_df.iterrows():
    gl_records.append({
        "document_number": doc_no, "posting_date": r["period"] + pd.Timedelta(days=random.randint(0, 27)),
        "period": r["period"], "company_code": r["company_code"], "profit_center": r["profit_center"],
        "cost_center": None, "gl_account": r["gl_account"], "amount": r["revenue"],
        "debit_credit": "C", "document_type": "RV", "source": "Billing"
    })
    doc_no += 1
for _, r in opex_df.iterrows():
    gl_records.append({
        "document_number": doc_no, "posting_date": r["period"] + pd.Timedelta(days=random.randint(0, 27)),
        "period": r["period"], "company_code": r["company_code"], "profit_center": None,
        "cost_center": r["cost_center"], "gl_account": r["gl_account"], "amount": r["amount"],
        "debit_credit": "D", "document_type": "SA", "source": "Payroll/AP"
    })
    doc_no += 1

gl_df = pd.DataFrame(gl_records)
gl_df.to_csv(f"{CSV_DIR}/fact_gl_transactions.csv", index=False)

# ----------------------------------------------------------------------
# 7. BUDGET (FY2024, FY2025, FY2026 — set once a year, ~Nov prior year, +growth assumptions)
# ----------------------------------------------------------------------
def build_budget(revenue_actuals, opex_actuals, target_years):
    """Budget = prior-year run-rate x growth assumption, with a deliberate optimism bias so
    actual-vs-budget variance tells a realistic story."""
    budget_rows = []
    for fy in target_years:
        prior_year_rev = revenue_actuals[revenue_actuals["period"].dt.year == fy - 1]
        prior_year_opex = opex_actuals[opex_actuals["period"].dt.year == fy - 1]
        rev_growth_assumption = {2024: 0.28, 2025: 0.24, 2026: 0.20}[fy]
        opex_growth_assumption = {2024: 0.22, 2025: 0.19, 2026: 0.16}[fy]
        if len(prior_year_rev) == 0:
            continue
        rev_by_seg_ent_gl_month = (prior_year_rev.assign(month=prior_year_rev["period"].dt.month)
                                    .groupby(["profit_center", "company_code", "gl_account", "month"])["revenue"].sum())
        for (seg, ent, gl, month), val in rev_by_seg_ent_gl_month.items():
            budget_rows.append({"period": pd.Timestamp(fy, month, 1), "dim1": seg, "dim2": ent, "gl_account": gl,
                                 "line_type": "Revenue", "budget_amount": round(val * (1 + rev_growth_assumption), 2)})
        opex_by_cc_ent_gl_month = (prior_year_opex.assign(month=prior_year_opex["period"].dt.month)
                                    .groupby(["cost_center", "company_code", "gl_account", "month"])["amount"].sum())
        for (cc, ent, gl, month), val in opex_by_cc_ent_gl_month.items():
            budget_rows.append({"period": pd.Timestamp(fy, month, 1), "dim1": cc, "dim2": ent, "gl_account": gl,
                                 "line_type": "Opex", "budget_amount": round(val * (1 + opex_growth_assumption), 2)})
    return pd.DataFrame(budget_rows)

budget_df = build_budget(revenue_df, opex_df, [2024, 2025, 2026])
budget_df.to_csv(f"{CSV_DIR}/fact_budget.csv", index=False)

# ----------------------------------------------------------------------
# 8. FORECAST (rolling monthly re-forecast, produced at end of each quarter, latest-view flag)
# ----------------------------------------------------------------------
# Simplified: one "latest forecast" per remaining month of FY2026, generated as of Jun-2026 close,
# blending trailing-3-month actual run-rate with budget-implied growth (typical FP&A technique).
def build_latest_forecast(revenue_actuals, opex_actuals, as_of=pd.Timestamp("2026-06-01")):
    fcst_rows = []
    remaining_months = [m for m in all_months if m > as_of]
    trailing = revenue_actuals[(revenue_actuals["period"] > as_of - pd.DateOffset(months=3)) & (revenue_actuals["period"] <= as_of)]
    trail_rev = trailing.groupby(["profit_center", "company_code", "gl_account"])["revenue"].mean()
    trail_opex = opex_actuals[(opex_actuals["period"] > as_of - pd.DateOffset(months=3)) & (opex_actuals["period"] <= as_of)]
    trail_opex_avg = trail_opex.groupby(["cost_center", "company_code", "gl_account"])["amount"].mean()
    monthly_rev_growth = 0.014   # ~1.4%/mo run-rate growth assumption embedded in forecast
    monthly_opex_growth = 0.011
    for i, m in enumerate(remaining_months, start=1):
        for (seg, ent, gl), val in trail_rev.items():
            fcst_rows.append({"period": m, "dim1": seg, "dim2": ent, "gl_account": gl, "line_type": "Revenue",
                               "forecast_amount": round(val * (1 + monthly_rev_growth) ** i * np.random.normal(1.0, 0.01), 2)})
        for (cc, ent, gl), val in trail_opex_avg.items():
            fcst_rows.append({"period": m, "dim1": cc, "dim2": ent, "gl_account": gl, "line_type": "Opex",
                               "forecast_amount": round(val * (1 + monthly_opex_growth) ** i * np.random.normal(1.0, 0.01), 2)})
    return pd.DataFrame(fcst_rows)

forecast_df = build_latest_forecast(revenue_df, opex_df)
forecast_df.to_csv(f"{CSV_DIR}/fact_forecast_latest.csv", index=False)

# ----------------------------------------------------------------------
# 9. THREE-YEAR LONG-RANGE PLAN (FY2027-FY2029, annual granularity, top-down + driver sanity check)
# ----------------------------------------------------------------------
fy2026_rev = revenue_df[revenue_df["period"].dt.year == 2026]["revenue"].sum() * 2  # annualize from H1 + forecast H2 roughly
fy2026_opex = opex_df[opex_df["period"].dt.year == 2026]["amount"].sum() * 2
lrp_rows = []
rev_cagr_by_year = {2027: 0.22, 2028: 0.19, 2029: 0.17}
opex_growth_by_year = {2027: 0.16, 2028: 0.14, 2029: 0.13}
rev, opx = fy2026_rev, fy2026_opex
for fy in [2027, 2028, 2029]:
    rev = rev * (1 + rev_cagr_by_year[fy])
    opx = opx * (1 + opex_growth_by_year[fy])
    lrp_rows.append({"fiscal_year": fy, "plan_revenue": round(rev, 0), "plan_opex": round(opx, 0),
                      "plan_ebitda": round(rev - opx, 0), "plan_ebitda_margin": round((rev - opx) / rev, 4)})
lrp_df = pd.DataFrame(lrp_rows)
lrp_df.to_csv(f"{CSV_DIR}/fact_lrp.csv", index=False)

# ----------------------------------------------------------------------
# 10. SCENARIO PLANNING (Base / Upside / Downside sensitivities on top of latest forecast + LRP)
# ----------------------------------------------------------------------
scenario_assumptions = pd.DataFrame([
    {"scenario": "Base",     "rev_growth_delta": 0.000, "churn_delta": 0.000, "opex_growth_delta": 0.000, "description": "Latest board-approved forecast trajectory."},
    {"scenario": "Upside",   "rev_growth_delta": 0.045, "churn_delta": -0.006, "opex_growth_delta": 0.015, "description": "Faster net-new logo growth + lower churn; opex flexes up to support delivery."},
    {"scenario": "Downside", "rev_growth_delta": -0.055, "churn_delta": 0.010, "opex_growth_delta": -0.020, "description": "Macro slowdown compresses new business and expands churn; discretionary opex cut in response."},
])
scenario_assumptions.to_csv(f"{CSV_DIR}/dim_scenario_assumptions.csv", index=False)

# ----------------------------------------------------------------------
# 11. MANAGEMENT COMMENTARY (unstructured text, per department per quarter) — for NLP module
# ----------------------------------------------------------------------
commentary_bank = {
    "CC100": {
        "positive": [
            "Sales & Marketing exceeded pipeline generation targets this quarter, driven by strong performance in the Cloud Platform segment and improved conversion rates from the new outbound motion.",
            "New logo bookings accelerated meaningfully, with enterprise deal sizes up double digits versus prior quarter; the recently hired enterprise AEs are ramping ahead of plan.",
            "Marketing-sourced pipeline grew significantly following the product launch event, and win rates against the primary competitor improved.",
        ],
        "negative": [
            "Sales cycles lengthened this quarter as budget scrutiny increased among mid-market prospects, pushing several six-figure deals into next quarter.",
            "Churn ticked up in the SMB segment due to increased competitive pressure and price sensitivity; we are launching a save-desk motion to address this.",
            "Marketing program spend ran over plan due to an unbudgeted trade show sponsorship, though pipeline contribution has been solid.",
        ],
        "neutral": [
            "Headcount in Sales & Marketing grew in line with plan as we continue to build out the EMEA go-to-market team.",
            "The team completed a territory realignment this quarter; early results are inconclusive and we will monitor next quarter.",
        ],
    },
    "CC200": {
        "positive": [
            "R&D shipped the new analytics module ahead of schedule, and engineering velocity metrics improved following the platform re-architecture completed last quarter.",
            "The team successfully reduced cloud infrastructure cost per customer through the optimization initiative, which should benefit gross margin going forward.",
        ],
        "negative": [
            "A key platform migration slipped by six weeks due to unforeseen technical debt in the legacy billing system, delaying two planned feature releases.",
            "Engineering attrition was elevated this quarter, requiring backfill hiring that pressured near-term productivity.",
        ],
        "neutral": [
            "R&D headcount grew as planned with the addition of the new APAC engineering hub.",
            "The team continued incremental investment in the data platform roadmap, consistent with the approved budget.",
        ],
    },
    "CC300": {
        "positive": [
            "G&A completed the ERP system upgrade under budget, and finance close cycle time improved by two days as a result.",
        ],
        "negative": [
            "Professional fees exceeded plan due to additional legal costs associated with a customer contract dispute, now substantially resolved.",
            "Facilities costs came in above budget following the unplanned office expansion in the APAC region.",
        ],
        "neutral": [
            "G&A headcount remained roughly flat quarter over quarter, consistent with our lean corporate function strategy.",
        ],
    },
    "CC400": {
        "positive": [
            "Customer Success drove a meaningful improvement in net revenue retention this quarter, aided by the new customer health-scoring model and proactive renewal outreach.",
            "Support ticket resolution times improved significantly following the rollout of the new knowledge base and staffing increase.",
        ],
        "negative": [
            "Renewal rates softened slightly in the Hardware & IoT segment as several large customers delayed procurement decisions amid budget freezes.",
        ],
        "neutral": [
            "Customer Success headcount grew modestly to support the expanding subscription customer base.",
        ],
    },
    "CC500": {
        "positive": [
            "Cloud Operations achieved a notable reduction in hosting cost per transaction through the infrastructure consolidation project, supporting gross margin expansion.",
        ],
        "negative": [
            "Hosting costs ran above plan this quarter due to unplanned capacity additions ahead of a major customer go-live.",
        ],
        "neutral": [
            "Cloud infrastructure spend tracked closely to plan this quarter with no material variances.",
        ],
    },
}

quarters = sorted(fiscal[fiscal["is_actual"]]["fiscal_year"].astype(str) + fiscal[fiscal["is_actual"]]["fiscal_quarter"]).__class__(
    dict.fromkeys((fiscal[fiscal["is_actual"]]["fiscal_year"].astype(str) + "-" + fiscal[fiscal["is_actual"]]["fiscal_quarter"]).tolist())
)
commentary_rows = []
tone_cycle = ["positive", "neutral", "negative"]
for i, q in enumerate(quarters):
    for cc, bank in commentary_bank.items():
        tone = np.random.choice(["positive", "neutral", "negative"], p=[0.45, 0.30, 0.25])
        text = random.choice(bank[tone])
        commentary_rows.append({"fiscal_quarter": q, "cost_center": cc, "commentary_text": text, "authored_tone_label": tone})

commentary_df = pd.DataFrame(commentary_rows)
commentary_df.to_csv(f"{CSV_DIR}/fact_management_commentary.csv", index=False)

# ----------------------------------------------------------------------
# 12. LOAD EVERYTHING INTO SQLITE (SAP-style relational schema)
# ----------------------------------------------------------------------
conn = sqlite3.connect(DB_PATH)
entities.to_sql("dim_entities", conn, if_exists="replace", index=False)
segments.to_sql("dim_segments", conn, if_exists="replace", index=False)
cost_centers.to_sql("dim_cost_centers", conn, if_exists="replace", index=False)
gl_accounts.to_sql("dim_gl_accounts", conn, if_exists="replace", index=False)
fiscal.to_sql("dim_calendar", conn, if_exists="replace", index=False)
revenue_df.to_sql("fact_revenue_actuals", conn, if_exists="replace", index=False)
headcount_df.to_sql("fact_headcount_actuals", conn, if_exists="replace", index=False)
opex_df.to_sql("fact_opex_actuals", conn, if_exists="replace", index=False)
gl_df.to_sql("fact_gl_transactions", conn, if_exists="replace", index=False)
budget_df.to_sql("fact_budget", conn, if_exists="replace", index=False)
forecast_df.to_sql("fact_forecast_latest", conn, if_exists="replace", index=False)
lrp_df.to_sql("fact_lrp", conn, if_exists="replace", index=False)
scenario_assumptions.to_sql("dim_scenario_assumptions", conn, if_exists="replace", index=False)
commentary_df.to_sql("fact_management_commentary", conn, if_exists="replace", index=False)
conn.commit()
conn.close()

print("Data generation complete.")
print(f"  GL transactions:      {len(gl_df):,}")
print(f"  Revenue actual rows:  {len(revenue_df):,}")
print(f"  Opex actual rows:     {len(opex_df):,}")
print(f"  Headcount rows:       {len(headcount_df):,}")
print(f"  Budget rows:          {len(budget_df):,}")
print(f"  Forecast rows:        {len(forecast_df):,}")
print(f"  LRP rows:             {len(lrp_df):,}")
print(f"  Commentary rows:      {len(commentary_df):,}")
print(f"DB written to {DB_PATH}")
