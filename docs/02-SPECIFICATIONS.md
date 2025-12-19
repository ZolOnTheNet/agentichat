# Spécifications techniques

## Tools exposés au LLM

### Classification

| Type | Tools | Confirmation |
|------|-------|--------------|
| **Internes** | `list_files`, `read_file`, `write_file`, `delete_file`, `search_text`, `search_semantic` | Écriture/suppression uniquement |
| **Externes** | `shell_exec` | Toujours |

### Définition JSON Schema

```json
{
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "list_files",
        "description": "Liste les fichiers d'un répertoire",
        "parameters": {
          "type": "object",
          "properties": {
            "path": {
              "type": "string",
              "description": "Chemin relatif du répertoire"
            },
            "recursive": {
              "type": "boolean",
              "default": false,
              "description": "Inclure les sous-répertoires"
            },
            "pattern": {
              "type": "string",
              "description": "Glob pattern (ex: *.py)"
            }
          },
          "required": ["path"]
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "read_file",
        "description": "Lit le contenu d'un fichier",
        "parameters": {
          "type": "object",
          "properties": {
            "path": {
              "type": "string",
              "description": "Chemin relatif du fichier"
            },
            "start_line": {
              "type": "integer",
              "description": "Ligne de début (optionnel)"
            },
            "end_line": {
              "type": "integer",
              "description": "Ligne de fin (optionnel)"
            }
          },
          "required": ["path"]
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "write_file",
        "description": "Crée ou modifie un fichier",
        "parameters": {
          "type": "object",
          "properties": {
            "path": {
              "type": "string",
              "description": "Chemin relatif du fichier"
            },
            "content": {
              "type": "string",
              "description": "Contenu à écrire"
            },
            "mode": {
              "type": "string",
              "enum": ["create", "overwrite", "append"],
              "default": "create"
            }
          },
          "required": ["path", "content"]
        }
      }
    },
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
              "description": "Chemin relatif du fichier à supprimer"
            }
          },
          "required": ["path"]
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "search_text",
        "description": "Recherche textuelle dans les fichiers (grep-like)",
        "parameters": {
          "type": "object",
          "properties": {
            "query": {
              "type": "string",
              "description": "Texte ou regex à chercher"
            },
            "path": {
              "type": "string",
              "default": ".",
              "description": "Répertoire de recherche"
            },
            "regex": {
              "type": "boolean",
              "default": false
            },
            "case_sensitive": {
              "type": "boolean",
              "default": false
            }
          },
          "required": ["query"]
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "search_semantic",
        "description": "Recherche sémantique via embeddings",
        "parameters": {
          "type": "object",
          "properties": {
            "query": {
              "type": "string",
              "description": "Description de ce qu'on cherche"
            },
            "top_k": {
              "type": "integer",
              "default": 5,
              "description": "Nombre de résultats"
            }
          },
          "required": ["query"]
        }
      }
    },
    {
      "type": "function",
      "function": {
        "name": "shell_exec",
        "description": "Exécute une commande shell. Utiliser pour git, npm, make, docker, tests, etc.",
        "parameters": {
          "type": "object",
          "properties": {
            "command": {
              "type": "string",
              "description": "Commande à exécuter"
            },
            "cwd": {
              "type": "string",
              "description": "Répertoire de travail (optionnel, défaut: racine workspace)"
            },
            "timeout": {
              "type": "integer",
              "default": 30,
              "description": "Timeout en secondes"
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

## Schéma base de données SQLite

### Base globale du proxy (`~/.agentichat/proxy.db`)

```sql
-- Workspaces connus
CREATE TABLE workspaces (
    id TEXT PRIMARY KEY,              -- Hash du chemin absolu
    root_path TEXT UNIQUE NOT NULL,   -- /home/user/projetA
    detected_by TEXT NOT NULL,        -- 'agentichat' | 'git' | 'cwd'
    created_at REAL NOT NULL,
    last_active REAL NOT NULL
);

CREATE INDEX idx_workspaces_path ON workspaces(root_path);
```

### Base locale du workspace (`.agentichat/workspace.db`)

```sql
-- Index des fichiers
CREATE TABLE files (
    id INTEGER PRIMARY KEY,
    path TEXT UNIQUE NOT NULL,        -- Relatif à la racine workspace
    hash TEXT NOT NULL,               -- SHA256 du contenu
    mtime REAL NOT NULL,              -- Timestamp modification
    size INTEGER NOT NULL,
    indexed_at REAL NOT NULL
);

-- Embeddings (vecteurs)
CREATE TABLE embeddings (
    id INTEGER PRIMARY KEY,
    file_id INTEGER REFERENCES files(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,     -- Position du chunk dans le fichier
    chunk_text TEXT NOT NULL,         -- Texte original du chunk
    vector BLOB NOT NULL,             -- Vecteur sérialisé (float32[])
    UNIQUE(file_id, chunk_index)
);

-- Cache des réponses
CREATE TABLE response_cache (
    id INTEGER PRIMARY KEY,
    prompt_hash TEXT UNIQUE NOT NULL, -- Hash normalisé du prompt
    response TEXT NOT NULL,
    model TEXT NOT NULL,
    created_at REAL NOT NULL,
    expires_at REAL,                  -- TTL
    hit_count INTEGER DEFAULT 0
);

-- Full-text search
CREATE VIRTUAL TABLE fts_content USING fts5(
    path,
    content,
    content='files',
    content_rowid='id'
);

-- Sessions
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    backend TEXT NOT NULL,
    model TEXT NOT NULL,
    metadata TEXT                     -- JSON (infos debug, stats)
);

-- Messages (historique conversation)
CREATE TABLE messages (
    id INTEGER PRIMARY KEY,
    session_id TEXT REFERENCES sessions(id) ON DELETE CASCADE,
    role TEXT NOT NULL,               -- user, assistant, tool
    content TEXT NOT NULL,
    tool_call_id TEXT,                -- Si role=tool
    tool_name TEXT,                   -- Si role=tool
    created_at REAL NOT NULL
);

-- Historique des commandes utilisateur (pour readline)
CREATE TABLE command_history (
    id INTEGER PRIMARY KEY,
    session_id TEXT REFERENCES sessions(id) ON DELETE CASCADE,
    command TEXT NOT NULL,
    created_at REAL NOT NULL
);

-- Index
CREATE INDEX idx_files_hash ON files(hash);
CREATE INDEX idx_embeddings_file ON embeddings(file_id);
CREATE INDEX idx_cache_expires ON response_cache(expires_at);
CREATE INDEX idx_messages_session ON messages(session_id, created_at);
CREATE INDEX idx_history_session ON command_history(session_id, created_at);
```

---

## Protocole Proxy ↔ Backend

### Format requête unifié (interne)

```python
@dataclass
class LLMRequest:
    messages: list[Message]
    model: str
    tools: list[Tool] | None = None
    stream: bool = True
    max_tokens: int = 4096
    temperature: float = 0.7

@dataclass
class Message:
    role: Literal["system", "user", "assistant", "tool"]
    content: str
    tool_call_id: str | None = None
    tool_calls: list[ToolCall] | None = None

@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict
```

### Adapter Ollama

```python
def to_ollama(request: LLMRequest) -> dict:
    return {
        "model": request.model,
        "messages": [
            {"role": m.role, "content": m.content}
            for m in request.messages
        ],
        "tools": request.tools,
        "stream": request.stream,
        "options": {
            "num_predict": request.max_tokens,
            "temperature": request.temperature
        }
    }
```

### Adapter vLLM / OpenAI

```python
def to_openai(request: LLMRequest) -> dict:
    return {
        "model": request.model,
        "messages": [
            {"role": m.role, "content": m.content}
            for m in request.messages
        ],
        "tools": request.tools,
        "stream": request.stream,
        "max_tokens": request.max_tokens,
        "temperature": request.temperature
    }
```

---

## Cache multi-niveau

### Niveau L1 : Mémoire (LRU)

```python
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_cached_response(prompt_hash: str) -> str | None:
    ...
```

### Niveau L2 : SQLite

```python
def get_from_db(prompt_hash: str) -> str | None:
    row = db.execute("""
        SELECT response FROM response_cache 
        WHERE prompt_hash = ? 
        AND (expires_at IS NULL OR expires_at > ?)
    """, (prompt_hash, time.time())).fetchone()
    
    if row:
        db.execute("""
            UPDATE response_cache 
            SET hit_count = hit_count + 1 
            WHERE prompt_hash = ?
        """, (prompt_hash,))
        return row[0]
    return None
```

### Normalisation du prompt (pour hash)

```python
import hashlib
import json

def normalize_prompt(messages: list[Message], model: str) -> str:
    """Génère un hash stable pour le cache."""
    data = {
        "model": model,
        "messages": [
            {"role": m.role, "content": m.content.strip().lower()}
            for m in messages
        ]
    }
    canonical = json.dumps(data, sort_keys=True)
    return hashlib.sha256(canonical.encode()).hexdigest()
```

---

## Boucle agentique

```python
async def agent_loop(
    user_prompt: str,
    backend: Backend,
    tools: list[Tool],
    max_iterations: int = 10,
    confirm_callback: Callable | None = None
) -> str:
    messages = [{"role": "user", "content": user_prompt}]
    
    for _ in range(max_iterations):
        response = await backend.chat(messages, tools=tools)
        
        if not response.tool_calls:
            return response.content
        
        # Exécute chaque tool call
        for call in response.tool_calls:
            # Demande confirmation si nécessaire
            if needs_confirmation(call.name) and confirm_callback:
                decision = await confirm_callback(call)
                if decision == "no":
                    messages.append({
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": json.dumps({
                            "success": False,
                            "error": "USER_REJECTED",
                            "message": "L'utilisateur a refusé et demande des explications."
                        })
                    })
                    continue
            
            result = await execute_tool(
                name=call.name,
                arguments=call.arguments
            )
            messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "content": json.dumps(result)
            })
    
    raise MaxIterationsExceeded()
```

---

## Streaming SSE

### Proxy → CLI

```python
async def stream_response(response: AsyncIterator[str]):
    async for chunk in response:
        yield f"data: {json.dumps({'content': chunk})}\n\n"
    yield "data: [DONE]\n\n"
```

### CLI réception

```python
async def receive_stream(url: str):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            async for line in resp.content:
                if line.startswith(b"data: "):
                    data = json.loads(line[6:])
                    if data != "[DONE]":
                        print(data["content"], end="", flush=True)
```

---

## Instructions système pour le LLM

Le proxy injecte ce prompt système pour guider l'utilisation des tools :

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
- `shell_exec(command, cwd?, timeout?)` : exécute une commande shell

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
