"""
generate_data.py
────────────────
WHY THIS FILE EXISTS:
  The assignment requires data. Real AFB data is confidential.
  We simulate a structurally realistic SME loan portfolio —
  same schema as production: borrower metadata, financial ratios,
  payment history, sector codes.

WHAT IT PRODUCES:
  data/portfolio.csv      — one row per loan (50 loans)
  data/transactions.json  — monthly payment events per loan (12 months)

RUN ONCE before any agent pipeline.
"""

import csv
import json
import random
import math
from datetime import date, timedelta

random.seed(42)  # reproducible results for the demo

# ── Sector distribution (weighted toward Afiland First Bank's Cameroon portfolio)
SECTORS = [
    ("Agriculture", 0.30),
    ("Retail Trade", 0.25),
    ("Manufacturing", 0.15),
    ("Transport", 0.12),
    ("Health Services", 0.08),
    ("Construction", 0.10),
]

REGIONS = ["Yaoundé", "Douala", "Bafoussam", "Garoua", "Maroua"]

def weighted_choice(choices):
    r = random.random()
    cumulative = 0.0
    for item, weight in choices:
        cumulative += weight
        if r < cumulative:
            return item
    return choices[-1][0]

def generate_portfolio(n=50):
    """
    Returns list of loan dicts.
    Key fields and WHY they matter for credit analysis:
      - exposure_xaf   : total outstanding principal (XAF)
      - dscr           : Debt Service Coverage Ratio = Net Operating Income / Debt Service
                         DSCR < 1.0 means borrower cannot cover payments from operations
                         DSCR > 1.25 is the AFB covenant minimum
      - ltv            : Loan-to-Value = outstanding / collateral value
                         LTV > 0.8 = under-collateralized
      - par90_flag     : True if any payment > 90 days past due (Portfolio at Risk)
      - dti            : Debt-to-Income ratio; > 0.45 is high risk
      - months_overdue : consecutive months with late payments
    """
    loans = []
    for i in range(n):
        loan_id = f"AFB-{10000 + i:05d}"
        sector = weighted_choice(SECTORS)
        region = random.choice(REGIONS)

        # Exposure: 500K to 50M XAF (small business range)
        exposure = round(random.uniform(500_000, 50_000_000), -3)

        # DSCR: normally distributed around 1.3, some distressed loans
        if random.random() < 0.15:          # 15% distressed
            dscr = round(random.uniform(0.60, 0.99), 2)
        elif random.random() < 0.20:        # 20% borderline
            dscr = round(random.uniform(1.00, 1.24), 2)
        else:                               # 65% healthy
            dscr = round(random.uniform(1.25, 2.40), 2)

        ltv = round(random.uniform(0.35, 0.95), 2)
        dti = round(random.uniform(0.15, 0.70), 2)

        # PAR90 correlated with DSCR
        par90 = dscr < 1.0 or (dscr < 1.15 and random.random() < 0.3)
        months_overdue = 0
        if par90:
            months_overdue = random.randint(1, 6)

        # Covenant status
        covenant_dscr_breach = dscr < 1.25
        covenant_ltv_breach  = ltv > 0.80

        disbursement_date = date(2023, 1, 1) + timedelta(days=random.randint(0, 365))
        maturity_date     = disbursement_date + timedelta(days=random.randint(365, 1825))

        loans.append({
            "loan_id":               loan_id,
            "borrower_name":         f"Enterprise {loan_id}",
            "sector":                sector,
            "region":                region,
            "exposure_xaf":          exposure,
            "dscr":                  dscr,
            "ltv":                   ltv,
            "dti":                   dti,
            "par90_flag":            par90,
            "months_overdue":        months_overdue,
            "covenant_dscr_breach":  covenant_dscr_breach,
            "covenant_ltv_breach":   covenant_ltv_breach,
            "disbursement_date":     str(disbursement_date),
            "maturity_date":         str(maturity_date),
            "loan_officer":          f"Officer-{random.randint(1, 8):02d}",
        })
    return loans

def generate_transactions(loans):
    """
    12 months of monthly payment events per loan.
    WHY: the Ratio Analyst agent needs payment history to compute PAR30/PAR90
    and to identify trend (improving vs. deteriorating borrower).
    """
    events = []
    for loan in loans:
        monthly_payment = round(loan["exposure_xaf"] * 0.025)   # ~2.5% monthly
        for month in range(1, 13):
            due_date = date(2024, month, 15)
            if loan["par90_flag"] and month > 9:
                # simulate late payment in last quarter
                days_late = random.randint(91, 150)
                paid_amount = round(monthly_payment * random.uniform(0.0, 0.5))
                status = "OVERDUE"
            elif loan["dscr"] < 1.25 and month > 6 and random.random() < 0.25:
                days_late = random.randint(1, 45)
                paid_amount = monthly_payment
                status = "LATE"
            else:
                days_late = 0
                paid_amount = monthly_payment
                status = "ON_TIME"
            events.append({
                "loan_id":        loan["loan_id"],
                "month":          month,
                "due_date":       str(due_date),
                "scheduled":      monthly_payment,
                "paid":           paid_amount,
                "days_late":      days_late,
                "status":         status,
            })
    return events

if __name__ == "__main__":
    import os
    os.makedirs("data", exist_ok=True)

    loans = generate_portfolio(50)

    # Write CSV
    with open("data/portfolio.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=loans[0].keys())
        writer.writeheader()
        writer.writerows(loans)

    # Write transactions JSON
    txns = generate_transactions(loans)
    with open("data/transactions.json", "w") as f:
        json.dump(txns, f, indent=2)

    print(f"Generated {len(loans)} loans → data/portfolio.csv")
    print(f"Generated {len(txns)} transactions → data/transactions.json")
    distressed = sum(1 for l in loans if l["par90_flag"])
    print(f"PAR90 loans: {distressed} / {len(loans)} ({100*distressed/len(loans):.1f}%)")
