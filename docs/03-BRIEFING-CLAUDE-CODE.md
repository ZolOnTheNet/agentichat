# Briefing Claude Code : CLI LLM Multi-Backend

## Contexte du projet

Développement d'un CLI agentique pour interagir avec des serveurs LLM (Ollama, vLLM, APIs cloud). Le LLM pilote les actions (lecture/écriture fichiers, commandes shell) via une boucle agentique.

**Documents de référence** :
- `01-ARCHITECTURE.md` : Vision globale et composants
- `02-SPECIFICATIONS.md` : Schémas techniques, tools, protocoles
- `04-COMPLEMENTS.md` : Exemple agentique, workspaces, confirmations

---

## Stack technique

| Composant | Technologie |
|-----------|-------------|
| Langage | Python 3.11+ (migration Rust/PyO3 ultérieure) |
| Async | asyncio + aiohttp |
| Base de données | SQLite + FTS5 |
| CLI | Click ou Typer |
| Éditeur ligne | prompt-toolkit |
| Streaming | SSE (Server-Sent Events) |
| Config | YAML (PyYAML) |
| Affichage | Rich |
| Tests | pytest + pytest-asyncio |

---

## Structure du projet

```
agentichat/
├── pyproject.toml
├── README.md
├── config.example.yaml
│
├── src/
│   └── agentichat/
│       ├── __init__.py
│       ├── main.py              # Point d'entrée CLI
│       │
│       ├── cli/
│       │   ├── __init__.py
│       │   ├── app.py           # Commandes CLI principales
│       │   ├── editor.py        # Éditeur de ligne multi-ligne
│       │   ├── completer.py     # Autocomplétion @fichiers, /commandes
│       │   ├── display.py       # Affichage streaming, diffs
│       │   ├── keybindings.py   # Raccourcis clavier
│       │   └── history.py       # Gestion historique commandes
│       │
│       ├── proxy/
│       │   ├── __init__.py
│       │   ├── server.py        # Serveur HTTP proxy
│       │   ├── daemon.py        # Gestion daemon start/stop
│       │   ├── routes.py        # Endpoints API
│       │   └── workspace.py     # Gestion multi-workspaces
│       │
│       ├── core/
│       │   ├── __init__.py
│       │   ├── agent.py         # Boucle agentique
│       │   ├── context.py       # Gestion contexte/historique
│       │   └── session.py       # Sessions persistantes
│       │
│       ├── backends/
│       │   ├── __init__.py
│       │   ├── base.py          # Interface abstraite Backend
│       │   ├── ollama.py        # Adapter Ollama
│       │   ├── vllm.py          # Adapter vLLM
│       │   └── openai.py        # Adapter OpenAI-compatible
│       │
│       ├── tools/
│       │   ├── __init__.py
│       │   ├── registry.py      # Registre des tools
│       │   ├── executor.py      # Exécution sandboxée
│       │   ├── file_ops.py      # list_files, read_file, write_file, delete_file
│       │   ├── search.py        # search_text, search_semantic
│       │   └── shell.py         # shell_exec (git, npm, etc.)
│       │
│       ├── cache/
│       │   ├── __init__.py
│       │   ├── memory.py        # Cache L1 (LRU mémoire)
│       │   └── sqlite.py        # Cache L2 (SQLite)
│       │
│       ├── index/
│       │   ├── __init__.py
│       │   ├── database.py      # Gestion SQLite
│       │   ├── files.py         # Indexation fichiers
│       │   ├── fts.py           # Full-text search
│       │   └── embeddings.py    # Vecteurs (optionnel)
│       │
│       ├── config/
│       │   ├── __init__.py
│       │   ├── loader.py        # Chargement config YAML
│       │   └── schema.py        # Validation config
│       │
│       └── utils/
│           ├── __init__.py
│           ├── sandbox.py       # Validation paths
│           └── hashing.py       # Hash fichiers/prompts
│
├── tests/
│   ├── conftest.py
│   ├── test_agent.py
│   ├── test_backends.py
│   ├── test_tools.py
│   ├── test_cache.py
│   ├── test_editor.py
│   └── test_sandbox.py
│
└── scripts/
    └── install.sh
```

### Structure workspace (`.agentichat/`)

```
~/projet/
├── .agentichat/                    # Répertoire local du workspace
│   ├── config.yaml              # Config locale (override global)
│   ├── workspace.db             # Index fichiers + FTS + cache + sessions
│   └── sessions/                # Historique sessions (optionnel)
│       └── 2024-01-15_abc123.json
│
├── .git/                        # (détection racine alternative)
└── ... (fichiers projet)
```

### Configuration globale (`~/.agentichat/`)

```
~/.agentichat/
├── config.yaml                  # Configuration globale
├── proxy.db                     # Workspaces connus
└── daemon.yaml                  # État du daemon (PID, port, token)
```

---

## Éditeur de ligne de commande

### Fonctionnalités requises

L'éditeur de ligne doit offrir une expérience proche d'un éditeur moderne :

| Fonctionnalité | Description |
|----------------|-------------|
| **Multi-ligne** | `Shift+Entrée` pour nouvelle ligne, `Entrée` pour envoyer |
| **Navigation** | Flèches, `Home`, `End`, `Ctrl+←/→` (mot par mot) |
| **Édition** | `Suppr`, `Backspace`, `Ctrl+K` (kill line), `Ctrl+U` (clear line) |
| **Copier/Coller** | `Ctrl+C` (si sélection), `Ctrl+V` ou clic molette |
| **Historique** | `↑` sur première ligne = précédent, `↓` sur dernière = suivant |
| **Ligne en cours** | Conserver le brouillon lors de la navigation historique |
| **Autocomplétion** | `Tab` pour @fichiers et /commandes |

### Navigation historique intelligente

```
┌─────────────────────────────────────────┐
│ Ligne 1: première ligne du message      │  ← ↑ ici = historique précédent
│ Ligne 2: suite du message               │
│ Ligne 3: dernière ligne                 │  ← ↓ ici = historique suivant
└─────────────────────────────────────────┘

Comportement :
- Curseur sur ligne 1 + ↑ → Message précédent de l'historique
- Curseur sur ligne 3 + ↓ → Message suivant de l'historique
- Curseur sur ligne 2 + ↑/↓ → Navigation normale dans le texte
- Brouillon actuel sauvegardé temporairement lors de navigation
```

### Implémentation avec prompt-toolkit

```python
from prompt_toolkit import PromptSession
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys

def create_editor() -> PromptSession:
    bindings = KeyBindings()
    
    @bindings.add(Keys.Enter, filter=has_shift)
    def newline(event):
        """Shift+Enter = nouvelle ligne."""
        event.current_buffer.insert_text('\n')
    
    @bindings.add(Keys.Enter)
    def submit(event):
        """Enter = soumettre si pas Shift."""
        event.current_buffer.validate_and_handle()
    
    @bindings.add(Keys.Up)
    def history_prev(event):
        """↑ sur première ligne = historique précédent."""
        buffer = event.current_buffer
        if buffer.document.cursor_position_row == 0:
            buffer.history_backward()
        else:
            buffer.cursor_up()
    
    @bindings.add(Keys.Down)
    def history_next(event):
        """↓ sur dernière ligne = historique suivant."""
        buffer = event.current_buffer
        if buffer.document.cursor_position_row == buffer.document.line_count - 1:
            buffer.history_forward()
        else:
            buffer.cursor_down()
    
    return PromptSession(
        key_bindings=bindings,
        multiline=True,
        # ... autres options
    )
```

### Raccourcis clavier complets

| Raccourci | Action |
|-----------|--------|
| `Entrée` | Envoyer le message |
| `Shift+Entrée` | Nouvelle ligne |
| `↑` / `↓` | Navigation texte ou historique (selon position) |
| `←` / `→` | Déplacer curseur |
| `Ctrl+←` / `Ctrl+→` | Mot précédent/suivant |
| `Home` / `End` | Début/fin de ligne |
| `Ctrl+Home` / `Ctrl+End` | Début/fin du texte |
| `Suppr` | Supprimer caractère après curseur |
| `Backspace` | Supprimer caractère avant curseur |
| `Ctrl+K` | Supprimer jusqu'à fin de ligne |
| `Ctrl+U` | Supprimer ligne entière |
| `Ctrl+V` | Coller |
| `Ctrl+C` | Copier (si sélection) ou annuler |
| `Ctrl+Tab` | Basculer mode passthrough |
| `Ctrl+D` | Quitter |
| `Tab` | Autocomplétion |
| `Échap` | Annuler saisie en cours |

---

## Phases de développement

### Phase 1 : Fondations

**Objectif** : CLI basique + connexion Ollama

```
[ ] Configuration (loader, schema)
[ ] Backend Ollama (chat simple, streaming)
[ ] Éditeur de ligne multi-ligne
[ ] CLI basique (prompt → réponse)
[ ] Daemon proxy (start/stop)
```

**Critère de succès** : `agentichat` fonctionne avec Ollama local, édition multi-ligne OK

---

### Phase 2 : Tools et agent

**Objectif** : Boucle agentique fonctionnelle

```
[ ] Registre tools
[ ] Tool executor avec sandbox
[ ] Tools fichiers (list, read, write, delete)
[ ] Tool shell_exec
[ ] Boucle agentique
[ ] Système de confirmation (Y/A/N)
```

**Critère de succès** : "Crée un fichier hello.py et commite-le" fonctionne

---

### Phase 3 : Cache et index

**Objectif** : Performances et recherche

```
[ ] Cache mémoire (LRU)
[ ] Cache SQLite
[ ] Index fichiers
[ ] Full-text search (FTS5)
[ ] Tool search_text
```

**Critère de succès** : Recherche dans fichiers fonctionnelle

---

### Phase 4 : Multi-backend et workspaces

**Objectif** : Support vLLM, APIs cloud, multi-projets

```
[ ] Backend vLLM
[ ] Backend OpenAI
[ ] Négociation capabilities
[ ] Gestion multi-workspaces
[ ] Isolation des sessions/caches
```

**Critère de succès** : Même CLI, backends interchangeables, projets isolés

---

### Phase 5 : Polish

**Objectif** : UX et robustesse

```
[ ] Autocomplétion @fichiers
[ ] Historique persistant
[ ] search_semantic (embeddings)
[ ] Tests complets
[ ] Documentation
```

---

## Interfaces clés à implémenter

### Backend (abstraite)

```python
from abc import ABC, abstractmethod
from typing import AsyncIterator
from dataclasses import dataclass

@dataclass
class Message:
    role: str  # user, assistant, system, tool
    content: str
    tool_calls: list | None = None

@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict

class Backend(ABC):
    @abstractmethod
    async def chat(
        self,
        messages: list[Message],
        tools: list[dict] | None = None,
        stream: bool = True
    ) -> AsyncIterator[str] | Message:
        ...
    
    @abstractmethod
    async def list_models(self) -> list[str]:
        ...
    
    @abstractmethod
    async def health_check(self) -> bool:
        ...
```

### Tool (abstraite)

```python
from abc import ABC, abstractmethod

class Tool(ABC):
    name: str
    description: str
    parameters: dict  # JSON Schema
    requires_confirmation: bool = False
    
    @abstractmethod
    async def execute(self, **kwargs) -> dict:
        ...
    
    def to_schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            }
        }
```

### Sandbox

```python
from pathlib import Path

class Sandbox:
    def __init__(self, root: Path, config: dict):
        self.root = root.resolve()
        self.max_file_size = config.get("max_file_size", 1_000_000)
        self.blocked_patterns = config.get("blocked_paths", [])
    
    def validate_path(self, path: str) -> Path:
        """Valide et résout un chemin relatif."""
        resolved = (self.root / path).resolve()
        
        # Vérifier qu'on reste dans la jail
        if not resolved.is_relative_to(self.root):
            raise SecurityError(f"Path escape: {path}")
        
        # Vérifier patterns bloqués
        for pattern in self.blocked_patterns:
            if resolved.match(pattern):
                raise SecurityError(f"Blocked path: {path}")
        
        return resolved
```

---

## Commandes CLI (bash)

```bash
# Daemon
agentichat proxy start          # Démarre le daemon
agentichat proxy stop           # Arrête le daemon
agentichat proxy status         # État du daemon

# Chat
agentichat                      # Mode interactif (défaut)
agentichat "prompt"             # One-shot
agentichat -c "prompt"          # One-shot (explicite)

# Configuration
agentichat config show          # Affiche config
agentichat config set key value # Modifie config

# Serveurs
agentichat servers              # Liste serveurs configurés
agentichat use <server>         # Change de serveur

# Debug
agentichat index                # Force réindexation
agentichat search "query"       # Recherche fichiers (debug)
```

---

## Commandes in-chat

### Navigation & Info

```
/help                   Aide générale
/help <commande>        Aide sur une commande
/quit, /exit, /q        Quitter
/clear                  Reset conversation (garde le contexte fichiers)
/context                Affiche tokens utilisés, fichiers en contexte
```

### Workspace

```
/workspace              Affiche workspace courant (alias: /ws)
/workspace list         Liste workspaces connus
/workspace info         Détails du workspace
```

### Session

```
/session                Info session courante
/session status         Informations synthétiques (connexion, modèle, stats)
/session whoami         Infos projet : workspace, branche git, backend
/session clean          Efface cache/session, repart quasi à zéro
/session debug          Dump complet pour debugging (dev only, masqué en prod)
/session save [path]    Exporte conversation
/session list           Historique des sessions
/session load <id>      Charge une session précédente
```

### Modèle & Serveur

```
/model                  Affiche modèle courant
/model <name>           Change de modèle
/models                 Liste modèles disponibles
/use <server>           Change de serveur backend
```

### Fichiers

```
/files                  Fichiers actuellement en contexte
/include <path>         Ajoute fichier(s) au contexte
/exclude <path>         Retire fichier(s) du contexte
/search <query>         Recherche dans les fichiers du workspace
```

### Confirmations

```
/confirm status         Affiche état des confirmations
/confirm text on|off    Active/désactive confirmation écritures
/confirm cmd on|off     Active/désactive confirmation commandes
/confirm all on|off     Active/désactive toutes les confirmations
```

### Cache & Debug

```
/cache status           Affiche stats du cache
/cache clean            Vide le cache du workspace courant
/cache clean all        Vide tous les caches (tous workspaces)
```

---

## Variables d'environnement

```bash
LLMCHAT_CONFIG=~/.agentichat/config.yaml
LLMCHAT_DATA=~/.agentichat/
LLMCHAT_PROXY_PORT=5157
LLMCHAT_LOG_LEVEL=INFO
LLMCHAT_DEV_MODE=0           # 1 = active /session debug

# Auth backends (référencés dans config)
OLLAMA_HOST=http://localhost:11434
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=...
```

---

## Dépendances Python

```toml
[project]
name = "agentichat"
version = "0.1.0"
requires-python = ">=3.11"

dependencies = [
    "aiohttp>=3.9",
    "click>=8.1",
    "pyyaml>=6.0",
    "aiosqlite>=0.19",
    "prompt-toolkit>=3.0",  # Éditeur de ligne
    "rich>=13.0",           # Affichage formaté
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4",
    "pytest-asyncio>=0.21",
    "pytest-cov>=4.1",
    "ruff>=0.1",
    "mypy>=1.5",
]
embeddings = [
    "sentence-transformers>=2.2",
    "numpy>=1.24",
]

[project.scripts]
agentichat = "agentichat.main:cli"
```

---

## Priorités et contraintes

### Must have (Phase 1-2)

- Connexion Ollama fonctionnelle
- **Éditeur de ligne complet** (multi-ligne, historique, copier/coller)
- Boucle agentique avec tools fichiers + shell_exec
- Sandbox sécurisé
- Système de confirmation
- Streaming réponses

### Should have (Phase 3-4)

- Cache multi-niveau
- Multi-backend
- Multi-workspaces
- Full-text search

### Nice to have (Phase 5)

- Embeddings/recherche sémantique
- Autocomplétion avancée
- Sessions persistantes

### Contraintes

- **Pas de dépendances lourdes** au départ (embeddings optionnel)
- **Async first** : tout en asyncio
- **Tests** : couverture minimale 70%
- **Type hints** : partout, vérifié par mypy
- **UX** : l'éditeur de ligne doit être fluide et intuitif

---

## Pour démarrer

1. Initialiser le projet avec `pyproject.toml`
2. Implémenter `cli/editor.py` (éditeur multi-ligne avec prompt-toolkit)
3. Implémenter `config/loader.py` et `config/schema.py`
4. Implémenter `backends/ollama.py`
5. Implémenter `cli/app.py` (boucle principale)
6. Tester manuellement avec Ollama local
7. Ajouter les tools progressivement

Bonne chance !
