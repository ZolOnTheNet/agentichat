"""Sélecteur interactif de modèle Ollama."""

from typing import Any

from prompt_toolkit.application import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from rich.console import Console


class ModelSelector:
    """Sélecteur interactif de modèle avec curseur."""

    def __init__(self, console: Console) -> None:
        """Initialise le sélecteur.

        Args:
            console: Console Rich pour l'affichage
        """
        self.console = console
        self.selected_index = 0
        self.models: list[dict[str, Any]] = []
        self.result: str | None = None

    async def select_model(self, models: list[dict[str, Any]]) -> str | None:
        """Affiche l'interface de sélection et retourne le modèle choisi.

        Args:
            models: Liste des modèles disponibles (format Ollama)

        Returns:
            Nom du modèle choisi ou None si annulé
        """
        if not models:
            self.console.print("[bold red]Aucun modèle disponible[/bold red]")
            return None

        self.models = models
        self.selected_index = 0
        self.result = None

        # Afficher l'interface
        self.console.print("\n[bold cyan]=== Sélection du modèle Ollama ===[/bold cyan]\n")
        self.console.print("[dim]Utilisez ↑/↓ pour naviguer, Enter pour sélectionner, Esc pour annuler[/dim]\n")

        # Créer les key bindings
        kb = KeyBindings()

        @kb.add("up")
        def _(event):  # type: ignore
            """Remonter dans la liste."""
            self.selected_index = max(0, self.selected_index - 1)

        @kb.add("down")
        def _(event):  # type: ignore
            """Descendre dans la liste."""
            self.selected_index = min(len(self.models) - 1, self.selected_index + 1)

        @kb.add("enter")
        def _(event):  # type: ignore
            """Valider la sélection."""
            self.result = self.models[self.selected_index]["name"]
            event.app.exit()

        @kb.add("escape")
        @kb.add("c-c")
        def _(event):  # type: ignore
            """Annuler la sélection."""
            self.result = None
            event.app.exit()

        # Créer le contenu de l'interface
        def get_text():
            """Génère le texte à afficher."""
            lines = []
            for i, model in enumerate(self.models):
                name = model.get("name", "unknown")
                size = model.get("size", 0)
                size_gb = size / (1024**3)

                # Indicateur de sélection
                prefix = "→ " if i == self.selected_index else "  "

                # Style
                if i == self.selected_index:
                    lines.append(("class:selected", f"{prefix}{name:35} {size_gb:6.2f} GB\n"))
                else:
                    lines.append(("", f"{prefix}{name:35} {size_gb:6.2f} GB\n"))

            return lines

        # Créer le layout
        text_control = FormattedTextControl(text=get_text)
        window = Window(content=text_control, wrap_lines=True)
        layout = Layout(window)

        # Créer l'application
        app: Application = Application(
            layout=layout,
            key_bindings=kb,
            full_screen=False,
            mouse_support=False,
        )

        # Lancer l'application
        await app.run_async()

        # Afficher le résultat
        if self.result:
            self.console.print(f"\n[bold green]✓[/bold green] Modèle sélectionné: {self.result}\n")
        else:
            self.console.print("\n[dim]Sélection annulée[/dim]\n")

        return self.result


def create_model_selector(console: Console) -> ModelSelector:
    """Crée un sélecteur de modèle.

    Args:
        console: Console Rich

    Returns:
        ModelSelector configuré
    """
    return ModelSelector(console)
