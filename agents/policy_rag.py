"""
agents/policy_rag.py
────────────────────
ROLE: Policy Retrieval Agent
MANDATE: Retrieve relevant AFB credit policy sections for the alert conditions
         found by the Ratio Analyst. CITE every policy reference. REFUSE
         to state policy thresholds not present in the policy document.
READS:  output/ratios.json (from RatioAnalyst)
        data/policy.json (simulated policy document chunks)
WRITES: output/policy_context.json

WHY A DEDICATED AGENT FOR THIS:
  Policy retrieval requires a different kind of reasoning than ratio
  computation. The Policy Agent must:
    1. Identify which sections of the credit policy are relevant
       to the specific alerts triggered (e.g., PAR90 > 5% triggers
       Section 4.2 "Provisioning Requirements")
    2. Cite the exact section, not paraphrase from training memory
    3. Flag where policy is SILENT (no section covers this situation)

  In the single-agent baseline, the narrative says "per AFB policy"
  without citing a section. This is legally insufficient for a
  Risk Committee report. The Policy Agent enforces citation discipline.

DESIGN PATTERN: Simulated RAG
  In a production system, this agent would embed the query and
  retrieve from a vector database. Here we simulate RAG by:
    1. Loading a structured policy document (JSON chunks)
    2. Passing relevant chunks to the LLM based on alert type
    3. Requiring [SECTION X.X] citation format in every claim

  This is the same cite-or-refuse contract from Assignment 9-B,
  applied here in the multi-agent context.
"""

import json
import os
from api_client import call_claude

# ── Simulated AFB Credit Policy (structured as RAG chunks)
# In production: embed these and retrieve by cosine similarity.
# Here: we load all sections and let the model select relevant ones.
POLICY_CHUNKS = {
    "S1.1": "DSCR Covenant Minimum: All SME loans must maintain a minimum Debt Service Coverage Ratio of 1.25. Loans with DSCR below 1.25 are in covenant breach and require a Covenant Breach Notice within 5 business days.",
    "S1.2": "DSCR Critical Threshold: Loans with DSCR below 1.0 indicate the borrower cannot service debt from operations. These must be classified as Non-Performing Loans (NPL) and provisioned at 50% within 30 days.",
    "S2.1": "LTV Maximum: The maximum Loan-to-Value ratio for SME term loans is 0.80. Loans exceeding this ratio require additional collateral or partial prepayment within 60 days of identification.",
    "S3.1": "PAR90 Classification: Any loan with payments more than 90 days past due is classified as Portfolio at Risk (PAR90). A PAR90 ratio exceeding 5% of total portfolio triggers a mandatory Risk Committee review.",
    "S3.2": "PAR30 Monitoring: Loans with payments 30–89 days past due are Watch loans. A PAR30 ratio exceeding 10% triggers enhanced monitoring and monthly reporting to the Chief Risk Officer.",
    "S4.1": "Provisioning — Watch: Loans in Watch status (DSCR 1.00–1.24, or PAR30) require a provision of 15% of outstanding exposure.",
    "S4.2": "Provisioning — Substandard: NPL loans (DSCR < 1.0) require a provision of 50% of outstanding exposure within 30 days of classification.",
    "S4.3": "Provisioning — Loss: Loans overdue more than 180 days require a provision of 100% and must be referred to the Legal Department for recovery action.",
    "S5.1": "Sector Concentration Limit: No single sector shall exceed 35% of total portfolio exposure. A breach requires notification to the Board Risk Committee.",
    "S5.2": "Regional Concentration: No single region shall exceed 40% of total portfolio exposure.",
    "S6.1": "Covenant Breach Response: Upon identification of a covenant breach, the loan officer must issue a formal Covenant Breach Notice, schedule a borrower review meeting within 10 business days, and document a remediation plan.",
    "S7.1": "Override Authority: Loan exceptions (loans approved despite covenant breach) require sign-off from the Regional Credit Director. All exceptions must be logged in the Exception Register.",
}

SYSTEM_PROMPT = """
You are the Policy Retrieval Agent for Afiland First Bank.

YOUR JOB: Given a set of risk alerts from the portfolio analysis,
identify the relevant policy sections and state what action is required.

STRICT CITE-OR-REFUSE RULE:
- Every policy statement you make MUST include the section reference
  in the format [S1.1], [S3.1], etc.
- If no policy section addresses a specific alert, say:
  "POLICY SILENT: No AFB policy section found for this condition."
- NEVER state policy thresholds from your training memory.
  Only use the sections provided to you.

OUTPUT: Valid JSON only, no markdown fences.
Schema:
{
  "cited_sections": [
    {
      "section_id": "S1.1",
      "section_title": "...",
      "triggered_by_alert": "...",
      "required_action": "...",
      "urgency": "IMMEDIATE" | "30_DAYS" | "60_DAYS" | "MONITORING"
    }
  ],
  "policy_gaps": ["Description of condition with no policy coverage"],
  "provisioning_requirements": [
    {
      "classification": "WATCH" | "SUBSTANDARD" | "LOSS",
      "affected_loan_count": <integer>,
      "required_provision_pct": <number>,
      "section_ref": "S4.X"
    }
  ]
}
"""


def run() -> dict:
    """
    1. Load alerts from ratios.json
    2. Select relevant policy chunks based on alert types
    3. Send to LLM with cite-or-refuse contract
    4. Save policy_context.json
    """
    with open("output/ratios.json") as f:
        ratios = json.load(f)

    if "error" in ratios:
        print("[PolicyRAG] ✗ RatioAnalyst output contains error — cannot proceed")
        return {"error": "upstream_failure"}

    alerts = ratios.get("alerts", [])

    # ── Simulated RAG retrieval:
    # Determine which policy sections are relevant based on alert types.
    # In production: embed alert descriptions and retrieve by cosine similarity.
    # Here: rule-based selection (fast, transparent, sufficient for the demo).
    relevant_sections = {}
    alert_descriptions = []

    for alert in alerts:
        metric = alert.get("metric", "")
        alert_descriptions.append(f"{alert['metric']}: {alert['value']} (threshold: {alert['threshold']}, severity: {alert['severity']})")
        if "npl" in metric.lower():
            relevant_sections.update({k: v for k, v in POLICY_CHUNKS.items() if k in ["S1.1","S1.2","S4.2"]})
        if "par90" in metric.lower():
            relevant_sections.update({k: v for k, v in POLICY_CHUNKS.items() if k in ["S3.1","S4.2","S4.3"]})
        if "par30" in metric.lower():
            relevant_sections.update({k: v for k, v in POLICY_CHUNKS.items() if k in ["S3.2","S4.1"]})
        if "covenant" in metric.lower() or "dscr" in metric.lower():
            relevant_sections.update({k: v for k, v in POLICY_CHUNKS.items() if k in ["S1.1","S1.2","S6.1"]})
        if "ltv" in metric.lower():
            relevant_sections.update({k: v for k, v in POLICY_CHUNKS.items() if k in ["S2.1"]})

    # Always include provisioning sections
    relevant_sections.update({k: v for k, v in POLICY_CHUNKS.items() if k.startswith("S4")})

    if not relevant_sections:
        # No alerts: include overview sections
        relevant_sections = {k: v for k, v in POLICY_CHUNKS.items() if k in ["S1.1","S3.1","S4.1"]}

    sections_text = "\n".join([f"[{sid}] {text}" for sid, text in relevant_sections.items()])

    user_prompt = f"""
The portfolio analysis has produced the following alerts:
{chr(10).join(alert_descriptions) if alert_descriptions else "No critical alerts. Run standard provisioning check."}

Portfolio context:
- NPL ratio: {ratios.get('npl_ratio_pct', 'N/A')}%
- PAR90 ratio: {ratios.get('par90_ratio_pct', 'N/A')}%
- Covenant breach rate: {ratios.get('covenant_breach_rate_pct', 'N/A')}%

POLICY DOCUMENT (cite ONLY these sections using [SX.X] format):
{sections_text}

For each alert, identify the applicable policy section(s), the required action,
and the urgency. Use ONLY the sections above. If a condition is not covered,
state "POLICY SILENT".

Output ONLY the JSON object.
"""

    raw = call_claude(
        agent_name="PolicyRAG",
        step="policy_retrieval",
        system=SYSTEM_PROMPT,
        user=user_prompt,
        max_tokens=2000,
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
        policy_context = json.loads(text)
    except json.JSONDecodeError as e:
        print(f"[PolicyRAG] JSON parse error: {e}")
        policy_context = {"error": str(e), "raw_snippet": raw[:400]}

    os.makedirs("output", exist_ok=True)
    with open("output/policy_context.json", "w") as f:
        json.dump(policy_context, f, indent=2)

    print(f"[PolicyRAG] ✓ Policy context saved → output/policy_context.json")
    cited = policy_context.get("cited_sections", [])
    print(f"           Sections cited: {[s.get('section_id') for s in cited]}")
    gaps = policy_context.get("policy_gaps", [])
    if gaps:
        print(f"           Policy gaps: {gaps}")

    return policy_context


if __name__ == "__main__":
    run()
