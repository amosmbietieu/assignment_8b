#!/bin/bash
# setup_local.sh
# Lance ce script UNE SEULE FOIS pour préparer tout l'environnement local.
# Usage : bash setup_local.sh

set -e  # arrête au premier échec

echo ""
echo "════════════════════════════════════════════════════════"
echo "  SETUP LOCAL — Assignment 8-B"
echo "  Afiland First Bank Credit Analysis Pipeline"
echo "════════════════════════════════════════════════════════"

# ── Vérifier qu'on est dans le bon dossier
if [ ! -f "requirements.txt" ]; then
    echo ""
    echo "✗ ERREUR : requirements.txt introuvable."
    echo "  Tu n'es pas dans le bon dossier."
    echo ""
    echo "  Commande à exécuter :"
    echo "  cd ~/Documents/PK\\ Fokam/Cours\\ IA\\ Business\\ \\&\\ IA\\ Finance/assignment-8b"
    echo ""
    exit 1
fi

echo ""
echo "── Étape 1 : Dossier courant vérifié"
echo "   $(pwd)"

# ── Créer les dossiers et fichiers vides obligatoires
mkdir -p agents tests data logs output
touch agents/__init__.py
touch tests/__init__.py
touch logs/.gitkeep
touch output/.gitkeep
echo ""
echo "── Étape 2 : Dossiers et __init__.py créés"

# ── Installer les packages
echo ""
echo "── Étape 3 : Installation des packages Python..."
echo "   (2 à 5 minutes selon ta connexion)"
echo ""
python -m pip install -r requirements.txt --quiet --progress-bar on

# ── Vérifier les packages
echo ""
echo "── Étape 4 : Vérification des packages..."
python -c "
import importlib.metadata as meta
packages = ['anthropic', 'streamlit', 'plotly', 'pandas', 'pytest']
all_ok = True
for p in packages:
    try:
        v = meta.version(p)
        print(f'   ✓ {p} {v}')
    except:
        print(f'   ✗ {p} — NON INSTALLÉ')
        all_ok = False
if not all_ok:
    print('')
    print('   Certains packages manquent. Réessaie :')
    print('   python -m pip install -r requirements.txt')
    exit(1)
"

# ── Générer les données
echo ""
echo "── Étape 5 : Génération des données..."
python data/generate_data.py

# ── Tests pré-pipeline
echo ""
echo "── Étape 6 : Tests pré-pipeline..."
python -m pytest tests/test_agents.py::TestDataGeneration tests/test_agents.py::TestLogger -v --tb=short

echo ""
echo "════════════════════════════════════════════════════════"
echo "  SETUP TERMINÉ AVEC SUCCÈS"
echo ""
echo "  Prochaines commandes à exécuter :"
echo ""
echo "  1. Lancer le pipeline :"
echo "     python orchestrator.py --mock"
echo "     (appuie ENTER quand demandé)"
echo ""
echo "  2. Tests post-pipeline :"
echo "     python -m pytest tests/ -v"
echo ""
echo "  3. Dashboard :"
echo "     streamlit run dashboard.py"
echo "════════════════════════════════════════════════════════"
