# Résolution des problèmes — Guide chirurgical
## Pour Ubuntu/Linux avec conda + VSCode

---

## CE QUE DIT TON ÉCRAN ET CE QUE ÇA SIGNIFIE

```
(assignment8b) (base) mbietieu@precision5520:~/Documents/.../assignment-8b$
```

| Partie | Signification |
|---|---|
| `(assignment8b)` | Un environnement virtuel Python nommé `assignment8b` est activé |
| `(base)` | conda est aussi actif en arrière-plan |
| `mbietieu@precision5520` | Ton nom d'utilisateur et ta machine |
| `~/Documents/.../assignment-8b` | Ton dossier courant — le projet est ici |

**Problème 1 identifié :** `anthropic` non trouvé
→ L'environnement `assignment8b` existe mais les packages n'y sont **pas encore installés**.

**Problème 2 identifié :** `data/generate_data.py` introuvable
→ Les fichiers Python du projet ne sont **pas encore copiés** dans ce dossier.

---

## SOLUTION COMPLÈTE — À exécuter dans l'ordre exact

### BLOC A — Vérifier où tu en es

Ouvre un terminal dans VSCode (`Ctrl+` ` `) ou ton terminal Ubuntu.
Colle ces deux commandes une par une :

```bash
# Voir exactement quel Python est utilisé
which python

# Voir la liste des fichiers dans ton dossier actuel
ls -la
```

**Résultat attendu pour `which python` :**
```
/home/mbietieu/.../assignment8b/bin/python
```
ou quelque chose contenant `assignment8b`.

**Si tu vois `/usr/bin/python` ou `/home/mbietieu/anaconda3/bin/python`**
→ Le mauvais Python est actif. Suis le BLOC B.

---

### BLOC B — Corriger l'environnement Python

Tu as deux options. Choisis **l'option 1** (plus simple avec conda).

#### Option 1 : Utiliser conda directement (RECOMMANDÉ)

```bash
# Désactiver le venv actuel si activé
deactivate 2>/dev/null || true

# Créer un environnement conda propre pour ce projet
conda create -n afb8b python=3.11 -y

# Activer l'environnement
conda activate afb8b
```

Ton prompt doit maintenant afficher : `(afb8b) (base) mbietieu@...`

#### Option 2 : Corriger le venv existant

```bash
# Désactiver ce qui est actif
deactivate 2>/dev/null || true
conda deactivate 2>/dev/null || true

# Recréer le venv proprement
python3 -m venv ~/venvs/assignment8b

# Activer
source ~/venvs/assignment8b/bin/activate
```

---

### BLOC C — Aller dans le bon dossier

```bash
cd ~/Documents/PK\ Fokam/Cours\ IA\ Business\ \&\ IA\ Finance/assignment-8b
```

**Note les `\` devant les espaces** — obligatoire sur Linux.

Vérifie que tu es au bon endroit :
```bash
pwd
```
Doit afficher : `/home/mbietieu/Documents/PK Fokam/Cours IA Business & IA Finance/assignment-8b`

---

### BLOC D — Copier les fichiers du projet

Tu dois avoir tous ces fichiers dans ce dossier.
Vérifie d'abord ce qui est déjà là :

```bash
ls -la
```

**Si le dossier est vide ou incomplet**, tu dois y copier les fichiers.
Les fichiers sont dans l'archive que tu as téléchargée depuis Claude.

Structure exacte à obtenir :
```
assignment-8b/
├── requirements.txt
├── orchestrator.py
├── api_client.py
├── mock_client.py
├── logger.py
├── circuit_breaker.py
├── single_agent.py
├── dashboard.py
├── .env.example
├── .gitignore
├── README.md
├── agents/
│   ├── __init__.py        ← fichier VIDE, obligatoire
│   ├── data_scout.py
│   ├── evaluator.py
│   ├── policy_rag.py
│   ├── ratio_analyst.py
│   └── report_writer.py
├── data/
│   ├── generate_data.py
│   └── golden_dataset.json
├── tests/
│   ├── __init__.py        ← fichier VIDE, obligatoire
│   └── test_agents.py
├── logs/
│   └── .gitkeep           ← fichier VIDE, obligatoire
└── output/
    └── .gitkeep           ← fichier VIDE, obligatoire
```

**Créer les dossiers et fichiers vides obligatoires :**
```bash
mkdir -p agents tests data logs output
touch agents/__init__.py
touch tests/__init__.py
touch logs/.gitkeep
touch output/.gitkeep
```

---

### BLOC E — Installer les packages

Assure-toi que ton environnement est activé (tu vois `(afb8b)` ou `(assignment8b)` dans le prompt), puis :

```bash
pip install -r requirements.txt
```

**Durée : 2 à 5 minutes. Tu verras défiler beaucoup de lignes.**

**Vérification immédiate :**
```bash
python -c "import anthropic, streamlit, plotly, pandas; print('✓ Tous les packages OK')"
```

Doit afficher : `✓ Tous les packages OK`

---

### BLOC F — Générer les données

```bash
python data/generate_data.py
```

**Sortie attendue exacte :**
```
Generated 50 loans → data/portfolio.csv
Generated 600 transactions → data/transactions.json
PAR90 loans: 10 / 50 (20.0%)
```

---

### BLOC G — Tests pré-pipeline

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

---

### BLOC H — Pipeline complet

```bash
python orchestrator.py --mock
```

Quand le terminal affiche :
```
── HUMAN REVIEW REQUIRED ──
   Press ENTER to confirm human review...
   >
```
→ Appuie simplement sur **ENTER**.

**Durée totale : ~15 secondes.**

---

### BLOC I — Tests post-pipeline

```bash
python -m pytest tests/ -v
```

Doit afficher : **14 passed**

---

### BLOC J — Dashboard

```bash
streamlit run dashboard.py
```

Streamlit affiche une URL dans le terminal :
```
  Local URL: http://localhost:8501
```

Ton navigateur s'ouvre automatiquement. Sinon, colle l'URL manuellement.

Pour arrêter : `Ctrl+C` dans le terminal.

---

## PROBLÈMES FRÉQUENTS SUR UBUNTU

### "bash: pip: command not found"
```bash
python -m pip install -r requirements.txt
# Utilise python -m pip au lieu de pip seul
```

### "pip install" installe mais Python ne trouve pas le package
```bash
# Ton pip et ton python ne sont pas liés
# Vérifie :
which python
which pip
# Si les chemins sont différents → utilise :
python -m pip install -r requirements.txt
```

### VSCode n'utilise pas le bon Python
- Ouvre VSCode
- `Ctrl+Shift+P` → tape `Python: Select Interpreter`
- Choisis celui qui contient `afb8b` ou `assignment8b`
- Ferme et rouvre le terminal VSCode intégré (`Ctrl+` ` `)

### "conda: command not found" après `deactivate`
```bash
# Réinitialise conda
source ~/anaconda3/etc/profile.d/conda.sh
# ou
source ~/miniconda3/etc/profile.d/conda.sh
```

### "ModuleNotFoundError: No module named 'agents'"
```bash
# Tu n'es pas dans le bon dossier OU agents/__init__.py manque
pwd                              # vérifie le dossier
ls agents/__init__.py            # doit exister (même vide)
touch agents/__init__.py         # crée-le si manquant
```

### Le terminal affiche "(assignment8b) (base)" — les deux en même temps
C'est normal sur Ubuntu avec conda. Ça signifie :
- conda base est chargé en arrière-plan
- Le venv `assignment8b` est actif par-dessus

Pour vérifier lequel est vraiment utilisé :
```bash
which python
python -m pip list | grep anthropic
```
Si `anthropic` apparaît → tout va bien, continue.
Si `anthropic` n'apparaît pas → installe avec `python -m pip install -r requirements.txt`

---

## SÉQUENCE COMPLÈTE EN UN SEUL BLOC (copier-coller)

Si tu veux repartir de zéro proprement, copie-colle tout ce bloc dans ton terminal :

```bash
# 1. Naviguer dans le projet
cd ~/Documents/PK\ Fokam/Cours\ IA\ Business\ \&\ IA\ Finance/assignment-8b

# 2. Créer les dossiers et fichiers obligatoires
mkdir -p agents tests data logs output
touch agents/__init__.py tests/__init__.py logs/.gitkeep output/.gitkeep

# 3. Installer les packages dans l'environnement actif
python -m pip install -r requirements.txt

# 4. Vérifier les packages
python -c "import anthropic, streamlit, plotly, pandas; print('✓ Packages OK')"

# 5. Générer les données
python data/generate_data.py

# 6. Tests pré-pipeline
python -m pytest tests/test_agents.py::TestDataGeneration tests/test_agents.py::TestLogger -v

# 7. Pipeline complet (appuie ENTER quand demandé)
python orchestrator.py --mock

# 8. Tests post-pipeline
python -m pytest tests/ -v

# 9. Dashboard (Ctrl+C pour arrêter)
streamlit run dashboard.py
```

