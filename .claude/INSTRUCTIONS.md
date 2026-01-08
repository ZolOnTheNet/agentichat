# agentichat

**Assistant IA autonome en ligne de commande** avec support multi-backends (Ollama local, Albert API Etalab).

## 🎯 En Bref

CLI interactive permettant d'interagir avec un LLM qui a accès à 18 outils pour manipuler des fichiers, exécuter des commandes, rechercher sur le web, et gérer des tâches.

## 🏗️ Architecture

```
agentichat/
├── src/agentichat/
│   ├── cli/          # Interface CLI (app.py = point d'entrée)
│   ├── backends/     # Adaptateurs LLM (Ollama, Albert)
│   ├── config/       # Gestion config YAML
│   ├── core/         # Boucle agentique (agent.py)
│   ├── tools/        # 18 tools (fichiers, web, shell, etc.)
│   └── utils/        # Sandbox, logs, database
├── docs/             # Documentation
└── tests/            # Tests unitaires
```

## 🛠️ Stack Technique

- **Python:** 3.11+
- **UI Terminal:** Rich (markdown, spinners, couleurs)
- **Async:** asyncio pour les requêtes LLM
- **Config:** YAML + Pydantic dataclasses
- **Base de données:** SQLite (aiosqlite) pour historique
- **Backend LLM:** Ollama (local) ou Albert API (Etalab)

## 🔧 Outils Disponibles (18 tools)

### Fichiers (6)
- list_files, read_file, write_file, delete_file, search_text, glob_search

### Répertoires (4)
- create_directory, delete_directory, move_file, copy_file

### Web (2)
- web_fetch, web_search

### Système (1)
- shell_exec

### Productivité (1)
- todo_write

### Albert uniquement (4)
- albert_search, albert_ocr, albert_transcription, albert_embeddings

## 🎨 Fonctionnalités Récentes

- ✅ **Compression de conversation** avec options (--keep, --max)
- ✅ **Avertissement automatique** quand historique trop long
- ✅ **Configuration `/config compress`** pour auto-compression
- ✅ **Aide hiérarchique** `/help <topic>` (8 topics)
- ✅ **Échappement Rich markup** dans messages d'erreur

## 📝 Conventions de Code

- **Format:** `ruff format` (obligatoire)
- **Lint:** `ruff check .`
- **Type hints:** Obligatoires, vérifiés avec mypy
- **Docstrings:** Format Google style
- **Commits:** Conventionnels (feat:, fix:, docs:, refactor:, test:, chore:)

## 🗂️ Configuration

### Fichiers de Config
- Global: `~/.agentichat/config.yaml`
- Local: `.agentichat/config.yaml` (prioritaire)

### Structure Config
```yaml
default_backend: ollama
backends:
  ollama:
    type: ollama
    url: http://localhost:11434
    model: qwen2.5-coder:7b
  albert:
    type: albert
    url: https://albert.api.etalab.gouv.fr
    api_key: ${ALBERT_API_KEY}
    model: AgentPublic/llama3-instruct

compression:
  auto_enabled: false
  auto_threshold: 20
  auto_keep: 5
  warning_threshold: 0.75

max_iterations: 10
```

## 🧪 Tests & Qualité

```bash
# Tests
pytest
pytest --cov=src/agentichat --cov-report=html

# Linting
ruff check .
ruff format .

# Type checking
mypy src/

# Syntaxe rapide
python3 -m py_compile src/agentichat/cli/app.py
```

## 🚀 Lancement

```bash
# Installation dev
pip install -e ".[dev]"

# Lancer
agentichat
agentichat --backend ollama
agentichat --model qwen2.5-coder:7b
```

## 📚 Documentation Clé

- `CLAUDE.md` - Guide complet pour Claude Code
- `README.md` - Guide utilisateur (FR/EN)
- `docs/MODEL_ALBERT.md` - Liste des modèles Albert
- `NOUVELLES_FONCTIONNALITES_COMPRESSION.md` - Features compression

## 🐛 Problèmes Connus & Solutions

### Rate Limiting Albert
**Symptôme:** `128000 input tokens per minute exceeded`
**Solution:** Automatique avec retry + `/clear` ou modèle plus petit

### Contrainte Single Tool
**Symptôme:** `only supports single tool-calls`
**Solution:** Détection auto + sauvegarde dans `~/.agentichat/model_metadata.json`

### Rich Markup Error (Fixed)
**Symptôme:** `MarkupError: closing tag '[/dim]' at position X`
**Solution:** Échappement automatique des exceptions (ligne 494, 702, 739, 1814, 1990, 2271, 2319)

## 💡 Points d'Attention pour Claude

### Zones Sensibles
- **Boucle agentique** (`core/agent.py`) - Tester exhaustivement si modifié
- **Confirmations** (`cli/confirmation.py`) - Ne pas skip sans raison
- **Sandbox** (`utils/sandbox.py`) - Sécurité critique
- **Gestion erreurs** - Toujours échapper Rich markup dans exceptions

### Fichiers Fréquemment Modifiés
- `cli/app.py` - Commandes slash, REPL
- `backends/*.py` - Adaptateurs LLM
- `tools/*.py` - Implémentation des outils

### Avant de Modifier
1. Lire le fichier avec `Read`
2. Comprendre les dépendances
3. Vérifier s'il existe des tests
4. Modifier avec `Edit` (pas `Write`)

---

**Version:** 1.0
**Dernière mise à jour:** 2026-01-06
**Mainteneur:** garrigues
