"""Interface abstraite pour les backends LLM."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import AsyncIterator, Literal


@dataclass
class Message:
    """Message dans une conversation."""

    role: Literal["system", "user", "assistant", "tool"]
    content: str
    tool_calls: list["ToolCall"] | None = None
    tool_call_id: str | None = None


@dataclass
class ToolCall:
    """Appel de tool par le LLM."""

    id: str
    name: str
    arguments: dict


@dataclass
class TokenUsage:
    """Statistiques d'utilisation de tokens."""

    prompt_tokens: int = 0  # Nombre de tokens du prompt
    completion_tokens: int = 0  # Nombre de tokens générés
    total_tokens: int = 0  # Total


@dataclass
class ChatResponse:
    """Réponse du LLM."""

    content: str
    tool_calls: list[ToolCall] | None = None
    finish_reason: str = "stop"  # stop, tool_calls, length, error
    usage: TokenUsage | None = None  # Statistiques de tokens


class Backend(ABC):
    """Interface abstraite pour un backend LLM."""

    def __init__(self, url: str, model: str, **kwargs: dict) -> None:
        """Initialise le backend.

        Args:
            url: URL du serveur backend
            model: Nom du modèle à utiliser
            **kwargs: Paramètres supplémentaires (timeout, api_key, etc.)
        """
        self.url = url
        self.model = model
        self.timeout = kwargs.get("timeout", 30)
        self.max_tokens = kwargs.get("max_tokens", 4096)
        self.temperature = kwargs.get("temperature", 0.7)
        self.api_key = kwargs.get("api_key")

    @abstractmethod
    async def chat(
        self,
        messages: list[Message],
        tools: list[dict] | None = None,
        stream: bool = False,
    ) -> AsyncIterator[str] | ChatResponse:
        """Envoie un message au LLM et reçoit la réponse.

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
        raise NotImplementedError

    @abstractmethod
    async def list_models(self) -> list[str]:
        """Liste les modèles disponibles sur ce backend.

        Returns:
            Liste des noms de modèles

        Raises:
            BackendError: En cas d'erreur de communication
        """
        raise NotImplementedError

    @abstractmethod
    async def health_check(self) -> bool:
        """Vérifie que le backend est accessible.

        Returns:
            True si le backend répond, False sinon
        """
        raise NotImplementedError


class BackendError(Exception):
    """Erreur de communication avec un backend LLM."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        """Initialise l'erreur.

        Args:
            message: Message d'erreur
            status_code: Code HTTP si applicable
        """
        super().__init__(message)
        self.status_code = status_code
