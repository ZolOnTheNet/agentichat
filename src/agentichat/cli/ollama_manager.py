"""Gestionnaire des commandes Ollama directes."""

from pathlib import Path
from typing import Any, AsyncIterator

import aiohttp

from ..backends.base import BackendError
from ..utils.logger import get_logger

logger = get_logger("agentichat.cli.ollama")


class OllamaManager:
    """Gestionnaire pour les commandes Ollama directes.

    Permet d'interagir avec l'API Ollama pour:
    - Lister les modèles
    - Afficher les infos d'un modèle
    - Changer de modèle à la volée
    - Lister les modèles en cours
    - Créer/copier/supprimer des modèles
    """

    def __init__(self, url: str, timeout: float = 30.0) -> None:
        """Initialise le gestionnaire.

        Args:
            url: URL du serveur Ollama
            timeout: Timeout pour les requêtes (par défaut 30s)
        """
        self.url = url
        self.timeout = timeout

    async def list_models(self) -> list[dict[str, Any]]:
        """Liste tous les modèles disponibles.

        Returns:
            Liste des modèles avec leurs métadonnées

        Raises:
            BackendError: En cas d'erreur
        """
        endpoint = f"{self.url}/api/tags"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    endpoint, timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise BackendError(
                            f"Ollama error: {error_text}", status_code=response.status
                        )

                    data = await response.json()
                    return data.get("models", [])

        except aiohttp.ClientError as e:
            raise BackendError(f"Connection error: {e}") from e

    async def show_model(self, model_name: str) -> dict[str, Any]:
        """Affiche les informations détaillées d'un modèle.

        Args:
            model_name: Nom du modèle

        Returns:
            Informations détaillées du modèle

        Raises:
            BackendError: En cas d'erreur
        """
        endpoint = f"{self.url}/api/show"
        payload = {"name": model_name}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    endpoint,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise BackendError(
                            f"Ollama error: {error_text}", status_code=response.status
                        )

                    return await response.json()

        except aiohttp.ClientError as e:
            raise BackendError(f"Connection error: {e}") from e

    async def list_running(self) -> list[dict[str, Any]]:
        """Liste les modèles actuellement en cours d'exécution.

        Returns:
            Liste des modèles en cours

        Raises:
            BackendError: En cas d'erreur
        """
        endpoint = f"{self.url}/api/ps"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    endpoint, timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise BackendError(
                            f"Ollama error: {error_text}", status_code=response.status
                        )

                    data = await response.json()
                    return data.get("models", [])

        except aiohttp.ClientError as e:
            raise BackendError(f"Connection error: {e}") from e

    async def create_model(
        self, model_name: str, modelfile: str | None = None, path: Path | None = None
    ) -> AsyncIterator[str]:
        """Crée un modèle à partir d'un Modelfile.

        Args:
            model_name: Nom du nouveau modèle
            modelfile: Contenu du Modelfile (si fourni directement)
            path: Chemin vers le Modelfile (si fourni via fichier)

        Yields:
            Messages de progression

        Raises:
            BackendError: En cas d'erreur
        """
        endpoint = f"{self.url}/api/create"

        # Lire le Modelfile si un chemin est fourni
        if path:
            if not path.exists():
                raise BackendError(f"Modelfile not found: {path}")
            modelfile = path.read_text()

        if not modelfile:
            raise BackendError("No Modelfile provided")

        payload = {"name": model_name, "modelfile": modelfile, "stream": True}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    endpoint,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=None),  # Pas de timeout pour create
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise BackendError(
                            f"Ollama error: {error_text}", status_code=response.status
                        )

                    # Stream les messages de progression
                    async for line in response.content:
                        if not line:
                            continue

                        try:
                            import json

                            data = json.loads(line)
                            if "status" in data:
                                yield data["status"]
                        except json.JSONDecodeError:
                            continue

        except aiohttp.ClientError as e:
            raise BackendError(f"Connection error: {e}") from e

    async def copy_model(self, source: str, destination: str) -> None:
        """Copie un modèle existant.

        Args:
            source: Nom du modèle source
            destination: Nom du nouveau modèle

        Raises:
            BackendError: En cas d'erreur
        """
        endpoint = f"{self.url}/api/copy"
        payload = {"source": source, "destination": destination}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    endpoint,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise BackendError(
                            f"Ollama error: {error_text}", status_code=response.status
                        )

        except aiohttp.ClientError as e:
            raise BackendError(f"Connection error: {e}") from e

    async def delete_model(self, model_name: str) -> None:
        """Supprime un modèle.

        Args:
            model_name: Nom du modèle à supprimer

        Raises:
            BackendError: En cas d'erreur
        """
        endpoint = f"{self.url}/api/delete"
        payload = {"name": model_name}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.delete(
                    endpoint,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.timeout),
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise BackendError(
                            f"Ollama error: {error_text}", status_code=response.status
                        )

        except aiohttp.ClientError as e:
            raise BackendError(f"Connection error: {e}") from e
