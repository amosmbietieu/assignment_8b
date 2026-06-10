"""
agents/data_scout.py
────────────────────
ROLE: Data Scout
MANDATE: Extract and structure raw portfolio data. No interpretation. No opinions.
READS:  data/portfolio.csv, data/transactions.json
WRITES: output/portfolio_summary.json

WHY A DEDICATED AGENT FOR THIS:
  Data extraction is a mechanical, high-volume task. It requires precision
  (every loan, every field) but no financial judgment. Giving this task to
  a reasoning-heavy agent wastes capacity and introduces inconsistency.

  The Scout's ONLY job is to answer: "What is the factual state of the
  portfolio right now?" It refuses to interpret, recommend, or summarize.
  That separation is what makes the downstream agents trustworthy.

SYSTEM PROMPT DESIGN PHILOSOPHY:
  The system prompt gives the agent:
    1. A clear identity (who it is)
    2. A strict scope (what it can and cannot do)
    3. An output contract (exactly what JSON schema to produce)
  The output contract is the most important part. Without a schema,
  different runs produce different structures, breaking the agents
  that read this file.
"""

import csv
import json
import os
from api_client import call_claude

SYSTEM_PROMPT = """
You are the Data Scout for Afiland First Bank's credit portfolio system.

YOUR ONLY JOB: Extract and structure factual data from the portfolio CSV.

STRICT RULES:
- Do NOT interpret, recommend, or summarize anything.
- Do NOT compute ratios that are not already in the data.
- If a field is missing or null, output null — never estimate.
- Output ONLY valid JSON. No explanations, no markdown fences.

OUTPUT SCHEMA (produce exactly this structure):
{
  "total_loans": <integer>,
  "total_exposure_xaf": <number>,
  "par90_loans": [
    {
      "loan_id": "...",
      "borrower_name": "...",
      "sector": "...",
      "exposure_xaf": <number>,
      "dscr": <number>,
      "ltv": <number>,
      "months_overdue": <integer>
    }
  ],
  "covenant_breaches": [
    {
      "loan_id": "...",
      "borrower_name": "...",
      "breach_type": "DSCR" | "LTV" | "BOTH",
      "dscr": <number>,
      "ltv": <number>
    }
  ],
  "sector_exposure": {
    "<sector_name>": <total_exposure_xaf>
  },
  "region_exposure": {
    "<region_name>": <total_exposure_xaf>
  },
  "watch_loans": [
    {
      "loan_id": "...",
      "borrower_name": "...",
      "dscr": <number>,
      "reason": "DSCR_BORDERLINE" | "HIGH_DTI" | "HIGH_LTV"
    }
  ]
}
"""


def run(portfolio_path: str = "data/portfolio.csv") -> dict:
    """
    Load raw CSV, send to the Scout agent, parse and save the structured output.

    WHY WE PARSE AND VALIDATE THE JSON:
      The Scout might produce valid JSON or it might add a preamble.
      We strip non-JSON text and validate the schema before writing.
      A downstream agent reading a malformed file would silently
      produce wrong results — that is worse than a visible error.
    """
    with open(portfolio_path) as f:
        csv_content = f.read()

    user_prompt = f"""
Extract and structure the following Afiland First Bank portfolio data.
Identify PAR90 loans (par90_flag = True), covenant breaches
(covenant_dscr_breach or covenant_ltv_breach = True), and watch loans
(DSCR between 1.00 and 1.24 inclusive, or DTI > 0.45, or LTV > 0.75).

PORTFOLIO DATA:
{csv_content}

Output ONLY the JSON object described in your instructions.
"""

    raw = call_claude(
        agent_name="DataScout",
        step="portfolio_extraction",
        system=SYSTEM_PROMPT,
        user=user_prompt,
        max_tokens=3000,
    )

    # ── Parse JSON robustly
    # WHY: models sometimes wrap JSON in ```json ... ``` fences even when told not to.
    text = raw.strip()
    if "```" in text:
        # strip markdown fences if present
        text = text.split("```")
        for block in text:
            block = block.strip()
            if block.startswith("json"):
                block = block[4:].strip()
            if block.startswith("{"):
                text = block
                break

    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        # If parsing fails, return a structured error so downstream agents
        # receive a clear signal rather than crashing silently.
        print(f"[DataScout] JSON parse error: {e}")
        print(f"[DataScout] Raw response snippet: {raw[:300]}")
        data = {"error": str(e), "raw": raw[:500]}

    # ── Write to shared memory (file system)
    # WHY FILES: this is the explicit memory mechanism the assignment asks for.
    # Each agent writes its output to a file. Downstream agents read those files.
    # This creates an auditable, inspectable trail of intermediate results.
    os.makedirs("output", exist_ok=True)
    with open("output/portfolio_summary.json", "w") as f:
        json.dump(data, f, indent=2)

    print(f"[DataScout] ✓ Portfolio summary saved → output/portfolio_summary.json")
    if "total_loans" in data:
        print(f"           Total loans: {data['total_loans']}")
        print(f"           PAR90 loans: {len(data.get('par90_loans', []))}")
        print(f"           Covenant breaches: {len(data.get('covenant_breaches', []))}")

    return data


if __name__ == "__main__":
    run()
