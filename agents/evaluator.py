"""
agents/evaluator.py
───────────────────
ROLE: Evaluator Agent
MANDATE: Score the credit memo on 5 dimensions (1–10 each).
         Identify ONE specific improvement per dimension.
         Feed improvement suggestions back to the ReportWriter.
READS:  output/credit_memo.md
WRITES: output/eval_scores.json
        output/credit_memo_v2.md  (improved version after feedback)

WHY THIS AGENT EXISTS:
  The assignment asks: "Add an evaluator agent that scores your overall
  architectural design, grade it from 1 to 10. Ask AI how to improve.
  Put this feedback back in. Did you create an improvement loop?"

  The evaluator is the quality gate. It answers: "Is this good enough
  to put in front of the Risk Committee?" with specific, actionable
  criteria — not a vague thumbs up or down.

  The IMPROVEMENT LOOP works as follows:
    1. Evaluator scores the memo (iteration 1)
    2. Evaluator identifies ONE concrete improvement per dimension
    3. ReportWriter is called again with the original data + evaluator feedback
    4. Evaluator scores the improved memo (iteration 2)
    5. Scores are compared: did the loop actually improve quality?

  The loop is intentionally limited to ONE iteration here because:
    - More iterations = more cost
    - The evaluator itself tends to inflate scores over iterations
      (it "learns" what the writer produces and grades on a curve)
    - One iteration with specific feedback produces the clearest signal

FIVE DIMENSIONS (with what each measures):
  1. Factual Accuracy    — are the numbers correct and consistently sourced?
  2. Completeness       — are all 7 required report sections present?
  3. Policy Compliance  — are policy citations present and correct?
  4. Narrative Clarity  — can a non-technical committee member understand this?
  5. Auditability       — can every figure be traced to a source?
"""

import json
import os
from api_client import call_claude

EVALUATOR_SYSTEM = """
You are a senior credit risk officer and document quality reviewer at Afiland First Bank.
Your job is to evaluate a credit committee report and score it rigorously.

SCORING CRITERIA (1 = unacceptable, 5 = adequate, 10 = publication-ready):
  1. Factual Accuracy (1-10):
     Are all numbers present? Are they labeled with source tags ([DS],[RA],[PR])?
     Deduct 2 points for any ratio that appears without a source tag.
     Deduct 3 points if any number appears to be fabricated (no data to support it).

  2. Completeness (1-10):
     Must contain ALL 7 sections: Executive Summary, Risk Metrics, Top-Risk Borrowers,
     Covenant Breach Summary, Sector/Regional Concentration, Required Actions,
     Risk Committee Decision Items. Deduct 1.5 points per missing section.

  3. Policy Compliance (1-10):
     Every required action must cite a policy section [S1.1], [S3.1], etc.
     Deduct 2 points for each action stated without a policy citation.

  4. Narrative Clarity (1-10):
     Can a Risk Committee member (not a data scientist) understand every paragraph?
     Are technical terms explained? Is the executive summary genuinely executive-level?

  5. Auditability (1-10):
     If a reviewer opens portfolio_summary.json, ratios.json, and policy_context.json,
     can they verify every claim in the memo? Deduct 2 points for each unverifiable claim.

Output ONLY valid JSON:
{
  "scores": {
    "factual_accuracy": <1-10>,
    "completeness": <1-10>,
    "policy_compliance": <1-10>,
    "narrative_clarity": <1-10>,
    "auditability": <1-10>
  },
  "overall_score": <average, 1 decimal place>,
  "improvements": {
    "factual_accuracy": "<ONE specific actionable improvement>",
    "completeness": "<ONE specific actionable improvement>",
    "policy_compliance": "<ONE specific actionable improvement>",
    "narrative_clarity": "<ONE specific actionable improvement>",
    "auditability": "<ONE specific actionable improvement>"
  },
  "enterprise_ready": true | false,
  "enterprise_ready_rationale": "<2 sentences: why yes or why not, and what condition must be met>"
}
"""


def evaluate(memo_path: str, iteration: int = 1) -> dict:
    """
    Score a credit memo and generate improvement instructions.

    PARAMETER: iteration — used for logging (1 = first eval, 2 = post-improvement)
    """
    with open(memo_path) as f:
        memo_text = f.read()

    user_prompt = f"""
Evaluate this Afiland First Bank credit committee report:

{memo_text}

Score each dimension 1-10 and provide one specific improvement per dimension.
Output ONLY the JSON object.
"""

    raw = call_claude(
        agent_name="Evaluator",
        step=f"evaluation_iteration_{iteration}",
        system=EVALUATOR_SYSTEM,
        user=user_prompt,
        model="claude-haiku-4-5-20251001",
        max_tokens=1500,
    )

    # Parse JSON
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
        result = json.loads(text)
    except json.JSONDecodeError as e:
        print(f"[Evaluator] JSON parse error: {e}")
        result = {"error": str(e), "raw": raw[:400]}

    # Save evaluation
    os.makedirs("output", exist_ok=True)
    eval_path = f"output/eval_scores_v{iteration}.json"
    with open(eval_path, "w") as f:
        json.dump(result, f, indent=2)

    overall = result.get("overall_score", "N/A")
    print(f"\n[Evaluator] ✓ Iteration {iteration} — Overall score: {overall}/10")
    if "scores" in result:
        for dim, score in result["scores"].items():
            print(f"             {dim}: {score}/10")
    print(f"             Enterprise ready: {result.get('enterprise_ready', '?')}")

    return result


def run_improvement_loop() -> dict:
    """
    THE IMPROVEMENT LOOP — core mechanism of the evaluator-optimizer pattern.

    STEP 1: Score the initial credit memo (output of ReportWriter, iteration 1)
    STEP 2: Extract specific improvements from the evaluator
    STEP 3: Re-call the ReportWriter with the original data + the improvements
    STEP 4: Score the improved memo (iteration 2)
    STEP 5: Return both scores so the dashboard can show the delta

    WHY THIS IS VALUABLE (and also limited):
      Valuable: the evaluator catches missing sections, unsourced figures,
      and generic language that the writer might produce on a first pass.

      Limited: the evaluator is the SAME model that wrote the memo.
      It will tend to inflate iteration-2 scores because it "recognises"
      its own writing. The delta between iteration 1 and iteration 2
      is real but should be treated as an estimate, not a measurement.
      In production, the evaluator would be a SEPARATE model or a human.
    """
    # ── Iteration 1: score original memo
    print("\n── EVALUATOR: ITERATION 1 (original memo) ──")
    eval_v1 = evaluate("output/credit_memo.md", iteration=1)

    if "error" in eval_v1:
        print("[Evaluator] Cannot run improvement loop — evaluation failed")
        return eval_v1

    improvements = eval_v1.get("improvements", {})

    # ── Iteration 2: improved memo
    # Feed the evaluator's specific improvements back to the ReportWriter
    # THIS IS THE LOOP: Evaluator → ReportWriter → Evaluator

    # Load all original data
    with open("output/portfolio_summary.json") as f:
        portfolio = json.load(f)
    with open("output/ratios.json") as f:
        ratios = json.load(f)
    with open("output/policy_context.json") as f:
        policy = json.load(f)
    with open("output/credit_memo.md") as f:
        original_memo = f.read()

    improvement_instructions = "\n".join([
        f"  - {dim}: {instruction}"
        for dim, instruction in improvements.items()
    ])

    print("\n── IMPROVEMENT LOOP: Feeding evaluator feedback to ReportWriter ──")
    print(f"   Improvements requested:\n{improvement_instructions}")

    from api_client import call_claude as _call

    WRITER_SYSTEM_V2 = """
You are the Report Writer for Afiland First Bank's Risk Committee.
You are producing an IMPROVED VERSION of a credit report, based on
specific quality feedback from a senior reviewer.

Apply ALL the improvements listed below. Do not drop any section.
Tag every figure with [DS], [RA], or [PR].
"""

    improved_text = _call(
        agent_name="ReportWriter",
        step="credit_memo_revision_v2",
        system=WRITER_SYSTEM_V2,
        user=f"""
Here is the original credit report that needs improvement:

{original_memo}

SPECIFIC IMPROVEMENTS REQUIRED BY SENIOR REVIEWER:
{improvement_instructions}

Original data (for reference — do not add figures not present here):
── DATA SCOUT [DS] ──
{json.dumps(portfolio, indent=2)[:2000]}

── RATIO ANALYST [RA] ──
{json.dumps(ratios, indent=2)[:1500]}

── POLICY RAG [PR] ──
{json.dumps(policy, indent=2)[:1500]}

Write the full improved report.
""",
        model="claude-haiku-4-5-20251001",
        max_tokens=4000,
    )

    # Save improved memo
    with open("output/credit_memo_v2.md", "w") as f:
        f.write("# Q4 2024 Credit Quality Report — REVISED VERSION\n")
        f.write("## Afiland First Bank — Risk Committee\n\n")
        f.write("*Revised based on evaluator feedback. Source tags: [DS] [RA] [PR]*\n\n")
        f.write("---\n\n")
        f.write(improved_text)

    print("\n── EVALUATOR: ITERATION 2 (improved memo) ──")
    eval_v2 = evaluate("output/credit_memo_v2.md", iteration=2)

    # ── Compute delta
    score_v1 = eval_v1.get("overall_score", 0)
    score_v2 = eval_v2.get("overall_score", 0)

    result = {
        "iteration_1": eval_v1,
        "iteration_2": eval_v2,
        "score_v1":    score_v1,
        "score_v2":    score_v2,
        "delta":       round(score_v2 - score_v1, 1),
        "loop_worked": score_v2 > score_v1,
    }

    with open("output/eval_scores.json", "w") as f:
        json.dump(result, f, indent=2)

    print(f"\n── IMPROVEMENT LOOP RESULT ──")
    print(f"   Score v1: {score_v1}/10  →  Score v2: {score_v2}/10  (Δ = {result['delta']})")
    print(f"   Loop worked: {result['loop_worked']}")

    return result


if __name__ == "__main__":
    run_improvement_loop()
