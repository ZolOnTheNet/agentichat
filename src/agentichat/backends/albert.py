"""Backend Albert API (Etalab) pour agentichat."""

import json
from typing import AsyncIterator

import aiohttp

from ..utils.logger import get_logger
from .base import Backend, BackendError, ChatResponse, Message, TokenUsage, ToolCall

logger = get_logger("agentichat.backends.albert")


class AlbertBackend(Backend):
    """Backend pour l'API Albert (OpenGateLLM) d'Etalab.

    Albert est un service public français qui donne accès à des modèles
    de langage avec des fonctionnalités avancées :
    - Chat avec function calling
    - Recherche sémantique dans des documents
    - OCR et parsing de documents
    - Transcription audio
    - Embeddings
    """

    def __init__(self, *args, **kwargs):
        """Initialise le backend Albert.

        Args:
            url: URL de l'API Albert (par défaut: https://albert.api.etalab.gouv.fr)
            model: Nom du modèle à utiliser
            api_key: Clé API pour l'authentification (obligatoire)
            **kwargs: Paramètres supplémentaires (temperature, max_tokens, etc.)
        """
        super().__init__(*args, **kwargs)
        self.last_usage: dict | None = None

        # Vérifier que l'API key est présente
        if not self.api_key:
            raise BackendError(
                "API key requise pour Albert. "
                "Ajoutez 'api_key: YOUR_KEY' dans la configuration."
            )

    def _extract_tool_calls_from_text(self, content: str) -> list[ToolCall] | None:
        """Extrait les tool calls du texte si le modèle les génère en texte.

        Supporte plusieurs formats:
        - [TOOL_CALLS]tool_name{"arg": "value"}
        - [TOOL_CALLS]{"function": "tool_name", "arg": "value"}
        - ```json\n{"name": "tool_name", "arguments": {...}}\n```

        Args:
            content: Contenu de la réponse du LLM

        Returns:
            Liste de ToolCall ou None si aucun trouvé
        """
        import re
        import uuid

        tool_calls = []

        # Format 1: [TOOL_CALLS]tool_name{...args...}
        # Chercher tous les [TOOL_CALLS]tool_name dans le texte
        pattern = r'\[TOOL_CALLS\](\w+)\s*(\{)'
        matches = re.finditer(pattern, content)

        for match in matches:
            tool_name = match.group(1)
            start_pos = match.end() - 1  # Position du '{'

            # Compter les accolades pour trouver la fin du JSON
            brace_count = 0
            end_pos = start_pos
            in_string = False
            escape_next = False

            for i in range(start_pos, len(content)):
                char = content[i]

                # Gérer les échappements dans les strings
                if escape_next:
                    escape_next = False
                    continue

                if char == '\\':
                    escape_next = True
                    continue

                # Gérer les guillemets (entrée/sortie de string)
                if char == '"' and not escape_next:
                    in_string = not in_string
                    continue

                # Compter les accolades seulement hors des strings
                if not in_string:
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1

                        # JSON complet trouvé
                        if brace_count == 0:
                            end_pos = i + 1
                            break

            # Extraire le JSON
            json_str = content[start_pos:end_pos]

            try:
                arguments = json.loads(json_str)
                tool_call = ToolCall(
                    id=str(uuid.uuid4()),
                    name=tool_name,
                    arguments=arguments if isinstance(arguments, dict) else {},
                )
                tool_calls.append(tool_call)
                logger.info(f"Extracted tool call from [TOOL_CALLS] format: {tool_name}")
            except json.JSONDecodeError as e:
                logger.debug(f"Failed to parse [TOOL_CALLS] arguments: {json_str[:100]}... Error: {e}")
                continue

        # Format 5: [TOOL_CALLS]{"function": "tool_name", ...args au même niveau...}
        # Nouveau format où le JSON contient directement "function" pour le nom
        pattern_func = r'\[TOOL_CALLS\](\{)'
        matches_func = re.finditer(pattern_func, content)

        for match in matches_func:
            start_pos = match.end() - 1  # Position du '{'

            # Compter les accolades pour trouver la fin du JSON
            brace_count = 0
            end_pos = start_pos
            in_string = False
            escape_next = False

            for i in range(start_pos, len(content)):
                char = content[i]

                if escape_next:
                    escape_next = False
                    continue

                if char == '\\':
                    escape_next = True
                    continue

                if char == '"' and not escape_next:
                    in_string = not in_string
                    continue

                if not in_string:
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1

                        if brace_count == 0:
                            end_pos = i + 1
                            break

            # Extraire le JSON
            json_str = content[start_pos:end_pos]

            try:
                data = json.loads(json_str)
                if isinstance(data, dict) and "function" in data:
                    tool_name = data.pop("function")  # Retirer "function" du dict
                    # Les autres clés sont les arguments
                    arguments = data

                    tool_call = ToolCall(
                        id=str(uuid.uuid4()),
                        name=tool_name,
                        arguments=arguments,
                    )
                    tool_calls.append(tool_call)
                    logger.info(f"Extracted tool call from [TOOL_CALLS]{{function:...}} format: {tool_name}")
            except json.JSONDecodeError as e:
                logger.debug(f"Failed to parse [TOOL_CALLS]{{function:...}} format: {json_str[:100]}... Error: {e}")
                continue

        # Format 2: Blocs ```json ... ``` avec name et arguments/parameters
        json_code_blocks = re.findall(r'```json\s*(.+?)\s*```', content, re.DOTALL)

        for block in json_code_blocks:
            lines = block.strip().split('\n')
            current_obj = ""
            brace_count = 0

            for line in lines:
                stripped = line.strip()
                if not stripped:
                    continue

                current_obj += line + "\n"
                brace_count += line.count('{') - line.count('}')

                if brace_count == 0 and current_obj.strip():
                    try:
                        data = json.loads(current_obj.strip())
                        if isinstance(data, dict) and "name" in data:
                            # Supporter "arguments" et "parameters"
                            arguments = data.get("arguments") or data.get("parameters") or {}
                            if not isinstance(arguments, dict):
                                arguments = {}

                            tool_call = ToolCall(
                                id=str(uuid.uuid4()),
                                name=data["name"],
                                arguments=arguments,
                            )
                            tool_calls.append(tool_call)
                            logger.info(f"Extracted tool call from JSON block: {data['name']}")
                    except json.JSONDecodeError as e:
                        logger.debug(f"Failed to parse JSON block: {current_obj[:100]}... Error: {e}")

                    current_obj = ""

        # Format 3: JSON direct dans le texte (sans blocs markdown)
        # Chercher tous les objets avec "name" et des paramètres
        if not tool_calls:
            potential_jsons = re.findall(r'\{[^{}]*"name"[^{}]*\{[^}]*\}[^{}]*\}', content)
            for json_str in potential_jsons:
                try:
                    data = json.loads(json_str)
                    if isinstance(data, dict) and "name" in data:
                        arguments = data.get("arguments") or data.get("parameters") or {}
                        if not isinstance(arguments, dict):
                            arguments = {}

                        tool_call = ToolCall(
                            id=str(uuid.uuid4()),
                            name=data["name"],
                            arguments=arguments,
                        )
                        tool_calls.append(tool_call)
                        logger.info(f"Extracted tool call from direct JSON: {data['name']}")
                except json.JSONDecodeError as e:
                    logger.debug(f"Failed to parse direct JSON: {json_str[:100]}... Error: {e}")

        # Format 4: Format XML de Qwen3 - <tool_call><function=...><parameter=...>
        # Exemple: <tool_call><function=list_files><parameter=path>.</parameter></function></tool_call>
        xml_pattern = r'<tool_call>\s*<function=(\w+)>(.*?)</function>\s*</tool_call>'
        xml_matches = re.finditer(xml_pattern, content, re.DOTALL)

        for match in xml_matches:
            tool_name = match.group(1)
            params_block = match.group(2)

            # Parser les paramètres - format: <parameter=name>value</parameter>
            arguments = {}
            param_pattern = r'<parameter=(\w+)>(.*?)</parameter>'
            param_matches = re.finditer(param_pattern, params_block, re.DOTALL)

            for param_match in param_matches:
                param_name = param_match.group(1)
                param_value = param_match.group(2).strip()
                arguments[param_name] = param_value

            tool_call = ToolCall(
                id=str(uuid.uuid4()),
                name=tool_name,
                arguments=arguments,
            )
            tool_calls.append(tool_call)
            logger.info(f"Extracted tool call from XML format (Qwen3): {tool_name}")

        return tool_calls if tool_calls else None

    def _get_headers(self) -> dict[str, str]:
        """Retourne les headers HTTP avec authentification.

        Returns:
            Headers avec Bearer token
        """
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def chat(
        self,
        messages: list[Message],
        tools: list[dict] | None = None,
        stream: bool = False,
    ) -> AsyncIterator[str] | ChatResponse:
        """Envoie un message au LLM Albert.

        Args:
            messages: Historique de la conversation
            tools: Liste des tools disponibles (format OpenAI function calling)
            stream: Si True, retourne un itérateur pour le streaming

        Returns:
            Si stream=True: AsyncIterator[str] pour recevoir les chunks
            Si stream=False: ChatResponse avec la réponse complète

        Raises:
            BackendError: En cas d'erreur de communication
        """
        endpoint = f"{self.url}/v1/chat/completions"

        # Convertir les messages au format OpenAI/Albert
        albert_messages = []
        for msg in messages:
            message_dict = {
                "role": msg.role,
                "content": msg.content,
            }

            # Convertir les tool_calls (objets ToolCall) en format OpenAI
            if msg.tool_calls:
                message_dict["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments),
                        },
                    }
                    for tc in msg.tool_calls
                ]

            # Ajouter tool_call_id si présent (pour réponses de tools)
            if msg.tool_call_id:
                message_dict["tool_call_id"] = msg.tool_call_id

            albert_messages.append(message_dict)

        # Construire la requête
        payload = {
            "model": self.model,
            "messages": albert_messages,
            "stream": stream,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

        # Ajouter les tools si fournis (format OpenAI function calling)
        # Note: tools sont déjà au bon format depuis registry.to_schemas()
        if tools:
            payload["tools"] = tools
            logger.debug(f"Sending request with {len(tools)} tools")
            logger.debug(f"Tools payload: {json.dumps(tools, indent=2)}")

        logger.debug(
            f"Albert request: model={self.model}, messages={len(messages)}, "
            f"stream={stream}, timeout={self.timeout}s"
        )

        try:
            if stream:
                # Pour le streaming, on doit garder la session ouverte
                logger.debug("Starting streaming chat")
                return self._stream_chat(endpoint, payload)
            else:
                # Pour le non-streaming, on peut fermer après avoir récupéré la réponse
                logger.debug("Starting non-streaming chat")
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

        except aiohttp.ClientError as e:
            raise BackendError(f"Connection error: {e}") from e

    async def _stream_chat(self, endpoint: str, payload: dict) -> AsyncIterator[str]:
        """Stream la réponse d'Albert avec session HTTP maintenue.

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
                headers=self._get_headers(),
                timeout=aiohttp.ClientTimeout(total=self.timeout),
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise BackendError(
                        f"Albert API error: {error_text}",
                        status_code=response.status,
                    )

                # Lire ligne par ligne (format SSE)
                async for line in response.content:
                    if not line:
                        continue

                    line_str = line.decode("utf-8").strip()

                    # Format SSE: "data: {...}"
                    if line_str.startswith("data: "):
                        data_str = line_str[6:]  # Enlever "data: "

                        # Fin du stream
                        if data_str == "[DONE]":
                            break

                        try:
                            data = json.loads(data_str)
                            if "choices" in data and len(data["choices"]) > 0:
                                delta = data["choices"][0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    yield content
                        except json.JSONDecodeError:
                            continue

    async def _parse_response(self, response: aiohttp.ClientResponse) -> ChatResponse:
        """Parse la réponse complète d'Albert.

        Args:
            response: Réponse HTTP d'Albert

        Returns:
            ChatResponse avec le contenu et éventuels tool calls
        """
        data = await response.json()
        logger.debug(f"Albert response data: {json.dumps(data, indent=2)}")

        if "choices" not in data or len(data["choices"]) == 0:
            raise BackendError("Invalid response format from Albert API")

        choice = data["choices"][0]
        message = choice.get("message", {})
        content = message.get("content", "")

        # Parser les tool calls si présents (format OpenAI)
        tool_calls = None
        if "tool_calls" in message and message["tool_calls"]:
            tool_calls = []
            for tc in message["tool_calls"]:
                func = tc.get("function", {})
                args_str = func.get("arguments", "{}")

                # Parser les arguments JSON
                try:
                    arguments = json.loads(args_str) if isinstance(args_str, str) else args_str
                except json.JSONDecodeError:
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
        finish_reason = choice.get("finish_reason", "stop")
        if tool_calls:
            finish_reason = "tool_calls"

        # Extraire les statistiques de tokens
        usage = None
        if "usage" in data:
            usage_data = data["usage"]
            usage = TokenUsage(
                prompt_tokens=usage_data.get("prompt_tokens", 0),
                completion_tokens=usage_data.get("completion_tokens", 0),
                total_tokens=usage_data.get("total_tokens", 0),
            )

        # Stocker les statistiques pour affichage
        if usage:
            self.last_usage = {
                "prompt_tokens": usage.prompt_tokens,
                "completion_tokens": usage.completion_tokens,
                "total_tokens": usage.total_tokens,
            }
            # Accumuler dans le compteur cumulatif
            self._accumulate_usage(usage.prompt_tokens, usage.completion_tokens)

        return ChatResponse(
            content=content,
            tool_calls=tool_calls,
            finish_reason=finish_reason,
            usage=usage,
        )

    async def list_models(self) -> list[str]:
        """Liste les modèles disponibles sur Albert.

        Returns:
            Liste des noms de modèles

        Raises:
            BackendError: En cas d'erreur de communication
        """
        endpoint = f"{self.url}/v1/models"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    endpoint,
                    headers=self._get_headers(),
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise BackendError(
                            f"Albert API error: {error_text}",
                            status_code=response.status,
                        )

                    data = await response.json()
                    models = data.get("data", [])
                    return [model["id"] for model in models]

        except aiohttp.ClientError as e:
            raise BackendError(f"Connection error: {e}") from e

    async def health_check(self) -> bool:
        """Vérifie que l'API Albert est accessible.

        Returns:
            True si l'API répond, False sinon
        """
        endpoint = f"{self.url}/health"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    endpoint,
                    timeout=aiohttp.ClientTimeout(total=5),
                ) as response:
                    return response.status == 200
        except aiohttp.ClientError:
            return False

    def set_model(self, model: str) -> None:
        """Change le modèle utilisé par le backend.

        Args:
            model: Nom du nouveau modèle
        """
        logger.info(f"Switching model from {self.model} to {model}")
        self.model = model
