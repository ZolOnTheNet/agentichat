# CLAUDE.md - Guide de Développement pour Claude Code

> 📋 Document de référence pour Claude Code travaillant sur le projet **agentichat**

## 🎯 Vue d'Ensemble du Projet

**agentichat** est un assistant IA autonome en ligne de commande qui permet aux utilisateurs d'interagir avec leurs fichiers, le web et leurs tâches via une IA agentique propulsée par Ollama ou Albert API.

### Caractéristiques Principales
- **Type**: CLI interactive avec boucle agentique
- **Backends supportés**: Ollama (local) et Albert API (Etalab)
- **Outils disponibles**: 18 outils (14 base + 4 Albert spécifiques)
- **Langage**: Python 3.11+
- **Architecture**: Modulaire avec backends extensibles

## 📂 Structure du Projet

```
agentichat/
├── src/agentichat/
│   ├── cli/              # Interface CLI
│   │   ├── app.py        # Point d'entrée principal et boucle REPL
│   │   ├── editor.py     # Éditeur multiline avec prompt_toolkit
│   │   └── confirmation.py  # Système de confirmations Y/N/A
│   ├── backends/         # Adaptateurs LLM
│   │   ├── base.py       # Classe de base abstraite
│   │   ├── ollama.py     # Backend Ollama
│   │   └── albert.py     # Backend Albert API
│   ├── config/           # Gestion de configuration
│   │   └── manager.py    # Chargement YAML, sélecteur de modèle
│   ├── core/             # Logique agentique
│   │   └── agent.py      # Boucle agentique et orchestration
│   ├── tools/            # Implémentation des 18 outils
│   │   ├── registry.py   # Registre central des outils
│   │   ├── file_ops.py   # 6 outils fichiers
│   │   ├── dir_ops.py    # 4 outils répertoires
│   │   ├── web_ops.py    # 2 outils web
│   │   ├── shell.py      # 1 outil shell
│   │   ├── todo.py       # 1 outil TODO
│   │   └── albert_ops.py # 4 outils Albert
│   └── utils/            # Utilitaires
│       ├── sandbox.py    # Validation des chemins et sécurité
│       └── logging.py    # Configuration des logs
├── docs/                 # Documentation technique
└── tests/                # Tests unitaires et d'intégration
```

## 🔑 Points d'Architecture Importants

### 1. Système de Backends Modulaire

Les backends suivent le pattern **Strategy** avec une classe de base abstraite:

```python
# backends/base.py
class LLMBackend(ABC):
    @abstractmethod
    async def chat(self, messages: List[Dict], tools: List[Dict]) -> Dict:
        """Point d'entrée principal pour chat avec tools"""
```

**Backends disponibles:**
- `OllamaBackend`: Streaming, local, rapide
- `AlbertBackend`: API distante, plus puissante, avec rate limiting

### 2. Système de Tools (Registre)

Tous les outils sont enregistrés dans `tools/registry.py`:

```python
TOOL_REGISTRY = {
    "read_file": {...},
    "write_file": {...},
    # ... 18 outils au total
}
```

**Convention de nommage:**
- Catégorie fichiers: `read_file`, `write_file`, `list_files`, `delete_file`, `search_text`, `glob_search`
- Catégorie répertoires: `create_directory`, `delete_directory`, `move_file`, `copy_file`
- Catégorie web: `web_fetch`, `web_search`
- Catégorie système: `shell_exec`
- Catégorie productivité: `todo_write`
- Catégorie Albert: `albert_search`, `albert_ocr`, `albert_transcription`, `albert_embeddings`

### 3. Boucle Agentique

La boucle agentique dans `core/agent.py` suit ce cycle:

```
1. Utilisateur envoie un message
2. Agent choisit des outils à appeler
3. Outils s'exécutent (avec confirmations si nécessaire)
4. Résultats retournés à l'agent
5. Agent répond ou continue (max 10 itérations)
```

**Points critiques:**
- Limite de 10 itérations par défaut (configurable)
- Confirmations pour opérations destructives
- Gestion du streaming pour Ollama

### 4. Système de Confirmations

Trois niveaux:
- **Y** (Yes): Confirmer cette action
- **N** (No): Refuser cette action
- **A** (Always): Confirmer toutes les actions restantes

Opérations nécessitant confirmation:
- `write_file`, `delete_file`, `delete_directory`
- `shell_exec`
- Configurable via `confirmations.text_operations` et `confirmations.shell_commands`

### 5. Sandbox de Sécurité

Le module `utils/sandbox.py` valide:
- Chemins en dehors du workspace (interdits)
- Fichiers sensibles (`.env`, `*.key`, etc.)
- Taille maximale des fichiers (1 MB par défaut)

## 🛠️ Conventions de Code

### Style Python
- **Formatage**: Utiliser `ruff format`
- **Linting**: `ruff check .`
- **Type hints**: Requis, vérifiés avec `mypy`
- **Docstrings**: Format Google style

### Nommage
- Modules: `snake_case`
- Classes: `PascalCase`
- Fonctions/méthodes: `snake_case`
- Constantes: `UPPER_SNAKE_CASE`

### Organisation des Imports
```python
# Standard library
import asyncio
from pathlib import Path

# Third-party
from rich.console import Console
import httpx

# Local
from agentichat.config import ConfigManager
from agentichat.tools import TOOL_REGISTRY
```

## 🔧 Commandes Utiles

### Développement
```bash
# Installation en mode développement
pip install -e ".[dev]"

# Lancer les tests
pytest

# Tests avec coverage
pytest --cov=src/agentichat --cov-report=html

# Linting et formatage
ruff check .
ruff format .

# Type checking
mypy src/
```

### Lancer l'Application
```bash
# Mode normal
agentichat

# Avec backend spécifique
agentichat --backend ollama
agentichat --backend albert

# Avec modèle spécifique
agentichat --model qwen2.5-coder:7b
```

## 🐛 Problèmes Connus et Solutions

### 1. Albert API Rate Limiting
**Symptôme:** `Quota API dépassé: 128000 input tokens per minute exceeded`
**Solution:**
- Automatiquement géré avec retry exponential backoff
- Utilisateur peut faire `/clear` pour réduire l'historique
- Basculer vers un modèle plus petit

### 2. Contrainte Single Tool (certains modèles Albert)
**Symptôme:** `only supports single tool-calls`
**Solution:**
- Détection automatique dans `backends/albert.py`
- Sauvegarde dans `~/.agentichat/model_metadata.json`
- Application automatique avec `max_parallel_tools: 1`

### 3. Timeouts avec Gros Modèles
**Symptôme:** `TimeoutError`
**Solution:** Augmenter `timeout` dans la config (défaut: 300s pour Ollama, 180s pour Albert)

## 📝 Fichiers de Configuration

### Emplacements (par priorité)
1. `.agentichat/config.yaml` (local au workspace)
2. `~/.agentichat/config.yaml` (global)

### Fichiers de Métadonnées
- `~/.agentichat/model_metadata.json`: Contraintes détectées automatiquement
- `~/.agentichat/agentichat.log`: Logs applicatifs

## 🚨 Points d'Attention lors des Modifications

### Ajout d'un Nouvel Outil
1. Créer la fonction dans le fichier approprié (`tools/*.py`)
2. Ajouter la définition dans `TOOL_REGISTRY` (`tools/registry.py`)
3. Ajouter des tests dans `tests/`
4. Mettre à jour la documentation dans `README.md`

### Ajout d'un Nouveau Backend
1. Créer une classe héritant de `LLMBackend` dans `backends/`
2. Implémenter les méthodes abstraites: `chat()`, `list_models()`, etc.
3. Ajouter le type dans `config/manager.py`
4. Documenter dans `README.md` et créer un doc spécifique si nécessaire

### Modification de la Boucle Agentique
⚠️ **Critique** - Tester exhaustivement:
- Gestion des erreurs et retries
- Limite d'itérations
- Streaming (Ollama)
- Confirmations utilisateur

## 📚 Documentation Importante

### Docs Principales
- `README.md`: Guide utilisateur complet (bilingue FR/EN)
- `docs/MODEL_ALBERT.md`: Liste et specs des modèles Albert
- `docs/QUICKSTART.md`: Guide de démarrage rapide
- `docs/CHANGELOG.md`: Historique des changements

### Docs de Phases (Historiques)
- `docs/PHASE1_COMPLETE.md`: Phase 1 - Configuration, Backend, CLI
- `docs/PHASE2_COMPLETE.md`: Phase 2 - Tools et Boucle Agentique

## 🔄 Workflow de Développement Typique

### Pour une Nouvelle Fonctionnalité
1. Créer une branche: `git checkout -b feature/nom-feature`
2. Implémenter avec tests
3. Vérifier qualité: `ruff check . && mypy src/ && pytest`
4. Commit: `git commit -m "feat: description"`
5. Push et PR

### Pour un Bug Fix
1. Reproduire le bug avec un test
2. Corriger le code
3. Vérifier que le test passe
4. Commit: `git commit -m "fix: description"`

## 💡 Astuces pour Claude Code

### Recherche de Code
```bash
# Trouver où un outil est défini
rg "def read_file" src/

# Trouver toutes les références à une classe
rg "OllamaBackend" src/

# Trouver les TODOs
rg "TODO|FIXME" src/
```

### Avant de Modifier
1. Lire le fichier concerné avec `Read`
2. Comprendre les dépendances (imports)
3. Vérifier s'il existe des tests
4. Modifier avec `Edit` (préférable à `Write` pour fichiers existants)

### Conventions de Commit
- `feat:` Nouvelle fonctionnalité
- `fix:` Correction de bug
- `docs:` Documentation seulement
- `refactor:` Refactoring sans changement de comportement
- `test:` Ajout ou modification de tests
- `chore:` Maintenance (deps, config, etc.)

## 🎓 Ressources Externes

- [Ollama API Docs](https://github.com/ollama/ollama/blob/main/docs/api.md)
- [Albert API Docs](https://albert.api.etalab.gouv.fr/docs)
- [Anthropic Tool Use Guide](https://docs.anthropic.com/claude/docs/tool-use)
- [Rich Terminal Formatting](https://rich.readthedocs.io/)
- [prompt_toolkit](https://python-prompt-toolkit.readthedocs.io/)

---

**Version:** 1.0
**Dernière mise à jour:** 2026-01-05
**Projet:** agentichat (anciennement llmchat)
