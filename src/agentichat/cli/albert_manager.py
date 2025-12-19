"""Gestionnaire des commandes Albert API directes."""

from typing import Any

import aiohttp

from ..backends.base import BackendError
from ..utils.logger import get_logger

logger = get_logger("agentichat.cli.albert")


class AlbertManager:
    """Gestionnaire pour les commandes Albert API directes.

    Permet d'interagir avec l'API Albert pour:
    - Lister les modèles disponibles
    - Afficher les infos d'un modèle
    - Changer de modèle à la volée
    - Vérifier l'usage et les quotas
    """

    def __init__(self, url: str, api_key: str, timeout: float = 30.0) -> None:
        """Initialise le gestionnaire.

        Args:
            url: URL de l'API Albert
            api_key: Clé API pour l'authentification
            timeout: Timeout pour les requêtes (par défaut 30s)
        """
        self.url = url
        self.api_key = api_key
        self.timeout = timeout

    def _get_headers(self) -> dict[str, str]:
        """Retourne les headers HTTP avec authentification.

        Returns:
            Headers avec Bearer token
        """
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def list_models(self) -> list[dict[str, Any]]:
        """Liste tous les modèles disponibles sur Albert.

        Returns:
            Liste des modèles avec leurs métadonnées (id, owned_by, etc.)

        Raises:
            BackendError: En cas d'erreur
        """
        endpoint = f"{self.url}/v1/models"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    endpoint,
                    headers=self._get_headers(),
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise BackendError(
                            f"Albert API error: {error_text}", status_code=response.status
                        )

                    data = await response.json()
                    return data.get("data", [])

        except aiohttp.ClientError as e:
            raise BackendError(f"Connection error: {e}") from e

    async def get_model_info(self, model_id: str) -> dict[str, Any]:
        """Récupère les informations détaillées d'un modèle.

        Args:
            model_id: ID du modèle

        Returns:
            Informations détaillées du modèle

        Raises:
            BackendError: En cas d'erreur
        """
        endpoint = f"{self.url}/v1/models/{model_id}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    endpoint,
                    headers=self._get_headers(),
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise BackendError(
                            f"Albert API error: {error_text}", status_code=response.status
                        )

                    return await response.json()

        except aiohttp.ClientError as e:
            raise BackendError(f"Connection error: {e}") from e

    async def get_usage(self) -> dict[str, Any]:
        """Récupère les statistiques d'utilisation.

        Returns:
            Statistiques d'utilisation (tokens, coûts, etc.)

        Raises:
            BackendError: En cas d'erreur
        """
        endpoint = f"{self.url}/v1/me/usage"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    endpoint,
                    headers=self._get_headers(),
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise BackendError(
                            f"Albert API error: {error_text}", status_code=response.status
                        )

                    return await response.json()

        except aiohttp.ClientError as e:
            raise BackendError(f"Connection error: {e}") from e

    async def get_user_info(self) -> dict[str, Any]:
        """Récupère les informations de l'utilisateur.

        Returns:
            Informations utilisateur (quotas, limites, etc.)

        Raises:
            BackendError: En cas d'erreur
        """
        endpoint = f"{self.url}/v1/me/info"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    endpoint,
                    headers=self._get_headers(),
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise BackendError(
                            f"Albert API error: {error_text}", status_code=response.status
                        )

                    return await response.json()

        except aiohttp.ClientError as e:
            raise BackendError(f"Connection error: {e}") from e
