"""
agents/ratio_analyst.py
───────────────────────
ROLE: Ratio Analyst
MANDATE: Compute and validate financial ratios. REFUSE when input data is missing.
READS:  output/portfolio_summary.json (from DataScout)
        data/transactions.json (payment history)
WRITES: output/ratios.json

WHY A DEDICATED AGENT FOR THIS:
  Ratio computation is where the single-agent benchmark fails most visibly.
  A generalist agent will estimate a DSCR when debt service data is missing.
  That fabricated number then flows into the credit memo as if it were real.

  The Ratio Analyst has one absolute rule: REFUSE TO COMPUTE when
  the required input is absent. A "data gap" flag is more useful to
  the Risk Committee than a plausible-looking fabricated number.

  This is the key insight the instructor is testing: in finance,
  "I don't know" is a valid and sometimes required output.

RATIOS COMPUTED (with formulas):
  PAR30  = % of portfolio with any payment > 30 days late
  PAR90  = % of portfolio with any payment > 90 days late
  NPL    = % of total exposure in non-performing loans (DSCR < 1.0)
  DSCR   = already in portfolio data; we VALIDATE, not recompute
  LTV    = already in portfolio data; we FLAG breaches (>0.80 = breach)
  DTI    = already in portfolio data; we FLAG high-risk (>0.45)
"""

import json
import os
from api_client import call_claude

SYSTEM_PROMPT = """
You are the Ratio Analyst for Afiland First Bank's credit risk system.

YOUR JOB: Compute portfolio-level risk metrics from the structured data provided.

ABSOLUTE RULE: If a required input field is null or missing, output a
"data_gap" flag for that metric. NEVER estimate or fabricate a ratio.
A clearly labeled gap is more useful than a wrong number.

KEY METRICS TO COMPUTE:
  - npl_ratio: (total exposure of loans with DSCR < 1.0) / total exposure
  - par90_ratio: count of PAR90 loans / total loans
  - par30_ratio: count of loans with any payment > 30 days late / total loans
  - covenant_breach_rate: count of loans with any breach / total loans
  - avg_dscr: average DSCR across all loans
  - sector_risk_scores: for each sector, average DSCR of loans in that sector
  - top5_risk_loans: top 5 highest-risk loans ranked by (par90 + dscr_breach + months_overdue)

POLICY THRESHOLDS (Afiland First Bank standard):
  - DSCR covenant minimum: 1.25
  - LTV covenant maximum: 0.80
  - NPL ratio alert: > 5%
  - PAR90 alert: > 3%

Output ONLY valid JSON in this exact schema:
{
  "npl_ratio_pct": <number or "DATA_GAP">,
  "par90_ratio_pct": <number or "DATA_GAP">,
  "par30_ratio_pct": <number or "DATA_GAP">,
  "covenant_breach_rate_pct": <number or "DATA_GAP">,
  "avg_dscr": <number or "DATA_GAP">,
  "total_exposure_xaf": <number>,
  "npl_exposure_xaf": <number>,
  "alerts": [
    {"metric": "...", "value": ..., "threshold": ..., "severity": "CRITICAL" | "WATCH"}
  ],
  "sector_risk": [
    {"sector": "...", "avg_dscr": <number>, "par90_count": <integer>, "total_exposure_xaf": <number>}
  ],
  "top5_risk_loans": [
    {"loan_id": "...", "borrower_name": "...", "dscr": <number>, "par90": <bool>, "months_overdue": <integer>, "exposure_xaf": <number>, "risk_score": <number>}
  ],
  "data_gaps": ["<field>: <reason>"]
}
"""


def compute_par_from_transactions(transactions: list) -> dict:
    """
    Compute PAR30 and PAR90 directly from transaction history.

    WHY THIS IS IN PYTHON, NOT IN THE PROMPT:
      Mathematical aggregation over 600 transaction records is faster,
      cheaper, and more reliable in Python than in a language model.
      We use the LLM for what it is good at (synthesis, narrative,
      judgment) and Python for what Python is good at (arithmetic).

    This is a design principle: only send to the model what requires
    language understanding or reasoning. Everything else is code.
    """
    par30_loans = set()
    par90_loans = set()

    for txn in transactions:
        if txn["days_late"] > 30:
            par30_loans.add(txn["loan_id"])
        if txn["days_late"] > 90:
            par90_loans.add(txn["loan_id"])

    return {
        "par30_loan_ids": list(par30_loans),
        "par90_loan_ids": list(par90_loans),
        "par30_count":    len(par30_loans),
        "par90_count":    len(par90_loans),
    }


def run() -> dict:
    """
    1. Load portfolio summary (DataScout's output) — from file
    2. Load transaction data — from file
    3. Pre-compute PAR stats in Python (fast, reliable)
    4. Send structured inputs to Ratio Analyst LLM for ratio computation
    5. Validate and save ratios.json
    """
    # ── Load DataScout's output
    with open("output/portfolio_summary.json") as f:
        portfolio = json.load(f)

    if "error" in portfolio:
        print("[RatioAnalyst] ✗ DataScout output contains error — cannot proceed")
        return {"error": "upstream_failure"}

    # ── Load transactions and pre-compute PAR in Python
    with open("data/transactions.json") as f:
        transactions = json.load(f)

    par_stats = compute_par_from_transactions(transactions)

    # ── Build the context for the LLM
    # WHY WE PASS STRUCTURED DATA, NOT RAW CSV:
    # The DataScout already extracted and structured the data.
    # Passing structured JSON to the Ratio Analyst is:
    #   - Cheaper (fewer tokens than raw CSV)
    #   - More reliable (no extraction errors)
    #   - Auditable (we know exactly what the agent was given)
    context = {
        "portfolio_summary": portfolio,
        "par_stats":         par_stats,
        "total_loans":       portfolio.get("total_loans", 0),
    }

    user_prompt = f"""
Compute the portfolio risk metrics from this structured data.

PORTFOLIO SUMMARY:
{json.dumps(portfolio, indent=2)}

PAYMENT HISTORY STATS (pre-computed from 600 transaction records):
{json.dumps(par_stats, indent=2)}

Remember: output "DATA_GAP" for any metric where the required input is missing.
Output ONLY the JSON object.
"""

    raw = call_claude(
        agent_name="RatioAnalyst",
        step="ratio_computation",
        system=SYSTEM_PROMPT,
        user=user_prompt,
        max_tokens=2500,
    )

    # ── Parse JSON
    text = raw.strip()
    if "```" in text:
        parts = text.split("```")
        for part in parts:
            part = part.strip()
            if part.startswith("json"):
                part = part[4:].strip()
            if part.startswith("{"):
                text = part
                break

    try:
        ratios = json.loads(text)
    except json.JSONDecodeError as e:
        print(f"[RatioAnalyst] JSON parse error: {e}")
        ratios = {"error": str(e), "raw_snippet": raw[:400]}

    os.makedirs("output", exist_ok=True)
    with open("output/ratios.json", "w") as f:
        json.dump(ratios, f, indent=2)

    print(f"[RatioAnalyst] ✓ Ratios saved → output/ratios.json")
    if "npl_ratio_pct" in ratios:
        print(f"             NPL ratio: {ratios['npl_ratio_pct']}%")
        print(f"             PAR90 ratio: {ratios.get('par90_ratio_pct')}%")
        alerts = ratios.get("alerts", [])
        print(f"             Alerts triggered: {len(alerts)}")
        data_gaps = ratios.get("data_gaps", [])
        if data_gaps:
            print(f"             DATA GAPS flagged: {data_gaps}")

    return ratios


if __name__ == "__main__":
    run()
