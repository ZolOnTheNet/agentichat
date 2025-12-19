"""Tools pour manipuler les répertoires."""

import shutil
from pathlib import Path
from typing import Any

from ..utils.sandbox import Sandbox
from .registry import Tool


class CreateDirectoryTool(Tool):
    """Tool pour créer des répertoires."""

    def __init__(self, sandbox: Sandbox) -> None:
        """Initialise le tool.

        Args:
            sandbox: Sandbox pour valider les chemins
        """
        super().__init__(
            name="create_directory",
            description="Crée un nouveau répertoire",
            parameters={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Chemin relatif du répertoire à créer",
                    },
                    "parents": {
                        "type": "boolean",
                        "description": (
                            "Créer les répertoires parents si nécessaire (défaut: True)"
                        ),
                        "default": True,
                    },
                },
                "required": ["path"],
            },
            requires_confirmation=False,
        )
        self.sandbox = sandbox

    async def execute(self, path: str, parents: bool = True) -> dict[str, Any]:
        """Crée un répertoire."""
        try:
            dir_path = self.sandbox.validate_path(path)

            if dir_path.exists():
                if dir_path.is_dir():
                    return {
                        "success": False,
                        "error": f"Le répertoire '{path}' existe déjà",
                    }
                else:
                    return {
                        "success": False,
                        "error": f"'{path}' existe déjà mais n'est pas un répertoire",
                    }

            # Créer le répertoire
            dir_path.mkdir(parents=parents, exist_ok=False)

            return {
                "success": True,
                "path": path,
                "absolute_path": str(dir_path),
                "message": f"Répertoire '{path}' créé avec succès",
            }

        except Exception as e:
            return {"success": False, "error": str(e)}


class DeleteDirectoryTool(Tool):
    """Tool pour supprimer des répertoires."""

    def __init__(self, sandbox: Sandbox) -> None:
        """Initialise le tool.

        Args:
            sandbox: Sandbox pour valider les chemins
        """
        super().__init__(
            name="delete_directory",
            description="Supprime un répertoire (vide ou avec son contenu)",
            parameters={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Chemin relatif du répertoire à supprimer",
                    },
                    "recursive": {
                        "type": "boolean",
                        "description": (
                            "Supprimer récursivement le contenu (défaut: False)"
                        ),
                        "default": False,
                    },
                },
                "required": ["path"],
            },
            requires_confirmation=True,  # Confirmation requise
        )
        self.sandbox = sandbox

    async def execute(self, path: str, recursive: bool = False) -> dict[str, Any]:
        """Supprime un répertoire."""
        try:
            dir_path = self.sandbox.validate_path(path)

            if not dir_path.exists():
                return {
                    "success": False,
                    "error": f"Le répertoire '{path}' n'existe pas",
                }

            if not dir_path.is_dir():
                return {
                    "success": False,
                    "error": f"'{path}' n'est pas un répertoire",
                }

            # Vérifier si le répertoire est vide
            if not recursive and any(dir_path.iterdir()):
                return {
                    "success": False,
                    "error": f"Le répertoire '{path}' n'est pas vide. "
                    f"Utilisez recursive=true pour supprimer le contenu.",
                }

            # Supprimer le répertoire
            if recursive:
                shutil.rmtree(dir_path)
            else:
                dir_path.rmdir()

            return {
                "success": True,
                "path": path,
                "message": f"Répertoire '{path}' supprimé avec succès",
            }

        except Exception as e:
            return {"success": False, "error": str(e)}


class MoveFileTool(Tool):
    """Tool pour déplacer ou renommer des fichiers/répertoires."""

    def __init__(self, sandbox: Sandbox) -> None:
        """Initialise le tool.

        Args:
            sandbox: Sandbox pour valider les chemins
        """
        super().__init__(
            name="move_file",
            description=(
                "Déplace ou renomme un fichier ou répertoire. "
                "Peut aussi être utilisé pour renommer."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "source": {
                        "type": "string",
                        "description": "Chemin relatif source (fichier ou répertoire)",
                    },
                    "destination": {
                        "type": "string",
                        "description": "Chemin relatif destination",
                    },
                    "overwrite": {
                        "type": "boolean",
                        "description": "Écraser si la destination existe (défaut: False)",
                        "default": False,
                    },
                },
                "required": ["source", "destination"],
            },
            requires_confirmation=False,  # Confirmation seulement si écrase
        )
        self.sandbox = sandbox

    async def execute(
        self, source: str, destination: str, overwrite: bool = False
    ) -> dict[str, Any]:
        """Déplace ou renomme un fichier/répertoire."""
        try:
            source_path = self.sandbox.validate_path(source)
            dest_path = self.sandbox.validate_path(destination)

            if not source_path.exists():
                return {
                    "success": False,
                    "error": f"La source '{source}' n'existe pas",
                }

            if dest_path.exists() and not overwrite:
                return {
                    "success": False,
                    "error": f"La destination '{destination}' existe déjà. "
                    f"Utilisez overwrite=true pour écraser.",
                }

            # Créer le répertoire parent de destination si nécessaire
            dest_path.parent.mkdir(parents=True, exist_ok=True)

            # Déplacer
            shutil.move(str(source_path), str(dest_path))

            return {
                "success": True,
                "source": source,
                "destination": destination,
                "message": f"'{source}' déplacé vers '{destination}' avec succès",
            }

        except Exception as e:
            return {"success": False, "error": str(e)}


class CopyFileTool(Tool):
    """Tool pour copier des fichiers ou répertoires."""

    def __init__(self, sandbox: Sandbox) -> None:
        """Initialise le tool.

        Args:
            sandbox: Sandbox pour valider les chemins
        """
        super().__init__(
            name="copy_file",
            description="Copie un fichier ou un répertoire (avec son contenu)",
            parameters={
                "type": "object",
                "properties": {
                    "source": {
                        "type": "string",
                        "description": "Chemin relatif source (fichier ou répertoire)",
                    },
                    "destination": {
                        "type": "string",
                        "description": "Chemin relatif destination",
                    },
                    "overwrite": {
                        "type": "boolean",
                        "description": "Écraser si la destination existe (défaut: False)",
                        "default": False,
                    },
                },
                "required": ["source", "destination"],
            },
            requires_confirmation=False,
        )
        self.sandbox = sandbox

    async def execute(
        self, source: str, destination: str, overwrite: bool = False
    ) -> dict[str, Any]:
        """Copie un fichier ou répertoire."""
        try:
            source_path = self.sandbox.validate_path(source)
            dest_path = self.sandbox.validate_path(destination)

            if not source_path.exists():
                return {
                    "success": False,
                    "error": f"La source '{source}' n'existe pas",
                }

            if dest_path.exists() and not overwrite:
                return {
                    "success": False,
                    "error": f"La destination '{destination}' existe déjà. "
                    f"Utilisez overwrite=true pour écraser.",
                }

            # Créer le répertoire parent de destination si nécessaire
            dest_path.parent.mkdir(parents=True, exist_ok=True)

            # Copier
            if source_path.is_file():
                shutil.copy2(str(source_path), str(dest_path))
                bytes_copied = dest_path.stat().st_size
                return {
                    "success": True,
                    "source": source,
                    "destination": destination,
                    "type": "file",
                    "bytes_copied": bytes_copied,
                    "message": f"Fichier '{source}' copié vers '{destination}' avec succès",
                }
            elif source_path.is_dir():
                if dest_path.exists():
                    shutil.rmtree(dest_path)
                shutil.copytree(str(source_path), str(dest_path))
                return {
                    "success": True,
                    "source": source,
                    "destination": destination,
                    "type": "directory",
                    "message": f"Répertoire '{source}' copié vers '{destination}' avec succès",
                }
            else:
                return {
                    "success": False,
                    "error": f"'{source}' n'est ni un fichier ni un répertoire",
                }

        except Exception as e:
            return {"success": False, "error": str(e)}
