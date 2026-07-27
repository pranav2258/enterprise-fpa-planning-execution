const pptxgen = require("pptxgenjs");

// ---------- Palette: "Midnight Executive" ----------
const NAVY = "1E2761";
const ICE = "CADCFC";
const WHITE = "FFFFFF";
const SLATE = "44506B";
const GREEN = "1E8A5F";
const RED = "C0392B";
const GOLD = "D4A94C";
const LIGHTGRAY = "F4F5F8";
const TEXTDARK = "22273A";

function newPres() {
  const p = new pptxgen();
  p.layout = "LAYOUT_WIDE"; // 13.3 x 7.5
  return p;
}

const pres = newPres();

// =====================================================================
// SLIDE 1 — TITLE
// =====================================================================
let s = pres.addSlide();
s.background = { color: NAVY };
s.addText("AURORA DYNAMICS", { x: 0.7, y: 2.55, w: 11.9, h: 0.6, fontFace: "Arial", fontSize: 16, color: ICE, charSpacing: 3, bold: true });
s.addText("Q2 FY2026 Business Review", { x: 0.7, y: 3.05, w: 11.9, h: 1.0, fontFace: "Cambria", fontSize: 40, color: WHITE, bold: true });
s.addText("Quarter ended June 30, 2026  ·  Prepared for the Executive Leadership Team & Board", { x: 0.7, y: 4.0, w: 11.9, h: 0.5, fontFace: "Arial", fontSize: 14, color: ICE });
s.addShape(pres.ShapeType.ellipse, { x: 10.6, y: 0.6, w: 2.4, h: 2.4, fill: { color: "273580" }, line: { type: "none" } });
s.addShape(pres.ShapeType.ellipse, { x: 11.4, y: 1.3, w: 1.2, h: 1.2, fill: { color: GOLD, transparency: 15 }, line: { type: "none" } });
s.addText("CONFIDENTIAL — INTERNAL FINANCE USE", { x: 0.7, y: 6.9, w: 8, h: 0.3, fontFace: "Arial", fontSize: 9, color: "8E9BC7" });

// =====================================================================
// SLIDE 2 — EXECUTIVE SUMMARY (stat callouts)
// =====================================================================
s = pres.addSlide();
s.background = { color: WHITE };
s.addText("Executive Summary", { x: 0.6, y: 0.4, w: 8, h: 0.6, fontFace: "Cambria", fontSize: 28, bold: true, color: NAVY });
s.addText("Revenue grew 13.7% YoY; disciplined opex management offset a revenue miss vs. an aggressive budget", { x: 0.6, y: 0.95, w: 11, h: 0.4, fontFace: "Arial", fontSize: 13, color: SLATE, italic: true });

const stats = [
  { label: "Q2 FY26 Revenue", value: "$14.68M", sub: "+13.7% YoY", subColor: GREEN },
  { label: "Q2 FY26 EBITDA Margin", value: "8.6%", sub: "vs. 9.1% PY", subColor: RED },
  { label: "Revenue vs. Budget", value: "-5.2%", sub: "-$0.81M miss", subColor: RED },
  { label: "Opex vs. Budget", value: "-1.4%", sub: "$0.19M favorable", subColor: GREEN },
];
const cardW = 2.78, gap = 0.28, startX = 0.6, y0 = 1.65;
stats.forEach((st, i) => {
  const x = startX + i * (cardW + gap);
  s.addShape(pres.ShapeType.roundRect, { x, y: y0, w: cardW, h: 1.9, rectRadius: 0.08, fill: { color: LIGHTGRAY }, line: { type: "none" }, shadow: { type: "outer", color: "888888", opacity: 0.25, blur: 6, offset: 2, angle: 90 } });
  s.addText(st.label, { x: x + 0.18, y: y0 + 0.18, w: cardW - 0.36, h: 0.5, fontFace: "Arial", fontSize: 11.5, color: SLATE, bold: true });
  s.addText(st.value, { x: x + 0.18, y: y0 + 0.6, w: cardW - 0.36, h: 0.75, fontFace: "Cambria", fontSize: 32, color: NAVY, bold: true });
  s.addText(st.sub, { x: x + 0.18, y: y0 + 1.35, w: cardW - 0.36, h: 0.4, fontFace: "Arial", fontSize: 12, color: st.subColor, bold: true });
});

s.addText("Key takeaways", { x: 0.6, y: 3.85, w: 6, h: 0.4, fontFace: "Arial", fontSize: 15, bold: true, color: NAVY });
const takeaways = [
  "Cloud Platform and Data Analytics subscription segments remain the primary growth engines, together contributing ~75% of Q2 revenue.",
  "Revenue underperformed an optimistic FY26 budget set last November; underlying growth trajectory remains healthy at double digits YoY.",
  "Gross margin held steady at ~75%; opex discipline in Sales & Marketing partially offset softer new-logo bookings.",
  "H2 FY26 rolling forecast and three scenario cases (Base / Upside / Downside) are presented later in this deck for planning purposes.",
];
s.addText(takeaways.map(t => ({ text: t, options: { bullet: { code: "25AA" }, color: TEXTDARK, breakLine: true, paraSpaceAfter: 10 } })),
  { x: 0.6, y: 4.25, w: 12.1, h: 2.6, fontFace: "Arial", fontSize: 13.5, valign: "top" });

// =====================================================================
// SLIDE 3 — REVENUE & EBITDA TREND (native line/bar combo chart)
// =====================================================================
s = pres.addSlide();
s.background = { color: WHITE };
s.addText("Revenue & EBITDA Trend — FY2023 to Q2 FY2026", { x: 0.6, y: 0.4, w: 11.5, h: 0.6, fontFace: "Cambria", fontSize: 24, bold: true, color: NAVY });

const qLabels = ["Q1'23","Q2'23","Q3'23","Q4'23","Q1'24","Q2'24","Q3'24","Q4'24","Q1'25","Q2'25","Q3'25","Q4'25","Q1'26","Q2'26"];
const revData = [8156629,8649991,9075121,9732533,10268392,10864822,11227663,11951862,12479170,12906922,13371320,13778713,14186856,14677009];
const ebitdaData = [-311169,-22247,-49655,473112,808372,844709,871994,1354995,1433401,1174189,1362956,1318050,1261409,1257247];

s.addChart(
  [
    { type: pres.ChartType.bar, data: [{ name: "Revenue ($)", labels: qLabels, values: revData }],
      options: { chartColors: [NAVY] } },
    { type: pres.ChartType.line, data: [{ name: "EBITDA ($)", labels: qLabels, values: ebitdaData }],
      options: { secondaryValAxis: true, secondaryCatAxis: true, chartColors: [GOLD] } },
  ],
  {
    x: 0.5, y: 1.15, w: 12.3, h: 5.7,
    barDir: "col",
    showTitle: true, title: "Quarterly Revenue (bars) vs. EBITDA (line)", titleFontSize: 13, titleColor: SLATE,
    showLegend: true, legendPos: "b", legendFontSize: 11,
    showValue: false,
    catAxisLabelColor: SLATE, catAxisLabelFontSize: 9,
    valAxisLabelColor: SLATE, valAxisLabelFontSize: 9, valAxisTitle: "Revenue ($)", showValAxisTitle: true,
    valGridLine: { color: "E5E7EB", size: 0.75 }, catGridLine: { style: "none" },
    valAxes: [
      { showValAxisTitle: true, valAxisTitle: "Revenue ($)", valAxisLabelFontSize: 9 },
      { showValAxisTitle: true, valAxisTitle: "EBITDA ($)", valAxisLabelFontSize: 9, valGridLine: { style: "none" } },
    ],
    catAxes: [
      { catAxisLabelFontSize: 9 },
      { catAxisHidden: true },
    ],
  }
);
s.addText("Source: Consolidated monthly P&L (synthetic dataset), rolled up to fiscal quarter.", { x: 0.6, y: 6.95, w: 10, h: 0.3, fontFace: "Arial", fontSize: 9, color: "999999", italic: true });

// =====================================================================
// SLIDE 4 — SEGMENT REVENUE MIX (Q2 FY26) — pie/donut
// =====================================================================
s = pres.addSlide();
s.background = { color: WHITE };
s.addText("Q2 FY26 Revenue by Segment", { x: 0.6, y: 0.4, w: 8, h: 0.6, fontFace: "Cambria", fontSize: 24, bold: true, color: NAVY });
s.addText("Subscription businesses (Cloud Platform + Data Analytics) drive ~75% of revenue", { x: 0.6, y: 0.95, w: 10, h: 0.4, fontFace: "Arial", fontSize: 13, color: SLATE, italic: true });

const segLabels = ["Cloud Platform", "Data Analytics", "Hardware & IoT", "Professional Svcs"];
const segValues = [6441886, 4598822, 2322056, 1314245];
s.addChart(pres.ChartType.doughnut,
  [{ name: "Revenue", labels: segLabels, values: segValues }],
  {
    x: 0.6, y: 1.5, w: 6.2, h: 5.3,
    chartColors: [NAVY, "3A56B4", GOLD, "9AA6C4"],
    showLegend: true, legendPos: "b", legendFontSize: 11,
    showValue: true, dataLabelFormatCode: "$#,##0,\"K\"", dataLabelColor: WHITE, dataLabelFontSize: 11,
    showTitle: false, holeSize: 55,
  }
);
const segRows = [
  ["Segment", "Q2 Revenue", "% of Total"],
  ["Cloud Platform", "$6.44M", "43.9%"],
  ["Data Analytics", "$4.60M", "31.3%"],
  ["Hardware & IoT", "$2.32M", "15.8%"],
  ["Professional Svcs", "$1.31M", "9.0%"],
];
s.addTable(segRows, {
  x: 7.2, y: 1.7, w: 5.5, h: 3.0,
  fontFace: "Arial", fontSize: 12.5, color: TEXTDARK,
  border: { type: "solid", color: "E5E7EB", pt: 0.75 },
  fill: { color: WHITE },
  autoPage: false,
  rowH: 0.5,
});
s.getObjects && null;
s.addText("Cloud Platform's enterprise motion continues to outperform, with services attach rate steady at ~11% of subscription revenue.",
  { x: 7.2, y: 5.0, w: 5.5, h: 1.5, fontFace: "Arial", fontSize: 12.5, color: TEXTDARK, valign: "top" });

// =====================================================================
// SLIDE 5 — ACTUAL vs BUDGET (Q2 FY26)
// =====================================================================
s = pres.addSlide();
s.background = { color: WHITE };
s.addText("Actual vs. Budget — Q2 FY2026", { x: 0.6, y: 0.4, w: 9, h: 0.6, fontFace: "Cambria", fontSize: 24, bold: true, color: NAVY });
s.addText("Revenue missed an aggressive budget; opex came in under plan", { x: 0.6, y: 0.95, w: 10, h: 0.4, fontFace: "Arial", fontSize: 13, color: SLATE, italic: true });

s.addChart(pres.ChartType.bar,
  [
    { name: "Budget", labels: ["Revenue", "Opex"], values: [15488306, 13609969] },
    { name: "Actual", labels: ["Revenue", "Opex"], values: [14677009, 13419762] },
  ],
  {
    x: 0.6, y: 1.55, w: 6.4, h: 4.9,
    barDir: "col", barGrouping: "clustered",
    chartColors: [SLATE, NAVY],
    showTitle: true, title: "Budget vs. Actual ($)", titleFontSize: 13, titleColor: SLATE,
    showLegend: true, legendPos: "b", legendFontSize: 11,
    showValue: true, dataLabelFormatCode: "$#,##0,,\"M\"", dataLabelFontSize: 10, dataLabelColor: TEXTDARK, dataLabelPosition: "outEnd",
    catAxisLabelColor: SLATE, valAxisLabelColor: SLATE, valAxisLabelFontSize: 9,
    valGridLine: { color: "E5E7EB", size: 0.75 }, catGridLine: { style: "none" },
  }
);

const varRows = [
  ["Line", "Budget", "Actual", "Variance $", "Variance %"],
  ["Revenue", "$15.49M", "$14.68M", "($0.81M)", "-5.2%"],
  ["Opex", "$13.61M", "$13.42M", "$0.19M", "-1.4%"],
];
s.addTable(varRows, {
  x: 7.3, y: 1.7, w: 5.4, h: 1.6,
  fontFace: "Arial", fontSize: 12.5, color: TEXTDARK,
  border: { type: "solid", color: "E5E7EB", pt: 0.75 },
  fill: { color: LIGHTGRAY },
  rowH: 0.5,
});
s.addText([
  { text: "Interpretation", options: { bold: true, color: NAVY, breakLine: true, fontSize: 14, paraSpaceAfter: 8 } },
  { text: "The revenue shortfall stems primarily from softer net-new logo bookings in the SMB segment and lengthening enterprise sales cycles amid macro budget scrutiny — not from pricing or churn deterioration. Opex favorability reflects delayed discretionary marketing spend and hiring-plan timing, not a structural cost reduction.", options: { color: TEXTDARK, fontSize: 12.5 } },
], { x: 7.3, y: 3.5, w: 5.4, h: 3.2, fontFace: "Arial", valign: "top" });

// =====================================================================
// SLIDE 6 — ROLLING FORECAST & ML MODEL ACCURACY
// =====================================================================
s = pres.addSlide();
s.background = { color: WHITE };
s.addText("Forecast Model Accuracy Comparison", { x: 0.6, y: 0.4, w: 10, h: 0.6, fontFace: "Cambria", fontSize: 24, bold: true, color: NAVY });
s.addText("Statistical and machine-learning models evaluated on a 6-month holdout of trailing actuals", { x: 0.6, y: 0.95, w: 11, h: 0.4, fontFace: "Arial", fontSize: 13, color: SLATE, italic: true });

const modelNames = ["Linear Regression", "Linear Trend", "Naive", "Gradient Boosting", "Moving Avg (3mo)", "Random Forest"];
const mapeVals = [1.65, 2.65, 2.66, 2.67, 2.96, 3.11];
s.addChart(pres.ChartType.bar,
  [{ name: "MAPE %", labels: modelNames, values: mapeVals }],
  {
    x: 0.6, y: 1.55, w: 7.3, h: 4.9,
    barDir: "bar",
    chartColors: [NAVY],
    showTitle: true, title: "Mean Absolute % Error (lower = better)", titleFontSize: 12, titleColor: SLATE,
    showLegend: false,
    showValue: true, dataLabelFormatCode: '0.00"%"', dataLabelFontSize: 10, dataLabelColor: TEXTDARK, dataLabelPosition: "outEnd",
    catAxisLabelColor: SLATE, catAxisLabelFontSize: 10.5,
    valAxisLabelColor: SLATE, valAxisLabelFontSize: 9,
    valGridLine: { color: "E5E7EB", size: 0.75 }, catGridLine: { style: "none" },
  }
);
s.addText([
  { text: "Methodology", options: { bold: true, color: NAVY, breakLine: true, fontSize: 14, paraSpaceAfter: 8 } },
  { text: "Feature-engineered regression models (lags, rolling means, seasonality) were trained on FY23–FY25 monthly revenue and tested against the trailing six actual months.", options: { breakLine: true, paraSpaceAfter: 10 } },
  { text: "Linear Regression with engineered features achieved the lowest error (1.65% MAPE), modestly outperforming tree-based ensembles on this relatively smooth, trend-dominated revenue series.", options: { breakLine: true, paraSpaceAfter: 10 } },
  { text: "The winning specification has been used to project the H2 FY26 revenue path shown in the appendix, supplementing the driver-based FP&A forecast.", options: {} },
], { x: 8.2, y: 1.7, w: 4.5, h: 4.9, fontFace: "Arial", fontSize: 12.5, color: TEXTDARK, valign: "top" });

// =====================================================================
// SLIDE 7 — SCENARIO PLANNING (Base / Upside / Downside)
// =====================================================================
s = pres.addSlide();
s.background = { color: WHITE };
s.addText("H2 FY2026 Scenario Planning", { x: 0.6, y: 0.4, w: 9, h: 0.6, fontFace: "Cambria", fontSize: 24, bold: true, color: NAVY });
s.addText("Base, Upside, and Downside cases applied to the latest rolling forecast", { x: 0.6, y: 0.95, w: 10, h: 0.4, fontFace: "Arial", fontSize: 13, color: SLATE, italic: true });

s.addChart(pres.ChartType.bar,
  [
    { name: "Revenue ($M)", labels: ["Downside", "Base", "Upside"], values: [28.78, 30.78, 32.35] },
    { name: "EBITDA proxy ($M)", labels: ["Downside", "Base", "Upside"], values: [1.48, 2.93, 4.08] },
  ],
  {
    x: 0.6, y: 1.55, w: 7.3, h: 4.9,
    barDir: "col", barGrouping: "clustered",
    chartColors: [SLATE, GOLD],
    showTitle: true, title: "H2 FY26 Revenue & EBITDA Proxy by Scenario ($M)", titleFontSize: 12, titleColor: SLATE,
    showLegend: true, legendPos: "b", legendFontSize: 11,
    showValue: true, dataLabelFormatCode: '$0.0"M"', dataLabelFontSize: 10, dataLabelColor: TEXTDARK, dataLabelPosition: "outEnd",
    catAxisLabelColor: SLATE, valAxisLabelColor: SLATE, valAxisLabelFontSize: 9,
    valGridLine: { color: "E5E7EB", size: 0.75 }, catGridLine: { style: "none" },
  }
);
const scenRows = [
  ["Scenario", "Key driver assumption", "H2 EBITDA proxy"],
  ["Upside", "+4.5pp rev growth, -0.6pp churn, opex flexes +1.5pp", "$4.08M"],
  ["Base", "Latest board-approved trajectory", "$2.93M"],
  ["Downside", "-5.5pp rev growth, +1.0pp churn, opex cut -2.0pp", "$1.48M"],
];
s.addTable(scenRows, {
  x: 8.2, y: 1.7, w: 4.5, h: 2.4,
  fontFace: "Arial", fontSize: 11, color: TEXTDARK,
  border: { type: "solid", color: "E5E7EB", pt: 0.75 },
  fill: { color: LIGHTGRAY },
  rowH: 0.6, valign: "middle",
});
s.addText("The Downside case still generates positive EBITDA, reflecting the flexibility built into discretionary opex (marketing programs, T&E, contractor spend).",
  { x: 8.2, y: 4.4, w: 4.5, h: 2.2, fontFace: "Arial", fontSize: 12, color: TEXTDARK, italic: true, valign: "top" });

// =====================================================================
// SLIDE 8 — 3-YEAR LONG-RANGE PLAN
// =====================================================================
s = pres.addSlide();
s.background = { color: WHITE };
s.addText("Three-Year Long-Range Plan (FY2027–FY2029)", { x: 0.6, y: 0.4, w: 10.5, h: 0.6, fontFace: "Cambria", fontSize: 24, bold: true, color: NAVY });
s.addText("Base case: revenue CAGR ~19%, EBITDA margin expanding from 12% to 18%", { x: 0.6, y: 0.95, w: 10.5, h: 0.4, fontFace: "Arial", fontSize: 13, color: SLATE, italic: true });

s.addChart(
  [
    { type: pres.ChartType.bar, data: [
        { name: "Plan Revenue ($M)", labels: ["FY27", "FY28", "FY29"], values: [144.1, 171.5, 200.7] },
        { name: "Plan Opex ($M)", labels: ["FY27", "FY28", "FY29"], values: [127.2, 145.0, 163.8] },
      ], options: { chartColors: [NAVY, SLATE] } },
    { type: pres.ChartType.line, data: [
        { name: "EBITDA Margin %", labels: ["FY27", "FY28", "FY29"], values: [11.8, 15.5, 18.4] },
      ], options: { secondaryValAxis: true, secondaryCatAxis: true, chartColors: [GOLD] } },
  ],
  {
    x: 0.6, y: 1.55, w: 12.1, h: 5.3,
    barDir: "col", barGrouping: "clustered",
    chartColors: [NAVY, SLATE, GOLD],
    showTitle: false,
    showLegend: true, legendPos: "b", legendFontSize: 11,
    showValue: false,
    catAxisLabelColor: SLATE, valAxisLabelColor: SLATE, valAxisLabelFontSize: 9,
    valAxisTitle: "$ Millions", showValAxisTitle: true,
    valGridLine: { color: "E5E7EB", size: 0.75 }, catGridLine: { style: "none" },
    valAxes: [
      { showValAxisTitle: true, valAxisTitle: "$ Millions", valAxisLabelFontSize: 9 },
      { showValAxisTitle: true, valAxisTitle: "EBITDA Margin %", valAxisLabelFontSize: 9, valGridLine: { style: "none" } },
    ],
    catAxes: [
      { catAxisLabelFontSize: 10 },
      { catAxisHidden: true },
    ],
  }
);

// =====================================================================
// SLIDE 9 — MANAGEMENT COMMENTARY (NLP THEMES)
// =====================================================================
s = pres.addSlide();
s.background = { color: WHITE };
s.addText("Management Commentary — NLP-Derived Themes", { x: 0.6, y: 0.4, w: 11, h: 0.6, fontFace: "Cambria", fontSize: 24, bold: true, color: NAVY });
s.addText("Sentiment scoring and topic clustering across 70 quarterly department narratives, FY23–FY26", { x: 0.6, y: 0.95, w: 11.5, h: 0.4, fontFace: "Arial", fontSize: 13, color: SLATE, italic: true });

const themes = [
  { title: "Growth & Expansion", tone: "Positive", detail: "Headcount growth, customer/subscription growth, and new-market expansion themes dominate ~35% of positive commentary." },
  { title: "Delivery Execution", tone: "Positive", detail: "Process and cycle-time improvements (close cycle, ticket resolution, onboarding) recur across G&A and Customer Success." },
  { title: "Cost Pressure", tone: "Negative", detail: "Unplanned hosting capacity, facilities expansion, and legal/professional fees are the leading sources of negative-tone commentary." },
  { title: "Talent & Staffing", tone: "Neutral", detail: "Routine headcount and staffing-increase language, largely neutral in tone and plan-consistent." },
];
const toneColor = { Positive: GREEN, Negative: RED, Neutral: SLATE };
const tw = 2.9, tgap = 0.25, tx0 = 0.6, ty0 = 1.55;
themes.forEach((th, i) => {
  const x = tx0 + i * (tw + tgap);
  s.addShape(pres.ShapeType.roundRect, { x, y: ty0, w: tw, h: 3.4, rectRadius: 0.08, fill: { color: LIGHTGRAY }, line: { type: "none" } });
  s.addShape(pres.ShapeType.roundRect, { x: x + 0.18, y: ty0 + 0.18, w: 1.5, h: 0.32, rectRadius: 0.16, fill: { color: toneColor[th.tone] }, line: { type: "none" } });
  s.addText(th.tone, { x: x + 0.18, y: ty0 + 0.18, w: 1.5, h: 0.32, fontFace: "Arial", fontSize: 10, bold: true, color: WHITE, align: "center", valign: "middle" });
  s.addText(th.title, { x: x + 0.18, y: ty0 + 0.62, w: tw - 0.36, h: 0.6, fontFace: "Arial", fontSize: 14.5, bold: true, color: NAVY });
  s.addText(th.detail, { x: x + 0.18, y: ty0 + 1.25, w: tw - 0.36, h: 2.0, fontFace: "Arial", fontSize: 11, color: TEXTDARK, valign: "top" });
});
s.addText("Methodology: lexicon-based sentiment scoring (custom finance/ops vocabulary) + TF-IDF vectorization with K-Means topic clustering (scikit-learn), run against synthetic quarterly management commentary.",
  { x: 0.6, y: 5.25, w: 12, h: 0.5, fontFace: "Arial", fontSize: 10, color: "999999", italic: true });
s.addText("Correlation observed between quarterly commentary sentiment and opex variance %: -0.15, directionally consistent with negative-tone commentary accompanying cost overruns.",
  { x: 0.6, y: 5.75, w: 12, h: 0.6, fontFace: "Arial", fontSize: 12, color: TEXTDARK, italic: false, bold: false });

// =====================================================================
// SLIDE 10 — CLOSING / NEXT STEPS
// =====================================================================
s = pres.addSlide();
s.background = { color: NAVY };
s.addText("Next Steps", { x: 0.7, y: 0.7, w: 8, h: 0.7, fontFace: "Cambria", fontSize: 30, bold: true, color: WHITE });
const nextSteps = [
  "Reforecast FY26 revenue to reflect Q2 actuals and updated H2 pipeline coverage; present to Board in August.",
  "Launch SMB save-desk motion to address early churn signal identified in Q2 commentary and driver-model churn rate.",
  "Tighten H2 discretionary opex approval workflow to preserve the favorable spend variance without impacting delivery.",
  "Extend the ML forecasting pipeline to segment-level revenue for FY27 annual budget cycle kickoff in Q4.",
];
s.addText(nextSteps.map(t => ({ text: t, options: { bullet: { code: "25B8" }, color: ICE, breakLine: true, paraSpaceAfter: 14 } })),
  { x: 0.7, y: 1.7, w: 11.5, h: 3.5, fontFace: "Arial", fontSize: 16, valign: "top" });
s.addText("Prepared by FP&A  ·  Aurora Dynamics Inc.  ·  Confidential", { x: 0.7, y: 6.9, w: 8, h: 0.3, fontFace: "Arial", fontSize: 9, color: "8E9BC7" });

pres.writeFile({ fileName: "/home/claude/fpa_project/outputs/Aurora_QBR_CFO_Deck.pptx" }).then(() => {
  console.log("Deck written.");
});
