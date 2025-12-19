"""Gestionnaire de prompt et barre d'information pour le CLI."""

import logging
import os
from pathlib import Path

from rich.console import Console

logger = logging.getLogger(__name__)


class PromptManager:
    """Gestionnaire du prompt et de la barre d'information.

    Affiche:
    - Un prompt personnalisable (court)
    - Une barre d'information avec workspace, debug, etc.
    """

    def __init__(self, console: Console) -> None:
        """Initialise le gestionnaire.

        Args:
            console: Console Rich pour l'affichage
        """
        self.console = console
        self.prompt_text = ">"  # Prompt par défaut
        self.show_info_bar = True

    def set_prompt(self, text: str) -> None:
        """Définit le texte du prompt.

        Args:
            text: Nouveau texte du prompt (le ">" sera ajouté automatiquement)
        """
        # Ajouter automatiquement ">" à la fin si absent
        if not text.endswith(">"):
            self.prompt_text = f"{text}>"
        else:
            self.prompt_text = text

    def get_prompt(self) -> str:
        """Retourne le prompt complet avec formatage.

        Returns:
            Prompt formaté pour prompt_toolkit
        """
        # Retourner juste le texte avec un espace
        return f"{self.prompt_text} "

    def show_info(
        self,
        workspace: Path,
        debug_mode: bool,
        backend_type: str | None = None,
        model: str | None = None,
    ) -> None:
        """Affiche la barre d'information.

        Args:
            workspace: Chemin du workspace
            debug_mode: État du mode debug
            backend_type: Type de backend (ollama, openai, etc.)
            model: Nom du modèle actuel
        """
        logger.debug(f"show_info() called - show_info_bar: {self.show_info_bar}")

        if not self.show_info_bar:
            logger.debug("show_info_bar is False, returning early")
            return

        # Préparer les informations
        parts = []

        # Workspace (nom court)
        workspace_name = workspace.name if workspace.name else "/"
        parts.append(f"[cyan]{workspace_name}[/cyan]")

        # Mode d'édition
        parts.append("[dim]Enter=send Shift+Enter=newline[/dim]")

        # Debug
        debug_status = "[green]on[/green]" if debug_mode else "[dim]off[/dim]"
        parts.append(f"debug:{debug_status}")

        # Backend/Modèle
        if backend_type and model:
            # Raccourcir le nom du modèle si trop long
            model_short = model.split(":")[0] if ":" in model else model
            if len(model_short) > 15:
                model_short = model_short[:12] + "..."
            parts.append(f"[yellow]{backend_type}[/yellow]:[dim]{model_short}[/dim]")

        # Calculer la largeur du terminal
        try:
            terminal_width = os.get_terminal_size().columns
        except OSError:
            terminal_width = 80  # Défaut si impossible de déterminer

        # Créer la ligne d'information
        info_line = " │ ".join(parts)

        logger.debug(f"Printing info line: {info_line}")
        # Afficher juste la ligne d'info (le séparateur est géré ailleurs)
        self.console.print(info_line)

    def show_separator(self, with_spacing: bool = True) -> None:
        """Affiche une ligne de séparation.

        Args:
            with_spacing: Si True, ajoute des lignes vides avant/après
        """
        try:
            terminal_width = os.get_terminal_size().columns
        except OSError:
            terminal_width = 80

        separator = "─" * min(terminal_width, 80)

        if with_spacing:
            self.console.print(f"\n[dim]{separator}[/dim]\n")
        else:
            self.console.print(f"[dim]{separator}[/dim]")

    def toggle_info_bar(self) -> bool:
        """Active/désactive la barre d'information.

        Returns:
            Nouvel état de la barre d'info
        """
        self.show_info_bar = not self.show_info_bar
        return self.show_info_bar

    def get_prompt_variants(self) -> dict[str, str]:
        """Retourne des variantes de prompt prédéfinies.

        Returns:
            Dictionnaire nom -> symbole de prompt
        """
        return {
            "classic": ">",
            "lambda": "λ",
            "arrow": "→",
            "chevron": "»",
            "prompt": "$",
            "hash": "#",
            "star": "★",
            "minimal": "·",
        }
