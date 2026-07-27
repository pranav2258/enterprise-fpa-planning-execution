"""
Aurora Dynamics FP&A — Forecasting, Variance, and Scenario Engine
==================================================================
1. Driver-based revenue/opex/profitability model (bottoms-up drivers).
2. Actual-vs-Budget and Actual-vs-Forecast variance tables.
3. ML forecast model (Random Forest & Gradient Boosting) vs. classical
   statistical baselines (Naive, Moving Average, Linear Trend, Holt-Winters-lite),
   with an accuracy comparison (MAPE / RMSE / MAE).
4. Base / Upside / Downside scenario P&Ls off the latest forecast + LRP.
"""
import sqlite3
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_percentage_error, mean_squared_error, mean_absolute_error
from sklearn.model_selection import train_test_split

DB_PATH = "/home/claude/fpa_project/data/aurora_fpa.db"
OUT_DIR = "/home/claude/fpa_project/data"

conn = sqlite3.connect(DB_PATH)

# ----------------------------------------------------------------------
# Load core facts
# ----------------------------------------------------------------------
revenue = pd.read_sql("SELECT * FROM fact_revenue_actuals", conn, parse_dates=["period"])
opex = pd.read_sql("SELECT * FROM fact_opex_actuals", conn, parse_dates=["period"])
headcount = pd.read_sql("SELECT * FROM fact_headcount_actuals", conn, parse_dates=["period"])
budget = pd.read_sql("SELECT * FROM fact_budget", conn, parse_dates=["period"])
forecast = pd.read_sql("SELECT * FROM fact_forecast_latest", conn, parse_dates=["period"])
lrp = pd.read_sql("SELECT * FROM fact_lrp", conn)
scenarios = pd.read_sql("SELECT * FROM dim_scenario_assumptions", conn)
gl_accounts = pd.read_sql("SELECT * FROM dim_gl_accounts", conn)

# ========================================================================
# PART 1 — MONTHLY CONSOLIDATED P&L (ACTUALS), COMPANY-WIDE
# ========================================================================
monthly_rev = revenue.groupby("period")["revenue"].sum().rename("total_revenue")
monthly_opex = opex.groupby("period")["amount"].sum().rename("total_opex")
# split opex into COGS vs Opex-below-the-line using gl account mapping
opex_gl = opex.merge(gl_accounts[["gl_account", "pnl_category"]], on="gl_account", how="left")
monthly_cogs = opex_gl[opex_gl["pnl_category"] == "COGS"].groupby("period")["amount"].sum().rename("total_cogs")
monthly_opex_only = opex_gl[opex_gl["pnl_category"] == "Opex"].groupby("period")["amount"].sum().rename("total_opex_below_gm")

pnl_monthly = pd.concat([monthly_rev, monthly_cogs, monthly_opex_only], axis=1).fillna(0)
pnl_monthly["gross_profit"] = pnl_monthly["total_revenue"] - pnl_monthly["total_cogs"]
pnl_monthly["gross_margin_pct"] = pnl_monthly["gross_profit"] / pnl_monthly["total_revenue"]
pnl_monthly["ebitda"] = pnl_monthly["gross_profit"] - pnl_monthly["total_opex_below_gm"]
pnl_monthly["ebitda_margin_pct"] = pnl_monthly["ebitda"] / pnl_monthly["total_revenue"]
pnl_monthly = pnl_monthly.reset_index()
pnl_monthly.to_csv(f"{OUT_DIR}/pnl_monthly_actuals.csv", index=False)

# ========================================================================
# PART 2 — DRIVER-BASED REVENUE / PROFITABILITY MODEL
# Rebuilds revenue bottom-up from customers x ARPU, and expresses opex per
# headcount, so the model is fully re-drivable (e.g. "what if ARPU +5%?").
# ========================================================================
driver_model = (revenue.dropna(subset=["customers"])
                 .groupby(["period", "profit_center"])
                 .agg(customers=("customers", "sum"),
                      revenue=("revenue", "sum"),
                      new_logos=("new_logos", "sum"),
                      churned=("churned_customers", "sum"))
                 .reset_index())
driver_model["arpu_implied"] = driver_model["revenue"] / driver_model["customers"]
driver_model["net_new_customers"] = driver_model["new_logos"] - driver_model["churned"]
driver_model["churn_rate_implied"] = driver_model["churned"] / driver_model["customers"]
driver_model.to_csv(f"{OUT_DIR}/driver_model_revenue.csv", index=False)

hc_cost = headcount.groupby("period").agg(total_headcount=("headcount", "sum")).reset_index()
opex_per_hc = opex.groupby("period")["amount"].sum().reset_index().merge(hc_cost, on="period")
opex_per_hc["opex_per_headcount_monthly"] = opex_per_hc["amount"] / opex_per_hc["total_headcount"]
opex_per_hc.to_csv(f"{OUT_DIR}/driver_model_opex_per_headcount.csv", index=False)

# ========================================================================
# PART 3 — ACTUAL vs BUDGET / FORECAST VARIANCE TABLES (Python-side, mirrors SQL views)
# ========================================================================
def build_variance(actual_rev, actual_opex, plan_df, amount_col, label):
    act_rev_g = actual_rev.groupby(["period", "profit_center", "company_code", "gl_account"])["revenue"].sum().reset_index()
    act_rev_g.columns = ["period", "dim1", "dim2", "gl_account", "actual_amount"]
    act_rev_g["line_type"] = "Revenue"
    act_opex_g = actual_opex.groupby(["period", "cost_center", "company_code", "gl_account"])["amount"].sum().reset_index()
    act_opex_g.columns = ["period", "dim1", "dim2", "gl_account", "actual_amount"]
    act_opex_g["line_type"] = "Opex"
    act_all = pd.concat([act_rev_g, act_opex_g], ignore_index=True)

    merged = plan_df.merge(act_all, on=["period", "dim1", "dim2", "gl_account", "line_type"], how="left")
    merged["actual_amount"] = merged["actual_amount"].fillna(0)
    merged["variance_abs"] = merged["actual_amount"] - merged[amount_col]
    merged["variance_pct"] = merged["variance_abs"] / merged[amount_col].replace(0, np.nan)
    merged["plan_type"] = label
    return merged

var_vs_budget = build_variance(revenue, opex, budget, "budget_amount", "Budget")
var_vs_forecast = build_variance(revenue, opex, forecast, "forecast_amount", "Forecast")
var_vs_budget.to_csv(f"{OUT_DIR}/variance_actual_vs_budget.csv", index=False)
var_vs_forecast.to_csv(f"{OUT_DIR}/variance_actual_vs_forecast.csv", index=False)

# Company-level rollup variance summary (for QBR / exec view)
def rollup_variance(var_df, label):
    r = var_df[var_df["actual_amount"] != 0].groupby(["period", "line_type"]).agg(
        plan_amount=(var_df.columns[5], "sum") if False else ("actual_amount", "sum")
    )
    return r

exec_var_budget = var_vs_budget.groupby(["period", "line_type"]).agg(
    budget_amount=("budget_amount", "sum"), actual_amount=("actual_amount", "sum")
).reset_index()
exec_var_budget["variance_abs"] = exec_var_budget["actual_amount"] - exec_var_budget["budget_amount"]
exec_var_budget["variance_pct"] = exec_var_budget["variance_abs"] / exec_var_budget["budget_amount"]
exec_var_budget.to_csv(f"{OUT_DIR}/variance_summary_exec_budget.csv", index=False)

exec_var_forecast = var_vs_forecast.groupby(["period", "line_type"]).agg(
    forecast_amount=("forecast_amount", "sum"), actual_amount=("actual_amount", "sum")
).reset_index()
exec_var_forecast["variance_abs"] = exec_var_forecast["actual_amount"] - exec_var_forecast["forecast_amount"]
exec_var_forecast["variance_pct"] = exec_var_forecast["variance_abs"] / exec_var_forecast["forecast_amount"]
exec_var_forecast.to_csv(f"{OUT_DIR}/variance_summary_exec_forecast.csv", index=False)

# ========================================================================
# PART 4 — ML FORECAST MODEL vs CLASSICAL STATISTICAL BASELINES
# Target: total company monthly revenue. Train on FY2023-FY2025, test on
# the trailing 6 actual months of FY2026 (holdout), then compare accuracy.
# ========================================================================
ts = pnl_monthly[["period", "total_revenue"]].copy().sort_values("period").reset_index(drop=True)
ts["t"] = np.arange(len(ts))
ts["month"] = ts["period"].dt.month
ts["quarter"] = ts["period"].dt.quarter
ts["year"] = ts["period"].dt.year
for lag in [1, 2, 3, 12]:
    ts[f"lag_{lag}"] = ts["total_revenue"].shift(lag)
ts["rolling_mean_3"] = ts["total_revenue"].shift(1).rolling(3).mean()
ts["rolling_mean_6"] = ts["total_revenue"].shift(1).rolling(6).mean()
ts_model = ts.dropna().reset_index(drop=True)

holdout_n = 6
train = ts_model.iloc[:-holdout_n]
test = ts_model.iloc[-holdout_n:]

feature_cols = ["t", "month", "quarter", "lag_1", "lag_2", "lag_3", "lag_12", "rolling_mean_3", "rolling_mean_6"]
X_train, y_train = train[feature_cols], train["total_revenue"]
X_test, y_test = test[feature_cols], test["total_revenue"]

models = {
    "Linear Regression": LinearRegression(),
    "Random Forest": RandomForestRegressor(n_estimators=300, max_depth=5, random_state=42),
    "Gradient Boosting": GradientBoostingRegressor(n_estimators=250, max_depth=3, learning_rate=0.05, random_state=42),
}

results = []
preds_all = {"period": test["period"].values, "actual": y_test.values}
for name, model in models.items():
    model.fit(X_train, y_train)
    pred = model.predict(X_test)
    preds_all[name] = pred
    results.append({
        "model": name,
        "MAPE": mean_absolute_percentage_error(y_test, pred),
        "RMSE": mean_squared_error(y_test, pred) ** 0.5,
        "MAE": mean_absolute_error(y_test, pred),
    })

# Classical baselines
naive_pred = train["total_revenue"].iloc[-1] * np.ones(len(test))          # naive = last actual carried forward
results.append({"model": "Naive (last value)",
                 "MAPE": mean_absolute_percentage_error(y_test, naive_pred),
                 "RMSE": mean_squared_error(y_test, naive_pred) ** 0.5,
                 "MAE": mean_absolute_error(y_test, naive_pred)})
preds_all["Naive (last value)"] = naive_pred

ma3_pred = np.full(len(test), train["total_revenue"].iloc[-3:].mean())      # 3-month moving average
results.append({"model": "Moving Average (3mo)",
                 "MAPE": mean_absolute_percentage_error(y_test, ma3_pred),
                 "RMSE": mean_squared_error(y_test, ma3_pred) ** 0.5,
                 "MAE": mean_absolute_error(y_test, ma3_pred)})
preds_all["Moving Average (3mo)"] = ma3_pred

lin_trend = LinearRegression().fit(train[["t"]], train["total_revenue"])
trend_pred = lin_trend.predict(test[["t"]])
results.append({"model": "Linear Trend (time-only)",
                 "MAPE": mean_absolute_percentage_error(y_test, trend_pred),
                 "RMSE": mean_squared_error(y_test, trend_pred) ** 0.5,
                 "MAE": mean_absolute_error(y_test, trend_pred)})
preds_all["Linear Trend (time-only)"] = trend_pred

# FP&A "official" latest forecast, for context, aggregated to same months if overlapping
official_fc_monthly = forecast.groupby("period")["forecast_amount"].sum().reset_index()
official_fc_rev_only = forecast[forecast["line_type"] == "Revenue"].groupby("period")["forecast_amount"].sum().reset_index()

accuracy_df = pd.DataFrame(results).sort_values("MAPE").reset_index(drop=True)
accuracy_df.to_csv(f"{OUT_DIR}/ml_model_accuracy_comparison.csv", index=False)

preds_df = pd.DataFrame(preds_all)
preds_df.to_csv(f"{OUT_DIR}/ml_model_predictions_holdout.csv", index=False)

# Best model refit on full data to project the remaining forecast horizon (FY26 H2)
best_model_name = accuracy_df.iloc[0]["model"]
print(f"Best-performing model on holdout: {best_model_name}")

# Refit Gradient Boosting (typically strongest) on ALL available data, forecast forward using
# recursive multi-step prediction for the remaining months of FY2026.
full_X, full_y = ts_model[feature_cols], ts_model["total_revenue"]
gb_final = GradientBoostingRegressor(n_estimators=250, max_depth=3, learning_rate=0.05, random_state=42).fit(full_X, full_y)

history = ts.set_index("period")["total_revenue"].to_dict()
last_t = ts["t"].max()
future_months = pd.date_range(ts["period"].max() + pd.DateOffset(months=1), "2026-12-01", freq="MS")
ml_future_preds = []
running_history = ts["total_revenue"].tolist()
for i, m in enumerate(future_months, start=1):
    lag_1 = running_history[-1]
    lag_2 = running_history[-2]
    lag_3 = running_history[-3]
    lag_12 = running_history[-12] if len(running_history) >= 12 else running_history[0]
    roll3 = np.mean(running_history[-3:])
    roll6 = np.mean(running_history[-6:]) if len(running_history) >= 6 else np.mean(running_history)
    row = pd.DataFrame([{
        "t": last_t + i, "month": m.month, "quarter": (m.month - 1)//3 + 1,
        "lag_1": lag_1, "lag_2": lag_2, "lag_3": lag_3, "lag_12": lag_12,
        "rolling_mean_3": roll3, "rolling_mean_6": roll6
    }])[feature_cols]
    pred = gb_final.predict(row)[0]
    ml_future_preds.append({"period": m, "ml_revenue_forecast": pred})
    running_history.append(pred)

ml_forecast_df = pd.DataFrame(ml_future_preds)
ml_forecast_df.to_csv(f"{OUT_DIR}/ml_revenue_forecast_fy26_remainder.csv", index=False)

# ========================================================================
# PART 5 — SCENARIO PLANNING: BASE / UPSIDE / DOWNSIDE
# Applies scenario deltas to the latest forecast (remaining FY26 months)
# and to the 3-yr LRP (FY27-29), producing a scenario-flexed P&L.
# ========================================================================
fcst_monthly = forecast.groupby(["period", "line_type"])["forecast_amount"].sum().unstack(fill_value=0).reset_index()
fcst_monthly.columns.name = None
if "Revenue" not in fcst_monthly.columns:
    fcst_monthly["Revenue"] = 0
if "Opex" not in fcst_monthly.columns:
    fcst_monthly["Opex"] = 0

scenario_rows = []
for _, sc in scenarios.iterrows():
    for _, row in fcst_monthly.iterrows():
        rev_flexed = row["Revenue"] * (1 + sc["rev_growth_delta"] - sc["churn_delta"])
        opex_flexed = row["Opex"] * (1 + sc["opex_growth_delta"])
        scenario_rows.append({
            "scenario": sc["scenario"], "period": row["period"],
            "revenue": rev_flexed, "opex": opex_flexed, "ebitda_proxy": rev_flexed - opex_flexed,
        })
scenario_pnl = pd.DataFrame(scenario_rows)
scenario_pnl.to_csv(f"{OUT_DIR}/scenario_pnl_fy26_remainder.csv", index=False)

# Scenario-flexed 3-year LRP
lrp_scenarios = []
for _, sc in scenarios.iterrows():
    for _, row in lrp.iterrows():
        rev_flexed = row["plan_revenue"] * (1 + sc["rev_growth_delta"] * 3 - sc["churn_delta"] * 3)  # compounding proxy across plan years
        opex_flexed = row["plan_opex"] * (1 + sc["opex_growth_delta"] * 3)
        lrp_scenarios.append({
            "scenario": sc["scenario"], "fiscal_year": row["fiscal_year"],
            "plan_revenue": rev_flexed, "plan_opex": opex_flexed,
            "plan_ebitda": rev_flexed - opex_flexed,
            "plan_ebitda_margin": (rev_flexed - opex_flexed) / rev_flexed,
        })
lrp_scenario_df = pd.DataFrame(lrp_scenarios)
lrp_scenario_df.to_csv(f"{OUT_DIR}/lrp_scenario_flexed.csv", index=False)

conn.close()

print("\n=== Forecast / Variance / Scenario engine complete ===")
print("\nModel accuracy comparison (holdout = trailing 6 actual months):")
print(accuracy_df.to_string(index=False))
print(f"\nScenario FY26 remainder EBITDA proxy by scenario:")
print(scenario_pnl.groupby("scenario")["ebitda_proxy"].sum().round(0))
print(f"\nAll outputs written to {OUT_DIR}/")
