"""
single_agent.py
───────────────
WHY THIS FILE EXISTS:
  The assignment requires: "First solve with only a single agent —
  your benchmark for yourself."

  This is NOT throwaway code. It exists to answer a hard question:
  is the complexity of multi-agent architecture justified by a
  measurable improvement? Without this baseline, you cannot answer.

  The single agent is given the raw CSV and asked to produce the
  full quarterly credit report in ONE call. It has no tools,
  no specialist sub-agents, no file-based memory. Just a prompt and data.

WHAT TO OBSERVE WHEN YOU RUN THIS:
  - It WILL produce a coherent report.
  - It WILL likely hallucinate at least one DSCR value.
  - It WILL miss some borrowers when the data exceeds ~2000 tokens.
  - The narrative WILL be generic (no AFB-specific policy thresholds).

These are the exact gaps that the multi-agent system is designed to fix.
"""

import csv
import json
import time
import os
from pathlib import Path
from api_client import call_claude


# ── System prompt: single agent with full responsibility
SINGLE_AGENT_SYSTEM = """
You are a senior credit analyst at Afiland First Bank (Cameroon).
Your task is to produce a quarterly portfolio quality report for the Risk Committee.

You will receive raw loan portfolio data in CSV format.
Produce a professional credit quality report including:
1. Executive Summary (key metrics: total exposure, NPL ratio, PAR90 count)
2. Top 5 highest-risk borrowers (by PAR90 + DSCR breach)
3. Sector concentration analysis
4. Covenant breach summary
5. Recommendations for the Risk Committee

Be specific with numbers. Flag any loans where DSCR < 1.0 as CRITICAL.
Flag loans where DSCR is 1.0–1.24 as WATCH.
"""


def run_single_agent(portfolio_path: str = "data/portfolio.csv") -> dict:
    """
    Run the entire analysis in ONE API call.

    WHY ONE CALL IS THE LIMIT:
      A single agent has no way to:
        - Parallelise data extraction and policy lookup
        - Maintain a separate, auditable chain of reasoning per dimension
        - Refuse to compute when input data is missing (it estimates instead)
      These limitations are structural, not prompt-engineering problems.

    RETURNS: dict with report text, timing, and quality metadata.
    """
    t0 = time.time()

    # Load the portfolio CSV and pass it as raw text
    # WHY RAW TEXT: the single agent has no file-reading tool.
    # This is the first structural limitation.
    with open(portfolio_path) as f:
        csv_content = f.read()

    user_prompt = f"""
Here is the Afiland First Bank Q4 2024 SME loan portfolio data (CSV format):

{csv_content}

Please produce the quarterly credit quality report for the Risk Committee.
"""

    t_call_start = time.time()
    report_text = call_claude(
        agent_name="SingleAgent",
        step="full_report_generation",
        system=SINGLE_AGENT_SYSTEM,
        user=user_prompt,
        model="claude-haiku-4-5-20251001",   # same model as multi-agent for fair comparison
        max_tokens=3000,
    )
    call_latency = time.time() - t_call_start

    total_latency = time.time() - t0

    # Save output for comparison
    os.makedirs("output", exist_ok=True)
    with open("output/single_agent_report.md", "w") as f:
        f.write("# Single-Agent Report (Baseline)\n\n")
        f.write(f"*Generated in {total_latency:.1f}s using 1 API call*\n\n")
        f.write("---\n\n")
        f.write(report_text)

    print(f"\n[SINGLE AGENT] Report generated in {total_latency:.1f}s")
    print(f"  Output saved → output/single_agent_report.md")
    print(f"  API call latency: {call_latency:.1f}s")

    return {
        "report":        report_text,
        "latency_s":     round(total_latency, 2),
        "api_calls":     1,
        "known_issues": [
            "No DSCR verification against debt service schedule (no file tool)",
            "Cannot parallelise data extraction and policy lookup",
            "Generic narrative — no AFB covenant thresholds cited",
            "All 50 loans in one prompt → may miss tail borrowers",
        ],
    }


if __name__ == "__main__":
    result = run_single_agent()
    print("\n── KNOWN LIMITATIONS OF SINGLE-AGENT APPROACH ──")
    for issue in result["known_issues"]:
        print(f"  ✗ {issue}")
    print("\n── BASELINE ESTABLISHED ──")
    print("Now run orchestrator.py to see the multi-agent improvement.")
