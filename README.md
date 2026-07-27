# Aurora Dynamics — Enterprise FP&A Planning & Executive Decision Intelligence Platform

A complete, runnable FP&A stack built on a synthetic SAP-style dataset for a
fictional SaaS company, "Aurora Dynamics Inc." Every figure is illustrative
(not real financial data), but the pipeline — data model, reconciliation,
forecasting, variance analysis, scenario planning, NLP, and reporting — is
built the way a real enterprise FP&A team would build it.

## What's included

| Folder / file | What it is |
|---|---|
| `data_csv/` | The synthetic dataset: SQLite DB (`aurora_fpa.db`) + all derived CSVs (GL, revenue, opex, headcount, budget, forecast, LRP, scenarios, commentary, model outputs) |
| `sql/02_reconciliation.sql` | SQL views: GL-to-fact reconciliation, data-quality checks, consolidated P&L, actual-vs-budget/forecast variance |
| `scripts/01_generate_data.py` | Generates the synthetic SAP-style dataset from scratch |
| `scripts/03_forecast_variance_scenario.py` | Driver-based models, ML vs. statistical forecast bake-off, variance tables, scenario P&Ls |
| `scripts/04_nlp_commentary.py` | NLP sentiment scoring, topic clustering, and commentary-to-variance linkage |
| `scripts/05_build_excel_workbook.py` | Builds the Excel workbook below |
| `scripts/build_cfo_deck.js` | Builds the PowerPoint deck below (pptxgenjs) |
| `Aurora_FPA_Executive_Workbook.xlsx` | Self-service Excel workbook — 9 tabs, live formulas, conditional formatting |
| `Aurora_QBR_CFO_Deck.pptx` | 10-slide CFO-ready quarterly business review deck |
| `streamlit_app/` | Interactive Streamlit dashboard (run locally — see its own README) |

## How the pieces fit together

```
01_generate_data.py  →  aurora_fpa.db + CSVs  (SAP-style GL, revenue, opex, headcount)
        ↓
02_reconciliation.sql → SQL views (reconciliation, consolidated P&L, variance)
        ↓
03_forecast_variance_scenario.py → driver models, ML forecast, variance tables, scenarios
        ↓
04_nlp_commentary.py → sentiment/topic analysis of management commentary
        ↓
05_build_excel_workbook.py  &  build_cfo_deck.js  &  streamlit_app/app.py
        →  Excel workbook, PowerPoint deck, interactive dashboard
```

Re-running `01` → `04` in order regenerates every downstream artifact from a
fresh (or re-seeded) synthetic dataset — change the `np.random.seed()` at the
top of `01_generate_data.py` for a different company trajectory.

## Key results in this run

- **Reconciliation**: GL-derived revenue ties to the source revenue fact table
  with **$0.00 variance** across all 42 months, 0 orphan GL accounts.
- **Unit economics**: ~74% gross margin, 4–10% EBITDA margin — realistic for a
  growth-stage, multi-segment SaaS business.
- **Forecast accuracy**: Linear Regression (with lag/rolling-mean/seasonality
  features) beat Random Forest, Gradient Boosting, and classical baselines on
  a 6-month holdout — 1.65% MAPE vs. 2.65–3.11% for the alternatives.
- **Q2 FY26 actuals**: $14.68M revenue (+13.7% YoY), 8.6% EBITDA margin;
  -5.2% vs. an aggressive budget, +1.4% opex favorability.
- **Scenario spread (H2 FY26)**: Downside $1.48M EBITDA proxy → Base $2.93M →
  Upside $4.08M — the business stays profitable even in the downside case.
- **3-year LRP (base case)**: revenue growing from ~$144M (FY27) to ~$201M
  (FY29), EBITDA margin expanding from ~12% to ~18%.

## Power BI note

No `.pbix` file is included (this environment can't author native Power BI
files), but every table needed is in `data_csv/` and `aurora_fpa.db`, and the
SQL views in `sql/02_reconciliation.sql` map directly onto Power Query steps
(swap `strftime` for `DATE_TRUNC`/`FORMAT`). Import the CSVs (or connect to
the SQLite file via an ODBC driver), then rebuild the same pages found in the
Streamlit app as report tabs — Executive Overview, Variance, Scenario
Planning, and LRP translate cleanly to Power BI visuals and DAX measures.
