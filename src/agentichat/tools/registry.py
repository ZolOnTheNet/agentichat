"""Registre des tools disponibles pour le LLM."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class Tool(ABC):
    """Interface abstraite pour un tool."""

    name: str
    description: str
    parameters: dict  # JSON Schema
    requires_confirmation: bool = False

    @abstractmethod
    async def execute(self, **kwargs: Any) -> dict[str, Any]:
        """Exécute le tool avec les arguments fournis.

        Args:
            **kwargs: Arguments du tool

        Returns:
            Résultat de l'exécution (dict avec success, result/error, etc.)
        """
        raise NotImplementedError

    def to_schema(self) -> dict[str, Any]:
        """Convertit le tool en schéma JSON pour le LLM.

        Returns:
            Schéma au format OpenAI/Ollama function calling
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class ToolRegistry:
    """Registre central des tools disponibles."""

    def __init__(self) -> None:
        """Initialise le registre vide."""
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """Enregistre un tool.

        Args:
            tool: Tool à enregistrer
        """
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        """Récupère un tool par son nom.

        Args:
            name: Nom du tool

        Returns:
            Tool ou None si introuvable
        """
        return self._tools.get(name)

    def list_tools(self) -> list[Tool]:
        """Liste tous les tools enregistrés.

        Returns:
            Liste des tools
        """
        return list(self._tools.values())

    def to_schemas(self) -> list[dict[str, Any]]:
        """Convertit tous les tools en schémas JSON.

        Returns:
            Liste des schémas pour le LLM
        """
        return [tool.to_schema() for tool in self._tools.values()]

    async def execute(
        self, name: str, arguments: dict[str, Any]
    ) -> dict[str, Any]:
        """Exécute un tool par son nom.

        Args:
            name: Nom du tool
            arguments: Arguments à passer au tool

        Returns:
            Résultat de l'exécution
        """
        tool = self.get(name)
        if not tool:
            return {
                "success": False,
                "error": f"Tool '{name}' introuvable",
            }

        try:
            return await tool.execute(**arguments)
        except Exception as e:
            return {
                "success": False,
                "error": f"Erreur lors de l'exécution de '{name}': {e}",
            }
