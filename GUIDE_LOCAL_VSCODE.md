# Guide Local VSCode — Assignment 8-B
## Du dossier vide au pipeline fonctionnel, commande par commande

---

## STRUCTURE EXACTE DU PROJET

Voici ce que tu vas avoir sur ta machine. Chaque fichier a une raison d'être précise.

```
assignment-8b-afb/                  ← racine du projet = ton dossier VSCode
│
├── .env.example                    ← modèle de fichier de clé API (jamais commité)
├── .gitignore                      ← liste ce qui ne va PAS sur GitHub
├── README.md                       ← description du projet pour GitHub
├── SETUP_AND_RUN.md                ← guide de soumission
├── GUIDE_LOCAL_VSCODE.md           ← CE FICHIER
├── requirements.txt                ← liste des packages Python à installer
│
├── .vscode/
│   └── launch.json                 ← boutons Run/Debug dans VSCode (F5)
│
├── agents/                         ← les 5 agents spécialisés
│   ├── __init__.py                 ← VIDE mais obligatoire — dit à Python que
│   │                                  c'est un package importable
│   ├── data_scout.py               ← Agent 1 : extraction données brutes
│   ├── ratio_analyst.py            ← Agent 2 : calcul des ratios financiers
│   ├── policy_rag.py               ← Agent 3 : récupération politique AFB
│   ├── report_writer.py            ← Agent 4 : rédaction du mémo de crédit
│   └── evaluator.py                ← Agent 5 : scoring + boucle d'amélioration
│
├── data/                           ← données d'entrée
│   ├── generate_data.py            ← génère portfolio.csv et transactions.json
│   ├── portfolio.csv               ← 50 prêts SME (généré, non commité)
│   ├── transactions.json           ← 600 paiements mensuels (généré, non commité)
│   └── golden_dataset.json         ← 3 scénarios vérifiés à la main (commité)
│
├── tests/
│   ├── __init__.py                 ← VIDE mais obligatoire
│   └── test_agents.py              ← 14 tests automatisés
│
├── logs/                           ← auto-généré par le pipeline
│   ├── .gitkeep                    ← fichier vide qui force git à commiter ce dossier
│   ├── agent_calls.jsonl           ← 1 ligne JSON par appel API (non commité)
│   └── circuit_breaker_alert.json  ← résultat des 6 vérifications (non commité)
│
├── output/                         ← auto-généré par le pipeline
│   ├── .gitkeep                    ← idem
│   ├── portfolio_summary.json      ← sortie de DataScout
│   ├── ratios.json                 ← sortie de RatioAnalyst
│   ├── policy_context.json         ← sortie de PolicyRAG
│   ├── credit_memo.md              ← mémo v1 (sortie de ReportWriter)
│   ├── credit_memo_v2.md           ← mémo v2 (après feedback évaluateur)
│   ├── eval_scores_v1.json         ← scores itération 1
│   ├── eval_scores_v2.json         ← scores itération 2
│   ├── eval_scores.json            ← comparaison v1 vs v2 + delta
│   ├── pipeline_results.json       ← timing et tokens de tout le pipeline
│   └── single_agent_report.md      ← rapport baseline agent unique
│
├── api_client.py                   ← wrapper Anthropic API partagé par tous les agents
├── mock_client.py                  ← réponses simulées réalistes (mode sans API key)
├── logger.py                       ← logger JSONL partagé + LogAnalyzer
├── circuit_breaker.py              ← 6 vérifications post-pipeline (Jim's stop button)
├── single_agent.py                 ← baseline : 1 seul agent, 1 seul appel API
├── orchestrator.py                 ← coordinateur central du pipeline
└── dashboard.py                    ← dashboard Streamlit pour le Board
```

---

## ÉTAPE 1 — Installer Python et VSCode

### Vérifier que Python est installé
Ouvre un terminal (PowerShell sur Windows, Terminal sur Mac) et tape :

```bash
python --version
# Doit afficher : Python 3.10.x ou 3.11.x ou 3.12.x
# Si erreur → installer depuis python.org
```

### Installer VSCode
Si pas déjà installé : https://code.visualstudio.com/download

### Extensions VSCode à installer (une seule fois)
Dans VSCode, appuie sur `Ctrl+Shift+X` (ou `Cmd+Shift+X` sur Mac) et installe :
- **Python** (éditeur : Microsoft) — obligatoire
- **Pylance** (éditeur : Microsoft) — obligatoire

---

## ÉTAPE 2 — Créer le dossier du projet

```bash
# Mac/Linux — dans ton terminal :
mkdir -p ~/Desktop/assignment-8b-afb
cd ~/Desktop/assignment-8b-afb

# Windows — dans PowerShell :
mkdir $env:USERPROFILE\Desktop\assignment-8b-afb
cd $env:USERPROFILE\Desktop\assignment-8b-afb
```

---

## ÉTAPE 3 — Ouvrir dans VSCode

```bash
code .
```

VSCode s'ouvre sur le dossier vide. Tu verras l'explorateur de fichiers à gauche.

---

## ÉTAPE 4 — Copier les fichiers du projet

Copie TOUS les fichiers que tu as reçus dans ce dossier.
La structure doit correspondre exactement au schéma ci-dessus.

**Points critiques :**
- Le dossier `agents/` doit contenir `__init__.py` (fichier vide)
- Le dossier `tests/` doit contenir `__init__.py` (fichier vide)
- Le dossier `logs/` doit exister avec `.gitkeep` à l'intérieur
- Le dossier `output/` doit exister avec `.gitkeep` à l'intérieur

**Vérification rapide — dans le terminal VSCode (`Ctrl+` ` `) :**

```bash
# Mac/Linux :
ls agents/       # doit afficher __init__.py + les 5 agents
ls tests/        # doit afficher __init__.py + test_agents.py
ls logs/         # doit afficher .gitkeep
ls output/       # doit afficher .gitkeep

# Windows :
dir agents\
dir tests\
dir logs\
dir output\
```

---

## ÉTAPE 5 — Créer l'environnement virtuel

Un environnement virtuel = un Python isolé juste pour ce projet.
C'est obligatoire pour éviter les conflits avec d'autres projets.

```bash
# Mac/Linux :
python3 -m venv venv
source venv/bin/activate

# Windows PowerShell :
python -m venv venv
.\venv\Scripts\Activate.ps1

# Windows Command Prompt :
python -m venv venv
venv\Scripts\activate.bat
```

**Signe que c'est activé :** ton terminal affiche `(venv)` au début de chaque ligne.

**Dans VSCode :** appuie sur `Ctrl+Shift+P` → tape `Python: Select Interpreter`
→ choisis `./venv/bin/python` (Mac/Linux) ou `./venv/Scripts/python.exe` (Windows)

---

## ÉTAPE 6 — Installer les dépendances

```bash
pip install -r requirements.txt
```

Tu verras défiler l'installation de : anthropic, streamlit, plotly, pandas, pytest.

**Durée : 1 à 3 minutes selon ta connexion.**

**Vérification :**
```bash
python -c "import anthropic, streamlit, plotly, pandas; print('OK')"
# Doit afficher : OK
```

---

## ÉTAPE 7 — Générer les données

```bash
python data/generate_data.py
```

**Sortie attendue :**
```
Generated 50 loans → data/portfolio.csv
Generated 600 transactions → data/transactions.json
PAR90 loans: 10 / 50 (20.0%)
```

**Vérification :**
```bash
# Mac/Linux :
wc -l data/portfolio.csv      # doit afficher 51 (1 header + 50 lignes)
wc -l data/transactions.json  # doit afficher 3604 lignes environ

# Windows :
find /c /v "" data\portfolio.csv
```

---

## ÉTAPE 8 — Lancer les tests de base

Ces tests vérifient la structure du projet AVANT de lancer le pipeline.
Aucune clé API requise.

```bash
python -m pytest tests/test_agents.py::TestDataGeneration tests/test_agents.py::TestLogger -v
```

**Sortie attendue :**
```
tests/test_agents.py::TestDataGeneration::test_portfolio_csv_exists PASSED
tests/test_agents.py::TestDataGeneration::test_portfolio_has_50_rows PASSED
tests/test_agents.py::TestDataGeneration::test_portfolio_required_columns PASSED
tests/test_agents.py::TestDataGeneration::test_transactions_json_exists PASSED
tests/test_agents.py::TestDataGeneration::test_transactions_structure PASSED
tests/test_agents.py::TestLogger::test_log_call_writes_parseable_json PASSED
tests/test_agents.py::TestLogger::test_log_analyzer_summary PASSED
7 passed
```

Si un test échoue ici → stop, corrige avant d'aller plus loin.

---

## ÉTAPE 9 — Lancer le pipeline complet (mode mock)

```bash
python orchestrator.py --mock
```

**Ce que tu verras dans le terminal (14-16 secondes) :**

```
[MOCK MODE] Running without API key — realistic simulated outputs

════════════════════════════════════════════════════════════
  ASSIGNMENT 8-B: MULTI-AGENT CREDIT ANALYSIS PIPELINE
  Afiland First Bank — Q4 2024 Portfolio Quality Report
════════════════════════════════════════════════════════════

── PHASE 1: DATA EXTRACTION ──
[DataScout] ✓ Portfolio summary saved → output/portfolio_summary.json
           Total loans: 50  |  PAR90 loans: 10  |  Covenant breaches: 15

── PHASE 2: RATIO COMPUTATION ──
[RatioAnalyst] ✓ Ratios saved → output/ratios.json
             NPL ratio: 17.35%  |  PAR90 ratio: 20.0%  |  Alerts: 3

── PHASE 3: POLICY RETRIEVAL ──
[PolicyRAG] ✓ Policy context saved → output/policy_context.json
           Sections cited: [S1.2, S4.2, S3.1, S1.1, S6.1]

── PHASE 4: REPORT GENERATION ──
[ReportWriter] ✓ Credit memo saved → output/credit_memo.md

── PHASE 5: EVALUATOR-OPTIMIZER LOOP ──
[Evaluator] ✓ Iteration 1 — Overall score: 7.4/10
[Evaluator] ✓ Iteration 2 — Overall score: 8.4/10
   Score v1: 7.4/10  →  Score v2: 8.4/10  (Δ = 1.0)

── PHASE 6: CIRCUIT BREAKER + HUMAN REVIEW GATE ──
  ✓ PAR90_CONSISTENCY    ✓ NPL_CONSISTENCY    ✓ ALERT_NON_SILENCE
  ✓ MEMO_COMPLETENESS    ✓ SOURCE_TAGS        ✓ PROMPT_INJECTION_SCAN
✅ CIRCUIT BREAKER: ALL 6 CHECKS PASSED

── HUMAN REVIEW REQUIRED ──
   Press ENTER to confirm human review...
   > [appuie sur ENTER]

Run the dashboard:  streamlit run dashboard.py
```

**Après le pipeline, vérifier les fichiers produits :**

```bash
# Mac/Linux :
ls -la output/
# Windows :
dir output\
```

Tu dois voir 8 fichiers non-vides dans output/ :
portfolio_summary.json, ratios.json, policy_context.json,
credit_memo.md, credit_memo_v2.md, eval_scores.json,
eval_scores_v1.json, eval_scores_v2.json, pipeline_results.json

---

## ÉTAPE 10 — Lancer les tests complets post-pipeline

```bash
python -m pytest tests/ -v
```

**Sortie attendue : 14 passed, 0 failed, 0 errors**

---

## ÉTAPE 11 — Lancer le dashboard

```bash
streamlit run dashboard.py
```

**Streamlit ouvre automatiquement ton navigateur à http://localhost:8501**

Tu verras 6 sections :
1. Pipeline KPIs (latence, calls, tokens)
2. Evaluator Score Gauge (7.4 → 8.4)
3. Top-risk borrowers table
4. Sector concentration chart
5. Agent performance log
6. Full credit memo

**Pour arrêter Streamlit :** `Ctrl+C` dans le terminal

---

## ÉTAPE 12 — Lire les fichiers de sortie dans VSCode

Ouvre chaque fichier dans VSCode pour comprendre ce que chaque agent produit :

```
output/portfolio_summary.json   ← ce que DataScout a extrait
output/ratios.json              ← ce que RatioAnalyst a calculé
output/policy_context.json      ← ce que PolicyRAG a cité
output/credit_memo.md           ← mémo v1 (avant amélioration)
output/credit_memo_v2.md        ← mémo v2 (après boucle d'amélioration)
output/eval_scores.json         ← scores des 2 itérations + delta
logs/agent_calls.jsonl          ← 1 ligne = 1 appel API (tokens, latence)
logs/circuit_breaker_alert.json ← résultat des 6 vérifications
```

**Pour lire les fichiers JSON joliment dans VSCode :**
Ouvre le fichier → `Shift+Alt+F` (Mac: `Shift+Option+F`) → formatage automatique

---

## ÉTAPE 13 — Résolution des problèmes fréquents

### "python: command not found" (Mac/Linux)
```bash
python3 orchestrator.py --mock
# Remplace python par python3 dans toutes les commandes
```

### "ModuleNotFoundError: No module named 'anthropic'"
```bash
# L'environnement virtuel n'est pas activé
source venv/bin/activate          # Mac/Linux
.\venv\Scripts\Activate.ps1       # Windows
pip install -r requirements.txt   # puis réinstaller
```

### "ModuleNotFoundError: No module named 'agents'"
```bash
# Tu n'es pas dans le bon dossier
pwd                               # Mac/Linux : affiche le dossier actuel
cd                                # Windows : affiche le dossier actuel
# Assure-toi d'être dans assignment-8b-afb/
# Vérifie que agents/__init__.py existe
ls agents/__init__.py
```

### Le dashboard s'ouvre mais ne montre rien
```bash
# Le pipeline n'a pas été lancé ou output/ est vide
python orchestrator.py --mock
# Puis relancer streamlit
streamlit run dashboard.py
```

### "Execution Policy" sur Windows PowerShell
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
# Puis réactiver le venv :
.\venv\Scripts\Activate.ps1
```

---

## RAPPEL : ordre exact des commandes du début à la fin

```bash
# 1. Aller dans le dossier
cd ~/Desktop/assignment-8b-afb

# 2. Créer et activer l'environnement virtuel
python3 -m venv venv
source venv/bin/activate        # Windows: .\venv\Scripts\Activate.ps1

# 3. Installer les dépendances
pip install -r requirements.txt

# 4. Générer les données
python data/generate_data.py

# 5. Tests pré-pipeline (doit afficher 7 passed)
python -m pytest tests/test_agents.py::TestDataGeneration tests/test_agents.py::TestLogger -v

# 6. Lancer le pipeline
python orchestrator.py --mock

# 7. Tests post-pipeline (doit afficher 14 passed)
python -m pytest tests/ -v

# 8. Dashboard
streamlit run dashboard.py
```

