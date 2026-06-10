"""
circuit_breaker.py
──────────────────
WHY THIS FILE EXISTS:
  Jim Liew, JHU 03/06/2026:
  "When do we know when to say: stop? If you're approving loans and
   typically you approve 500 loans a week, and all of a sudden you're
   not approving any — you kind of have to know those."

  And: "How fast can you shut it down? That's the key."

  The circuit breaker is the answer to both questions. It runs AFTER
  the pipeline completes and checks that the outputs make sense given
  the inputs. If they don't, it halts and alerts before any human
  reviews a potentially incorrect memo.

  ANALOGY Jim uses: the assembly line. When the factory robot stops
  moving boxes, you know something broke. This is the software
  equivalent: observable anomalies that trigger a halt.

CHECKS PERFORMED:
  1. PAR90 Consistency   — if portfolio.csv has par90_flag=True loans,
                           ratios.json must show par90_count > 0
  2. NPL Consistency     — if any loan has DSCR < 1.0, NPL ratio > 0
  3. Alert Non-Silence   — if covenant breaches exist, at least 1 alert
  4. Memo Completeness   — credit memo must contain required sections
  5. Source Tag Minimum  — memo must have at least 5 [DS]/[RA]/[PR] tags
  6. Prompt Injection    — no agent output contains injection patterns

WHAT HAPPENS ON FAILURE:
  - Prints CIRCUIT BREAKER TRIGGERED with the specific check that failed
  - Writes logs/circuit_breaker_alert.json with full details
  - Returns False (caller can decide to halt or alert)
  - Does NOT automatically delete outputs (preserves evidence for debugging)
"""

import json
import re
import csv
import os
from pathlib import Path
from datetime import datetime, timezone


# ── Prompt injection patterns (Jim: "people were injecting malicious prompts
#    inside there, hidden")
INJECTION_PATTERNS = [
    r"ignore\s+previous\s+instructions",
    r"disregard\s+your\s+system\s+prompt",
    r"reveal\s+your\s+api\s+key",
    r"give\s+me\s+your\s+api\s+key",
    r"ANTHROPIC_API_KEY",
    r"sk-ant-",
    r"you\s+are\s+now\s+in\s+jailbreak\s+mode",
    r"pretend\s+you\s+have\s+no\s+restrictions",
    r"system:\s+you\s+are",
]


def check_injection(text: str, source: str) -> tuple[bool, str]:
    """
    Scan agent output text for prompt injection patterns.
    Returns (clean, message).

    WHY: Jim explicitly warns about injected prompts hidden in data
    that get passed to downstream agents. An agent reading a file
    could execute hidden instructions in that file.
    """
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return False, f"Injection pattern detected in {source}: '{pattern}'"
    return True, "Clean"


def run_circuit_breaker() -> dict:
    """
    Run all circuit breaker checks after pipeline completes.
    Returns a dict with: passed (bool), checks (list of results), summary.
    """
    results = []
    all_passed = True

    # ── Load files
    def load(path):
        if Path(path).exists():
            with open(path) as f:
                return json.load(f)
        return None

    portfolio = load("output/portfolio_summary.json")
    ratios    = load("output/ratios.json")
    memo_path = "output/credit_memo_v2.md"
    if not Path(memo_path).exists():
        memo_path = "output/credit_memo.md"
    memo_text = open(memo_path).read() if Path(memo_path).exists() else ""

    # ── Check 1: PAR90 Consistency
    # Jim: "if you're approving loans and all of a sudden you're not approving any"
    if portfolio and ratios:
        actual_par90 = len(portfolio.get("par90_loans", []))
        reported_par90_ratio = ratios.get("par90_ratio_pct", 0)

        if actual_par90 > 0 and reported_par90_ratio == 0:
            check = {
                "check": "PAR90_CONSISTENCY",
                "passed": False,
                "detail": f"Portfolio has {actual_par90} PAR90 loans but ratio reports 0%. Possible fabrication or extraction error.",
                "jim_rule": "If you're approving 500 loans a week and all of a sudden you're not approving any — you have to know."
            }
            all_passed = False
        else:
            check = {"check": "PAR90_CONSISTENCY", "passed": True,
                     "detail": f"PAR90 count ({actual_par90}) consistent with reported ratio ({reported_par90_ratio}%)."}
        results.append(check)

    # ── Check 2: NPL Consistency
    if portfolio and ratios:
        par90_loans = portfolio.get("par90_loans", [])
        npl_dscr_below_1 = [l for l in par90_loans if l.get("dscr", 2.0) < 1.0]
        npl_ratio = ratios.get("npl_ratio_pct", 0)

        if len(npl_dscr_below_1) > 0:
            try:
                npl_val = float(npl_ratio)
                if npl_val == 0.0:
                    check = {
                        "check": "NPL_CONSISTENCY",
                        "passed": False,
                        "detail": f"{len(npl_dscr_below_1)} loans have DSCR < 1.0 but NPL ratio = 0%. RatioAnalyst may have failed.",
                        "jim_rule": "The circuit breaker fires when outputs contradict the input data."
                    }
                    all_passed = False
                else:
                    check = {"check": "NPL_CONSISTENCY", "passed": True,
                             "detail": f"NPL ratio {npl_val}% consistent with {len(npl_dscr_below_1)} sub-1.0 DSCR loans."}
            except (TypeError, ValueError):
                check = {"check": "NPL_CONSISTENCY", "passed": True,
                         "detail": f"NPL ratio is '{npl_ratio}' (DATA_GAP or non-numeric — acceptable)."}
        else:
            check = {"check": "NPL_CONSISTENCY", "passed": True, "detail": "No DSCR < 1.0 loans in PAR90 set."}
        results.append(check)

    # ── Check 3: Alert Non-Silence
    if ratios and portfolio:
        covenant_breaches = portfolio.get("covenant_breaches", [])
        alerts = ratios.get("alerts", [])
        if len(covenant_breaches) > 0 and len(alerts) == 0:
            check = {
                "check": "ALERT_NON_SILENCE",
                "passed": False,
                "detail": f"{len(covenant_breaches)} covenant breaches in portfolio but zero alerts triggered. System may be suppressing alerts.",
                "jim_rule": "How do you know when it's not working? When something that should trigger doesn't."
            }
            all_passed = False
        else:
            check = {"check": "ALERT_NON_SILENCE", "passed": True,
                     "detail": f"Alerts ({len(alerts)}) consistent with breaches ({len(covenant_breaches)})."}
        results.append(check)

    # ── Check 4: Memo Completeness
    REQUIRED_SECTIONS = [
        "EXECUTIVE SUMMARY", "PORTFOLIO RISK METRICS",
        "COVENANT BREACH", "REQUIRED ACTIONS"
    ]
    memo_upper = memo_text.upper()
    missing_sections = [s for s in REQUIRED_SECTIONS if s not in memo_upper]
    if missing_sections:
        check = {
            "check": "MEMO_COMPLETENESS",
            "passed": False,
            "detail": f"Credit memo missing required sections: {missing_sections}",
            "jim_rule": "The board needs to see everything — completeness is non-negotiable."
        }
        all_passed = False
    else:
        check = {"check": "MEMO_COMPLETENESS", "passed": True,
                 "detail": f"All {len(REQUIRED_SECTIONS)} required sections present."}
    results.append(check)

    # ── Check 5: Source Tag Minimum
    tag_count = memo_text.count("[DS]") + memo_text.count("[RA]") + memo_text.count("[PR]")
    if tag_count < 5:
        check = {
            "check": "SOURCE_TAGS",
            "passed": False,
            "detail": f"Memo has only {tag_count} source tags. Minimum 5 required for auditability.",
            "jim_rule": "You want to be able to back up and rerun — every claim must be traceable."
        }
        all_passed = False
    else:
        check = {"check": "SOURCE_TAGS", "passed": True,
                 "detail": f"{tag_count} source tags present — auditability satisfied."}
    results.append(check)

    # ── Check 6: Prompt Injection Scan
    # Jim: "people were injecting malicious prompts inside there, hidden"
    files_to_scan = {
        "portfolio_summary.json": json.dumps(portfolio or {}),
        "ratios.json":            json.dumps(ratios or {}),
        "credit_memo":            memo_text,
    }
    injection_clean = True
    injection_detail = ""
    for fname, content in files_to_scan.items():
        clean, msg = check_injection(content, fname)
        if not clean:
            injection_clean = False
            injection_detail = msg
            all_passed = False
            break

    results.append({
        "check": "PROMPT_INJECTION_SCAN",
        "passed": injection_clean,
        "detail": injection_detail if not injection_clean else "No injection patterns detected in any agent output.",
        "jim_rule": "Be very careful if the orchestrator is getting agent outputs — people try to inject."
    })

    # ── Write alert log
    os.makedirs("logs", exist_ok=True)
    alert = {
        "timestamp":  datetime.now(timezone.utc).isoformat(),
        "all_passed": all_passed,
        "checks":     results,
        "summary":    f"{sum(1 for c in results if c['passed'])}/{len(results)} checks passed"
    }
    with open("logs/circuit_breaker_alert.json", "w") as f:
        json.dump(alert, f, indent=2)

    # ── Print results
    print("\n── CIRCUIT BREAKER REPORT ──")
    for check in results:
        icon = "✓" if check["passed"] else "✗"
        print(f"  {icon} {check['check']}: {check['detail']}")

    if all_passed:
        print(f"\n✅ CIRCUIT BREAKER: ALL {len(results)} CHECKS PASSED — pipeline output is trustworthy")
    else:
        failed = [c for c in results if not c["passed"]]
        print(f"\n🛑 CIRCUIT BREAKER TRIGGERED: {len(failed)} check(s) failed")
        print("   Review logs/circuit_breaker_alert.json for details")
        print("   Do NOT present this output to the Risk Committee without resolving these issues")

    return alert


if __name__ == "__main__":
    run_circuit_breaker()
