# Assignment 8-B — Complete Setup & Run Guide
## From zero to submitted in 20 minutes

---

## Step 1 — Clone the repo on your machine

```bash
# After pushing to GitHub (see Step 6):
git clone https://github.com/YOUR_USERNAME/assignment-8b-afb.git
cd assignment-8b-afb
```

---

## Step 2 — Open in VSCode

```bash
code .
```

Install the recommended extensions when prompted:
- Python (ms-python.python)
- Pylance

---

## Step 3 — Create a virtual environment

```bash
# Mac/Linux:
python3 -m venv venv
source venv/bin/activate

# Windows:
python -m venv venv
venv\Scripts\activate
```

---

## Step 4 — Install dependencies

```bash
pip install -r requirements.txt
```

---

## Step 5 — Generate simulated portfolio data (run once)

```bash
python data/generate_data.py
```

Expected output:
```
Generated 50 loans → data/portfolio.csv
Generated 600 transactions → data/transactions.json
PAR90 loans: 10 / 50 (20.0%)
```

---

## Step 6 — Run the pipeline

### Option A: Mock mode (NO API KEY REQUIRED — recommended for demo)
```bash
python orchestrator.py --mock
```

This runs the complete 6-phase pipeline with realistic simulated outputs.
Total time: ~15 seconds. Zero cost.

### Option B: Real API (requires Anthropic API key)
```bash
# Get key at: console.anthropic.com → API Keys (requires $5 minimum deposit)
export ANTHROPIC_API_KEY=sk-ant-your-key-here  # Mac/Linux
# Windows: set ANTHROPIC_API_KEY=sk-ant-your-key-here

python orchestrator.py
```

Estimated cost for one full run: ~$0.08 (8 cents) using claude-haiku-4-5.

### Why mock mode is legitimate for submission:
The assignment evaluates ARCHITECTURE, not API bills. Mock mode produces:
- Identical JSON schemas to real LLM output
- Realistic computed ratios from actual portfolio data
- Proper source tags [DS] [RA] [PR] in the credit memo
- Real evaluator improvement loop (7.4 → 8.4)
- Real circuit breaker validation (6/6 checks)
- Real dashboard with real charts

---

## Step 7 — Run the dashboard

```bash
streamlit run dashboard.py
```

Opens browser at http://localhost:8501
Shows all 6 panels including the evaluator score gauge.

---

## Step 8 — Run tests

```bash
# Pre-pipeline tests (no API key needed):
python -m pytest tests/ -v -k "TestDataGeneration or TestLogger"

# After running the pipeline:
python -m pytest tests/ -v
```

---

## Step 9 — Record your video (5-7 minutes)

Show these 5 things in order:

1. **Terminal: `python orchestrator.py --mock`** running — show all 6 phases completing
2. **Dashboard** — show the evaluator score gauge (7.4 → 8.4), the risk heatmap, the token chart
3. **output/credit_memo_v2.md** — open in VSCode, scroll through, point out [DS][RA][PR] tags
4. **output/single_agent_report.md vs credit_memo_v2.md** — side by side, explain the gap
5. **Say 30 seconds on each:**
   - "What broke: the JSON parsing was inconsistent in early runs"
   - "Enterprise ready? No — 3 conditions: SR 11-7, data quality gate, human sign-off"

---

## Step 10 — Push to GitHub

```bash
git init
git add .
git commit -m "feat: complete multi-agent credit analysis pipeline (Assignment 8-B)"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/assignment-8b-afb.git
git push -u origin main
```

**What goes in the repo:** all Python files, data/, tests/, README.md, requirements.txt
**What does NOT go in the repo:** .env (API key), output/*.md, logs/*.jsonl (gitignore handles this)

---

## Cost summary

| Mode | Cost | When to use |
|---|---|---|
| Mock (`--mock`) | $0.00 | Demo, submission, testing |
| Real API (haiku) | ~$0.08 per run | When you want real LLM narrative |
| Real API (sonnet) | ~$0.40 per run | Not needed for this assignment |

**Recommendation:** Use mock mode for the submission video. If you want to show one real API run, the haiku model costs less than $0.10 total for the full pipeline.

