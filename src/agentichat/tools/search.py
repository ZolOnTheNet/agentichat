"""Tool de recherche textuelle dans les fichiers."""

import re
from pathlib import Path
from typing import Any

from ..utils.sandbox import Sandbox
from .registry import Tool


class SearchTextTool(Tool):
    """Tool pour rechercher du texte dans les fichiers (grep-like)."""

    def __init__(self, sandbox: Sandbox) -> None:
        """Initialise le tool.

        Args:
            sandbox: Sandbox pour valider les chemins
        """
        super().__init__(
            name="search_text",
            description=(
                "Recherche textuelle dans les fichiers (grep-like). "
                "Parcourt AUTOMATIQUEMENT tous les sous-répertoires de manière récursive."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Texte ou regex à chercher",
                    },
                    "path": {
                        "type": "string",
                        "description": (
                            "Répertoire de départ pour la recherche récursive (défaut: .). "
                            "La recherche inclura automatiquement tous les sous-répertoires."
                        ),
                        "default": ".",
                    },
                    "regex": {
                        "type": "boolean",
                        "description": "Utiliser une regex",
                        "default": False,
                    },
                    "case_sensitive": {
                        "type": "boolean",
                        "description": "Sensible à la casse",
                        "default": False,
                    },
                    "include_ignored": {
                        "type": "boolean",
                        "description": (
                            "Si True, inclut les répertoires normalement ignorés (.venv, node_modules, .git, etc.). "
                            "Par défaut False."
                        ),
                        "default": False,
                    },
                },
                "required": ["query"],
            },
            requires_confirmation=False,
        )
        self.sandbox = sandbox

    async def execute(
        self,
        query: str,
        path: str = ".",
        regex: bool = False,
        case_sensitive: bool = False,
        include_ignored: bool = False,
    ) -> dict[str, Any]:
        """Recherche le texte dans les fichiers."""
        try:
            search_path = self.sandbox.validate_path(path)

            if not search_path.exists():
                return {"success": False, "error": f"Chemin '{path}' introuvable"}

            # Compiler la regex si nécessaire
            if regex:
                flags = 0 if case_sensitive else re.IGNORECASE
                try:
                    pattern = re.compile(query, flags)
                except re.error as e:
                    return {"success": False, "error": f"Regex invalide: {e}"}
            else:
                # Recherche simple (escape les caractères spéciaux)
                escaped_query = re.escape(query)
                flags = 0 if case_sensitive else re.IGNORECASE
                pattern = re.compile(escaped_query, flags)

            # Rechercher dans les fichiers
            matches = []
            ignored_count = 0

            # Si c'est un fichier unique
            if search_path.is_file():
                file_matches = self._search_in_file(search_path, pattern)
                if file_matches:
                    matches.extend(file_matches)
            # Si c'est un répertoire
            elif search_path.is_dir():
                for file_path in search_path.rglob("*"):
                    if file_path.is_file():
                        try:
                            # Ignorer les chemins configurés sauf si include_ignored=True
                            if not include_ignored and self.sandbox.should_ignore(file_path):
                                ignored_count += 1
                                continue

                            # Vérifier la taille
                            self.sandbox.validate_size(file_path)

                            file_matches = self._search_in_file(file_path, pattern)
                            if file_matches:
                                matches.extend(file_matches)
                        except Exception:
                            # Ignorer les fichiers qui posent problème
                            continue

            result = {
                "success": True,
                "query": query,
                "matches": matches,
                "count": len(matches),
            }
            if ignored_count > 0:
                result["ignored_count"] = ignored_count
                result["note"] = f"{ignored_count} fichiers ignorés (.venv, node_modules, etc.)"
            return result

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _search_in_file(
        self, file_path: Path, pattern: re.Pattern
    ) -> list[dict[str, Any]]:
        """Recherche dans un fichier spécifique.

        Args:
            file_path: Chemin du fichier
            pattern: Pattern compilé à chercher

        Returns:
            Liste des correspondances trouvées
        """
        matches = []

        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
            lines = content.splitlines()

            for line_num, line in enumerate(lines, start=1):
                if pattern.search(line):
                    matches.append({
                        "file": str(file_path.relative_to(self.sandbox.root)),
                        "line": line_num,
                        "content": line.strip(),
                    })

        except Exception:
            # Ignorer les fichiers binaires ou non lisibles
            pass

        return matches
