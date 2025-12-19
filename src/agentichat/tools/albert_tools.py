"""Tools spécifiques à l'API Albert (Etalab)."""

import aiohttp
from typing import Any

from ..utils.logger import get_logger
from .registry import Tool

logger = get_logger("agentichat.tools.albert")


class AlbertSearchTool(Tool):
    """Tool pour rechercher dans des collections de documents via Albert API."""

    def __init__(self, api_url: str, api_key: str) -> None:
        """Initialise le tool de recherche Albert.

        Args:
            api_url: URL de l'API Albert
            api_key: Clé API pour l'authentification
        """
        super().__init__(
            name="albert_search",
            description=(
                "Recherche dans des documents indexés sur Albert API. "
                "Retourne les passages les plus pertinents pour répondre à une question."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Question ou requête de recherche",
                    },
                    "collections": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Liste des collections dans lesquelles chercher (optionnel)",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Nombre maximum de résultats (défaut: 5)",
                        "default": 5,
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["semantic", "lexical", "hybrid"],
                        "description": "Mode de recherche (défaut: hybrid)",
                        "default": "hybrid",
                    },
                },
                "required": ["query"],
            },
            requires_confirmation=False,
        )
        self.api_url = api_url
        self.api_key = api_key

    async def execute(
        self,
        query: str,
        collections: list[str] | None = None,
        limit: int = 5,
        mode: str = "hybrid",
    ) -> dict[str, Any]:
        """Recherche dans les documents Albert.

        Args:
            query: Question ou requête de recherche
            collections: Collections dans lesquelles chercher
            limit: Nombre de résultats maximum
            mode: Mode de recherche (semantic, lexical, hybrid)

        Returns:
            Résultats de recherche avec passages pertinents
        """
        endpoint = f"{self.api_url}/v1/search"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "query": query,
            "limit": limit,
            "mode": mode,
        }

        if collections:
            payload["collections"] = collections

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    endpoint,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        return {
                            "success": False,
                            "error": f"Erreur API Albert: {error_text}",
                        }

                    data = await response.json()
                    chunks = data.get("data", [])

                    # Formater les résultats
                    results = []
                    for chunk in chunks:
                        results.append(
                            {
                                "text": chunk.get("chunk", ""),
                                "score": chunk.get("score", 0.0),
                                "document": chunk.get("document", ""),
                                "collection": chunk.get("collection", ""),
                            }
                        )

                    return {
                        "success": True,
                        "query": query,
                        "mode": mode,
                        "results_count": len(results),
                        "results": results,
                    }

        except Exception as e:
            return {"success": False, "error": str(e)}


class AlbertOCRTool(Tool):
    """Tool pour extraire du texte depuis des images/PDF via Albert API."""

    def __init__(self, api_url: str, api_key: str) -> None:
        """Initialise le tool OCR Albert.

        Args:
            api_url: URL de l'API Albert
            api_key: Clé API pour l'authentification
        """
        super().__init__(
            name="albert_ocr",
            description=(
                "Extrait le texte depuis une image ou un PDF en utilisant "
                "des modèles de vision (OCR avancé)."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Chemin vers le fichier image ou PDF",
                    },
                    "prompt": {
                        "type": "string",
                        "description": (
                            "Instruction pour guider l'extraction "
                            "(ex: 'Extraire les tableaux', optionnel)"
                        ),
                    },
                },
                "required": ["file_path"],
            },
            requires_confirmation=False,
        )
        self.api_url = api_url
        self.api_key = api_key

    async def execute(
        self, file_path: str, prompt: str | None = None
    ) -> dict[str, Any]:
        """Extrait le texte d'un fichier image/PDF.

        Args:
            file_path: Chemin vers le fichier
            prompt: Instruction optionnelle pour l'extraction

        Returns:
            Texte extrait du fichier
        """
        endpoint = f"{self.api_url}/v1/ocr"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
        }

        try:
            # Lire le fichier
            with open(file_path, "rb") as f:
                files = {"file": f}
                data = {}
                if prompt:
                    data["prompt"] = prompt

                async with aiohttp.ClientSession() as session:
                    form_data = aiohttp.FormData()
                    form_data.add_field("file", f, filename=file_path)
                    if prompt:
                        form_data.add_field("prompt", prompt)

                    async with session.post(
                        endpoint,
                        data=form_data,
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=60),
                    ) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            return {
                                "success": False,
                                "error": f"Erreur API Albert: {error_text}",
                            }

                        data = await response.json()
                        return {
                            "success": True,
                            "file_path": file_path,
                            "text": data.get("text", ""),
                        }

        except FileNotFoundError:
            return {
                "success": False,
                "error": f"Fichier non trouvé: {file_path}",
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


class AlbertTranscriptionTool(Tool):
    """Tool pour transcrire de l'audio en texte via Albert API."""

    def __init__(self, api_url: str, api_key: str) -> None:
        """Initialise le tool de transcription Albert.

        Args:
            api_url: URL de l'API Albert
            api_key: Clé API pour l'authentification
        """
        super().__init__(
            name="albert_transcription",
            description=(
                "Transcrit un fichier audio (MP3, WAV, etc.) en texte "
                "en utilisant des modèles de reconnaissance vocale."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Chemin vers le fichier audio",
                    },
                    "language": {
                        "type": "string",
                        "description": (
                            "Code langue (ex: 'fr', 'en', optionnel - "
                            "détection automatique par défaut)"
                        ),
                    },
                    "prompt": {
                        "type": "string",
                        "description": (
                            "Contexte pour améliorer la transcription (optionnel)"
                        ),
                    },
                },
                "required": ["file_path"],
            },
            requires_confirmation=False,
        )
        self.api_url = api_url
        self.api_key = api_key

    async def execute(
        self,
        file_path: str,
        language: str | None = None,
        prompt: str | None = None,
    ) -> dict[str, Any]:
        """Transcrit un fichier audio en texte.

        Args:
            file_path: Chemin vers le fichier audio
            language: Code langue (optionnel)
            prompt: Contexte pour la transcription (optionnel)

        Returns:
            Texte transcrit de l'audio
        """
        endpoint = f"{self.api_url}/v1/audio/transcriptions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
        }

        try:
            # Lire le fichier audio
            with open(file_path, "rb") as f:
                async with aiohttp.ClientSession() as session:
                    form_data = aiohttp.FormData()
                    form_data.add_field("file", f, filename=file_path)
                    if language:
                        form_data.add_field("language", language)
                    if prompt:
                        form_data.add_field("prompt", prompt)

                    async with session.post(
                        endpoint,
                        data=form_data,
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=120),
                    ) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            return {
                                "success": False,
                                "error": f"Erreur API Albert: {error_text}",
                            }

                        data = await response.json()
                        return {
                            "success": True,
                            "file_path": file_path,
                            "text": data.get("text", ""),
                            "language": data.get("language", ""),
                        }

        except FileNotFoundError:
            return {
                "success": False,
                "error": f"Fichier audio non trouvé: {file_path}",
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


class AlbertEmbeddingsTool(Tool):
    """Tool pour créer des embeddings (vecteurs) de texte via Albert API."""

    def __init__(self, api_url: str, api_key: str) -> None:
        """Initialise le tool d'embeddings Albert.

        Args:
            api_url: URL de l'API Albert
            api_key: Clé API pour l'authentification
        """
        super().__init__(
            name="albert_embeddings",
            description=(
                "Crée des vecteurs (embeddings) pour du texte, "
                "utile pour la recherche sémantique et la comparaison de textes."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Texte à vectoriser",
                    },
                    "model": {
                        "type": "string",
                        "description": "Modèle d'embedding à utiliser (optionnel)",
                    },
                },
                "required": ["text"],
            },
            requires_confirmation=False,
        )
        self.api_url = api_url
        self.api_key = api_key

    async def execute(
        self, text: str, model: str | None = None
    ) -> dict[str, Any]:
        """Crée un embedding pour du texte.

        Args:
            text: Texte à vectoriser
            model: Modèle à utiliser (optionnel)

        Returns:
            Vecteur d'embedding
        """
        endpoint = f"{self.api_url}/v1/embeddings"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {"input": text}
        if model:
            payload["model"] = model

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    endpoint,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        return {
                            "success": False,
                            "error": f"Erreur API Albert: {error_text}",
                        }

                    data = await response.json()
                    embeddings_data = data.get("data", [])

                    if not embeddings_data:
                        return {
                            "success": False,
                            "error": "Aucun embedding retourné",
                        }

                    embedding = embeddings_data[0].get("embedding", [])

                    return {
                        "success": True,
                        "text": text,
                        "embedding_dimension": len(embedding),
                        "embedding": embedding,
                    }

        except Exception as e:
            return {"success": False, "error": str(e)}
