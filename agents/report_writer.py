"""
agents/report_writer.py
───────────────────────
ROLE: Report Writer
MANDATE: Synthesise all agent outputs into a professional credit memo.
         CITE every figure to its source JSON file.
         Output a structured markdown document suitable for the Risk Committee.
READS:  output/portfolio_summary.json  (DataScout)
        output/ratios.json             (RatioAnalyst)
        output/policy_context.json     (PolicyRAG)
WRITES: output/credit_memo.md

WHY A DEDICATED AGENT FOR THIS:
  Narrative synthesis is the task most suited to a language model.
  By the time the Report Writer runs, all factual content has been
  extracted, computed, and verified by specialist agents.

  The Writer's job is NOT to invent content — it is to organise,
  clarify, and communicate what the other agents have produced.
  Every number it writes must trace back to a source file.

  This is the structural reason the single-agent baseline fails:
  a single agent must extract AND compute AND write simultaneously,
  which introduces fabrication risk at every step.

CITATION CONTRACT:
  The Writer is instructed to tag each figure with its source:
    [DS] = DataScout (portfolio_summary.json)
    [RA] = RatioAnalyst (ratios.json)
    [PR] = PolicyRAG (policy_context.json)
  These tags make the memo auditable — a reviewer can verify
  any number by opening the corresponding JSON file.
"""

import json
import os
from api_client import call_claude

SYSTEM_PROMPT = """
You are the Report Writer for Afiland First Bank's Risk Committee.

YOUR JOB: Write a professional quarterly credit quality report using
ONLY the data provided to you. Every factual claim must be tagged with
its source: [DS] for portfolio data, [RA] for computed ratios, [PR] for policy.

STRICT RULES:
- Do NOT add numbers, ratios, or recommendations not present in the input data.
- Do NOT write generic boilerplate. Every paragraph must contain specific figures.
- Tag every number with its source tag: e.g., "NPL ratio: 12.4% [RA]"
- If a required section has no data (e.g., no policy context provided),
  write: "DATA NOT AVAILABLE FOR THIS SECTION."

REPORT STRUCTURE (follow exactly):
1. EXECUTIVE SUMMARY (5–7 sentences, key metrics only)
2. PORTFOLIO RISK METRICS (numbered list of all ratios with source tags)
3. TOP-RISK BORROWERS (table: Loan ID | Borrower | DSCR | PAR90 | Exposure)
4. COVENANT BREACH SUMMARY (list of breaches with required action per policy)
5. SECTOR & REGIONAL CONCENTRATION (flag any concentration limit breaches)
6. REQUIRED ACTIONS (numbered list, each with urgency level from policy)
7. RISK COMMITTEE DECISION ITEMS (what the committee must vote on today)
"""


def run() -> dict:
    """
    Load all three upstream agent outputs and synthesise the credit memo.
    """
    # ── Load all inputs — each file is the verified output of a specialist agent
    with open("output/portfolio_summary.json") as f:
        portfolio = json.load(f)

    with open("output/ratios.json") as f:
        ratios = json.load(f)

    with open("output/policy_context.json") as f:
        policy = json.load(f)

    user_prompt = f"""
Write the Q4 2024 Quarterly Credit Quality Report for the Afiland First Bank Risk Committee.

Use ONLY the following data. Tag every figure with [DS], [RA], or [PR].

── DATA SCOUT OUTPUT [DS] ──
{json.dumps(portfolio, indent=2)}

── RATIO ANALYST OUTPUT [RA] ──
{json.dumps(ratios, indent=2)}

── POLICY RAG OUTPUT [PR] ──
{json.dumps(policy, indent=2)}

Write the full report following the structure in your instructions.
"""

    report_text = call_claude(
        agent_name="ReportWriter",
        step="credit_memo_generation",
        system=SYSTEM_PROMPT,
        user=user_prompt,
        model="claude-haiku-4-5-20251001",
        max_tokens=3500,
    )

    os.makedirs("output", exist_ok=True)

    # Save the markdown memo
    memo_path = "output/credit_memo.md"
    with open(memo_path, "w") as f:
        f.write("# Q4 2024 Quarterly Credit Quality Report\n")
        f.write("## Afiland First Bank — Risk Committee\n\n")
        f.write("*Source tags: [DS] = DataScout | [RA] = RatioAnalyst | [PR] = PolicyRAG*\n\n")
        f.write("---\n\n")
        f.write(report_text)

    print(f"[ReportWriter] ✓ Credit memo saved → {memo_path}")
    print(f"               Length: {len(report_text)} characters")

    return {
        "memo_path":  memo_path,
        "memo_text":  report_text,
        "char_count": len(report_text),
    }


if __name__ == "__main__":
    run()
