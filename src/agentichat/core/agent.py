"""Boucle agentique pour gérer les tool calls."""

import json
from typing import Any, Callable

from ..backends.base import Backend, Message, ToolCall
from ..tools.registry import ToolRegistry


class AgentLoop:
    """Boucle agentique pour exécuter les tool calls du LLM."""

    def __init__(
        self,
        backend: Backend,
        registry: ToolRegistry,
        max_iterations: int = 10,
        confirmation_callback: Callable[[str, dict], bool] | None = None,
    ) -> None:
        """Initialise la boucle agentique.

        Args:
            backend: Backend LLM à utiliser
            registry: Registre des tools disponibles
            max_iterations: Nombre maximum d'itérations
            confirmation_callback: Callback pour demander confirmation (name, args) -> bool
        """
        self.backend = backend
        self.registry = registry
        self.max_iterations = max_iterations
        self.confirmation_callback = confirmation_callback

    async def run(
        self, messages: list[Message], stream_callback: Callable[[str], None] | None = None
    ) -> tuple[str, list[Message]]:
        """Exécute la boucle agentique.

        Args:
            messages: Historique de conversation
            stream_callback: Callback pour recevoir les chunks de streaming

        Returns:
            Tuple (réponse finale, historique complet)
        """
        # Ajouter un message système si pas déjà présent et si des tools sont disponibles
        has_system_message = messages and messages[0].role == "system"
        if self.registry.list_tools() and not has_system_message:
            system_message = Message(
                role="system",
                content=(
                    "Vous êtes un assistant IA avec accès à des outils pour interagir avec "
                    "le système de fichiers, le web et gérer des tâches.\n\n"
                    "Quand l'utilisateur vous demande quelque chose, appelez les outils appropriés "
                    "en utilisant le format suivant :\n\n"
                    "```json\n"
                    '{"name": "nom_outil", "arguments": {"param1": "valeur1", "param2": "valeur2"}}\n'
                    "```\n\n"
                    "Outils disponibles :\n\n"
                    "**Fichiers :**\n"
                    "- read_file : lit un fichier (param: path)\n"
                    "- list_files : liste les fichiers (params: path, recursive, pattern)\n"
                    "- write_file : crée/modifie un fichier (params: path, content, mode)\n"
                    "- delete_file : supprime un fichier (param: path)\n"
                    "- search_text : cherche du texte (params: pattern, path, recursive)\n"
                    "- glob_search : cherche des fichiers par pattern glob (params: pattern, path, exclude)\n"
                    "  Exemples: '*.py', '**/*.js', 'src/**/*.tsx'\n\n"
                    "**Répertoires :**\n"
                    "- create_directory : crée un répertoire (params: path, parents)\n"
                    "- delete_directory : supprime un répertoire (params: path, recursive)\n"
                    "- move_file : déplace/renomme fichier ou répertoire (params: source, destination, overwrite)\n"
                    "- copy_file : copie fichier ou répertoire (params: source, destination, overwrite)\n\n"
                    "**Web :**\n"
                    "- web_fetch : récupère le contenu d'une URL (params: url, timeout)\n"
                    "- web_search : recherche sur le web avec DuckDuckGo (params: query, max_results)\n\n"
                    "**Système :**\n"
                    "- shell_exec : exécute une commande (param: command)\n\n"
                    "**Productivité :**\n"
                    "- todo_write : crée/met à jour une liste de tâches (param: todos)\n"
                    "  Chaque tâche doit avoir: content, status (pending/in_progress/completed), activeForm\n\n"
                    "Exemple : Pour lire test.py :\n"
                    "```json\n"
                    '{"name": "read_file", "arguments": {"path": "test.py"}}\n'
                    "```\n\n"
                    "IMPORTANT : Appelez les outils directement, n'expliquez PAS à l'utilisateur "
                    "comment les utiliser."
                ),
            )
            messages = [system_message] + messages

        iteration = 0

        while iteration < self.max_iterations:
            iteration += 1

            # Envoyer au LLM avec les tools
            response = await self.backend.chat(
                messages=messages,
                tools=self.registry.to_schemas(),
                stream=False,  # Pas de streaming pour les tool calls
            )

            # Si pas de tool calls, on a la réponse finale
            if not response.tool_calls:
                # Ajouter la réponse à l'historique
                messages.append(
                    Message(role="assistant", content=response.content)
                )
                return response.content, messages

            # Ajouter le message assistant avec tool_calls
            messages.append(
                Message(
                    role="assistant",
                    content=response.content or "",
                    tool_calls=response.tool_calls,
                )
            )

            # Exécuter chaque tool call
            for tool_call in response.tool_calls:
                result = await self._execute_tool_call(tool_call)

                # Ajouter le résultat à l'historique
                messages.append(
                    Message(
                        role="tool",
                        content=json.dumps(result),
                        tool_call_id=tool_call.id,
                    )
                )

        # Si on atteint la limite d'itérations
        # Ajouter un message assistant pour informer l'utilisateur
        error_message = (
            f"⚠ Limite d'itérations atteinte ({self.max_iterations} itérations maximum).\n\n"
            "La tâche est trop complexe pour être effectuée en une seule fois. "
            "Vous pouvez :\n"
            "- Simplifier votre demande\n"
            "- La diviser en plusieurs étapes\n"
            "- Augmenter la limite avec /config"
        )
        messages.append(
            Message(role="assistant", content=error_message)
        )
        return error_message, messages

    async def _execute_tool_call(self, tool_call: ToolCall) -> dict[str, Any]:
        """Exécute un tool call avec confirmation si nécessaire.

        Args:
            tool_call: Tool call à exécuter

        Returns:
            Résultat de l'exécution
        """
        tool = self.registry.get(tool_call.name)

        # Tool introuvable
        if not tool:
            return {
                "success": False,
                "error": f"Tool '{tool_call.name}' introuvable",
            }

        # Demander confirmation si nécessaire
        if tool.requires_confirmation and self.confirmation_callback:
            confirmed = await self.confirmation_callback(
                tool_call.name, tool_call.arguments
            )

            if not confirmed:
                return {
                    "success": False,
                    "error": "USER_REJECTED",
                    "message": "L'utilisateur a refusé cette opération.",
                }

        # Exécuter le tool
        try:
            result = await self.registry.execute(
                tool_call.name, tool_call.arguments
            )
            return result
        except Exception as e:
            return {
                "success": False,
                "error": f"Erreur lors de l'exécution: {e}",
            }


async def run_agent(
    backend: Backend,
    registry: ToolRegistry,
    user_message: str,
    history: list[Message] | None = None,
    max_iterations: int = 10,
    confirmation_callback: Callable[[str, dict], bool] | None = None,
) -> tuple[str, list[Message]]:
    """Helper pour lancer la boucle agentique facilement.

    Args:
        backend: Backend LLM
        registry: Registre des tools
        user_message: Message de l'utilisateur
        history: Historique existant
        max_iterations: Limite d'itérations
        confirmation_callback: Callback pour confirmations

    Returns:
        Tuple (réponse, historique complet)
    """
    messages = history or []
    messages.append(Message(role="user", content=user_message))

    agent = AgentLoop(
        backend=backend,
        registry=registry,
        max_iterations=max_iterations,
        confirmation_callback=confirmation_callback,
    )

    return await agent.run(messages)
