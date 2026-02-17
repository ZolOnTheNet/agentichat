"""Tools pour manipuler les fichiers."""

import fnmatch
from pathlib import Path
from typing import Any

from ..utils.sandbox import Sandbox
from .registry import Tool


class ListFilesTool(Tool):
    """Tool pour lister les fichiers d'un répertoire."""

    def __init__(self, sandbox: Sandbox) -> None:
        """Initialise le tool.

        Args:
            sandbox: Sandbox pour valider les chemins
        """
        super().__init__(
            name="list_files",
            description=(
                "Liste les fichiers d'un répertoire. "
                "IMPORTANT: Utiliser recursive=True pour inclure les sous-répertoires."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Chemin relatif du répertoire (défaut: .)",
                    },
                    "recursive": {
                        "type": "boolean",
                        "description": (
                            "Si True, parcourt tous les sous-répertoires récursivement. "
                            "Si False (défaut), liste uniquement le répertoire spécifié."
                        ),
                        "default": False,
                    },
                    "pattern": {
                        "type": "string",
                        "description": "Pattern glob (ex: *.py)",
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
            },
            requires_confirmation=False,
        )
        self.sandbox = sandbox

    async def execute(
        self, path: str = ".", recursive: bool = False, pattern: str | None = None,
        include_ignored: bool = False
    ) -> dict[str, Any]:
        """Liste les fichiers."""
        try:
            dir_path = self.sandbox.validate_path(path)

            if not dir_path.exists():
                return {"success": False, "error": f"Répertoire '{path}' introuvable"}

            if not dir_path.is_dir():
                return {"success": False, "error": f"'{path}' n'est pas un répertoire"}

            # Lister les fichiers
            files = []
            ignored_count = 0
            if recursive:
                glob_pattern = "**/*" if not pattern else f"**/{pattern}"
                for item in dir_path.glob(glob_pattern):
                    if item.is_file():
                        # Ignorer les chemins configurés sauf si include_ignored=True
                        if not include_ignored and self.sandbox.should_ignore(item):
                            ignored_count += 1
                            continue
                        files.append(str(item.relative_to(self.sandbox.root)))
            else:
                for item in dir_path.iterdir():
                    if item.is_file():
                        if not pattern or fnmatch.fnmatch(item.name, pattern):
                            files.append(str(item.relative_to(self.sandbox.root)))

            result = {"success": True, "files": sorted(files), "count": len(files)}
            if ignored_count > 0:
                result["ignored_count"] = ignored_count
                result["note"] = f"{ignored_count} fichiers ignorés (.venv, node_modules, etc.)"
            return result

        except Exception as e:
            return {"success": False, "error": str(e)}


class ReadFileTool(Tool):
    """Tool pour lire le contenu d'un fichier."""

    def __init__(self, sandbox: Sandbox) -> None:
        """Initialise le tool.

        Args:
            sandbox: Sandbox pour valider les chemins
        """
        super().__init__(
            name="read_file",
            description="Lit le contenu d'un fichier",
            parameters={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Chemin relatif du fichier",
                    },
                    "start_line": {
                        "type": "integer",
                        "description": "Ligne de début (1-indexed, optionnel)",
                    },
                    "end_line": {
                        "type": "integer",
                        "description": "Ligne de fin (1-indexed, optionnel)",
                    },
                },
                "required": ["path"],
            },
            requires_confirmation=False,
        )
        self.sandbox = sandbox

    async def execute(
        self, path: str, start_line: int | None = None, end_line: int | None = None
    ) -> dict[str, Any]:
        """Lit le fichier."""
        try:
            file_path = self.sandbox.validate_path(path)

            if not file_path.exists():
                return {"success": False, "error": f"Fichier '{path}' introuvable"}

            if not file_path.is_file():
                return {"success": False, "error": f"'{path}' n'est pas un fichier"}

            # Vérifier la taille
            self.sandbox.validate_size(file_path)

            # Lire le contenu
            content = file_path.read_text(encoding="utf-8", errors="replace")

            # Filtrer par lignes si demandé
            if start_line is not None or end_line is not None:
                lines = content.splitlines()
                start = (start_line - 1) if start_line else 0
                end = end_line if end_line else len(lines)
                content = "\n".join(lines[start:end])

            return {"success": True, "content": content, "path": path}

        except Exception as e:
            return {"success": False, "error": str(e)}


class WriteFileTool(Tool):
    """Tool pour écrire/modifier un fichier."""

    def __init__(self, sandbox: Sandbox) -> None:
        """Initialise le tool.

        Args:
            sandbox: Sandbox pour valider les chemins
        """
        super().__init__(
            name="write_file",
            description="Crée ou modifie un fichier",
            parameters={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Chemin relatif du fichier",
                    },
                    "content": {
                        "type": "string",
                        "description": "Contenu à écrire",
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["create", "overwrite", "append"],
                        "description": "Mode d'écriture (défaut: create)",
                        "default": "create",
                    },
                },
                "required": ["path", "content"],
            },
            requires_confirmation=True,  # Confirmation requise
        )
        self.sandbox = sandbox

    async def execute(
        self, path: str, content: str, mode: str = "create"
    ) -> dict[str, Any]:
        """Écrit dans le fichier."""
        try:
            file_path = self.sandbox.validate_path(path)

            # Vérifier le mode
            if mode == "create" and file_path.exists():
                return {
                    "success": False,
                    "error": f"Fichier '{path}' existe déjà (utilisez mode='overwrite')",
                }

            # Créer le répertoire parent si nécessaire
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Écrire le contenu
            if mode == "append":
                with open(file_path, "a", encoding="utf-8") as f:
                    f.write(content)
            else:
                file_path.write_text(content, encoding="utf-8")

            return {
                "success": True,
                "path": path,
                "bytes_written": len(content.encode("utf-8")),
            }

        except Exception as e:
            return {"success": False, "error": str(e)}


class DeleteFileTool(Tool):
    """Tool pour supprimer un fichier."""

    def __init__(self, sandbox: Sandbox) -> None:
        """Initialise le tool.

        Args:
            sandbox: Sandbox pour valider les chemins
        """
        super().__init__(
            name="delete_file",
            description="Supprime un fichier",
            parameters={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Chemin relatif du fichier à supprimer",
                    }
                },
                "required": ["path"],
            },
            requires_confirmation=True,  # Confirmation requise
        )
        self.sandbox = sandbox

    async def execute(self, path: str) -> dict[str, Any]:
        """Supprime le fichier."""
        try:
            file_path = self.sandbox.validate_path(path)

            if not file_path.exists():
                return {"success": False, "error": f"Fichier '{path}' introuvable"}

            if not file_path.is_file():
                return {"success": False, "error": f"'{path}' n'est pas un fichier"}

            file_path.unlink()

            return {"success": True, "path": path, "deleted": True}

        except Exception as e:
            return {"success": False, "error": str(e)}
