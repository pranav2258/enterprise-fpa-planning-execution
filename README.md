# Enterprise FP&A Planning & Executive Decision Intelligence Platform

A full-stack FP&A analytics platform built on a synthetic SAP-style dataset for
a fictional SaaS company, **Aurora Dynamics Inc.** It covers the complete FP&A
lifecycle — data generation and reconciliation, monthly forecasting and annual
budgeting, a three-year long-range plan, variance analysis, driver-based
modeling, scenario planning, machine-learning forecasting, NLP on management
commentary, and executive reporting — end to end, in one repo.

**Live app:** _add your Streamlit Community Cloud URL here once deployed_
**Stack:** SAP-style synthetic data · SQL · Python · pandas · scikit-learn · Streamlit · Excel (openpyxl) · PowerPoint (pptxgenjs) · NLP (TF-IDF + KMeans)

---

## What's inside

| Capability | Where |
|---|---|
| Synthetic SAP-style GL, revenue, opex, headcount, and operational data | `data/`, `01_generate_data.py` |
| SQL reconciliation, consolidated P&L, and variance views | `02_reconciliation.sql` |
| Monthly forecast, annual budget, 3-year long-range plan | `03_forecast_variance_scenario.py` |
| Actual-vs-budget and actual-vs-forecast variance analysis | `03_forecast_variance_scenario.py`, Streamlit app |
| Driver-based revenue, profitability, and expense models | `03_forecast_variance_scenario.py`, Streamlit app (what-if sliders) |
| Base / Upside / Downside scenario planning | `03_forecast_variance_scenario.py`, Streamlit app |
| Quarterly business review dashboard & CFO-ready deck | `Aurora_QBR_CFO_Deck.pptx`, `build_cfo_deck.js` |
| ML forecast model with accuracy comparison (vs. statistical baselines) | `03_forecast_variance_scenario.py`, Streamlit app |
| Automated SQL/Python data prep and reconciliation | `02_reconciliation.sql`, `01_generate_data.py` |
| NLP analysis of unstructured management commentary | `04_nlp_commentary.py` |
| Interactive dashboard & self-service reporting | `app.py` (Streamlit), `Aurora_FPA_Executive_Workbook.xlsx` |

---

## Quick start

```bash
git clone https://github.com/pranav2258/enterprise-fpa-planning-execution.git
cd enterprise-fpa-planning-execution

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\Activate.ps1

pip install -r requirements.txt
streamlit run app.py
```

The app opens at `http://localhost:8501`. All data ships in the `data/`
folder (a SQLite database + derived CSVs), so no external database
connection is required to run it.

---

## Dashboard pages

The Streamlit app (`app.py`) has 8 pages, navigable from the sidebar:

1. **Executive Overview** — revenue & EBITDA trend, segment mix, margin trend
2. **Actuals & Variance** — actual vs. budget and actual vs. forecast, filterable by line type
3. **Driver-Based Model** — customers × ARPU revenue model, with live ARPU/churn what-if sliders
4. **Forecasting (ML vs Statistical)** — Linear Regression, Random Forest, and Gradient Boosting benchmarked against Naive, Moving Average, and Linear Trend baselines on a 6-month holdout
5. **Scenario Planning** — Base / Upside / Downside cases applied to the latest rolling forecast
6. **3-Year LRP** — FY2027–FY2029 long-range plan, scenario-flexed
7. **Management Commentary (NLP)** — lexicon-based sentiment scoring, TF-IDF + K-Means topic clusters, and a sentiment-vs-variance linkage analysis
8. **Data Explorer** — raw fact/dimension tables with CSV download

---

## Architecture

```
01_generate_data.py
   → aurora_fpa.db + CSVs (SAP-style GL, revenue, opex, headcount, budget)
        ↓
02_reconciliation.sql
   → SQL views: GL-to-fact reconciliation, consolidated P&L, variance
        ↓
03_forecast_variance_scenario.py
   → driver models, ML forecast bake-off, variance tables, scenario P&Ls
        ↓
04_nlp_commentary.py
   → sentiment scoring, topic clustering on management commentary
        ↓
05_build_excel_workbook.py   build_cfo_deck.js   app.py
   → Excel workbook          → CFO PPTX deck     → Streamlit dashboard
```

Re-running the scripts in order regenerates every downstream artifact from a
fresh (or re-seeded) synthetic dataset — change `np.random.seed()` at the top
of `01_generate_data.py` for a different company trajectory.

---

## Key results in the shipped dataset

- **Reconciliation**: GL-derived revenue ties to the source revenue fact table
  with **$0.00 variance** across all 42 modeled months, 0 orphan GL accounts.
- **Unit economics**: ~74% gross margin, 4–10% EBITDA margin — realistic for a
  growth-stage, multi-segment SaaS business.
- **Forecast accuracy**: Linear Regression (with lag/rolling-mean/seasonality
  features) beat Random Forest, Gradient Boosting, and classical baselines on
  a genuine 6-month actuals holdout — **0.92% MAPE** vs. 1.6–5.1% for the
  alternatives.
- **Q2 FY26 actuals**: $14.68M revenue (+13.7% YoY), 8.6% EBITDA margin;
  -5.2% vs. an aggressive budget, +1.4% opex favorability.
- **Scenario spread (H2 FY26)**: Downside $1.48M EBITDA proxy → Base $2.93M
  → Upside $4.08M — the business stays profitable even in the downside case.
- **3-year LRP (base case)**: revenue growing from ~$144M (FY27) to ~$201M
  (FY29), EBITDA margin expanding from ~12% to ~18%.

All figures are synthetic and illustrative — not real financial data.

---

## Repo structure

```
├── app.py                              # Streamlit dashboard
├── requirements.txt                    # streamlit, pandas, numpy, plotly
├── data/                                # SQLite DB + derived CSVs (self-contained)
│   └── aurora_fpa.db
├── 01_generate_data.py                 # synthetic SAP-style data generator
├── 02_reconciliation.sql               # SQL reconciliation & variance views
├── 03_forecast_variance_scenario.py    # forecasting, ML, variance, scenarios
├── 04_nlp_commentary.py                # NLP on management commentary
├── 05_build_excel_workbook.py          # builds the Excel workbook
├── build_cfo_deck.js                   # builds the CFO PowerPoint deck (pptxgenjs)
├── Aurora_FPA_Executive_Workbook.xlsx  # self-service Excel workbook (live formulas)
└── Aurora_QBR_CFO_Deck.pptx            # CFO-ready quarterly business review deck
```

---

## Regenerating the data or extending the model

Each pipeline stage is a standalone script — run them in order to rebuild
everything from scratch:

```bash
python 01_generate_data.py                    # regenerate the synthetic dataset
python 03_forecast_variance_scenario.py       # rebuild forecasts, variance, scenarios
python 04_nlp_commentary.py                   # rescore commentary sentiment/topics
python 05_build_excel_workbook.py             # rebuild the Excel workbook
node build_cfo_deck.js                        # rebuild the CFO deck (requires pptxgenjs)
```

`02_reconciliation.sql` runs against `data/aurora_fpa.db` in any SQLite
client (or via `sqlite3` / Python's `sqlite3` module) to refresh the
reconciliation and variance views after regenerating data.

---

## Power BI note

No native `.pbix` is included, but every table needed is in `data/` (CSV and
SQLite), and the views in `02_reconciliation.sql` map directly onto Power
Query steps (swap `strftime` for `DATE_TRUNC`/`FORMAT`). Import the CSVs (or
connect to the SQLite file via an ODBC driver) and rebuild the same pages
found in the Streamlit app as report tabs.

---

## Tech stack

- **Data & pipeline**: Python, pandas, NumPy, SQLite, SQL
- **Forecasting & ML**: scikit-learn (Linear Regression, Random Forest, Gradient Boosting)
- **NLP**: scikit-learn TF-IDF + K-Means, custom lexicon-based sentiment scoring
- **Dashboard**: Streamlit, Plotly
- **Reporting**: openpyxl (Excel), pptxgenjs (PowerPoint)

## License

This project uses entirely synthetic data for illustrative purposes. Adapt
and reuse freely.
