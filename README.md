# agentichat

> 📖 **Version française** ci-dessous. [English version below](#english-version) ⬇️

**Assistant IA autonome dans votre terminal** - Interagissez avec vos fichiers, le web et vos tâches grâce à une IA agentique propulsée par Ollama ou Albert API.

## ✨ Fonctionnalités

- 🤖 **IA Agentique**: Assistant autonome avec 18 outils intégrés (14 base + 4 Albert)
- 📁 **Opérations Fichiers**: Lire, écrire, chercher, lister fichiers et répertoires
- 🌐 **Accès Web**: Récupérer des URLs et rechercher sur le web (DuckDuckGo)
- 📋 **Gestion de Tâches**: Liste TODO intégrée avec suivi de statut
- 🔄 **Interface Interactive**: Stats temps réel, confirmations, sélecteur de modèle
- 🔒 **Sécurisé**: Opérations fichiers en sandbox avec confirmations utilisateur
- ⚡ **Rapide**: Optimisé pour Ollama avec support du streaming
- 🇫🇷 **Albert API**: Support de l'API Albert (Etalab) avec outils spécialisés

## 🚀 Démarrage Rapide

### Prérequis

- Python 3.11+
- [Ollama](https://ollama.ai/) installé et en cours d'exécution OU
- Un compte [Albert API](https://albert.api.etalab.gouv.fr) (service public français)

### Installation

```bash
# Installation depuis les sources
git clone <repository>
cd agentichat
python -m venv .venv
source .venv/bin/activate  # ou `.venv\Scripts\activate` sous Windows
pip install -e .
```

### Premier Lancement

```bash
agentichat
```

Au premier lancement, le programme va:
1. Détecter si votre modèle configuré est invalide
2. Afficher un sélecteur de modèle interactif
3. Sauvegarder votre choix dans la configuration

## 🛠️ Outils Disponibles

L'assistant IA a accès à 18 outils organisés par catégorie:

### 📁 Fichiers (6 outils)
- `read_file` - Lire le contenu d'un fichier
- `write_file` - Créer ou modifier des fichiers
- `list_files` - Lister le contenu d'un répertoire
- `delete_file` - Supprimer des fichiers
- `search_text` - Chercher du texte avec regex
- `glob_search` - Trouver des fichiers par pattern (ex: `*.py`, `**/*.js`)

### 📂 Répertoires (4 outils)
- `create_directory` - Créer des répertoires
- `delete_directory` - Supprimer des répertoires
- `move_file` - Déplacer/renommer fichiers ou répertoires
- `copy_file` - Copier fichiers ou répertoires

### 🌐 Web (2 outils)
- `web_fetch` - Récupérer le contenu d'URLs
- `web_search` - Rechercher sur le web (DuckDuckGo)

### 💻 Système (1 outil)
- `shell_exec` - Exécuter des commandes shell

### 📋 Productivité (1 outil)
- `todo_write` - Gérer des listes de tâches avec suivi de statut

### ⚡ Albert API uniquement (4 outils supplémentaires)
- `albert_search` - Recherche sémantique dans collections de documents
- `albert_ocr` - Extraire du texte depuis images/PDFs
- `albert_transcription` - Convertir audio en texte
- `albert_embeddings` - Créer des embeddings texte pour similarité

## 💬 Utilisation

### Mode Interactif

```bash
agentichat
```

Posez simplement des questions en langage naturel:
```
> Liste tous les fichiers Python dans ce répertoire
> Lis le fichier config et explique ce qu'il fait
> Recherche sur le web "Ollama function calling"
> Crée une liste TODO pour ce projet
```

L'IA utilisera automatiquement les outils appropriés pour compléter vos requêtes.

### Commandes

#### Commandes Générales
- `/help` - Afficher l'aide
- `/quit`, `/exit`, `/q` - Quitter
- `/clear` - Réinitialiser la conversation
- `/config` - Afficher la configuration
- `/config backend list` - Lister les backends disponibles
- `/config backend <nom>` - Changer de backend (ollama/albert)

#### Commandes Ollama
- `/ollama list` - Lister les modèles disponibles
- `/ollama run <modèle>` - Changer de modèle
- `/ollama show <modèle>` - Afficher les détails d'un modèle
- `/ollama ps` - Afficher les modèles en cours d'exécution

#### Commandes Albert
- `/albert list` - Lister les modèles Albert disponibles
- `/albert run <modèle>` - Changer de modèle Albert
- `/albert show <modèle>` - Afficher les détails d'un modèle
- `/albert usage` - Afficher les statistiques d'utilisation
- `/albert me` - Afficher les informations du compte

### Raccourcis Clavier

- `Enter` - Envoyer le message
- `Alt+Enter` ou `Ctrl+J` - Nouvelle ligne
- `↑` / `↓` - Naviguer dans l'historique (sur première/dernière ligne)
- `Esc` - Effacer l'entrée actuelle
- `Ctrl+D` - Quitter

## ⚙️ Configuration

Fichiers de configuration (par ordre de priorité):
1. `.agentichat/config.yaml` (local au workspace)
2. `~/.agentichat/config.yaml` (global)

### Configuration de Base (Ollama)

```yaml
default_backend: ollama

backends:
  ollama:
    type: ollama
    url: http://localhost:11434
    model: qwen2.5-coder:7b
    temperature: 0.7
    max_tokens: 4096
    timeout: 300

sandbox:
  max_file_size: 1000000  # 1 MB
  blocked_paths:
    - "**/.env"
    - "**/*.key"

confirmations:
  text_operations: true
  shell_commands: true

max_iterations: 10
```

### Utiliser Albert API (Etalab)

Albert est une API de service public français avec fonctionnalités avancées:

```yaml
default_backend: albert

backends:
  albert:
    type: albert
    url: https://albert.api.etalab.gouv.fr
    model: mistralai/Mistral-Small-3.2-24B-Instruct-2506
    api_key: VOTRE_CLE_API  # Obtenir sur albert.api.etalab.gouv.fr
    temperature: 0.7
    max_tokens: 4096
    timeout: 180  # Augmenté pour gros modèles
    # max_parallel_tools: 1  # Détecté automatiquement si besoin
```

**Modèles Albert disponibles** (voir `docs/MODEL_ALBERT.md`):
- `meta-llama/Llama-3.1-8B-Instruct` (8B, rapide)
- `mistralai/Mistral-Small-3.2-24B-Instruct-2506` (24B, puissant)
- `Qwen/Qwen2.5-Coder-32B-Instruct-AWQ` (32B, spécialisé code)
- Et plus...

**Détection automatique des contraintes:**
- Le programme détecte automatiquement les limitations des modèles (ex: un seul tool à la fois)
- Les contraintes sont sauvegardées dans `~/.agentichat/model_metadata.json`
- Appliquées automatiquement au prochain lancement

## 🏗️ Architecture

```
agentichat/
├── src/agentichat/
│   ├── cli/           # Interface CLI (app, éditeur, confirmations)
│   ├── backends/      # Adaptateurs LLM (Ollama, Albert, extensible)
│   ├── config/        # Gestion de configuration
│   ├── core/          # Boucle agentique et orchestration
│   ├── tools/         # Implémentations des outils (14 base + 4 Albert)
│   └── utils/         # Sandbox, logging, helpers
└── docs/              # Documentation
```

## 🔐 Sécurité

- **Sandbox**: Toutes les opérations fichiers sont validées contre les chemins autorisés
- **Confirmations**: Les opérations destructives (suppression, shell) nécessitent approbation
- **Transparence**: Tous les appels d'outils sont loggés et visibles

## 🎯 Comparaison avec Autres Outils

| Outil | Type | Cas d'Usage |
|------|------|-------------|
| `llm` (Simon Willison) | Outil CLI de prompt | Prompts rapides, scriptable |
| `llama-agents` | Framework multi-agents | Construire systèmes agents complexes |
| `agentichat` | **CLI Agentique** | **Assistant autonome prêt à l'emploi** |

**agentichat** comble le fossé entre le prompting simple et les frameworks complexes - c'est un assistant autonome qui fonctionne immédiatement.

## 🧪 Développement

### Lancer les Tests

```bash
pip install -e ".[dev]"
pytest
```

### Qualité du Code

```bash
# Linting
ruff check .
ruff format .

# Vérification de types
mypy src/
```

## 🐛 Gestion des Erreurs Communes

### Rate Limit API Albert
```
⚠ Quota API dépassé: 128000 input tokens per minute exceeded
```
**Solutions:**
- Attendez ~60 secondes
- Utilisez `/clear` pour réduire l'historique
- Utilisez un modèle plus petit

### Contrainte Single Tool
```
⚠ Contrainte détectée: only supports single tool-calls
```
**Solution:** Automatiquement sauvegardée et appliquée au prochain lancement.

### Timeout
```
TimeoutError
```
**Solutions:**
- Augmentez `timeout: 180` dans config
- Utilisez un modèle plus rapide

## 📝 Licence

MIT

## 🙏 Remerciements

Construit avec:
- [Ollama](https://ollama.ai/) - Runtime LLM local
- [Rich](https://github.com/Textualize/rich) - Formatage terminal
- [prompt_toolkit](https://github.com/prompt-toolkit/python-prompt-toolkit) - CLI interactive
- [Albert API](https://albert.api.etalab.gouv.fr) - API IA service public français

---

# English Version

**Autonomous AI assistant in your terminal** - Talk to your files, the web, and your tasks with agentic AI powered by Ollama or Albert API.

## ✨ Features

- 🤖 **Agentic AI**: Autonomous assistant with 18 built-in tools (14 base + 4 Albert)
- 📁 **File Operations**: Read, write, search, list files and directories
- 🌐 **Web Access**: Fetch URLs and search the web (DuckDuckGo)
- 📋 **Task Management**: Built-in TODO list with status tracking
- 🔄 **Interactive UX**: Real-time stats, confirmations, model selector
- 🔒 **Secure**: Sandboxed file operations with user confirmations
- ⚡ **Fast**: Optimized for Ollama with streaming support
- 🇫🇷 **Albert API**: Support for Albert API (Etalab) with specialized tools

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- [Ollama](https://ollama.ai/) installed and running OR
- An [Albert API](https://albert.api.etalab.gouv.fr) account (French public service)

### Installation

```bash
# Install from source
git clone <repository>
cd agentichat
python -m venv .venv
source .venv/bin/activate  # or `.venv\Scripts\activate` on Windows
pip install -e .
```

### First Run

```bash
agentichat
```

On first run, the program will:
1. Detect if your configured model is invalid
2. Show an interactive model selector
3. Save your choice to configuration

## 🛠️ Available Tools

The AI assistant has access to 18 tools organized by category:

### 📁 Files (6 tools)
- `read_file` - Read file contents
- `write_file` - Create or modify files
- `list_files` - List directory contents
- `delete_file` - Delete files
- `search_text` - Search text with regex
- `glob_search` - Find files by pattern (e.g., `*.py`, `**/*.js`)

### 📂 Directories (4 tools)
- `create_directory` - Create directories
- `delete_directory` - Remove directories
- `move_file` - Move/rename files or directories
- `copy_file` - Copy files or directories

### 🌐 Web (2 tools)
- `web_fetch` - Fetch content from URLs
- `web_search` - Search the web (DuckDuckGo)

### 💻 System (1 tool)
- `shell_exec` - Execute shell commands

### 📋 Productivity (1 tool)
- `todo_write` - Manage task lists with status tracking

### ⚡ Albert API only (4 additional tools)
- `albert_search` - Semantic search in document collections
- `albert_ocr` - Extract text from images/PDFs
- `albert_transcription` - Convert audio to text
- `albert_embeddings` - Create text embeddings for similarity

## 💬 Usage

### Interactive Mode

```bash
agentichat
```

Just ask natural language questions:
```
> List all Python files in this directory
> Read the config file and explain what it does
> Search the web for "Ollama function calling"
> Create a TODO list for this project
```

The AI will automatically use the appropriate tools to complete your requests.

### Commands

#### General Commands
- `/help` - Show help
- `/quit`, `/exit`, `/q` - Quit
- `/clear` - Reset conversation
- `/config` - Show configuration
- `/config backend list` - List available backends
- `/config backend <name>` - Switch backend (ollama/albert)

#### Ollama Commands
- `/ollama list` - List available models
- `/ollama run <model>` - Switch model
- `/ollama show <model>` - Show model details
- `/ollama ps` - Show running models

#### Albert Commands
- `/albert list` - List available Albert models
- `/albert run <model>` - Switch Albert model
- `/albert show <model>` - Show model details
- `/albert usage` - Show usage statistics
- `/albert me` - Show account information

### Keyboard Shortcuts

- `Enter` - Send message
- `Alt+Enter` or `Ctrl+J` - New line
- `↑` / `↓` - Navigate history (on first/last line)
- `Esc` - Clear current input
- `Ctrl+D` - Quit

## ⚙️ Configuration

Configuration file locations (in priority order):
1. `.agentichat/config.yaml` (workspace local)
2. `~/.agentichat/config.yaml` (global)

### Basic Configuration (Ollama)

```yaml
default_backend: ollama

backends:
  ollama:
    type: ollama
    url: http://localhost:11434
    model: qwen2.5-coder:7b
    temperature: 0.7
    max_tokens: 4096
    timeout: 300

sandbox:
  max_file_size: 1000000  # 1 MB
  blocked_paths:
    - "**/.env"
    - "**/*.key"

confirmations:
  text_operations: true
  shell_commands: true

max_iterations: 10
```

### Using Albert API (Etalab)

Albert is a French public service API providing advanced features:

```yaml
default_backend: albert

backends:
  albert:
    type: albert
    url: https://albert.api.etalab.gouv.fr
    model: mistralai/Mistral-Small-3.2-24B-Instruct-2506
    api_key: YOUR_API_KEY  # Get one at albert.api.etalab.gouv.fr
    temperature: 0.7
    max_tokens: 4096
    timeout: 180  # Increased for large models
    # max_parallel_tools: 1  # Auto-detected if needed
```

**Available Albert models** (see `docs/MODEL_ALBERT.md`):
- `meta-llama/Llama-3.1-8B-Instruct` (8B, fast)
- `mistralai/Mistral-Small-3.2-24B-Instruct-2506` (24B, powerful)
- `Qwen/Qwen2.5-Coder-32B-Instruct-AWQ` (32B, code-specialized)
- And more...

**Automatic constraint detection:**
- Program automatically detects model limitations (e.g., single tool at a time)
- Constraints are saved in `~/.agentichat/model_metadata.json`
- Automatically applied on next launch

## 🏗️ Architecture

```
agentichat/
├── src/agentichat/
│   ├── cli/           # CLI interface (app, editor, confirmations)
│   ├── backends/      # LLM adapters (Ollama, Albert, extensible)
│   ├── config/        # Configuration management
│   ├── core/          # Agent loop and orchestration
│   ├── tools/         # Tool implementations (14 base + 4 Albert)
│   └── utils/         # Sandbox, logging, helpers
└── docs/              # Documentation
```

## 🔐 Security

- **Sandbox**: All file operations are validated against allowed paths
- **Confirmations**: Destructive operations (delete, shell exec) require user approval
- **Transparency**: All tool calls are logged and visible

## 🎯 Comparison with Other Tools

| Tool | Type | Use Case |
|------|------|----------|
| `llm` (Simon Willison) | CLI prompt tool | Quick prompts, scriptable |
| `llama-agents` | Multi-agent framework | Build complex agent systems |
| `agentichat` | **Agentic CLI** | **Ready-to-use autonomous assistant** |

**agentichat** fills the gap between simple prompting and complex frameworks - it's an autonomous assistant that works out of the box.

## 🧪 Development

### Run Tests

```bash
pip install -e ".[dev]"
pytest
```

### Code Quality

```bash
# Linting
ruff check .
ruff format .

# Type checking
mypy src/
```

## 🐛 Common Error Handling

### Albert API Rate Limit
```
⚠ Quota API dépassé: 128000 input tokens per minute exceeded
```
**Solutions:**
- Wait ~60 seconds
- Use `/clear` to reduce history
- Use a smaller model

### Single Tool Constraint
```
⚠ Constraint detected: only supports single tool-calls
```
**Solution:** Automatically saved and applied on next launch.

### Timeout
```
TimeoutError
```
**Solutions:**
- Increase `timeout: 180` in config
- Use a faster model

## 📝 License

MIT

## 🙏 Acknowledgments

Built with:
- [Ollama](https://ollama.ai/) - Local LLM runtime
- [Rich](https://github.com/Textualize/rich) - Terminal formatting
- [prompt_toolkit](https://github.com/prompt-toolkit/python-prompt-toolkit) - Interactive CLI
- [Albert API](https://albert.api.etalab.gouv.fr) - French public service AI API
