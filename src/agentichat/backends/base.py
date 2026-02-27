"""Interface abstraite pour les backends LLM."""

import asyncio
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import AsyncIterator, Callable, Literal

logger = logging.getLogger(__name__)


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
        self.max_parallel_tools = kwargs.get("max_parallel_tools")  # None = illimité
        self.context_max_tokens = kwargs.get("context_max_tokens")  # None = pas de limite
        # Info de retry en cours (lue par le spinner dans app.py)
        self.retry_info: dict | None = None  # None = pas de retry en cours
        # Compteurs cumulatifs pour la requête en cours (reset avant chaque agent.run)
        self.cumulative_usage: dict = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "api_calls": 0,
        }

    def reset_cumulative_usage(self) -> None:
        """Remet à zéro les compteurs cumulatifs (à appeler avant chaque agent.run)."""
        self.cumulative_usage = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "api_calls": 0,
        }

    def _accumulate_usage(self, prompt_tokens: int, completion_tokens: int) -> None:
        """Accumule les tokens dans le compteur cumulatif.

        Args:
            prompt_tokens: Tokens du prompt de cet appel
            completion_tokens: Tokens de la réponse de cet appel
        """
        self.cumulative_usage["prompt_tokens"] += prompt_tokens
        self.cumulative_usage["completion_tokens"] += completion_tokens
        self.cumulative_usage["total_tokens"] += prompt_tokens + completion_tokens
        self.cumulative_usage["api_calls"] += 1

    def _limit_tool_calls(self, tool_calls: list[ToolCall] | None) -> list[ToolCall] | None:
        """Limite le nombre de tool calls selon max_parallel_tools.

        Args:
            tool_calls: Liste des tool calls à limiter

        Returns:
            Liste limitée ou None
        """
        if not tool_calls or not self.max_parallel_tools:
            return tool_calls

        if len(tool_calls) > self.max_parallel_tools:
            return tool_calls[:self.max_parallel_tools]

        return tool_calls

    async def _retry_on_error(
        self,
        coro_factory: Callable,
        max_retries: int = 3,
        base_delay: float = 2.0,
        retryable_status: tuple[int, ...] = (429, 500, 502, 503, 504),
    ):
        """Exécute une coroutine avec retry et backoff exponentiel.

        Met à jour `self.retry_info` pendant les tentatives pour que le spinner
        puisse afficher l'état en temps réel.

        Args:
            coro_factory: Callable sans argument retournant une coroutine
            max_retries: Nombre maximum de nouvelles tentatives (défaut: 3)
            base_delay: Délai initial en secondes (doublé à chaque tentative)
            retryable_status: Codes HTTP qui déclenchent un retry

        Returns:
            Résultat de la coroutine si succès

        Raises:
            BackendError: Si toutes les tentatives échouent
        """
        last_error = None
        self.retry_info = None  # Pas de retry en cours

        for attempt in range(max_retries + 1):
            try:
                result = await coro_factory()
                self.retry_info = None  # Succès, effacer l'info de retry
                return result
            except BackendError as e:
                last_error = e
                # Ne pas retenter si le code HTTP n'est pas dans la liste
                if e.status_code not in retryable_status:
                    self.retry_info = None
                    raise
                # Dernière tentative : propager l'erreur
                if attempt == max_retries:
                    self.retry_info = None
                    raise

                delay = base_delay * (2 ** attempt)  # 2s → 4s → 8s
                self.retry_info = {
                    "attempt": attempt + 1,
                    "max_retries": max_retries,
                    "delay": delay,
                    "status_code": e.status_code,
                }
                logger.warning(
                    f"Erreur HTTP {e.status_code}, retry {attempt + 1}/{max_retries} "
                    f"dans {delay:.0f}s..."
                )
                await asyncio.sleep(delay)

        # Sécurité (normalement jamais atteint)
        self.retry_info = None
        raise last_error

    def estimate_tokens(self, text: str) -> int:
        """Estimation rapide du nombre de tokens (heuristique).

        Règle : ~3 caractères par token (marge de sécurité vs la moyenne de 4).
        Suffisant pour du budgeting de contexte.
        """
        return len(text) // 3

    def estimate_messages_tokens(self, messages: list["Message"]) -> int:
        """Estime le nombre total de tokens dans une liste de messages.

        Args:
            messages: Liste de messages à estimer

        Returns:
            Estimation du nombre de tokens
        """
        total = 0
        for msg in messages:
            total += 4  # Overhead par message (role + délimiteurs)
            total += self.estimate_tokens(msg.content or "")
            if msg.tool_calls:
                for tc in msg.tool_calls:
                    total += self.estimate_tokens(json.dumps(tc.arguments))
                    total += self.estimate_tokens(tc.name)
        return total

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

    # Types d'erreurs catégorisés — utilisés par app.py pour le handling structuré
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
        """Initialise l'erreur.

        Args:
            message: Message d'erreur
            status_code: Code HTTP si applicable
            error_type: Catégorie de l'erreur (constantes de classe)
        """
        super().__init__(message)
        self.status_code = status_code
        self.error_type = error_type

    @property
    def is_retryable(self) -> bool:
        """Indique si l'erreur est transitoire et peut être retentée."""
        return self.error_type in (self.RATE_LIMIT, self.SERVER_ERROR, self.TIMEOUT)
