"""Gestionnaire de metadata des modèles LLM.

Sauvegarde automatiquement les contraintes découvertes (ex: max_parallel_tools)
pour éviter à l'utilisateur de les configurer manuellement.
"""

import json
from pathlib import Path
from typing import Any

from .logger import get_logger

logger = get_logger("agentichat.utils.model_metadata")


class ModelMetadataManager:
    """Gestionnaire de metadata des modèles."""

    def __init__(self, data_dir: Path) -> None:
        """Initialise le gestionnaire.

        Args:
            data_dir: Répertoire de données (~/.agentichat/)
        """
        self.data_dir = data_dir
        self.metadata_file = data_dir / "model_metadata.json"
        self.metadata: dict[str, dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        """Charge les metadata depuis le fichier."""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, "r") as f:
                    self.metadata = json.load(f)
                logger.info(f"Loaded model metadata from {self.metadata_file}")
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load model metadata: {e}")
                self.metadata = {}
        else:
            self.metadata = {}

    def _save(self) -> None:
        """Sauvegarde les metadata dans le fichier."""
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            with open(self.metadata_file, "w") as f:
                json.dump(self.metadata, f, indent=2)
            logger.info(f"Saved model metadata to {self.metadata_file}")
        except IOError as e:
            logger.error(f"Failed to save model metadata: {e}")

    def get_max_parallel_tools(self, model: str) -> int | None:
        """Récupère la limite de tool calls parallèles pour un modèle.

        Args:
            model: Nom du modèle

        Returns:
            Limite sauvegardée ou None
        """
        if model in self.metadata:
            return self.metadata[model].get("max_parallel_tools")
        return None

    def set_max_parallel_tools(self, model: str, limit: int) -> None:
        """Sauvegarde la limite de tool calls parallèles pour un modèle.

        Args:
            model: Nom du modèle
            limit: Limite à sauvegarder
        """
        if model not in self.metadata:
            self.metadata[model] = {}

        self.metadata[model]["max_parallel_tools"] = limit
        self._save()
        logger.info(f"Saved max_parallel_tools={limit} for model '{model}'")

    def detect_and_save_constraint(self, model: str, error_message: str) -> bool:
        """Détecte une contrainte dans un message d'erreur et la sauvegarde.

        Args:
            model: Nom du modèle
            error_message: Message d'erreur de l'API

        Returns:
            True si une contrainte a été détectée et sauvegardée
        """
        # Détecter "only supports single tool-calls"
        if "only supports single tool-calls" in error_message.lower():
            logger.warning(
                f"Detected single tool-call constraint for model '{model}'. "
                "Auto-saving to metadata..."
            )
            self.set_max_parallel_tools(model, 1)
            return True

        return False
