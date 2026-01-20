"""Éditeur de ligne multi-ligne avec prompt-toolkit."""

from pathlib import Path

from prompt_toolkit import PromptSession
from prompt_toolkit.filters import Condition
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys
from prompt_toolkit.styles import Style


class MultiLineEditor:
    """Éditeur de ligne de commande multi-ligne.

    Fonctionnalités :
    - Shift+Enter pour nouvelle ligne
    - Enter pour soumettre
    - Flèches haut/bas intelligentes (historique ou navigation selon position)
    - Historique persistant
    - Copier/coller
    """

    def __init__(
        self,
        history_file: Path | None = None,
        bottom_toolbar=None,
        on_shift_tab=None
    ) -> None:
        """Initialise l'éditeur.

        Args:
            history_file: Chemin vers le fichier d'historique (optionnel)
            bottom_toolbar: Fonction ou callable qui retourne le texte de la barre de statut en bas
            on_shift_tab: Callback appelé quand l'utilisateur tape Shift+Tab (optionnel)
        """
        self.history_file = history_file
        self._session: PromptSession | None = None
        self._draft_text = ""  # Brouillon en cours d'édition
        self.bottom_toolbar = bottom_toolbar  # Fonction pour la barre de statut
        self.on_shift_tab = on_shift_tab  # Callback pour Shift+Tab

    def _create_key_bindings(self) -> KeyBindings:
        """Crée les raccourcis clavier personnalisés.

        Returns:
            KeyBindings configurés
        """
        kb = KeyBindings()

        # Ctrl+J = nouvelle ligne (standard prompt-toolkit)
        @kb.add("c-j")
        def _(event):  # type: ignore
            """Insère une nouvelle ligne avec Ctrl+J."""
            event.current_buffer.insert_text("\n")

        # Meta+Enter (Alt+Enter) = nouvelle ligne
        @kb.add(Keys.Escape, Keys.Enter)
        def _(event):  # type: ignore
            """Insère une nouvelle ligne avec Alt+Enter."""
            event.current_buffer.insert_text("\n")

        # Enter seul = soumettre
        @kb.add(Keys.Enter)
        def _(event):  # type: ignore
            """Soumet le message avec Enter seul."""
            event.current_buffer.validate_and_handle()

        # Flèche haut = navigation dans le texte, historique SEULEMENT si sur première ligne
        @kb.add(Keys.Up)
        def _(event):  # type: ignore
            """Remonte dans l'historique ou d'une ligne selon la position."""
            buffer = event.current_buffer
            doc = buffer.document

            # Vérifier qu'on est vraiment sur la première ligne (ligne 0)
            current_row = doc.cursor_position_row

            # Si on est sur la première ligne, naviguer dans l'historique
            if current_row == 0:
                # Ne naviguer dans l'historique que si on a du texte ou si le buffer est vide
                buffer.history_backward()
            else:
                # Sinon, monter d'une ligne dans le texte actuel
                buffer.cursor_up()

        # Flèche bas = navigation dans le texte, historique SEULEMENT si sur dernière ligne
        @kb.add(Keys.Down)
        def _(event):  # type: ignore
            """Descend dans l'historique ou d'une ligne selon la position."""
            buffer = event.current_buffer
            doc = buffer.document

            # Vérifier qu'on est vraiment sur la dernière ligne
            current_row = doc.cursor_position_row
            last_row = doc.line_count - 1

            # Si on est sur la dernière ligne, naviguer dans l'historique
            if current_row >= last_row:
                buffer.history_forward()
            else:
                # Sinon, descendre d'une ligne dans le texte actuel
                buffer.cursor_down()

        # ESC = annuler la saisie en cours
        @kb.add(Keys.Escape)
        def _(event):  # type: ignore
            """Annule la saisie en cours."""
            event.current_buffer.text = ""
            # Note: L'utilisateur verra le buffer se vider comme feedback visuel

        # Ctrl+C = copier (comportement par défaut si sélection)
        # On garde Ctrl+C pour la copie standard

        # Ctrl+D = quitter
        @kb.add(Keys.ControlD)
        def _(event):  # type: ignore
            """Quitte l'application."""
            event.app.exit(exception=EOFError)

        # Shift+Tab = Cycler les modes de confirmation
        @kb.add(Keys.BackTab)  # BackTab = Shift+Tab
        def _(event):  # type: ignore
            """Cycle les modes de confirmation (Ask → Auto → Force → Ask)."""
            if self.on_shift_tab:
                self.on_shift_tab()

        return kb

    async def prompt(self, message: str = "> ") -> str:
        """Affiche le prompt et attend la saisie utilisateur.

        Args:
            message: Message du prompt

        Returns:
            Texte saisi par l'utilisateur

        Raises:
            EOFError: Si l'utilisateur quitte (Ctrl+D)
            KeyboardInterrupt: Si l'utilisateur annule (Ctrl+C)
        """
        # Créer la session si elle n'existe pas
        if self._session is None:
            history = None
            if self.history_file:
                # Créer le répertoire parent si nécessaire
                self.history_file.parent.mkdir(parents=True, exist_ok=True)
                history = FileHistory(str(self.history_file))

            # Créer un style avec fond grisé pour la zone de saisie
            custom_style = Style.from_dict({
                '': 'bg:#303030',  # Fond gris pour tout le texte saisi
            })

            self._session = PromptSession(
                history=history,
                multiline=True,
                prompt_continuation="... ",
                key_bindings=self._create_key_bindings(),
                style=custom_style,
            )

        # Réinitialiser le brouillon
        self._draft_text = ""

        # Afficher le prompt et attendre la saisie (version async)
        try:
            text = await self._session.prompt_async(
                message,
                bottom_toolbar=self.bottom_toolbar if self.bottom_toolbar else None
            )
            return text.strip()
        except KeyboardInterrupt:
            # Ctrl+C sans sélection
            return ""
        except EOFError:
            # Ctrl+D
            raise


def create_editor(
    history_file: Path | None = None,
    bottom_toolbar=None,
    on_shift_tab=None
) -> MultiLineEditor:
    """Crée un éditeur de ligne multi-ligne.

    Args:
        history_file: Chemin vers le fichier d'historique (optionnel)
        bottom_toolbar: Fonction pour la barre de statut en bas
        on_shift_tab: Callback pour Shift+Tab (optionnel)

    Returns:
        MultiLineEditor configuré
    """
    return MultiLineEditor(
        history_file=history_file,
        bottom_toolbar=bottom_toolbar,
        on_shift_tab=on_shift_tab
    )
