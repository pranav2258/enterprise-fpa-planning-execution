-- ============================================================================
-- Aurora Dynamics FP&A — SQL Data Preparation & Reconciliation Layer
-- Target: SQLite (aurora_fpa.db). Portable to SQL Server / Snowflake with
-- minor date-function changes (strftime -> DATE_TRUNC / FORMAT).
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. GL -> P&L RECONCILIATION CHECK
-- Confirms every GL transaction rolls up to a valid, mapped GL account and
-- that revenue (credit) / opex (debit) totals reconcile to the source facts.
-- ----------------------------------------------------------------------------
DROP VIEW IF EXISTS vw_gl_reconciliation_check;
CREATE VIEW vw_gl_reconciliation_check AS
SELECT
    g.period,
    g.debit_credit,
    a.pnl_category,
    COUNT(*)                    AS txn_count,
    ROUND(SUM(g.amount), 2)     AS gl_total_amount
FROM fact_gl_transactions g
LEFT JOIN dim_gl_accounts a ON g.gl_account = a.gl_account
GROUP BY g.period, g.debit_credit, a.pnl_category;

-- Orphan check: any GL postings referencing an account not in the chart of accounts
DROP VIEW IF EXISTS vw_gl_orphan_accounts;
CREATE VIEW vw_gl_orphan_accounts AS
SELECT DISTINCT g.gl_account
FROM fact_gl_transactions g
LEFT JOIN dim_gl_accounts a ON g.gl_account = a.gl_account
WHERE a.gl_account IS NULL;

-- Reconciliation: GL-derived revenue vs. source revenue fact table (should tie to $0.00)
DROP VIEW IF EXISTS vw_recon_revenue_gl_vs_fact;
CREATE VIEW vw_recon_revenue_gl_vs_fact AS
WITH gl_rev AS (
    SELECT period, ROUND(SUM(amount), 2) AS gl_revenue
    FROM fact_gl_transactions
    WHERE debit_credit = 'C'
    GROUP BY period
),
fact_rev AS (
    SELECT period, ROUND(SUM(revenue), 2) AS source_revenue
    FROM fact_revenue_actuals
    GROUP BY period
)
SELECT COALESCE(g.period, f.period) AS period,
       g.gl_revenue,
       f.source_revenue,
       ROUND(COALESCE(g.gl_revenue,0) - COALESCE(f.source_revenue,0), 2) AS variance
FROM gl_rev g
FULL OUTER JOIN fact_rev f ON g.period = f.period;
-- Note: SQLite (3.39+) supports FULL OUTER JOIN. If running on an older engine,
-- replace with a UNION of LEFT JOINs.

-- ----------------------------------------------------------------------------
-- 2. CONSOLIDATED MONTHLY P&L (actuals) — the core reporting cube
-- ----------------------------------------------------------------------------
DROP VIEW IF EXISTS vw_pnl_actuals_monthly;
CREATE VIEW vw_pnl_actuals_monthly AS
SELECT
    r.period,
    strftime('%Y', r.period)                              AS fiscal_year,
    r.company_code,
    e.entity_name,
    r.profit_center,
    s.segment_name,
    'Revenue'                                              AS pnl_line,
    r.gl_account,
    ga.account_name,
    ROUND(SUM(r.revenue), 2)                               AS amount
FROM fact_revenue_actuals r
JOIN dim_entities e   ON r.company_code = e.company_code
JOIN dim_segments s   ON r.profit_center = s.profit_center
JOIN dim_gl_accounts ga ON r.gl_account = ga.gl_account
GROUP BY r.period, r.company_code, r.profit_center, r.gl_account

UNION ALL

SELECT
    o.period,
    strftime('%Y', o.period)                              AS fiscal_year,
    o.company_code,
    e.entity_name,
    NULL                                                    AS profit_center,
    cc.department                                          AS segment_name,
    ga.pnl_category                                        AS pnl_line,
    o.gl_account,
    ga.account_name,
    -ROUND(SUM(o.amount), 2)                               AS amount   -- expense as negative for P&L waterfall
FROM fact_opex_actuals o
JOIN dim_entities e      ON o.company_code = e.company_code
JOIN dim_cost_centers cc ON o.cost_center = cc.cost_center
JOIN dim_gl_accounts ga  ON o.gl_account = ga.gl_account
GROUP BY o.period, o.company_code, o.cost_center, o.gl_account;

-- ----------------------------------------------------------------------------
-- 3. ACTUAL vs BUDGET vs FORECAST VARIANCE (revenue + opex, monthly, all dims)
-- ----------------------------------------------------------------------------
DROP VIEW IF EXISTS vw_variance_actual_vs_budget;
CREATE VIEW vw_variance_actual_vs_budget AS
WITH act_rev AS (
    SELECT period, profit_center AS dim1, company_code AS dim2, gl_account,
           'Revenue' AS line_type, SUM(revenue) AS actual_amount
    FROM fact_revenue_actuals GROUP BY period, profit_center, company_code, gl_account
),
act_opex AS (
    SELECT period, cost_center AS dim1, company_code AS dim2, gl_account,
           'Opex' AS line_type, SUM(amount) AS actual_amount
    FROM fact_opex_actuals GROUP BY period, cost_center, company_code, gl_account
),
act_all AS (SELECT * FROM act_rev UNION ALL SELECT * FROM act_opex)
SELECT
    b.period, b.dim1, b.dim2, b.gl_account, b.line_type,
    b.budget_amount,
    a.actual_amount,
    ROUND(COALESCE(a.actual_amount, 0) - b.budget_amount, 2)                      AS variance_abs,
    ROUND( (COALESCE(a.actual_amount, 0) - b.budget_amount) / NULLIF(b.budget_amount,0), 4) AS variance_pct
FROM fact_budget b
LEFT JOIN act_all a
    ON b.period = a.period AND b.dim1 = a.dim1 AND b.dim2 = a.dim2
    AND b.gl_account = a.gl_account AND b.line_type = a.line_type;

DROP VIEW IF EXISTS vw_variance_actual_vs_forecast;
CREATE VIEW vw_variance_actual_vs_forecast AS
WITH act_rev AS (
    SELECT period, profit_center AS dim1, company_code AS dim2, gl_account,
           'Revenue' AS line_type, SUM(revenue) AS actual_amount
    FROM fact_revenue_actuals GROUP BY period, profit_center, company_code, gl_account
),
act_opex AS (
    SELECT period, cost_center AS dim1, company_code AS dim2, gl_account,
           'Opex' AS line_type, SUM(amount) AS actual_amount
    FROM fact_opex_actuals GROUP BY period, cost_center, company_code, gl_account
),
act_all AS (SELECT * FROM act_rev UNION ALL SELECT * FROM act_opex)
SELECT
    f.period, f.dim1, f.dim2, f.gl_account, f.line_type,
    f.forecast_amount,
    a.actual_amount,
    ROUND(COALESCE(a.actual_amount, 0) - f.forecast_amount, 2) AS variance_abs,
    ROUND( (COALESCE(a.actual_amount, 0) - f.forecast_amount) / NULLIF(f.forecast_amount,0), 4) AS variance_pct
FROM fact_forecast_latest f
LEFT JOIN act_all a
    ON f.period = a.period AND f.dim1 = a.dim1 AND f.dim2 = a.dim2
    AND f.gl_account = a.gl_account AND f.line_type = a.line_type;

-- ----------------------------------------------------------------------------
-- 4. SEGMENT / QUARTER SUMMARY FOR QBR DASHBOARD
-- ----------------------------------------------------------------------------
DROP VIEW IF EXISTS vw_qbr_segment_quarterly;
CREATE VIEW vw_qbr_segment_quarterly AS
SELECT
    c.fiscal_year,
    c.fiscal_quarter,
    s.segment_name,
    ROUND(SUM(r.revenue), 2) AS revenue
FROM fact_revenue_actuals r
JOIN dim_calendar c ON r.period = c.period
JOIN dim_segments s ON r.profit_center = s.profit_center
WHERE c.is_actual = 1
GROUP BY c.fiscal_year, c.fiscal_quarter, s.segment_name;

-- ----------------------------------------------------------------------------
-- 5. DATA QUALITY CHECKS (row counts, null checks, negative-revenue flags)
-- ----------------------------------------------------------------------------
DROP VIEW IF EXISTS vw_dq_negative_revenue_flags;
CREATE VIEW vw_dq_negative_revenue_flags AS
SELECT * FROM fact_revenue_actuals WHERE revenue < 0;

DROP VIEW IF EXISTS vw_dq_null_dimension_check;
CREATE VIEW vw_dq_null_dimension_check AS
SELECT 'fact_opex_actuals' AS table_name, COUNT(*) AS null_cost_center_rows
FROM fact_opex_actuals WHERE cost_center IS NULL
UNION ALL
SELECT 'fact_revenue_actuals', COUNT(*) FROM fact_revenue_actuals WHERE profit_center IS NULL;
