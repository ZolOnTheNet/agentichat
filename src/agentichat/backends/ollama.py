"""Backend Ollama pour agentichat."""

import json
import re
from typing import AsyncIterator

import aiohttp

from ..utils.logger import get_logger
from .base import Backend, BackendError, ChatResponse, Message, ToolCall

logger = get_logger("agentichat.backends.ollama")


class OllamaBackend(Backend):
    """Backend pour serveur Ollama local ou distant."""

    def __init__(self, *args, **kwargs):
        """Initialise le backend Ollama."""
        super().__init__(*args, **kwargs)
        self.last_usage: dict | None = None  # Dernières statistiques d'utilisation

    def _extract_tool_calls_from_text(self, content: str) -> list[ToolCall] | None:
        """Extrait les tool calls du texte si le modèle les génère en JSON.

        Args:
            content: Contenu de la réponse du LLM

        Returns:
            Liste de ToolCall ou None si aucun trouvé
        """
        import uuid

        tool_calls = []

        # Étape 1: Extraire le contenu des blocs ```json ... ```
        json_code_blocks = re.findall(r'```json\s*(.+?)\s*```', content, re.DOTALL)

        # Pour chaque bloc de code JSON, extraire tous les objets JSON
        json_objects = []
        for block in json_code_blocks:
            # Trouver tous les objets JSON dans le bloc (peuvent être sur plusieurs lignes)
            # On cherche des objets qui commencent par { et finissent par }
            # et qui contiennent "name" et "arguments"
            lines = block.strip().split('\n')
            current_obj = ""
            brace_count = 0

            for line in lines:
                stripped = line.strip()
                if not stripped:
                    continue

                current_obj += line + "\n"

                # Compter les accolades pour savoir quand l'objet est complet
                brace_count += line.count('{') - line.count('}')

                # Si on a un objet complet (brace_count retourne à 0)
                if brace_count == 0 and current_obj.strip():
                    json_objects.append(current_obj.strip())
                    current_obj = ""

        # Si pas de blocs markdown, chercher directement des objets JSON dans le texte
        if not json_objects:
            # Pattern pour JSONs simples (supporter "arguments" et "parameters")
            # Chercher tous les objets avec "name" et un objet imbriqué
            potential_jsons = re.findall(r'\{[^{}]*"name"[^{}]*\{[^}]*\}[^{}]*\}', content)
            json_objects.extend(potential_jsons)

        # Parser chaque objet JSON trouvé
        for json_str in json_objects:
            data = None

            # Tentative 1 : parsing JSON direct
            try:
                data = json.loads(json_str)
            except json.JSONDecodeError:
                pass

            # Tentative 2 : corriger les backslashes non échappés (regex dans JSON)
            # ex: \s+ → \\s+, \d+ → \\d+, \. → \\.
            if data is None:
                try:
                    fixed = re.sub(r'\\(?!["\\/bfnrtu])', r'\\\\', json_str)
                    data = json.loads(fixed)
                    logger.debug("Parsed JSON after fixing unescaped backslashes")
                except (json.JSONDecodeError, TypeError):
                    pass

            if data is None:
                logger.debug(f"Failed to parse JSON: {json_str[:100]}...")
                continue

            if isinstance(data, dict) and "name" in data:
                # Valider que le tool call a un nom non vide
                tool_name = data.get("name", "").strip()
                if not tool_name:
                    continue

                # Supporter "arguments" et "parameters" (certains modèles utilisent parameters)
                arguments = data.get("arguments") or data.get("parameters") or {}
                if not isinstance(arguments, dict):
                    arguments = {}

                tool_call = ToolCall(
                    id=str(uuid.uuid4()),
                    name=tool_name,
                    arguments=arguments,
                )
                tool_calls.append(tool_call)
                logger.info(f"Extracted tool call from text: {tool_name}")

        return tool_calls if tool_calls else None

    async def chat(
        self,
        messages: list[Message],
        tools: list[dict] | None = None,
        stream: bool = False,
    ) -> AsyncIterator[str] | ChatResponse:
        """Envoie un message au LLM Ollama.

        Args:
            messages: Historique de la conversation
            tools: Liste des tools disponibles (format JSON Schema)
            stream: Si True, retourne un itérateur pour le streaming

        Returns:
            Si stream=True: AsyncIterator[str] pour recevoir les chunks
            Si stream=False: ChatResponse avec la réponse complète

        Raises:
            BackendError: En cas d'erreur de communication
        """
        endpoint = f"{self.url}/api/chat"

        # Convertir les messages au format Ollama
        ollama_messages = []
        for msg in messages:
            message_dict = {
                "role": msg.role,
                "content": msg.content,
            }

            # Convertir les tool_calls (objets ToolCall) en dictionnaires
            if msg.tool_calls:
                message_dict["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": tc.arguments,
                        },
                    }
                    for tc in msg.tool_calls
                ]

            ollama_messages.append(message_dict)

        # Construire la requête
        payload = {
            "model": self.model,
            "messages": ollama_messages,
            "stream": stream,
            "options": {
                "num_predict": self.max_tokens,
                "temperature": self.temperature,
            },
        }

        # Ajouter les tools si fournis
        if tools:
            payload["tools"] = tools
            logger.debug(f"Sending request with {len(tools)} tools")
            logger.debug(f"Tools payload: {json.dumps(tools, indent=2)}")

        logger.debug(
            f"Ollama request: model={self.model}, messages={len(messages)}, "
            f"stream={stream}, timeout={self.timeout}s"
        )

        if stream:
            # Pour le streaming, on doit garder la session ouverte (pas de retry)
            logger.debug("Starting streaming chat")
            return self._stream_chat(endpoint, payload)

        # Pour le non-streaming : retry automatique sur erreurs transitoires
        logger.debug("Starting non-streaming chat")

        async def _do_request():
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        endpoint,
                        json=payload,
                        timeout=aiohttp.ClientTimeout(total=self.timeout),
                    ) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            error_type = (
                                BackendError.MODEL_NOT_FOUND if response.status == 404
                                else BackendError.SERVER_ERROR if response.status >= 500
                                else BackendError.UNKNOWN
                            )
                            raise BackendError(
                                f"Ollama error: {error_text}",
                                status_code=response.status,
                                error_type=error_type,
                            )
                        return await self._parse_response(response)
            except aiohttp.ServerTimeoutError as e:
                raise BackendError(
                    f"Timeout: {e}", error_type=BackendError.TIMEOUT
                ) from e
            except aiohttp.ClientError as e:
                raise BackendError(
                    f"Connection error: {e}", error_type=BackendError.SERVER_ERROR
                ) from e

        return await self._retry_on_error(_do_request)

    async def _stream_chat(self, endpoint: str, payload: dict) -> AsyncIterator[str]:
        """Stream la réponse d'Ollama avec session HTTP maintenue.

        Args:
            endpoint: URL de l'endpoint
            payload: Données à envoyer

        Yields:
            Chunks de texte au fur et à mesure
        """
        async with aiohttp.ClientSession() as session:
            async with session.post(
                endpoint,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=self.timeout),
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    error_type = (
                        BackendError.MODEL_NOT_FOUND if response.status == 404
                        else BackendError.SERVER_ERROR if response.status >= 500
                        else BackendError.UNKNOWN
                    )
                    raise BackendError(
                        f"Ollama error: {error_text}",
                        status_code=response.status,
                        error_type=error_type,
                    )

                # Lire ligne par ligne
                async for line in response.content:
                    if not line:
                        continue

                    try:
                        data = json.loads(line)
                        if "message" in data:
                            content = data["message"].get("content", "")
                            if content:
                                yield content

                        # Fin du stream
                        if data.get("done", False):
                            break

                    except json.JSONDecodeError:
                        continue

    async def _parse_response(self, response: aiohttp.ClientResponse) -> ChatResponse:
        """Parse la réponse complète d'Ollama.

        Args:
            response: Réponse HTTP d'Ollama

        Returns:
            ChatResponse avec le contenu et éventuels tool calls
        """
        data = await response.json()
        logger.debug(f"Ollama response data: {json.dumps(data, indent=2)}")

        message = data.get("message", {})
        content = message.get("content", "")

        # Parser les tool calls si présents (natifs d'Ollama)
        tool_calls = None
        if "tool_calls" in message:
            tool_calls = []
            for tc in message["tool_calls"]:
                func = tc.get("function", {})
                args_raw = func.get("arguments", "{}")

                # Si arguments est déjà un dict, l'utiliser directement
                # Sinon, le parser comme JSON
                if isinstance(args_raw, dict):
                    arguments = args_raw
                elif isinstance(args_raw, str):
                    arguments = json.loads(args_raw)
                else:
                    arguments = {}

                tool_calls.append(
                    ToolCall(
                        id=tc.get("id", ""),
                        name=func.get("name", ""),
                        arguments=arguments,
                    )
                )

        # Si aucun tool call natif trouvé, essayer d'en extraire du texte
        if not tool_calls and content:
            extracted_calls = self._extract_tool_calls_from_text(content)
            if extracted_calls:
                tool_calls = extracted_calls
                logger.info("Using fallback: extracted tool calls from response text")

        # Limiter le nombre de tool calls si nécessaire
        tool_calls = self._limit_tool_calls(tool_calls)
        if tool_calls and self.max_parallel_tools and len(tool_calls) == self.max_parallel_tools:
            logger.info(f"Limited tool calls to {self.max_parallel_tools} (max_parallel_tools setting)")

        # Déterminer la raison de fin
        finish_reason = "stop"
        if tool_calls:
            finish_reason = "tool_calls"
        elif data.get("done_reason") == "length":
            finish_reason = "length"

        # Extraire les statistiques de tokens
        from .base import TokenUsage

        usage = None
        if "prompt_eval_count" in data or "eval_count" in data:
            prompt_tokens = data.get("prompt_eval_count", 0)
            completion_tokens = data.get("eval_count", 0)
            usage = TokenUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
            )

        # Stocker les statistiques détaillées pour affichage
        prompt_tokens = data.get("prompt_eval_count", 0)
        completion_tokens = data.get("eval_count", 0)
        self.last_usage = {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "prompt_eval_duration_ms": data.get("prompt_eval_duration", 0) / 1_000_000,  # ns -> ms
            "eval_duration_ms": data.get("eval_duration", 0) / 1_000_000,  # ns -> ms
            "total_duration_ms": data.get("total_duration", 0) / 1_000_000,  # ns -> ms
            "load_duration_ms": data.get("load_duration", 0) / 1_000_000,  # ns -> ms
        }
        # Accumuler dans le compteur cumulatif
        self._accumulate_usage(prompt_tokens, completion_tokens)

        return ChatResponse(
            content=content, tool_calls=tool_calls, finish_reason=finish_reason, usage=usage
        )

    async def list_models(self) -> list[str]:
        """Liste les modèles disponibles sur Ollama.

        Returns:
            Liste des noms de modèles

        Raises:
            BackendError: En cas d'erreur de communication
        """
        endpoint = f"{self.url}/api/tags"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    endpoint, timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise BackendError(
                            f"Ollama error: {error_text}", status_code=response.status
                        )

                    data = await response.json()
                    models = data.get("models", [])
                    return [model["name"] for model in models]

        except aiohttp.ClientError as e:
            raise BackendError(f"Connection error: {e}") from e

    async def health_check(self) -> bool:
        """Vérifie que le serveur Ollama est accessible.

        Returns:
            True si le serveur répond, False sinon
        """
        try:
            await self.list_models()
            return True
        except BackendError:
            return False

    def set_model(self, model: str) -> None:
        """Change le modèle utilisé par le backend.

        Args:
            model: Nom du nouveau modèle
        """
        logger.info(f"Switching model from {self.model} to {model}")
        self.model = model
