"""
dashboard.py
────────────
THE BOARD OF DIRECTORS DASHBOARD

WHY STREAMLIT:
  Streamlit converts Python scripts into interactive web apps.
  No HTML/JS required. The dashboard reads the JSON output files
  produced by the agent pipeline and renders them visually.

WHAT THE DASHBOARD SHOWS (and WHY each panel matters):
  1. Pipeline KPIs   — proves the system ran (latency, token cost, calls)
  2. Evaluator Loop  — shows the score improvement from the feedback loop
  3. Risk Heatmap    — top-risk borrowers at a glance (for the Board)
  4. Sector exposure — concentration risk (regulatory limit = 35%)
  5. NPL / PAR chart — portfolio health trend
  6. Full memo       — the actual deliverable, readable in the app
  7. Log analysis    — token and latency breakdown per agent

HOW TO RUN:
  streamlit run dashboard.py
  (opens browser at http://localhost:8501)
"""

import json
import os
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

st.set_page_config(
    page_title="AFB Credit Portfolio Dashboard",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Custom CSS: professional dark header, clean cards
st.markdown("""
<style>
  .main-header {
    background: #1F3864;
    padding: 18px 24px;
    border-radius: 8px;
    margin-bottom: 20px;
  }
  .main-header h1 { color: white; margin: 0; font-size: 22px; }
  .main-header p  { color: #CCDDFF; margin: 4px 0 0 0; font-size: 14px; }
  .kpi-card {
    background: #F8F9FC;
    border: 1px solid #E0E6F0;
    border-radius: 8px;
    padding: 16px;
    text-align: center;
  }
  .kpi-value { font-size: 28px; font-weight: bold; color: #1F3864; }
  .kpi-label { font-size: 12px; color: #666; margin-top: 4px; }
  .alert-critical { background: #FFEBEE; border-left: 4px solid #C62828; padding: 10px 14px; border-radius: 4px; }
  .alert-watch    { background: #FFF8E1; border-left: 4px solid #F57F17; padding: 10px 14px; border-radius: 4px; }
</style>
""", unsafe_allow_html=True)


# ── Header
st.markdown("""
<div class="main-header">
  <h1>Afiland First Bank — Q4 2024 Credit Portfolio Dashboard</h1>
  <p>Multi-Agent Analysis System &nbsp;|&nbsp; Assignment 8-B &nbsp;|&nbsp; CO.EN.FAI.LLL.2026.01</p>
</div>
""", unsafe_allow_html=True)


# ── Load all output files
def load_json(path):
    if Path(path).exists():
        with open(path) as f:
            return json.load(f)
    return None


portfolio = load_json("output/portfolio_summary.json")
ratios    = load_json("output/ratios.json")
policy    = load_json("output/policy_context.json")
pipeline  = load_json("output/pipeline_results.json")
eval_data = load_json("output/eval_scores.json")


# ── Check data availability
if portfolio is None or ratios is None:
    st.warning("⚠️ No pipeline output found. Run the pipeline first:")
    st.code("python orchestrator.py", language="bash")
    st.stop()


# ══════════════════════════════════════════════════════════════
# ROW 1: PIPELINE PERFORMANCE KPIs
# ══════════════════════════════════════════════════════════════
st.subheader("Pipeline Performance")
col1, col2, col3, col4, col5 = st.columns(5)

log = pipeline.get("log_summary", {}) if pipeline else {}
phase5 = pipeline.get("phase5_evaluator", {}) if pipeline else {}

metrics = [
    (col1, str(pipeline.get("total_latency_s","—"))+"s", "Total Pipeline Latency"),
    (col2, str(log.get("total_calls","—")), "Total API Calls"),
    (col3, f"{log.get('total_tokens',0):,}", "Total Tokens Used"),
    (col4, f"{phase5.get('score_v1','—')}/10 → {phase5.get('score_v2','—')}/10", "Evaluator Score v1 → v2"),
    (col5, "+" + str(phase5.get("delta","—")), "Score Delta (Improvement Loop)"),
]

for col, val, label in metrics:
    with col:
        st.markdown(f"""
        <div class="kpi-card">
          <div class="kpi-value">{val}</div>
          <div class="kpi-label">{label}</div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# ROW 2: EVALUATOR IMPROVEMENT LOOP CHART
# ══════════════════════════════════════════════════════════════
if eval_data:
    st.subheader("Evaluator-Optimizer Loop — Score Comparison")
    col_a, col_b = st.columns([1, 1])

    with col_a:
        s1 = eval_data.get("iteration_1", {}).get("scores", {})
        s2 = eval_data.get("iteration_2", {}).get("scores", {})
        dimensions = list(s1.keys()) if s1 else []

        if dimensions:
            fig = go.Figure()
            fig.add_trace(go.Bar(
                name="Iteration 1 (original)",
                x=[d.replace("_", " ").title() for d in dimensions],
                y=[s1.get(d, 0) for d in dimensions],
                marker_color="#6B8CBF",
            ))
            fig.add_trace(go.Bar(
                name="Iteration 2 (after feedback)",
                x=[d.replace("_", " ").title() for d in dimensions],
                y=[s2.get(d, 0) for d in dimensions],
                marker_color="#1F3864",
            ))
            fig.update_layout(
                barmode="group",
                yaxis=dict(range=[0, 10], title="Score (1-10)"),
                title="Quality Scores Before and After Improvement Loop",
                height=320,
                margin=dict(t=40, b=20, l=20, r=20),
            )
            st.plotly_chart(fig, use_container_width=True)

    with col_b:
        v1_overall = eval_data.get("score_v1", 0)
        v2_overall = eval_data.get("score_v2", 0)
        fig2 = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=v2_overall,
            delta={"reference": v1_overall, "valueformat": ".1f"},
            gauge={
                "axis": {"range": [0, 10]},
                "bar":  {"color": "#1F3864"},
                "steps": [
                    {"range": [0, 5],  "color": "#FFCDD2"},
                    {"range": [5, 7],  "color": "#FFF9C4"},
                    {"range": [7, 10], "color": "#E8F5E9"},
                ],
                "threshold": {"line": {"color": "#C62828", "width": 3}, "value": 7},
            },
            title={"text": "Overall Score (v2)"},
        ))
        fig2.update_layout(height=320, margin=dict(t=40, b=20, l=20, r=20))
        st.plotly_chart(fig2, use_container_width=True)

st.markdown("---")


# ══════════════════════════════════════════════════════════════
# ROW 3: PORTFOLIO RISK OVERVIEW
# ══════════════════════════════════════════════════════════════
st.subheader("Portfolio Risk Overview")
col1, col2 = st.columns(2)

with col1:
    # ── Top-risk borrowers table
    top5 = ratios.get("top5_risk_loans", [])
    if top5:
        df_top5 = pd.DataFrame(top5)[["loan_id", "borrower_name", "dscr", "par90", "months_overdue", "exposure_xaf"]]
        df_top5.columns = ["Loan ID", "Borrower", "DSCR", "PAR90", "Months Overdue", "Exposure (XAF)"]
        df_top5["Exposure (XAF)"] = df_top5["Exposure (XAF)"].apply(lambda x: f"{x:,.0f}")

        # Color-code by DSCR
        def dscr_color(val):
            try:
                v = float(val)
                if v < 1.0:  return "background-color: #FFCDD2"
                if v < 1.25: return "background-color: #FFF9C4"
                return ""
            except: return ""

        st.markdown("**Top 5 Highest-Risk Borrowers** *(red = DSCR < 1.0 = NPL)*")
        st.dataframe(
            df_top5.style.map(dscr_color, subset=["DSCR"]),
            width="stretch",
            height=220,
        )
    else:
        st.info("No top-risk borrower data available.")

with col2:
    # ── Risk alerts
    alerts = ratios.get("alerts", [])
    if alerts:
        st.markdown("**Active Risk Alerts**")
        for alert in alerts:
            severity = alert.get("severity", "WATCH")
            css_class = "alert-critical" if severity == "CRITICAL" else "alert-watch"
            icon = "🔴" if severity == "CRITICAL" else "🟡"
            st.markdown(f"""
            <div class="{css_class}">
              {icon} <strong>{alert.get('metric','')}</strong>:
              {alert.get('value','')} (threshold: {alert.get('threshold','')}) — {severity}
            </div>
            """, unsafe_allow_html=True)
            st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
    else:
        st.success("✅ No critical alerts triggered.")

st.markdown("---")


# ══════════════════════════════════════════════════════════════
# ROW 4: SECTOR EXPOSURE + NPL RATIO
# ══════════════════════════════════════════════════════════════
st.subheader("Sector Concentration & Risk Metrics")
col1, col2 = st.columns(2)

with col1:
    sector_exposure = portfolio.get("sector_exposure", {})
    if sector_exposure:
        total_exp = sum(sector_exposure.values()) or 1
        df_sector = pd.DataFrame([
            {"Sector": k, "Exposure XAF": v, "Share %": round(100 * v / total_exp, 1)}
            for k, v in sorted(sector_exposure.items(), key=lambda x: -x[1])
        ])
        fig = px.bar(
            df_sector, x="Share %", y="Sector", orientation="h",
            color="Share %",
            color_continuous_scale=["#A8C8E8", "#1F3864"],
            title="Sector Exposure Share (limit: 35%)",
        )
        fig.add_vline(x=35, line_dash="dash", line_color="red",
                      annotation_text="35% limit", annotation_position="top right")
        fig.update_layout(height=300, margin=dict(t=40, b=20, l=20, r=20), showlegend=False)
        st.plotly_chart(fig, use_container_width=True)

with col2:
    # ── Key ratios gauge
    npl     = ratios.get("npl_ratio_pct", 0)
    par90   = ratios.get("par90_ratio_pct", 0)
    cov_br  = ratios.get("covenant_breach_rate_pct", 0)
    avg_dscr = ratios.get("avg_dscr", 0)

    try: npl = float(npl)
    except: npl = 0
    try: par90 = float(par90)
    except: par90 = 0

    metrics_df = pd.DataFrame([
        {"Metric": "NPL Ratio (%)",           "Value": npl,        "Alert Threshold": 5.0},
        {"Metric": "PAR90 Ratio (%)",          "Value": par90,      "Alert Threshold": 3.0},
        {"Metric": "Covenant Breach Rate (%)", "Value": cov_br,     "Alert Threshold": 15.0},
        {"Metric": "Avg DSCR",                 "Value": avg_dscr,   "Alert Threshold": 1.25},
    ])

    fig3 = px.bar(
        metrics_df, x="Metric", y="Value",
        color="Value",
        color_continuous_scale=["#4CAF50", "#FF5722"],
        title="Key Risk Ratios",
    )
    fig3.update_layout(height=300, margin=dict(t=40, b=20, l=20, r=20), showlegend=False)
    st.plotly_chart(fig3, use_container_width=True)

st.markdown("---")


# ══════════════════════════════════════════════════════════════
# ROW 5: LOG ANALYSIS (token and latency per agent)
# ══════════════════════════════════════════════════════════════
if pipeline and "log_summary" in pipeline:
    st.subheader("Agent Performance Log")
    log_s = pipeline["log_summary"]

    col1, col2 = st.columns(2)
    with col1:
        tokens = log_s.get("tokens_per_agent", {})
        if tokens:
            fig_t = px.pie(
                values=list(tokens.values()),
                names=list(tokens.keys()),
                title="Token Share by Agent",
                color_discrete_sequence=px.colors.sequential.Blues_r,
            )
            fig_t.update_layout(height=280, margin=dict(t=40, b=10))
            st.plotly_chart(fig_t, use_container_width=True)

    with col2:
        latency = log_s.get("latency_per_agent", {})
        if latency:
            fig_l = px.bar(
                x=list(latency.keys()),
                y=list(latency.values()),
                labels={"x": "Agent", "y": "Total Latency (s)"},
                title="Latency by Agent (seconds)",
                color=list(latency.values()),
                color_continuous_scale=["#A8C8E8", "#1F3864"],
            )
            fig_l.update_layout(height=280, margin=dict(t=40, b=20), showlegend=False)
            st.plotly_chart(fig_l, use_container_width=True)

st.markdown("---")


# ══════════════════════════════════════════════════════════════
# ROW 6: CREDIT MEMO (the actual deliverable)
# ══════════════════════════════════════════════════════════════
st.subheader("Credit Committee Report (v2 — Post Improvement Loop)")

memo_path = "output/credit_memo_v2.md"
if not Path(memo_path).exists():
    memo_path = "output/credit_memo.md"

if Path(memo_path).exists():
    with open(memo_path) as f:
        memo_text = f.read()
    with st.expander("📄 View Full Credit Memo", expanded=False):
        st.markdown(memo_text)
else:
    st.info("Credit memo not yet generated. Run orchestrator.py first.")


# ── Single-agent vs multi-agent comparison
st.markdown("---")
st.subheader("Single-Agent vs Multi-Agent Comparison")

col1, col2 = st.columns(2)
with col1:
    st.markdown("**Single-Agent Baseline**")
    if Path("output/single_agent_report.md").exists():
        with open("output/single_agent_report.md") as f:
            sa_text = f.read()
        with st.expander("View Single-Agent Report"):
            st.markdown(sa_text)
    sa_info = pipeline.get("single_agent", {}) if pipeline else {}
    st.info(f"1 API call · {sa_info.get('latency_s','—')}s · No source tags · No policy citations")

with col2:
    st.markdown("**Multi-Agent System (v2)**")
    st.info(f"{log.get('total_calls','—')} API calls · {pipeline.get('total_latency_s','—')}s · Source tags [DS][RA][PR] · Policy citations [S1.1]–[S7.1]")
    st.markdown("**Structural advantages:**")
    st.markdown("- DataScout refuses missing fields → no fabricated ratios")
    st.markdown("- PolicyRAG cites section or stays silent → no invented thresholds")
    st.markdown("- Evaluator loop improves score before delivery")
    st.markdown("- Every file is auditable independently")

st.markdown("---")
st.caption("Assignment 8-B · CO.EN.FAI.LLL.2026.01 · Multi-Agent Finance Patterns · Afiland First Bank")
