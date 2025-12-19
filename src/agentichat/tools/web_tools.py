"""Tools pour interagir avec le web."""

import re
from typing import Any

import aiohttp

from .registry import Tool


class WebFetchTool(Tool):
    """Tool pour récupérer du contenu depuis une URL."""

    def __init__(self) -> None:
        """Initialise le tool."""
        super().__init__(
            name="web_fetch",
            description=(
                "Récupère le contenu d'une page web depuis une URL. "
                "Retourne le contenu HTML ou texte de la page."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL complète à récupérer (doit commencer par http:// ou https://)",
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Timeout en secondes (défaut: 10)",
                        "default": 10,
                    },
                },
                "required": ["url"],
            },
            requires_confirmation=False,
        )

    async def execute(self, url: str, timeout: int = 10) -> dict[str, Any]:
        """Récupère le contenu d'une URL."""
        try:
            # Valider l'URL
            if not url.startswith(("http://", "https://")):
                return {
                    "success": False,
                    "error": "L'URL doit commencer par http:// ou https://",
                }

            # Faire la requête
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url, timeout=aiohttp.ClientTimeout(total=timeout)
                ) as response:
                    if response.status != 200:
                        return {
                            "success": False,
                            "error": f"Erreur HTTP {response.status}",
                            "status_code": response.status,
                        }

                    # Récupérer le contenu
                    content = await response.text()

                    # Nettoyer basiquement le HTML (enlever les balises)
                    text_content = re.sub(r"<[^>]+>", " ", content)
                    text_content = re.sub(r"\s+", " ", text_content).strip()

                    # Limiter la taille (max 10000 caractères pour éviter les réponses trop longues)
                    if len(text_content) > 10000:
                        text_content = text_content[:10000] + "... [contenu tronqué]"

                    return {
                        "success": True,
                        "url": url,
                        "status_code": response.status,
                        "content": text_content,
                        "content_length": len(content),
                        "content_type": response.headers.get("Content-Type", "unknown"),
                    }

        except aiohttp.ClientError as e:
            return {"success": False, "error": f"Erreur de connexion: {e}"}
        except Exception as e:
            return {"success": False, "error": str(e)}


class WebSearchTool(Tool):
    """Tool pour rechercher sur le web."""

    def __init__(self) -> None:
        """Initialise le tool."""
        super().__init__(
            name="web_search",
            description=(
                "Effectue une recherche sur le web et retourne les résultats. "
                "Utilise DuckDuckGo comme moteur de recherche."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Requête de recherche",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Nombre maximum de résultats à retourner (défaut: 5)",
                        "default": 5,
                    },
                },
                "required": ["query"],
            },
            requires_confirmation=False,
        )

    async def execute(self, query: str, max_results: int = 5) -> dict[str, Any]:
        """Effectue une recherche web."""
        try:
            # Utiliser l'API DuckDuckGo
            search_url = "https://api.duckduckgo.com/"
            params = {
                "q": query,
                "format": "json",
                "no_html": 1,
                "skip_disambig": 1,
            }

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    search_url, params=params, timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status != 200:
                        return {
                            "success": False,
                            "error": f"Erreur HTTP {response.status}",
                        }

                    data = await response.json()

                    results = []

                    # Résultat principal
                    if data.get("AbstractText"):
                        results.append(
                            {
                                "title": data.get("Heading", "Résultat principal"),
                                "snippet": data.get("AbstractText", ""),
                                "url": data.get("AbstractURL", ""),
                            }
                        )

                    # Résultats liés
                    for topic in data.get("RelatedTopics", [])[:max_results]:
                        if isinstance(topic, dict) and "Text" in topic:
                            results.append(
                                {
                                    "title": topic.get("Text", "")[:100],
                                    "snippet": topic.get("Text", ""),
                                    "url": topic.get("FirstURL", ""),
                                }
                            )

                    # Limiter au nombre demandé
                    results = results[:max_results]

                    if not results:
                        return {
                            "success": True,
                            "query": query,
                            "results": [],
                            "count": 0,
                            "message": "Aucun résultat trouvé",
                        }

                    return {
                        "success": True,
                        "query": query,
                        "results": results,
                        "count": len(results),
                    }

        except aiohttp.ClientError as e:
            return {"success": False, "error": f"Erreur de connexion: {e}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
