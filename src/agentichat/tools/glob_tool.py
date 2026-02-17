"""Tool pour rechercher des fichiers par pattern (glob)."""

from pathlib import Path
from typing import Any

from ..utils.sandbox import Sandbox
from .registry import Tool


class GlobTool(Tool):
    """Tool pour rechercher des fichiers avec des patterns glob."""

    def __init__(self, sandbox: Sandbox) -> None:
        """Initialise le tool.

        Args:
            sandbox: Sandbox pour valider les chemins
        """
        super().__init__(
            name="glob_search",
            description=(
                "Recherche des fichiers en utilisant des patterns glob. "
                "Exemples: '*.py' (tous les .py), '**/*.js' (tous les .js récursivement), "
                "'src/**/*.tsx' (tous les .tsx dans src/)"
            ),
            parameters={
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": (
                            "Pattern glob à rechercher. Exemples: '*.py', '**/*.js', "
                            "'src/**/*.tsx', 'test_*.py'"
                        ),
                    },
                    "path": {
                        "type": "string",
                        "description": "Répertoire de départ pour la recherche (défaut: .)",
                        "default": ".",
                    },
                    "exclude": {
                        "type": "string",
                        "description": (
                            "Pattern additionnel à exclure (optionnel). Exemples: '**/tests/**', "
                            "'**/docs/**'. Note: .venv, node_modules, .git sont déjà exclus par défaut."
                        ),
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
                "required": ["pattern"],
            },
            requires_confirmation=False,
        )
        self.sandbox = sandbox

    async def execute(
        self, pattern: str, path: str = ".", exclude: str | None = None,
        include_ignored: bool = False
    ) -> dict[str, Any]:
        """Recherche des fichiers par pattern glob."""
        try:
            search_dir = self.sandbox.validate_path(path)

            if not search_dir.exists():
                return {"success": False, "error": f"Répertoire '{path}' introuvable"}

            if not search_dir.is_dir():
                return {"success": False, "error": f"'{path}' n'est pas un répertoire"}

            # Rechercher les fichiers
            matches = []
            ignored_count = 0
            for item in search_dir.glob(pattern):
                # Vérifier l'exclusion utilisateur
                if exclude and item.match(exclude):
                    continue

                # Ajouter seulement les fichiers (pas les répertoires)
                if item.is_file():
                    try:
                        # Ignorer les chemins configurés sauf si include_ignored=True
                        if not include_ignored and self.sandbox.should_ignore(item):
                            ignored_count += 1
                            continue

                        rel_path = item.relative_to(self.sandbox.root)
                        matches.append(str(rel_path))
                    except ValueError:
                        # Fichier hors du sandbox, ignorer
                        continue

            # Trier les résultats
            matches.sort()

            result = {
                "success": True,
                "matches": matches,
                "count": len(matches),
                "pattern": pattern,
                "search_dir": path,
            }
            if ignored_count > 0:
                result["ignored_count"] = ignored_count
                result["note"] = f"{ignored_count} fichiers ignorés (.venv, node_modules, etc.)"
            return result

        except Exception as e:
            return {"success": False, "error": str(e)}
