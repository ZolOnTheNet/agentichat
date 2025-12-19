"""Tool pour gérer une liste de tâches (todo list)."""

import json
from pathlib import Path
from typing import Any

from .registry import Tool


class TodoWriteTool(Tool):
    """Tool pour créer et gérer une liste de tâches."""

    def __init__(self, data_dir: Path) -> None:
        """Initialise le tool.

        Args:
            data_dir: Répertoire où stocker la liste de tâches
        """
        super().__init__(
            name="todo_write",
            description=(
                "Crée ou met à jour une liste de tâches. "
                "Permet de suivre la progression des tâches complexes. "
                "Chaque tâche a un contenu, un statut (pending/in_progress/completed) "
                "et une forme active (texte affiché pendant l'exécution)."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "todos": {
                        "type": "array",
                        "description": "Liste complète des tâches à enregistrer",
                        "items": {
                            "type": "object",
                            "properties": {
                                "content": {
                                    "type": "string",
                                    "description": "Description de la tâche (impératif)",
                                },
                                "status": {
                                    "type": "string",
                                    "enum": ["pending", "in_progress", "completed"],
                                    "description": "Statut de la tâche",
                                },
                                "activeForm": {
                                    "type": "string",
                                    "description": (
                                        "Forme active de la tâche (présent continu). "
                                        "Ex: 'Création du fichier' pour 'Créer le fichier'"
                                    ),
                                },
                            },
                            "required": ["content", "status", "activeForm"],
                        },
                    }
                },
                "required": ["todos"],
            },
            requires_confirmation=False,
        )
        self.data_dir = data_dir
        self.todo_file = data_dir / "current_todos.json"

    async def execute(self, todos: list[dict[str, str]]) -> dict[str, Any]:
        """Enregistre la liste de tâches."""
        try:
            # Valider les tâches
            for i, todo in enumerate(todos):
                if "content" not in todo:
                    return {
                        "success": False,
                        "error": f"Tâche {i+1}: 'content' manquant",
                    }
                if "status" not in todo:
                    return {
                        "success": False,
                        "error": f"Tâche {i+1}: 'status' manquant",
                    }
                if "activeForm" not in todo:
                    return {
                        "success": False,
                        "error": f"Tâche {i+1}: 'activeForm' manquant",
                    }
                if todo["status"] not in ["pending", "in_progress", "completed"]:
                    return {
                        "success": False,
                        "error": f"Tâche {i+1}: statut invalide '{todo['status']}'",
                    }

            # Créer le répertoire si nécessaire
            self.data_dir.mkdir(parents=True, exist_ok=True)

            # Sauvegarder les tâches
            with open(self.todo_file, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "todos": todos,
                        "timestamp": str(Path.cwd()),  # Info contexte
                    },
                    f,
                    indent=2,
                    ensure_ascii=False,
                )

            # Compter les statuts
            pending = sum(1 for t in todos if t["status"] == "pending")
            in_progress = sum(1 for t in todos if t["status"] == "in_progress")
            completed = sum(1 for t in todos if t["status"] == "completed")

            return {
                "success": True,
                "total_tasks": len(todos),
                "pending": pending,
                "in_progress": in_progress,
                "completed": completed,
                "saved_to": str(self.todo_file),
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_current_todos(self) -> list[dict[str, str]] | None:
        """Récupère la liste de tâches actuelle.

        Returns:
            Liste des tâches ou None si aucune
        """
        try:
            if not self.todo_file.exists():
                return None

            with open(self.todo_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("todos", [])

        except Exception:
            return None
