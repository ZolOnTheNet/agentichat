# Compléments techniques

## 1. Exemple d'échange agentique complet

### Scénario

**Demande utilisateur** :
> "Ajoute une fonction `validate_email` dans `utils/validators.py`, mets à jour la doc API, et commite le tout"

### Séquence complète

```
User ──▶ Proxy ──▶ LLM
                    │
                    ▼
            ┌───────────────┐
            │ Analyse requête│
            │ Plan d'action  │
            └───────┬───────┘
                    │
    ┌───────────────┼───────────────────────────────────┐
    ▼               ▼               ▼                   ▼
Tool Call 1    Tool Call 2    Tool Call 3-6       Tool Call 7-8
read_file      read_file      write (x2)          git_add/commit
    │               │               │                   │
    ▼               ▼               ▼                   ▼
 Résultat       Résultat      Confirmation         Confirmation
                              utilisateur          utilisateur
```

---

### Étape 1 : Requête initiale

**CLI → Proxy**
```json
POST /chat
{
  "session_id": "abc123",
  "message": "Ajoute une fonction validate_email dans utils/validators.py, mets à jour la doc API, et commite le tout"
}
```

**Proxy → Backend LLM**
```json
{
  "model": "llama3:8b",
  "messages": [
    {
      "role": "system",
      "content": "Tu es un assistant de développement. Tu disposes de tools pour manipuler les fichiers et exécuter des commandes git. Utilise-les pour accomplir les tâches demandées."
    },
    {
      "role": "user",
      "content": "Ajoute une fonction validate_email dans utils/validators.py, mets à jour la doc API, et commite le tout"
    }
  ],
  "tools": [
    {"type": "function", "function": {"name": "list_files", ...}},
    {"type": "function", "function": {"name": "read_file", ...}},
    {"type": "function", "function": {"name": "write_file", ...}},
    {"type": "function", "function": {"name": "delete_file", ...}},
    {"type": "function", "function": {"name": "search_text", ...}},
    {"type": "function", "function": {"name": "shell_exec", ...}}
  ],
  "stream": false
}
```

---

### Étape 2 : LLM demande lecture fichiers

**Backend LLM → Proxy**
```json
{
  "message": {
    "role": "assistant",
    "content": null,
    "tool_calls": [
      {
        "id": "call_001",
        "type": "function",
        "function": {
          "name": "read_file",
          "arguments": "{\"path\": \"utils/validators.py\"}"
        }
      },
      {
        "id": "call_002",
        "type": "function",
        "function": {
          "name": "read_file",
          "arguments": "{\"path\": \"docs/api.md\"}"
        }
      }
    ]
  }
}
```

**Proxy exécute (tools internes, pas de confirmation)**
```json
[
  {
    "tool_call_id": "call_001",
    "role": "tool",
    "content": "{\"success\": true, \"content\": \"import re\\n\\ndef validate_url(url: str) -> bool:\\n    \\\"\\\"\\\"Valide une URL.\\\"\\\"\\\"\\n    pattern = r'^https?://[\\\\w\\\\.-]+\\\\.[a-z]{2,}.*$'\\n    return bool(re.match(pattern, url))\\n\\ndef validate_phone(phone: str) -> bool:\\n    \\\"\\\"\\\"Valide un numéro de téléphone français.\\\"\\\"\\\"\\n    pattern = r'^(?:(?:\\\\+|00)33|0)\\\\s*[1-9](?:[\\\\s.-]*\\\\d{2}){4}$'\\n    return bool(re.match(pattern, phone))\\n\"}"
  },
  {
    "tool_call_id": "call_002",
    "role": "tool",
    "content": "{\"success\": true, \"content\": \"# API Documentation\\n\\n## Validators\\n\\n### validate_url(url: str) -> bool\\nValide qu'une chaîne est une URL valide.\\n\\n### validate_phone(phone: str) -> bool\\nValide un numéro de téléphone français.\\n\"}"
  }
]
```

---

### Étape 3 : LLM demande écriture fichiers

**Backend LLM → Proxy**
```json
{
  "message": {
    "role": "assistant",
    "content": "Je vais ajouter la fonction validate_email et mettre à jour la documentation.",
    "tool_calls": [
      {
        "id": "call_003",
        "type": "function",
        "function": {
          "name": "write_file",
          "arguments": "{\"path\": \"utils/validators.py\", \"content\": \"import re\\n\\ndef validate_url(url: str) -> bool:\\n    \\\"\\\"\\\"Valide une URL.\\\"\\\"\\\"\\n    pattern = r'^https?://[\\\\w\\\\.-]+\\\\.[a-z]{2,}.*$'\\n    return bool(re.match(pattern, url))\\n\\ndef validate_phone(phone: str) -> bool:\\n    \\\"\\\"\\\"Valide un numéro de téléphone français.\\\"\\\"\\\"\\n    pattern = r'^(?:(?:\\\\+|00)33|0)\\\\s*[1-9](?:[\\\\s.-]*\\\\d{2}){4}$'\\n    return bool(re.match(pattern, phone))\\n\\ndef validate_email(email: str) -> bool:\\n    \\\"\\\"\\\"Valide une adresse email.\\\"\\\"\\\"\\n    pattern = r'^[\\\\w\\\\.-]+@[\\\\w\\\\.-]+\\\\.\\\\w+$'\\n    return bool(re.match(pattern, email))\\n\", \"mode\": \"overwrite\"}"
        }
      },
      {
        "id": "call_004",
        "type": "function",
        "function": {
          "name": "write_file",
          "arguments": "{\"path\": \"docs/api.md\", \"content\": \"# API Documentation\\n\\n## Validators\\n\\n### validate_url(url: str) -> bool\\nValide qu'une chaîne est une URL valide.\\n\\n### validate_phone(phone: str) -> bool\\nValide un numéro de téléphone français.\\n\\n### validate_email(email: str) -> bool\\nValide une adresse email.\\n\\n**Paramètres** :\\n- `email` : chaîne à valider\\n\\n**Retourne** : `True` si l'email est valide, `False` sinon.\\n\", \"mode\": \"overwrite\"}"
        }
      }
    ]
  }
}
```

---

### Étape 4 : Confirmation utilisateur (write_file)

**Proxy → CLI : Demande de confirmation**
```json
{
  "type": "confirmation_request",
  "tool": "write_file",
  "tool_call_id": "call_003",
  "path": "utils/validators.py",
  "diff": {
    "type": "unified",
    "hunks": [
      {
        "old_start": 14,
        "old_count": 0,
        "new_start": 14,
        "new_count": 6,
        "lines": [
          {"type": "add", "content": ""},
          {"type": "add", "content": "def validate_email(email: str) -> bool:"},
          {"type": "add", "content": "    \"\"\"Valide une adresse email.\"\"\""},
          {"type": "add", "content": "    pattern = r'^[\\w\\.-]+@[\\w\\.-]+\\.\\w+$'"},
          {"type": "add", "content": "    return bool(re.match(pattern, email))"}
        ]
      }
    ]
  }
}
```

**Affichage CLI**
```
┌─────────────────────────────────────────────────────────────────┐
│ 📝 write_file: utils/validators.py                              │
├─────────────────────────────────────────────────────────────────┤
│  @@ -14,0 +14,6 @@                                              │
│                                                                 │
│ + def validate_email(email: str) -> bool:                       │
│ +     """Valide une adresse email."""                           │
│ +     pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'                      │
│ +     return bool(re.match(pattern, email))                     │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│ [Y] Oui   [A] Oui à tout   [N] Non, expliquer   [?] Aide        │
│                                                                 │
│ Mode actuel: confirmation ON       (Ctrl+Tab pour basculer)     │
└─────────────────────────────────────────────────────────────────┘
```

**CLI → Proxy : Réponse utilisateur**
```json
{
  "type": "confirmation_response",
  "tool_call_id": "call_003",
  "decision": "yes"
}
```

*Même processus pour `call_004` (docs/api.md)*

---

### Étape 5 : LLM demande git add + commit

**Backend LLM → Proxy**
```json
{
  "message": {
    "role": "assistant",
    "content": "Fichiers modifiés. Je vais maintenant les commiter.",
    "tool_calls": [
      {
        "id": "call_005",
        "type": "function",
        "function": {
          "name": "shell_exec",
          "arguments": "{\"command\": \"git add utils/validators.py docs/api.md\"}"
        }
      }
    ]
  }
}
```

**Affichage CLI (commande externe)**
```
┌─────────────────────────────────────────────────────────────────┐
│ ⚡ shell_exec                                                    │
├─────────────────────────────────────────────────────────────────┤
│ $ git add utils/validators.py docs/api.md                       │
├─────────────────────────────────────────────────────────────────┤
│ [Y] Oui   [A] Oui à tout   [N] Non, expliquer   [?] Aide        │
└─────────────────────────────────────────────────────────────────┘
```

**Après confirmation, LLM continue**
```json
{
  "message": {
    "role": "assistant",
    "content": null,
    "tool_calls": [
      {
        "id": "call_006",
        "type": "function",
        "function": {
          "name": "shell_exec",
          "arguments": "{\"command\": \"git commit -m \\\"feat(validators): add validate_email function\\\"\"}"
        }
      }
    ]
  }
}
```

**Affichage CLI**
```
┌─────────────────────────────────────────────────────────────────┐
│ ⚡ shell_exec                                                    │
├─────────────────────────────────────────────────────────────────┤
│ $ git commit -m "feat(validators): add validate_email function" │
├─────────────────────────────────────────────────────────────────┤
│ [Y] Oui   [A] Oui à tout   [N] Non, expliquer   [?] Aide        │
└─────────────────────────────────────────────────────────────────┘
```

---

### Étape 6 : Réponse finale

**Backend LLM → Proxy**
```json
{
  "message": {
    "role": "assistant",
    "content": "✅ Terminé !\n\nJ'ai effectué les modifications suivantes :\n\n1. **utils/validators.py** : ajout de `validate_email(email: str) -> bool`\n2. **docs/api.md** : documentation de la nouvelle fonction\n3. **Git** : commit `feat(validators): add validate_email function`\n\nLa fonction utilise une regex simple pour valider le format email. Pour une validation plus robuste en production, tu pourrais envisager une lib comme `email-validator`."
  }
}
```

**Proxy → CLI**
```json
{
  "type": "response",
  "session_id": "abc123",
  "content": "✅ Terminé !\n\nJ'ai effectué les modifications suivantes :\n\n1. **utils/validators.py** : ajout de `validate_email(email: str) -> bool`\n2. **docs/api.md** : documentation de la nouvelle fonction\n3. **Git** : commit `feat(validators): add validate_email function`\n\nLa fonction utilise une regex simple pour valider le format email. Pour une validation plus robuste en production, tu pourrais envisager une lib comme `email-validator`.",
  "stats": {
    "tool_calls": 6,
    "files_modified": 2,
    "tokens_used": 1847
  }
}
```

---

### Cas d'erreur : Refus utilisateur

Si l'utilisateur répond **N** (Non) :

**CLI → Proxy**
```json
{
  "type": "confirmation_response",
  "tool_call_id": "call_003",
  "decision": "no",
  "reason": "explain"
}
```

**Proxy → LLM** (message ajouté à la conversation)
```json
{
  "role": "tool",
  "tool_call_id": "call_003",
  "content": "{\"success\": false, \"error\": \"USER_REJECTED\", \"message\": \"L'utilisateur a refusé cette modification et demande des explications.\"}"
}
```

Le LLM reçoit ce feedback et peut reformuler, expliquer son approche, ou proposer une alternative.

---

## 2. Système de confirmation utilisateur

### Modes de confirmation

| Commande | Effet |
|----------|-------|
| `/confirm text on` | Demande confirmation pour chaque écriture fichier |
| `/confirm text off` | Écriture automatique (passthrough) |
| `/confirm cmd on` | Demande confirmation pour chaque commande externe |
| `/confirm cmd off` | Exécution automatique (passthrough) |
| `/confirm all on` | Active les deux confirmations |
| `/confirm all off` | Désactive les deux (mode confiance totale) |
| `/confirm status` | Affiche l'état actuel |

### Raccourci clavier

| Raccourci | Action |
|-----------|--------|
| `Ctrl+Tab` | Bascule le mode passthrough global (toggle) |

### Réponses utilisateur

| Touche | Action | Effet |
|--------|--------|-------|
| `Y` / `Entrée` | Oui | Exécute cette action |
| `A` | Oui à tout | Exécute + passe en passthrough pour ce type |
| `N` | Non | Refuse + demande explication au LLM |
| `?` | Aide | Affiche l'aide contextuelle |
| `Ctrl+C` | Annuler | Annule toute la séquence agentique |

> **Note v2** : Option `[E] Éditer` (ouverture dans `$EDITOR`) prévue pour une version ultérieure.

### Persistance

Les préférences sont sauvegardées dans la session :

```yaml
# .llm-context/session.json
{
  "session_id": "abc123",
  "confirm": {
    "text": true,
    "cmd": true
  },
  "passthrough_until": null
}
```

Le `passthrough_until` permet de gérer le "Oui à tout" temporaire (reset à la prochaine requête utilisateur).

---

## 3. Classification des tools

### Tools internes (Python natif)

Implémentés directement dans le proxy, aucune dépendance externe.

| Tool | Description | Confirmation |
|------|-------------|--------------|
| `list_files` | Liste fichiers/répertoires | Non |
| `read_file` | Lit un fichier | Non |
| `write_file` | Crée/modifie un fichier | **Oui (text)** |
| `delete_file` | Supprime un fichier | **Oui (text)** |
| `search_text` | Recherche grep-like | Non |
| `search_semantic` | Recherche par embeddings | Non |

### Tools externes (subprocess)

Un seul tool générique pour toutes les commandes système :

| Tool | Description | Confirmation | Binaire requis |
|------|-------------|--------------|----------------|
| `shell_exec` | Exécute une commande shell | **Oui (cmd)** | Variable |

Le LLM utilise `shell_exec` pour git, npm, docker, make, etc. Les consignes système lui indiquent comment procéder (voir section 7).

### Vérification au démarrage

```python
async def check_external_tools() -> dict[str, bool]:
    """Vérifie la disponibilité des outils externes."""
    tools = {
        "git": "git --version",
        "docker": "docker --version",
        "npm": "npm --version",
    }
    
    availability = {}
    for name, cmd in tools.items():
        try:
            proc = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL
            )
            await proc.wait()
            availability[name] = proc.returncode == 0
        except Exception:
            availability[name] = False
    
    return availability
```

**Affichage au démarrage**
```
🔧 Tools externes:
   ✓ git 2.43.0
   ✓ docker 24.0.7
   ✗ npm (non installé - https://nodejs.org/)
```

### Schéma tools supplémentaires

```json
{
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "delete_file",
        "description": "Supprime un fichier",
        "parameters": {
          "type": "object",
          "properties": {
            "path": {
              "type": "string",
              "description": "Chemin du fichier à supprimer"
            }
          },
          "required": ["path"]
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "shell_exec",
        "description": "Exécute une commande shell. Utiliser pour git, npm, make, docker, etc.",
        "parameters": {
          "type": "object",
          "properties": {
            "command": {
              "type": "string",
              "description": "Commande à exécuter"
            },
            "cwd": {
              "type": "string",
              "description": "Répertoire de travail (optionnel, défaut: racine projet)"
            }
          },
          "required": ["command"]
        }
      }
    }
  ]
}
```

---

## 4. Gestion des erreurs

### Codes d'erreur

| Code | Nom | Description |
|------|-----|-------------|
| `E001` | `PATH_OUTSIDE_SANDBOX` | Tentative d'accès hors du répertoire autorisé |
| `E002` | `PATH_BLOCKED` | Chemin dans la liste noire (.env, *.key) |
| `E003` | `FILE_NOT_FOUND` | Fichier inexistant |
| `E004` | `FILE_TOO_LARGE` | Fichier dépasse la limite de taille |
| `E005` | `PERMISSION_DENIED` | Droits insuffisants |
| `E006` | `USER_REJECTED` | Utilisateur a refusé l'action |
| `E007` | `TOOL_NOT_AVAILABLE` | Outil externe non installé |
| `E008` | `COMMAND_FAILED` | Commande externe a échoué |
| `E009` | `TIMEOUT` | Opération trop longue |
| `E010` | `MAX_ITERATIONS` | Boucle agentique limite atteinte |

### Format de réponse erreur

```python
@dataclass
class ToolError:
    code: str           # E001, E002, etc.
    error: str          # Nom court
    message: str        # Description pour le LLM
    details: dict | None = None  # Infos techniques optionnelles

# Exemple
ToolError(
    code="E003",
    error="FILE_NOT_FOUND",
    message="Le fichier 'utils/validators.py' n'existe pas. Voulez-vous le créer ?",
    details={"path": "utils/validators.py", "cwd": "/home/user/project"}
)
```

**Sérialisation pour le LLM**
```json
{
  "success": false,
  "error": {
    "code": "E003",
    "type": "FILE_NOT_FOUND",
    "message": "Le fichier 'utils/validators.py' n'existe pas. Voulez-vous le créer ?"
  }
}
```

### Stratégie de retry

```python
@dataclass
class RetryPolicy:
    max_attempts: int = 3
    backoff_base: float = 1.0      # secondes
    backoff_factor: float = 2.0    # exponentiel
    retryable_errors: set[str] = field(default_factory=lambda: {
        "TIMEOUT",
        "CONNECTION_ERROR", 
        "RATE_LIMITED"
    })

async def with_retry(
    func: Callable,
    policy: RetryPolicy
) -> Any:
    last_error = None
    
    for attempt in range(policy.max_attempts):
        try:
            return await func()
        except ToolError as e:
            if e.error not in policy.retryable_errors:
                raise
            last_error = e
            delay = policy.backoff_base * (policy.backoff_factor ** attempt)
            await asyncio.sleep(delay)
    
    raise last_error
```

### Exceptions Python

```python
class LLMCLIError(Exception):
    """Base exception."""
    pass

class SandboxError(LLMCLIError):
    """Violation de sécurité sandbox."""
    pass

class BackendError(LLMCLIError):
    """Erreur communication backend LLM."""
    pass

class ToolExecutionError(LLMCLIError):
    """Erreur exécution d'un tool."""
    def __init__(self, code: str, message: str, details: dict = None):
        self.code = code
        self.message = message
        self.details = details or {}
        super().__init__(f"[{code}] {message}")

class MaxIterationsError(LLMCLIError):
    """Boucle agentique a atteint la limite."""
    pass

class UserCancelledError(LLMCLIError):
    """Utilisateur a annulé (Ctrl+C)."""
    pass
```

---

## 5. Protocole CLI ↔ Proxy

### Transport

| Option | Choix | Justification |
|--------|-------|---------------|
| Protocole | **HTTP/1.1** | Simple, debuggable, outils standards |
| Port par défaut | **5157** | Peu utilisé, facile à retenir |
| Host | `127.0.0.1` | Localhost uniquement (sécurité) |
| Format | **JSON** | Universel |
| Streaming | **SSE** | Server-Sent Events pour réponses |

### Authentification locale

Pas d'auth complexe (localhost), mais un token de session pour éviter les collisions :

```yaml
# ~/.llm-cli/daemon.yaml (créé au démarrage)
pid: 12345
port: 5157
token: "a7b3c9d2e1f0"  # Généré aléatoirement
started_at: "2024-01-15T10:30:00Z"
```

Le CLI lit ce fichier pour se connecter.

### Endpoints

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| `GET` | `/health` | État du proxy |
| `POST` | `/chat` | Envoyer message (retourne SSE) |
| `POST` | `/confirm` | Réponse à une demande de confirmation |
| `GET` | `/session` | Info session courante |
| `DELETE` | `/session` | Reset session |
| `GET` | `/models` | Liste modèles disponibles |
| `POST` | `/model` | Changer de modèle |
| `GET` | `/config` | Configuration actuelle |
| `PUT` | `/config` | Modifier configuration |

### Format des messages

**Requête chat**
```json
POST /chat
Headers:
  X-Session-Token: a7b3c9d2e1f0
  Content-Type: application/json
  Accept: text/event-stream

{
  "message": "Ajoute une fonction validate_email...",
  "context": {
    "files": ["utils/validators.py"],
    "include_git_status": true
  }
}
```

**Réponse SSE**
```
HTTP/1.1 200 OK
Content-Type: text/event-stream
Cache-Control: no-cache

event: thinking
data: {"status": "reading files..."}

event: confirmation
data: {"id": "conf_001", "tool": "write_file", "path": "utils/validators.py", "diff": {...}}

event: waiting
data: {"for": "conf_001"}

event: chunk
data: {"content": "J'ai ajouté"}

event: chunk  
data: {"content": " la fonction"}

event: chunk
data: {"content": " validate_email..."}

event: done
data: {"stats": {"tool_calls": 6, "tokens": 1847}}
```

**Confirmation**
```json
POST /confirm
Headers:
  X-Session-Token: a7b3c9d2e1f0

{
  "id": "conf_001",
  "decision": "yes"
}
```

### Gestion déconnexion

Si le CLI se déconnecte pendant une requête :
- Le proxy continue l'exécution jusqu'à la prochaine confirmation
- Les confirmations en attente timeout après 5 minutes
- Le CLI peut reprendre avec `GET /session/pending`

```json
GET /session/pending
Response:
{
  "pending_confirmations": [
    {"id": "conf_001", "tool": "write_file", "path": "...", "created_at": "..."}
  ]
}
```

---

## 6. Architecture multi-workspaces

### Principe

Un seul daemon proxy gère plusieurs projets simultanément. Chaque projet = un **workspace** isolé.

```
CLI (terminal 1, ~/projetA) ──┐
                              ├──▶ Proxy (daemon unique) ──▶ Backend LLM
CLI (terminal 2, ~/projetB) ──┘         │
                                        ├── Workspace projetA (isolé)
                                        ├── Workspace projetB (isolé)
                                        └── Connexion backend (partagée)
```

### Détection de la racine projet

Le proxy détecte la racine du workspace en remontant l'arborescence depuis le `cwd` du CLI :

```
Priorité de détection :
1. .agentichat/        → Fichier config du programme (prioritaire)
2. .llm-context/    → Répertoire contexte existant
3. .git/            → Racine repository git
4. cwd              → Fallback : répertoire courant
```

**Exemple** :
```
~/projetA/
├── .git/
├── .agentichat/           ← Racine détectée
├── src/
│   └── module/         ← CLI lancé ici
└── docs/

# Le workspace sera ~/projetA/, pas ~/projetA/src/module/
```

### Isolation des workspaces

| Élément | Scope | Stockage |
|---------|-------|----------|
| Session/Historique | Workspace | `.agentichat/session.json` |
| Index fichiers | Workspace | `.agentichat/index.db` |
| Cache réponses | Workspace | `.agentichat/cache.db` |
| Configuration | Workspace | `.agentichat/config.yaml` |
| Sandbox jail | Workspace | Racine du workspace |
| Connexion LLM | **Global** | Partagée (économie) |

### Structure répertoire workspace

```
~/projetA/
├── .agentichat/
│   ├── config.yaml       # Config locale (override global)
│   ├── index.db          # Index fichiers + FTS
│   ├── cache.db          # Cache réponses
│   ├── session.json      # Session courante
│   └── sessions/         # Historique sessions
│       ├── 2024-01-15_abc123.json
│       └── 2024-01-14_def456.json
└── ... (fichiers projet)
```

### Gestion concurrence

**Même workspace, plusieurs terminaux** :

```
Terminal 1 (~/projetA) ──┐
                         ├──▶ Workspace projetA ──▶ Session partagée
Terminal 2 (~/projetA) ──┘
```

- Les messages sont entrelacés dans la même session
- Chaque CLI reçoit les réponses en temps réel (broadcast)
- Lock SQLite pour éviter corruptions

**Alternative** : sessions distinctes par terminal (configurable).

### Schéma DB workspaces

```sql
-- Table workspaces (dans DB globale du proxy)
CREATE TABLE workspaces (
    id TEXT PRIMARY KEY,              -- Hash du chemin absolu
    root_path TEXT UNIQUE NOT NULL,   -- /home/user/projetA
    detected_by TEXT NOT NULL,        -- 'agentichat' | 'git' | 'cwd'
    created_at REAL NOT NULL,
    last_active REAL NOT NULL
);

-- Index pour lookup rapide
CREATE INDEX idx_workspaces_path ON workspaces(root_path);
```

### Commande /workspace

```
/workspace              # Affiche workspace courant
/workspace list         # Liste tous les workspaces connus
/workspace info         # Détails (sessions, cache, index)
```

---

## 7. Instructions système pour le LLM

### Prompt système de base

Le proxy injecte ces instructions au LLM pour guider l'utilisation des tools :

```
Tu es un assistant de développement avec accès au système de fichiers et au shell.

## Tools disponibles

### Fichiers (internes)
- `list_files(path, recursive?, pattern?)` : liste le contenu d'un répertoire
- `read_file(path, start_line?, end_line?)` : lit un fichier
- `write_file(path, content, mode?)` : crée ou modifie un fichier
- `delete_file(path)` : supprime un fichier
- `search_text(query, path?, regex?, case_sensitive?)` : recherche dans les fichiers

### Shell (externe)
- `shell_exec(command, cwd?)` : exécute une commande shell

## Règles

1. **Lecture d'abord** : Avant de modifier un fichier, lis-le pour comprendre le contexte.
2. **Modifications ciblées** : Préfère des modifications précises plutôt que réécrire un fichier entier.
3. **Une étape à la fois** : Pour les tâches complexes, procède par étapes vérifiables.
4. **Explique tes actions** : Décris brièvement ce que tu fais et pourquoi.

## Commandes shell courantes

### Git
- Vérifier l'état : `shell_exec("git status")`
- Voir les changements : `shell_exec("git diff")` ou `shell_exec("git diff --staged")`
- Historique : `shell_exec("git log --oneline -10")`
- Stager des fichiers : `shell_exec("git add fichier1 fichier2")`
- Commiter : `shell_exec("git commit -m \"type(scope): description\"")`
- Pousser : `shell_exec("git push")`

⚠️ Avant un push, vérifie s'il y a des changements distants :
```
shell_exec("git fetch")
shell_exec("git status")
```

### Autres commandes utiles
- Exécuter des tests : `shell_exec("pytest")` ou `shell_exec("npm test")`
- Installer dépendances : `shell_exec("pip install -r requirements.txt")`
- Linter : `shell_exec("ruff check .")` ou `shell_exec("eslint .")`
```

### Instructions contextuelles

Le proxy ajoute des infos dynamiques :

```
## Contexte actuel

- **Workspace** : /home/user/projetA
- **Branche git** : main (3 commits ahead of origin)
- **Fichiers modifiés** : 2 (src/app.py, README.md)
- **Tools externes disponibles** : git ✓, python ✓, npm ✗
```

### Adaptation par backend

| Backend | Support tools | Adaptation |
|---------|---------------|------------|
| Ollama (llama3) | Oui (récent) | Instructions standard |
| Ollama (mistral) | Partiel | Format simplifié |
| OpenAI | Oui | Format natif |
| Anthropic | Oui | Format natif |

---

## 8. Commandes in-chat

### Liste complète

```
# Navigation & Info
/help                   Aide générale
/help <commande>        Aide sur une commande
/quit, /exit            Quitter
/clear                  Reset conversation (garde le contexte fichiers)
/context                Affiche tokens utilisés, fichiers en contexte

# Workspace
/workspace              Affiche workspace courant
/workspace list         Liste workspaces connus
/workspace info         Détails du workspace

# Modèle & Serveur
/model                  Affiche modèle courant
/model <name>           Change de modèle
/models                 Liste modèles disponibles
/use <server>           Change de serveur backend

# Fichiers
/files                  Fichiers actuellement en contexte
/include <path>         Ajoute fichier(s) au contexte
/exclude <path>         Retire fichier(s) du contexte
/search <query>         Recherche dans les fichiers du workspace

# Confirmations
/confirm status         Affiche état des confirmations
/confirm text on|off    Active/désactive confirmation écritures
/confirm cmd on|off     Active/désactive confirmation commandes
/confirm all on|off     Active/désactive toutes les confirmations

# Cache & Debug
/cache status           Affiche stats du cache
/cache clean            Vide le cache du workspace courant
/cache clean all        Vide tous les caches (tous workspaces)

# Session
/session                Info session courante (alias: /session status)
/session status         Infos synthétiques (workspace, modèle, tokens, erreurs)
/session whoami         Infos projet (workspace, backend, branche git, etc.)
/session save [path]    Exporte conversation
/session list           Historique des sessions
/session load <id>      Charge une session précédente
/session clean          Efface caches et reset session (repart quasi à zéro)
/session debug          [DEV] Dump complet pour debugging (masqué en prod)
```

### Raccourcis clavier

| Raccourci | Action |
|-----------|--------|
| `Entrée` | Envoyer le message |
| `Shift+Entrée` | Nouvelle ligne |
| `↑` / `↓` | Navigation texte ou historique (selon position curseur) |
| `←` / `→` | Déplacer curseur |
| `Ctrl+←` / `Ctrl+→` | Mot précédent/suivant |
| `Home` / `End` | Début/fin de ligne |
| `Ctrl+U` | Effacer ligne |
| `Ctrl+K` | Effacer jusqu'à fin de ligne |
| `Ctrl+V` | Coller |
| `Ctrl+Tab` | Bascule mode passthrough |
| `Ctrl+C` | Annule requête en cours (ou copie si sélection) |
| `Ctrl+D` | Quitte (équivalent /quit) |
| `Tab` | Autocomplétion (@fichiers, /commandes) |
| `Échap` | Annuler saisie en cours |

---

## 10. Éditeur de ligne de commande

### Fonctionnalités requises

Le CLI doit offrir une expérience d'édition avancée comparable aux shells modernes.

### Édition de base

| Touche | Action |
|--------|--------|
| `←` / `→` | Déplacer curseur caractère par caractère |
| `Ctrl+←` / `Ctrl+→` | Déplacer curseur mot par mot |
| `Home` / `Ctrl+A` | Début de ligne |
| `End` / `Ctrl+E` | Fin de ligne |
| `Backspace` | Supprimer caractère avant curseur |
| `Delete` / `Suppr` | Supprimer caractère après curseur |
| `Ctrl+U` | Supprimer du curseur au début de ligne |
| `Ctrl+K` | Supprimer du curseur à la fin de ligne |
| `Ctrl+W` | Supprimer mot précédent |

### Multi-lignes

| Touche | Action |
|--------|--------|
| `Entrée` | Envoyer le message |
| `Shift+Entrée` | Nouvelle ligne (mode multi-lignes) |
| `↑` (sur ligne 1) | Historique précédent |
| `↓` (sur dernière ligne) | Historique suivant |
| `↑` / `↓` (au milieu) | Naviguer entre les lignes du texte |

### Presse-papier

| Touche | Action |
|--------|--------|
| `Ctrl+V` / `Shift+Insert` | Coller |
| `Ctrl+C` (sans sélection) | Annuler requête en cours |
| `Ctrl+C` (avec sélection) | Copier (si supporté par terminal) |

### Historique intelligent

```
┌─────────────────────────────────────────────────────────────────┐
│ Comportement historique                                         │
├─────────────────────────────────────────────────────────────────┤
│ 1. Le texte en cours d'édition est préservé                     │
│ 2. Flèche ↑ sur ligne 1 → message précédent                     │
│ 3. Flèche ↓ sur dernière ligne → message suivant                │
│ 4. Revenir au "présent" restaure le texte en cours              │
│ 5. Historique persisté entre sessions                           │
└─────────────────────────────────────────────────────────────────┘
```

**Exemple de flux** :
```
> En train de taper quelque ch|     ← Curseur ici, ligne 1
  [↑ pressé]
> Comment faire un git rebase?      ← Message précédent affiché
  [↑ pressé]  
> Explique les decorators Python    ← Message encore avant
  [↓↓ pressé - retour au présent]
> En train de taper quelque ch|     ← Texte restauré
```

### Implémentation recommandée

```python
# Utiliser prompt_toolkit pour toutes ces fonctionnalités
from prompt_toolkit import PromptSession
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.history import FileHistory

bindings = KeyBindings()

@bindings.add('s-enter')  # Shift+Enter
def insert_newline(event):
    event.current_buffer.insert_text('\n')

@bindings.add('c-tab')  # Ctrl+Tab
def toggle_passthrough(event):
    # Toggle confirmation mode
    ...

session = PromptSession(
    history=FileHistory('.agentichat/history.txt'),
    key_bindings=bindings,
    multiline=True,
    prompt_continuation='... ',  # Indicateur lignes suivantes
)
```

### Affichage multi-lignes

```
> Voici un message           ← Première ligne, prompt normal
... sur plusieurs            ← Lignes suivantes, prompt continuation
... lignes différentes       
... [curseur ici]|           ← Curseur visible
```

### Fichier historique

```
# .agentichat/history.txt
# Format : une entrée par bloc, séparées par lignes vides

Comment faire un git rebase interactif?

Explique les decorators Python
avec des exemples concrets

Voici du code:
```python
def hello():
    pass
```
Corrige les erreurs
```

L'historique est partagé au sein d'un workspace mais pas entre workspaces.

---

## 11. Récapitulatif fichiers de référence

| Fichier | Contenu |
|---------|---------|
| `00-SYNTHESE.md` | Décisions validées, vue d'ensemble |
| `01-ARCHITECTURE.md` | Vision, composants, flux |
| `02-SPECIFICATIONS.md` | Tools JSON, schéma DB, protocoles |
| `03-BRIEFING-CLAUDE-CODE.md` | Structure projet, phases, interfaces |
| `04-COMPLEMENTS.md` | Exemple agentique, workspaces, confirmations, éditeur CLI, erreurs, protocole |
