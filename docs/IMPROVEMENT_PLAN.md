# Plan d'Amélioration agentichat - Consignes pour Claude Code

> Ce document décrit les modifications à apporter au logiciel agentichat.
> Chaque section est une tâche indépendante. Implémentez-les dans l'ordre.
> **Règle absolue** : ne pas casser l'existant. Chaque modification doit être
> testable indépendamment.

---

## Tâche 1 : Gestion du contexte avec limite de tokens (CRITIQUE)

### Problème
La boucle agentique (`core/agent.py`) envoie l'intégralité de `messages` au
backend à chaque itération. Il n'y a aucun contrôle de taille. Quand le contexte
dépasse la limite du modèle (ex: 128k tokens Albert), l'API retourne une erreur
et la requête est perdue.

### Fichiers à modifier
- `src/agentichat/config/schema.py` — ajouter `context_max_tokens` dans BackendConfig
- `src/agentichat/backends/base.py` — ajouter méthode `estimate_tokens()`
- `src/agentichat/core/agent.py` — ajouter troncature avant chaque appel

### Spécification

#### 1.1 Ajouter `context_max_tokens` à BackendConfig (schema.py)

```python
@dataclass
class BackendConfig:
    # ... champs existants ...
    context_max_tokens: int | None = None  # Limite de contexte (None = pas de limite)
```

Et dans `validate_config()`, lire `context_max_tokens` depuis le YAML.

#### 1.2 Estimation de tokens dans Backend (base.py)

Ajouter à la classe `Backend` :

```python
def estimate_tokens(self, text: str) -> int:
    """Estimation rapide du nombre de tokens (heuristique).

    Règle : ~4 caractères par token en moyenne pour du texte mixte.
    C'est une approximation, mais suffisante pour du budgeting.
    """
    return len(text) // 3  # Marge de sécurité (3 chars/token au lieu de 4)

def estimate_messages_tokens(self, messages: list[Message]) -> int:
    """Estime le nombre total de tokens dans une liste de messages."""
    total = 0
    for msg in messages:
        # Overhead par message (~4 tokens pour role + délimiteurs)
        total += 4
        total += self.estimate_tokens(msg.content or "")
        if msg.tool_calls:
            for tc in msg.tool_calls:
                total += self.estimate_tokens(json.dumps(tc.arguments))
                total += self.estimate_tokens(tc.name)
    return total
```

Stocker `self.context_max_tokens` dans `__init__` depuis kwargs.

#### 1.3 Troncature intelligente du contexte dans AgentLoop (agent.py)

Ajouter une méthode `_trim_context()` appelée **avant chaque appel à
`self.backend.chat()`** dans la boucle `while` :

```python
def _trim_context(self, messages: list[Message]) -> list[Message]:
    """Tronque les messages pour respecter la limite de tokens du backend.

    Stratégie :
    1. Toujours garder le message système (index 0) s'il existe
    2. Toujours garder les N derniers messages (au minimum 4)
    3. Supprimer les messages les plus anciens en premier
    4. Tronquer les tool results trop longs (> 2000 chars) avec un résumé
    """
    max_tokens = getattr(self.backend, 'context_max_tokens', None)
    if not max_tokens:
        return messages

    # Réserver 20% pour la réponse + tools schema
    budget = int(max_tokens * 0.80)

    # Estimer le total actuel
    current = self.backend.estimate_messages_tokens(messages)
    if current <= budget:
        return messages

    # Phase 1 : Tronquer les tool results volumineux
    for msg in messages:
        if msg.role == "tool" and len(msg.content or "") > 2000:
            # Garder seulement les 500 premiers et 500 derniers caractères
            content = msg.content
            msg.content = content[:500] + "\n\n[... contenu tronqué ...]\n\n" + content[-500:]

    current = self.backend.estimate_messages_tokens(messages)
    if current <= budget:
        return messages

    # Phase 2 : Supprimer les messages anciens (garder system + 4 derniers)
    system_msgs = [m for m in messages if m.role == "system"]
    non_system = [m for m in messages if m.role != "system"]

    min_keep = 4  # Garder au minimum les 4 derniers messages
    while len(non_system) > min_keep:
        non_system.pop(0)  # Supprimer le plus ancien
        trial = system_msgs + non_system
        if self.backend.estimate_messages_tokens(trial) <= budget:
            return trial

    return system_msgs + non_system
```

**Intégration** dans la boucle `while` de `run()` (avant l'appel `self.backend.chat`) :

```python
# Avant l'appel au LLM, tronquer si nécessaire
trimmed_messages = self._trim_context(messages)

response = await self.backend.chat(
    messages=trimmed_messages,  # <-- utiliser la version tronquée
    tools=self.registry.to_schemas(),
    stream=False,
)
```

**IMPORTANT** : `messages` (la liste originale) continue de s'accumuler pour
l'historique complet. Seul `trimmed_messages` est envoyé au backend. Cela permet
de ne pas perdre l'historique pour la DB.

#### 1.4 Configuration YAML

Exemple de config :

```yaml
backends:
  albert:
    type: albert
    url: https://albert.api.etalab.gouv.fr
    model: meta-llama/Llama-3.1-70B-Instruct
    api_key: ${ALBERT_API_KEY}
    max_tokens: 4096
    context_max_tokens: 120000  # Limite Albert: 128k, on prend marge
```

---

## Tâche 2 : Retry avec backoff exponentiel (IMPORTANT)

### Problème
Aucun retry n'existe. Un 429 (rate limit) ou 503 (service indisponible) provoque
un arrêt immédiat alors que ces erreurs sont transitoires.

### Fichiers à modifier
- `src/agentichat/backends/base.py` — ajouter décorateur/méthode retry
- `src/agentichat/backends/albert.py` — appliquer le retry
- `src/agentichat/backends/ollama.py` — appliquer le retry

### Spécification

#### 2.1 Méthode retry dans Backend (base.py)

Ajouter dans la classe `Backend` :

```python
import asyncio
import logging

logger = logging.getLogger(__name__)

async def _retry_on_error(
    self,
    coro_factory,  # Callable qui retourne une coroutine
    max_retries: int = 3,
    base_delay: float = 2.0,
    retryable_status: tuple[int, ...] = (429, 500, 502, 503, 504),
) -> any:
    """Exécute une coroutine avec retry et backoff exponentiel.

    Args:
        coro_factory: Fonction qui crée la coroutine à chaque tentative
        max_retries: Nombre maximum de tentatives
        base_delay: Délai initial en secondes
        retryable_status: Codes HTTP qui déclenchent un retry

    Returns:
        Résultat de la coroutine

    Raises:
        BackendError: Si toutes les tentatives échouent
    """
    last_error = None

    for attempt in range(max_retries + 1):
        try:
            return await coro_factory()
        except BackendError as e:
            last_error = e
            if e.status_code not in retryable_status:
                raise  # Pas retryable (400, 401, 404, etc.)

            if attempt == max_retries:
                raise  # Dernière tentative, propager l'erreur

            delay = base_delay * (2 ** attempt)  # 2s, 4s, 8s
            logger.warning(
                f"Erreur {e.status_code}, retry {attempt + 1}/{max_retries} "
                f"dans {delay:.0f}s..."
            )
            await asyncio.sleep(delay)

    raise last_error
```

#### 2.2 Appliquer dans AlbertBackend.chat() (albert.py)

Wrapper l'appel HTTP existant :

```python
async def chat(self, messages, tools=None, stream=False):
    # ... préparation du payload (existant) ...

    if stream:
        return self._stream_chat(endpoint, payload)

    async def _do_request():
        async with aiohttp.ClientSession() as session:
            async with session.post(
                endpoint,
                json=payload,
                headers=self._get_headers(),
                timeout=aiohttp.ClientTimeout(total=self.timeout),
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise BackendError(
                        f"Albert API error: {error_text}",
                        status_code=response.status,
                    )
                return await self._parse_response(response)

    return await self._retry_on_error(_do_request)
```

#### 2.3 Notification utilisateur pendant le retry

Dans `app.py`, dans `_process_agent_loop()`, le spinner doit afficher quand
un retry est en cours. Pour cela, ajouter un attribut `self.backend.retry_info`
(dict avec `attempt`, `max_retries`, `delay`) mis à jour dans `_retry_on_error`,
et lu par `update_spinner()`.

---

## Tâche 3 : Appliquer `max_messages` (quick win)

### Problème
`CompressionConfig.max_messages` existe dans le schéma mais n'est **jamais
appliqué** nulle part dans le code.

### Fichier à modifier
- `src/agentichat/cli/app.py` — dans `_check_compression_warning()`

### Spécification

Dans `_check_compression_warning()` (app.py, ligne ~702), ajouter **après**
l'avertissement existant :

```python
# Appliquer max_messages si configuré ET auto_enabled
if compress_config.max_messages and compress_config.auto_enabled:
    if message_count >= compress_config.max_messages:
        self.console.print(
            f"[bold yellow]⚠ Limite de {compress_config.max_messages} messages atteinte, "
            f"compression automatique...[/bold yellow]"
        )
        # Lancer la compression automatique
        await self._handle_compress_command(
            f"/compress --keep {compress_config.auto_keep}"
        )
```

**Note** : `_check_compression_warning` doit devenir `async` pour cela.

---

## Tâche 4 : Troncature des tool results volumineux (IMPORTANT)

### Problème
Un `read_file` sur un gros fichier ou un `web_fetch` retourne parfois des
milliers de lignes. Ce résultat est sérialisé en JSON brut dans les messages
(`agent.py:128`), gonflant le contexte inutilement.

### Fichier à modifier
- `src/agentichat/core/agent.py` — dans la boucle d'exécution des tool calls

### Spécification

Ajouter une méthode de troncature des résultats :

```python
MAX_TOOL_RESULT_CHARS = 8000  # ~2000 tokens

def _truncate_tool_result(self, result: dict) -> dict:
    """Tronque les résultats d'outils trop volumineux.

    Garde le début et la fin du contenu pour que le LLM comprenne
    la structure sans consommer tout le budget de tokens.
    """
    result_str = json.dumps(result)
    if len(result_str) <= self.MAX_TOOL_RESULT_CHARS:
        return result

    # Tronquer le contenu textuel à l'intérieur du résultat
    if isinstance(result.get("content"), str):
        content = result["content"]
        if len(content) > self.MAX_TOOL_RESULT_CHARS:
            half = self.MAX_TOOL_RESULT_CHARS // 2
            result["content"] = (
                content[:half]
                + f"\n\n[... {len(content) - self.MAX_TOOL_RESULT_CHARS} caractères omis ...]\n\n"
                + content[-half:]
            )
            result["_truncated"] = True

    return result
```

Appeler dans la boucle `for tool_call in response.tool_calls:` :

```python
result = await self._execute_tool_call(tool_call)
result = self._truncate_tool_result(result)  # <-- AJOUTER
messages.append(
    Message(
        role="tool",
        content=json.dumps(result),
        tool_call_id=tool_call.id,
    )
)
```

---

## Tâche 5 : Vérification de `finish_reason` (IMPORTANT)

### Problème
Quand le backend retourne `finish_reason: "length"`, cela signifie que la réponse
a été tronquée par `max_tokens`. Le code actuel ignore complètement cette info.
Le LLM peut générer un JSON de tool call incomplet, qui échoue silencieusement.

### Fichier à modifier
- `src/agentichat/core/agent.py` — après l'appel `self.backend.chat()`

### Spécification

Après la réception de la réponse dans la boucle `while` :

```python
response = await self.backend.chat(...)

# Vérifier si la réponse a été tronquée
if response.finish_reason == "length":
    # Si pas de tool_calls valides et contenu tronqué, signaler
    if not response.tool_calls:
        messages.append(
            Message(role="assistant", content=response.content or "")
        )
        # Ajouter un message système pour demander au LLM de continuer
        messages.append(
            Message(
                role="user",
                content="[Système] Ta réponse a été tronquée (max_tokens atteint). "
                "Résume ta réponse de manière plus concise."
            )
        )
        continue  # Refaire une itération
```

---

## Tâche 6 : Gestion d'erreur structurée dans les backends (MODÉRÉ)

### Problème
`BackendError` a un `status_code` optionnel mais le code appelant fait du
pattern matching sur des strings (`"tokens per minute exceeded"`, `"rate limit"`,
`"not found"`) ce qui est fragile.

### Fichiers à modifier
- `src/agentichat/backends/base.py` — enrichir BackendError
- `src/agentichat/cli/app.py` — utiliser les attributs structurés

### Spécification

#### 6.1 Enrichir BackendError (base.py)

```python
class BackendError(Exception):
    """Erreur de communication avec un backend LLM."""

    # Types d'erreurs catégorisés
    RATE_LIMIT = "rate_limit"
    CONTEXT_TOO_LONG = "context_too_long"
    MODEL_NOT_FOUND = "model_not_found"
    TIMEOUT = "timeout"
    SERVER_ERROR = "server_error"
    AUTH_ERROR = "auth_error"
    UNKNOWN = "unknown"

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        error_type: str = "unknown",
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.error_type = error_type

    @property
    def is_retryable(self) -> bool:
        """Indique si cette erreur est transitoire et retryable."""
        return self.error_type in (self.RATE_LIMIT, self.SERVER_ERROR, self.TIMEOUT)
```

#### 6.2 Catégoriser les erreurs dans AlbertBackend (albert.py)

Quand on lève `BackendError`, détecter le type :

```python
if response.status == 429:
    raise BackendError(
        f"Rate limit: {error_text}",
        status_code=429,
        error_type=BackendError.RATE_LIMIT,
    )
elif response.status == 404:
    raise BackendError(
        f"Modèle introuvable: {error_text}",
        status_code=404,
        error_type=BackendError.MODEL_NOT_FOUND,
    )
elif response.status >= 500:
    raise BackendError(
        f"Erreur serveur: {error_text}",
        status_code=response.status,
        error_type=BackendError.SERVER_ERROR,
    )
# etc.
```

#### 6.3 Simplifier le handling dans app.py

Remplacer le pattern matching sur strings par :

```python
except BackendError as e:
    self._display_token_stats(time.time() - start_time)

    if e.error_type == BackendError.RATE_LIMIT:
        self.console.print(f"\n[bold yellow]⚠ Quota API dépassé[/bold yellow]")
        self.console.print("[dim]Le retry automatique a échoué. Attendez ~60s.[/dim]")

    elif e.error_type == BackendError.CONTEXT_TOO_LONG:
        self.console.print(f"\n[bold yellow]⚠ Contexte trop long[/bold yellow]")
        self.console.print("[dim]→ /compress pour réduire l'historique[/dim]")

    elif e.error_type == BackendError.MODEL_NOT_FOUND:
        # ... proposer changement de modèle ...

    else:
        self.console.print(f"\n[bold red]Erreur:[/bold red] {e}")
```

---

## Tâche 7 : Optimisation de la boucle de feedback (PERFORMANCE)

### Problème
Même si les commandes internes (`/help`, `/clear`, etc.) sont rapides, la boucle
agentique peut être optimisée pour un retour plus réactif.

### Fichiers à modifier
- `src/agentichat/core/agent.py` — ne pas ré-envoyer les tools schemas quand inutile
- `src/agentichat/cli/app.py` — cache des schemas

### Spécification

#### 7.1 Cache des tool schemas

`self.registry.to_schemas()` est appelé à chaque itération de la boucle agentique.
Si le registre ne change pas, c'est du calcul inutile.

Dans `ToolRegistry`, ajouter un cache :

```python
class ToolRegistry:
    def __init__(self):
        self._tools = {}
        self._schemas_cache = None

    def to_schemas(self) -> list[dict]:
        if self._schemas_cache is None:
            self._schemas_cache = [... construire les schemas ...]
        return self._schemas_cache

    def register(self, tool):
        self._tools[tool.name] = tool
        self._schemas_cache = None  # Invalider le cache
```

#### 7.2 Ne pas re-sérialiser le système prompt à chaque run()

Le message système (`agent.py:48-88`) est reconstruit à chaque appel de `run()`.
C'est une string constante. Le pré-construire dans `__init__` :

```python
class AgentLoop:
    def __init__(self, backend, registry, ...):
        # ... existant ...
        self._system_message = self._build_system_message()

    def _build_system_message(self) -> Message | None:
        if not self.registry.list_tools():
            return None
        return Message(role="system", content="Vous êtes un assistant...")
```

#### 7.3 Réutiliser la session aiohttp (albert.py)

Actuellement, `AlbertBackend.chat()` crée une nouvelle `aiohttp.ClientSession()`
à chaque appel. Avec le retry et les itérations multiples de la boucle agentique,
c'est N sessions HTTP créées/détruites.

Ajouter une session persistante :

```python
class AlbertBackend(Backend):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
```

Et utiliser `session = await self._get_session()` au lieu de
`async with aiohttp.ClientSession() as session:`.

**Attention** : il faut appeler `await backend.close()` dans `app.py` à la
sortie de l'application (dans le `finally` ou après la boucle REPL).

---

## Résumé des priorités

| # | Tâche | Impact | Difficulté | Fichiers |
|---|-------|--------|------------|----------|
| 1 | Limite de contexte (tokens) | CRITIQUE | Moyenne | schema.py, base.py, agent.py |
| 2 | Retry + backoff | IMPORTANT | Facile | base.py, albert.py, ollama.py |
| 4 | Troncature tool results | IMPORTANT | Facile | agent.py |
| 5 | Vérification finish_reason | IMPORTANT | Facile | agent.py |
| 3 | Appliquer max_messages | Quick win | Facile | app.py |
| 6 | Erreurs structurées | MODÉRÉ | Moyenne | base.py, albert.py, app.py |
| 7 | Optimisations performance | MODÉRÉ | Facile | agent.py, registry.py, albert.py |

## Tests à écrire

Pour chaque tâche, ajouter des tests dans `tests/` :

- `test_context_trimming.py` — vérifier que `_trim_context()` respecte le budget
- `test_retry.py` — simuler des 429 et vérifier le backoff
- `test_tool_result_truncation.py` — vérifier la troncature des gros résultats
- `test_finish_reason.py` — vérifier le comportement sur `finish_reason: "length"`
- `test_error_types.py` — vérifier la catégorisation des erreurs

## Config recommandée pour Albert

```yaml
backends:
  albert:
    type: albert
    url: https://albert.api.etalab.gouv.fr
    model: meta-llama/Llama-3.1-70B-Instruct
    api_key: ${ALBERT_API_KEY}
    timeout: 180
    max_tokens: 4096
    context_max_tokens: 120000   # 128k - marge de sécurité
    max_parallel_tools: 1

compression:
  auto_enabled: true
  auto_threshold: 30
  auto_keep: 5
  max_messages: 50  # Hard limit, déclenche auto-compress
```
