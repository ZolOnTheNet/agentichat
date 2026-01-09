"""Système de confirmation pour les opérations sensibles."""

import json
from enum import Enum
from typing import Any

from prompt_toolkit import PromptSession
from prompt_toolkit.key_binding import KeyBindings
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.syntax import Syntax


class ConfirmationMode(Enum):
    """Modes de confirmation disponibles."""
    ASK = "ask"      # Demander confirmation (défaut)
    AUTO = "auto"    # Accepter automatiquement (après un "A")
    FORCE = "force"  # Toujours accepter sans demander


class ConfirmationManager:
    """Gestionnaire des confirmations utilisateur."""

    def __init__(self, console: Console) -> None:
        """Initialise le gestionnaire.

        Args:
            console: Console Rich pour l'affichage
        """
        self.console = console
        self.mode = ConfirmationMode.ASK  # Mode par défaut
        self.prompt_session = PromptSession()
        self.live_display: Live | None = None  # Référence au Live display actif
        self._setup_keybindings()

    def _setup_keybindings(self) -> None:
        """Configure les raccourcis clavier pour la confirmation."""
        self.kb = KeyBindings()

        # Validation automatique sur Y/N/A/? (minuscule et majuscule)
        @self.kb.add("y")
        @self.kb.add("Y")
        def _(event):
            event.current_buffer.text = "y"
            event.current_buffer.validate_and_handle()

        @self.kb.add("n")
        @self.kb.add("N")
        def _(event):
            event.current_buffer.text = "n"
            event.current_buffer.validate_and_handle()

        @self.kb.add("a")
        @self.kb.add("A")
        def _(event):
            event.current_buffer.text = "a"
            event.current_buffer.validate_and_handle()

        @self.kb.add("?")
        def _(event):
            event.current_buffer.text = "?"
            event.current_buffer.validate_and_handle()

    def cycle_mode(self) -> None:
        """Change de mode de confirmation (cyclique).

        ASK → AUTO → FORCE → ASK
        """
        if self.mode == ConfirmationMode.ASK:
            self.mode = ConfirmationMode.AUTO
        elif self.mode == ConfirmationMode.AUTO:
            self.mode = ConfirmationMode.FORCE
        else:  # FORCE
            self.mode = ConfirmationMode.ASK

    def get_mode_display(self) -> str:
        """Retourne l'affichage du mode actuel pour la barre de statut.

        Returns:
            Chaîne formatée (ex: "Ask", "Auto", "Force")
        """
        if self.mode == ConfirmationMode.ASK:
            return "Ask"
        elif self.mode == ConfirmationMode.AUTO:
            return "Auto"
        else:  # FORCE
            return "Force"

    async def confirm(self, tool_name: str, arguments: dict[str, Any]) -> bool:
        """Demande confirmation à l'utilisateur.

        Args:
            tool_name: Nom du tool à exécuter
            arguments: Arguments du tool

        Returns:
            True si confirmé, False sinon
        """
        # Si mode AUTO ou FORCE, accepter automatiquement
        if self.mode in [ConfirmationMode.AUTO, ConfirmationMode.FORCE]:
            return True

        # Arrêter le spinner si actif
        live_was_active = False
        if self.live_display is not None:
            live_was_active = True
            self.live_display.stop()

        # Message d'attente très visible
        self.console.print("\n")
        self.console.print("[bold yellow on blue]═══ CONFIRMATION REQUISE ═══[/bold yellow on blue]")

        # Afficher la demande de confirmation
        self._display_confirmation_request(tool_name, arguments)

        # Message clair pour l'utilisateur
        self.console.print("\n[bold cyan]→ Veuillez répondre (une seule touche suffit):[/bold cyan]")

        # Attendre la réponse avec prompt interactif
        while True:
            try:
                response = await self.prompt_session.prompt_async(
                    "[Y/A/N/?] ",
                    key_bindings=self.kb,
                )
                response = response.strip().lower()
            except (KeyboardInterrupt, EOFError):
                self.console.print("\n[dim]Annulé[/dim]")
                return False

            if response in ["y", "yes", "o", "oui", ""]:
                self.console.print("[bold green on black] ✓ OUI - Opération acceptée [/bold green on black]\n")
                # Redémarrer le spinner si nécessaire
                if live_was_active and self.live_display is not None:
                    self.live_display.start()
                return True

            elif response in ["a", "all", "t", "tout"]:
                self.mode = ConfirmationMode.AUTO
                self.console.print(
                    "[bold yellow on black] ✓ OUI À TOUT - Mode AUTO activé (Shift+Tab pour changer) [/bold yellow on black]\n"
                )
                # Redémarrer le spinner si nécessaire
                if live_was_active and self.live_display is not None:
                    self.live_display.start()
                return True

            elif response in ["n", "no", "non"]:
                self.console.print("[bold red on black] ✗ NON - Opération refusée [/bold red on black]\n")
                # Redémarrer le spinner si nécessaire
                if live_was_active and self.live_display is not None:
                    self.live_display.start()
                return False

            elif response == "?":
                self._show_help()

            else:
                self.console.print(
                    "[red]Réponse invalide. Tapez Y/A/N ou ? pour l'aide[/red]"
                )

    def _display_confirmation_request(
        self, tool_name: str, arguments: dict[str, Any]
    ) -> None:
        """Affiche la demande de confirmation.

        Args:
            tool_name: Nom du tool
            arguments: Arguments du tool
        """
        # Titre selon le type de tool
        if tool_name == "write_file":
            title = "📝 Écriture de fichier"
            action = f"Fichier : {arguments.get('path', '?')}"
            if "content" in arguments:
                preview = arguments["content"][:200]
                if len(arguments["content"]) > 200:
                    preview += "..."
                content_display = Syntax(
                    preview, "text", theme="monokai", word_wrap=True
                )
                self.console.print(Panel(content_display, title=action, border_style="yellow"))
            else:
                self.console.print(Panel(action, border_style="yellow"))

        elif tool_name == "delete_file":
            title = "🗑️  Suppression de fichier"
            action = f"Fichier : {arguments.get('path', '?')}"
            self.console.print(
                Panel(action, title=title, border_style="red")
            )

        elif tool_name == "shell_exec":
            title = "⚡ Exécution de commande"
            command = arguments.get("command", "?")
            cwd = arguments.get("cwd", ".")
            self.console.print(
                Panel(
                    f"[bold]$ {command}[/bold]\n[dim]Répertoire: {cwd}[/dim]",
                    title=title,
                    border_style="cyan",
                )
            )

        else:
            # Tool générique
            self.console.print(
                Panel(
                    json.dumps(arguments, indent=2),
                    title=f"🔧 {tool_name}",
                    border_style="blue",
                )
            )

        # Options
        self.console.print(
            "\n[yellow][Y][/yellow] Oui  "
            "[yellow][A][/yellow] Oui à tout  "
            "[yellow][N][/yellow] Non  "
            "[dim][?] Aide[/dim]"
        )

    def _show_help(self) -> None:
        """Affiche l'aide sur les confirmations."""
        help_text = """
[bold cyan]Options de confirmation :[/bold cyan]

[green]Y[/green] / [green]Yes[/green] / [green]Entrée[/green]
    Accepte cette opération

[yellow]A[/yellow] / [yellow]All[/yellow]
    Accepte cette opération ET toutes les suivantes
    (active le mode passthrough pour toute la session)

[red]N[/red] / [red]No[/red]
    Refuse cette opération
    Le LLM recevra un message d'erreur et pourra expliquer ou proposer une alternative

[dim]?[/dim]
    Affiche cette aide
"""
        self.console.print(help_text)

    def reset_mode(self) -> None:
        """Réinitialise le mode de confirmation à ASK."""
        self.mode = ConfirmationMode.ASK

    # Compatibility alias (pour ne pas casser le code existant)
    def reset_passthrough(self) -> None:
        """Alias pour reset_mode() (compatibilité)."""
        self.reset_mode()
