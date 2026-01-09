"""Boucle CLI principale de agentichat."""

import asyncio
import signal
import time
from pathlib import Path

from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.spinner import Spinner
from rich.text import Text

from ..backends.albert import AlbertBackend
from ..backends.base import Backend, BackendError, Message
from ..backends.ollama import OllamaBackend
from ..config.loader import get_config_path, load_config, save_config
from ..config.schema import Config
from ..core.agent import AgentLoop
from ..tools.albert_tools import (
    AlbertEmbeddingsTool,
    AlbertOCRTool,
    AlbertSearchTool,
    AlbertTranscriptionTool,
)
from ..tools.directory_ops import (
    CopyFileTool,
    CreateDirectoryTool,
    DeleteDirectoryTool,
    MoveFileTool,
)
from ..tools.file_ops import DeleteFileTool, ListFilesTool, ReadFileTool, WriteFileTool
from ..tools.glob_tool import GlobTool
from ..tools.registry import ToolRegistry
from ..tools.search import SearchTextTool
from ..tools.shell import ShellExecTool
from ..tools.todo_tool import TodoWriteTool
from ..tools.web_tools import WebFetchTool, WebSearchTool
from ..utils.database import DatabaseManager
from ..utils.logger import get_logger, setup_logger
from ..utils.model_metadata import ModelMetadataManager
from ..utils.sandbox import Sandbox
from .albert_manager import AlbertManager
from .confirmation import ConfirmationManager
from .editor import create_editor
from .log_viewer import LogViewer
from .model_selector import create_model_selector
from .ollama_manager import OllamaManager
from .prompt_manager import PromptManager

logger = get_logger("agentichat.cli")


class ChatApp:
    """Application CLI de chat avec LLM."""

    def __init__(self, config: Config) -> None:
        """Initialise l'application.

        Args:
            config: Configuration de l'application
        """
        self.config = config
        self.debug_mode = False
        self.console = Console()
        self.messages: list[Message] = []
        self.backend: Backend | None = None
        self.sandbox: Sandbox | None = None
        self.registry: ToolRegistry | None = None
        self.agent: AgentLoop | None = None
        self.confirmation_manager: ConfirmationManager | None = None
        self.model_metadata = ModelMetadataManager(config.config_dir)  # Global

        # Créer le gestionnaire de base de données (local au projet)
        db_path = config.data_dir / "agentichat.db"
        self.db = DatabaseManager(db_path)

        # Créer l'éditeur avec historique, bottom toolbar ET callback Shift+Tab
        history_file = config.data_dir / "history.txt"
        self.editor = create_editor(
            history_file=history_file,
            bottom_toolbar=self._get_bottom_toolbar,
            on_shift_tab=self._cycle_confirmation_mode
        )

        # Créer le visualiseur de logs
        log_file = config.data_dir / "agentichat.log"
        self.log_viewer = LogViewer(log_file)

        # Créer les gestionnaires de backends (seront initialisés avec leurs URLs)
        self.ollama_manager: OllamaManager | None = None
        self.albert_manager: AlbertManager | None = None

        # Créer le gestionnaire de prompt
        self.prompt_manager = PromptManager(self.console)

    async def initialize(self) -> None:
        """Initialise l'application (backend, tools, etc.)."""
        # Créer le répertoire de données si nécessaire
        self.config.data_dir.mkdir(parents=True, exist_ok=True)

        # Initialiser la base de données
        await self.db.initialize()

        # Initialiser le logger
        log_level = "DEBUG" if self.debug_mode else "INFO"
        log_file = self.config.data_dir / "agentichat.log"
        setup_logger("agentichat", level=log_level, log_file=log_file)
        setup_logger("agentichat.cli", level=log_level, log_file=log_file)
        setup_logger("agentichat.backends.ollama", level=log_level, log_file=log_file)
        setup_logger("agentichat.backends.albert", level=log_level, log_file=log_file)
        setup_logger("agentichat.core.agent", level=log_level, log_file=log_file)

        if self.debug_mode:
            self.console.print(f"[dim]Mode debug activé. Logs: {log_file}[/dim]")

        logger.info(f"Starting agentichat (debug={self.debug_mode})")

        # Vérifier qu'au moins un backend est configuré
        if not self.config.backends:
            self.console.print(
                "\n[bold red]Erreur:[/bold red] Aucun backend configuré\n"
            )
            self.console.print(
                "[dim]Agentichat a besoin d'un backend LLM pour fonctionner.[/dim]\n"
            )
            self.console.print("[bold]Configuration rapide:[/bold]")
            self.console.print("  1. Copier le fichier de configuration exemple:")
            self.console.print("     [cyan]cp config.example.yaml ~/.agentichat/config.yaml[/cyan]\n")
            self.console.print("  2. Pour Ollama (local):")
            self.console.print("     - Installer Ollama: [cyan]https://ollama.ai[/cyan]")
            self.console.print("     - Télécharger un modèle: [cyan]ollama pull qwen2.5-coder:7b[/cyan]")
            self.console.print("     - La config par défaut devrait fonctionner\n")
            self.console.print("  3. Pour Albert (API Etalab):")
            self.console.print("     - Copier: [cyan]cp config.albert.example.yaml ~/.agentichat/config.yaml[/cyan]")
            self.console.print("     - Obtenir une clé: [cyan]https://albert.api.etalab.gouv.fr[/cyan]")
            self.console.print("     - Éditer ~/.agentichat/config.yaml et mettre votre clé\n")
            return

        # Initialiser le backend par défaut
        backend_name = self.config.default_backend
        if backend_name not in self.config.backends:
            self.console.print(
                f"\n[bold red]Erreur:[/bold red] Backend '{backend_name}' n'existe pas dans la configuration\n"
            )
            available = ", ".join(self.config.backends.keys())
            self.console.print(f"[dim]Backends disponibles: {available}[/dim]")
            self.console.print(
                f"\n[dim]Vérifiez votre fichier de configuration.[/dim]\n"
            )
            return

        backend_config = self.config.backends[backend_name]

        # Appliquer les metadata sauvegardées si max_parallel_tools n'est pas configuré
        max_parallel_tools = backend_config.max_parallel_tools
        if max_parallel_tools is None:
            saved_limit = self.model_metadata.get_max_parallel_tools(backend_config.model)
            if saved_limit is not None:
                max_parallel_tools = saved_limit
                logger.info(
                    f"Using saved max_parallel_tools={saved_limit} for model '{backend_config.model}'"
                )

        # Instancier le backend selon le type
        if backend_config.type == "ollama":
            self.backend = OllamaBackend(
                url=backend_config.url,
                model=backend_config.model,
                timeout=backend_config.timeout,
                max_tokens=backend_config.max_tokens,
                temperature=backend_config.temperature,
                max_parallel_tools=max_parallel_tools,
            )
        elif backend_config.type == "albert":
            self.backend = AlbertBackend(
                url=backend_config.url,
                model=backend_config.model,
                api_key=backend_config.api_key,
                timeout=backend_config.timeout,
                max_tokens=backend_config.max_tokens,
                temperature=backend_config.temperature,
                max_parallel_tools=max_parallel_tools,
            )
        else:
            self.console.print(
                f"[bold red]Erreur:[/bold red] Type de backend '{backend_config.type}' "
                f"non supporté (types disponibles: 'ollama', 'albert')"
            )
            return

        # Vérifier la connexion
        self.console.print(f"[dim]Connexion à {backend_config.url}...[/dim]")
        if not await self.backend.health_check():
            self.console.print(
                f"[bold red]Erreur:[/bold red] Impossible de se connecter à "
                f"{backend_config.url}"
            )
            self.backend = None
            return

        self.console.print(
            f"[bold green]✓[/bold green] Connecté à {backend_config.type} "
            f"(modèle: {backend_config.model})"
        )

        # Initialiser les gestionnaires de backends
        if backend_config.type == "ollama":
            self.ollama_manager = OllamaManager(
                url=backend_config.url, timeout=backend_config.timeout
            )
        elif backend_config.type == "albert":
            self.albert_manager = AlbertManager(
                url=backend_config.url,
                api_key=backend_config.api_key,
                timeout=backend_config.timeout,
            )

        # Initialiser le sandbox
        workspace_root = Path.cwd()
        self.sandbox = Sandbox(
            root=workspace_root,
            config={
                "max_file_size": self.config.sandbox.max_file_size,
                "blocked_paths": self.config.sandbox.blocked_paths,
            },
        )
        self.console.print(f"[dim]Workspace: {workspace_root}[/dim]")

        # Initialiser le registre des tools
        self.registry = ToolRegistry()

        # Enregistrer les tools - Fichiers
        self.registry.register(ListFilesTool(self.sandbox))
        self.registry.register(ReadFileTool(self.sandbox))
        self.registry.register(WriteFileTool(self.sandbox))
        self.registry.register(DeleteFileTool(self.sandbox))
        self.registry.register(SearchTextTool(self.sandbox))
        self.registry.register(GlobTool(self.sandbox))

        # Enregistrer les tools - Répertoires
        self.registry.register(CreateDirectoryTool(self.sandbox))
        self.registry.register(DeleteDirectoryTool(self.sandbox))
        self.registry.register(MoveFileTool(self.sandbox))
        self.registry.register(CopyFileTool(self.sandbox))

        # Enregistrer les tools - Système
        self.registry.register(ShellExecTool(self.sandbox))

        # Enregistrer les tools - Web
        self.registry.register(WebFetchTool())
        self.registry.register(WebSearchTool())

        # Enregistrer les tools - Productivité
        self.registry.register(TodoWriteTool(self.config.data_dir))

        # Enregistrer les tools - Albert (si backend Albert)
        if backend_config.type == "albert":
            self.registry.register(
                AlbertSearchTool(backend_config.url, backend_config.api_key)
            )
            self.registry.register(
                AlbertOCRTool(backend_config.url, backend_config.api_key)
            )
            self.registry.register(
                AlbertTranscriptionTool(backend_config.url, backend_config.api_key)
            )
            self.registry.register(
                AlbertEmbeddingsTool(backend_config.url, backend_config.api_key)
            )
            self.console.print("[dim]+ 4 tools Albert ajoutés[/dim]")

        tools_count = len(self.registry.list_tools())
        self.console.print(f"[dim]{tools_count} tools disponibles[/dim]")

        # Initialiser le gestionnaire de confirmation
        self.confirmation_manager = ConfirmationManager(self.console)

        # Vérifier que le modèle configuré existe
        if not await self._verify_model():
            self.console.print(
                "[bold red]Erreur:[/bold red] Impossible de démarrer sans modèle valide"
            )
            self.backend = None
            return

        # Initialiser l'agent
        self.agent = AgentLoop(
            backend=self.backend,
            registry=self.registry,
            max_iterations=self.config.max_iterations,
            confirmation_callback=self.confirmation_manager.confirm,
        )

        # Créer une nouvelle session dans la base de données
        await self.db.create_session(backend=backend_name, model=backend_config.model)
        logger.info(f"Session created: {self.db.session_id}")

    async def _verify_model(self) -> bool:
        """Vérifie que le modèle configuré existe et propose de choisir si non.

        Returns:
            True si le modèle est valide, False sinon
        """
        if not self.backend:
            return False

        # Pour Albert et autres backends API, on suppose que le modèle est valide
        # La vérification se fera lors de la première requête
        if isinstance(self.backend, AlbertBackend):
            logger.info(f"Using Albert model: {self.backend.model}")
            return True

        # Pour Ollama, vérifier que le modèle existe localement
        if not self.ollama_manager:
            return False

        # Lister les modèles disponibles
        try:
            models = await self.ollama_manager.list_models()
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            self.console.print(
                f"[bold red]Erreur:[/bold red] Impossible de lister les modèles: {e}"
            )
            return False

        if not models:
            self.console.print(
                "[bold red]Erreur:[/bold red] Aucun modèle Ollama disponible\n"
                "[dim]Installez un modèle avec: ollama pull <model>[/dim]"
            )
            return False

        # Vérifier si le modèle actuel existe
        model_names = [m.get("name") for m in models]
        current_model = self.backend.model

        if current_model in model_names:
            # Modèle valide
            return True

        # Modèle invalide, proposer de choisir
        self.console.print(
            f"\n[bold yellow]⚠ Attention:[/bold yellow] Le modèle configuré "
            f"'{current_model}' n'existe pas\n"
        )

        # Proposer la sélection interactive
        selector = create_model_selector(self.console)
        selected_model = await selector.select_model(models)

        if not selected_model:
            # Utilisateur a annulé
            return False

        # Changer le modèle
        self.backend.set_model(selected_model)

        # Sauvegarder dans la configuration
        backend_name = self.config.default_backend
        self.config.backends[backend_name].model = selected_model

        try:
            save_config(self.config)
            config_path = get_config_path()
            self.console.print(
                f"[bold green]✓[/bold green] Configuration sauvegardée dans {config_path}"
            )
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
            self.console.print(
                f"[bold yellow]⚠[/bold yellow] Impossible de sauvegarder la configuration: {e}"
            )

        return True

    async def run(self) -> None:
        """Lance la boucle principale du CLI."""
        if not self.backend or not self.agent:
            self.console.print(
                "[bold red]Erreur:[/bold red] Aucun backend disponible"
            )
            return

        self.console.print("\n[bold cyan]agentichat[/bold cyan] - Mode agentique activé")
        self.console.print(
            "[dim]Ctrl+J ou Alt+Enter=nouvelle ligne │ Enter=envoyer │ "
            "ESC=vider saisie │ Ctrl+C=annuler traitement │ Ctrl+D=quitter[/dim]"
        )
        self.console.print(
            "[dim]Tapez /help pour l'aide ou /prompt pour personnaliser le prompt[/dim]"
        )
        self.console.print(
            "[dim]💡 Après une erreur ou limite d'itérations, vous pouvez toujours continuer[/dim]\n"
        )

        # Boucle principale
        while True:
            try:
                # Afficher une barre de séparation au-dessus de la zone de saisie
                self.console.print()  # Ligne vide
                self.prompt_manager.show_separator(with_spacing=False)

                # Lire la saisie utilisateur avec le prompt personnalisé
                # (le pied de page en bas est affiché automatiquement par bottom_toolbar)
                prompt_text = self.prompt_manager.get_prompt()
                user_input = await self.editor.prompt(message=prompt_text)

                if not user_input:
                    continue

                # Vérifier les commandes spéciales
                if user_input in ["/quit", "/exit", "/q", "/bye"]:
                    break

                if user_input == "/clear":
                    self.messages = []
                    # Réinitialiser aussi le mode passthrough (nouvelle conversation)
                    if self.confirmation_manager:
                        self.confirmation_manager.reset_passthrough()
                    self.console.print("[dim]Conversation réinitialisée[/dim]\n")
                    continue

                if user_input.startswith("/help"):
                    self._show_help(user_input)
                    continue

                # Commande /config
                if user_input.startswith("/config"):
                    await self._handle_config_command(user_input)
                    continue

                # Commande /log
                if user_input.startswith("/log"):
                    self._handle_log_command(user_input)
                    continue

                # Commande /ollama
                if user_input.startswith("/ollama"):
                    await self._handle_ollama_command(user_input)
                    continue

                # Commande /albert
                if user_input.startswith("/albert"):
                    await self._handle_albert_command(user_input)
                    continue

                # Commande /prompt
                if user_input.startswith("/prompt"):
                    self._handle_prompt_command(user_input)
                    continue

                # Commande /model
                if user_input == "/model":
                    self._handle_model_command()
                    continue

                # Commande /info
                if user_input == "/info":
                    await self._handle_info_command()
                    continue

                # Commande /compress
                if user_input.startswith("/compress"):
                    await self._handle_compress_command(user_input)
                    continue

                # Commande /! pour exécuter directement une commande shell
                if user_input.startswith("/!"):
                    await self._handle_shell_command(user_input)
                    continue

                # Note: Le mode passthrough (Always) persiste pour toute la session
                # et n'est pas réinitialisé entre les requêtes

                # Ajouter le message utilisateur
                user_message = Message(role="user", content=user_input)
                self.messages.append(user_message)

                # Sauvegarder le message dans la base de données
                await self.db.save_message(user_message)

                # Vérifier si un avertissement de compression est nécessaire
                self._check_compression_warning()

                # Exécuter la boucle agentique
                await self._process_agent_loop()

            except EOFError:
                # Ctrl+D
                break
            except KeyboardInterrupt:
                # Ctrl+C
                self.console.print("\n[dim]Annulé[/dim]")
                continue
            except Exception as e:
                # Échapper le message d'erreur pour éviter les conflits de markup
                error_msg = str(e).replace("[", "\\[").replace("]", "\\]")
                self.console.print(f"\n[bold red]Erreur:[/bold red] {error_msg}")
                self.console.print("[dim]Vous pouvez continuer avec une nouvelle commande[/dim]\n")
                logger.error(f"Unexpected error in main loop: {e}", exc_info=True)
                continue

        self.console.print("\n[dim]Au revoir ![/dim]")

    def _check_compression_warning(self) -> None:
        """Vérifie et affiche un avertissement si la compression est recommandée."""
        compress_config = self.config.compression

        # Si pas de seuil configuré, pas d'avertissement
        if not compress_config.auto_threshold:
            return

        message_count = len(self.messages)
        threshold = compress_config.auto_threshold
        warning_pct = compress_config.warning_threshold

        # Calculer le pourcentage
        if threshold > 0:
            current_pct = message_count / threshold

            # Afficher avertissement si on dépasse le seuil d'avertissement
            if current_pct >= warning_pct:
                pct_display = int(current_pct * 100)

                # Message adapté selon si on a dépassé le seuil ou pas
                if message_count >= threshold:
                    # Dépassé
                    over_pct = int((current_pct - 1) * 100)
                    status = f"[bold red]seuil dépassé de {over_pct}%[/bold red]" if over_pct > 0 else "[bold red]seuil atteint[/bold red]"
                else:
                    # Proche mais pas encore dépassé
                    status = f"{pct_display}% du seuil"

                self.console.print(
                    f"\n[bold yellow]💡 Info:[/bold yellow] Vous avez {message_count}/{threshold} messages "
                    f"({status})"
                )
                self.console.print(
                    "[dim]→ Utilisez [bold]/compress[/bold] pour réduire l'historique et économiser des tokens[/dim]"
                )
                self.console.print(
                    "[dim]→ Tapez [bold]/help compress[/bold] pour plus d'infos ou "
                    "[bold]/config compress[/bold] pour configurer[/dim]\n"
                )

    async def _process_agent_loop(self) -> None:
        """Exécute la boucle agentique et affiche les résultats."""
        if not self.agent:
            return

        try:
            # Message de début avec instruction d'annulation
            self.console.print("\n[bold yellow]⚡ Traitement en cours...[/bold yellow]")
            self.console.print("[dim]Appuyez sur Ctrl+C pour annuler[/dim]\n")

            spinner = Spinner("dots", text="")
            start_time = time.time()

            # Messages sympathiques variés
            friendly_messages = [
                "Le LLM analyse votre demande",
                "Le LLM génère une réponse",
                "Le LLM prépare les actions",
                "Le LLM organise les outils",
                "Le LLM affine sa réponse",
                "Le LLM réfléchit",
                "Le LLM traite les informations",
                "Le LLM construit la réponse",
            ]
            message_index = 0
            last_message_change = time.time()

            async def update_spinner():
                """Met à jour le spinner avec messages sympathiques + vraies statistiques d'Ollama."""
                nonlocal message_index, last_message_change
                while True:
                    elapsed = time.time() - start_time

                    # Changer de message toutes les 2 secondes
                    if time.time() - last_message_change >= 2.0:
                        message_index += 1
                        last_message_change = time.time()

                    # Message sympathique qui tourne
                    friendly_msg = friendly_messages[message_index % len(friendly_messages)]

                    # Construire le message avec les stats réelles
                    if self.backend and hasattr(self.backend, 'last_usage') and self.backend.last_usage:
                        stats = self.backend.last_usage
                        prompt_tokens = stats.get("prompt_tokens", 0)
                        completion_tokens = stats.get("completion_tokens", 0)
                        total_time = stats.get("total_duration_ms", 0)

                        # Calculer les tokens/sec si on a des données
                        if total_time > 0 and completion_tokens > 0:
                            tokens_per_sec = (completion_tokens / total_time) * 1000
                            stats_text = (
                                f"[dim]│ {prompt_tokens}+{completion_tokens} tok │ "
                                f"{tokens_per_sec:.1f} tok/s │ {elapsed:.1f}s[/dim]"
                            )
                        else:
                            stats_text = (
                                f"[dim]│ {prompt_tokens}+{completion_tokens} tok │ {elapsed:.1f}s[/dim]"
                            )

                        msg = f"[cyan]{friendly_msg}...[/cyan] {stats_text}"
                    else:
                        # Pas encore de stats, afficher juste le message et le temps
                        msg = f"[cyan]{friendly_msg}...[/cyan] [dim]│ {elapsed:.1f}s[/dim]"

                    # Utiliser from_markup pour interpréter les balises Rich
                    spinner.text = Text.from_markup(msg)
                    await asyncio.sleep(0.5)  # Rafraîchir toutes les 0.5s

            # Lancer la mise à jour du spinner en arrière-plan
            update_task = asyncio.create_task(update_spinner())

            try:
                with Live(spinner, console=self.console, transient=True, refresh_per_second=4) as live:
                    # Passer la référence au Live display au confirmation manager
                    if self.confirmation_manager:
                        self.confirmation_manager.live_display = live

                    # Exécuter l'agent
                    logger.debug("Starting agent loop")
                    response, updated_messages = await self.agent.run(self.messages)
                    logger.debug(f"Agent loop completed with {len(updated_messages)} messages")

                    # Retirer la référence
                    if self.confirmation_manager:
                        self.confirmation_manager.live_display = None
            finally:
                # Arrêter la tâche de mise à jour
                update_task.cancel()
                try:
                    await update_task
                except asyncio.CancelledError:
                    pass

            # Mettre à jour l'historique et sauvegarder les nouveaux messages
            old_count = len(self.messages)
            self.messages = updated_messages
            new_count = len(self.messages)

            # Sauvegarder les nouveaux messages dans la base de données
            if new_count > old_count:
                for msg in self.messages[old_count:]:
                    await self.db.save_message(msg)

            # Afficher les statistiques finales
            elapsed_total = time.time() - start_time
            if self.backend and hasattr(self.backend, 'last_usage') and self.backend.last_usage:
                stats = self.backend.last_usage
                prompt_tokens = stats.get("prompt_tokens", 0)
                completion_tokens = stats.get("completion_tokens", 0)
                total_tokens = prompt_tokens + completion_tokens

                self.console.print(
                    f"\n[dim]Terminé en {elapsed_total:.1f}s │ "
                    f"{total_tokens} tokens total "
                    f"({prompt_tokens} prompt + {completion_tokens} réponse)[/dim]"
                )

            # Afficher la réponse (si elle existe)
            if response:
                self.console.print("\n[bold green]Assistant:[/bold green]")
                self.console.print(response)

                # Si c'est un message de limite d'itérations, ajouter une note
                if "Limite d'itérations atteinte" in response:
                    self.console.print(
                        "\n[dim]→ Vous pouvez continuer avec une nouvelle commande ou "
                        "reformuler votre demande[/dim]"
                    )

        except KeyboardInterrupt:
            # Message d'annulation très visible
            self.console.print("\n")
            self.console.print("[bold red on black] ✗ ANNULÉ - Traitement interrompu (Ctrl+C) [/bold red on black]")
            self.console.print("[dim]Le LLM a été arrêté. Vous pouvez continuer avec une nouvelle demande.[/dim]\n")
            logger.info("Request cancelled by user with Ctrl+C")
        except BackendError as e:
            # Erreur backend (potentiellement modèle invalide ou contrainte)
            error_msg = str(e)

            # Détecter un rate limit (quota tokens dépassé)
            if "tokens per minute exceeded" in error_msg.lower() or "rate limit" in error_msg.lower():
                self.console.print(
                    f"\n[bold yellow]⚠ Quota API dépassé:[/bold yellow] {e}\n"
                )
                self.console.print(
                    "[yellow]L'API Albert limite le nombre de tokens par minute.[/yellow]\n"
                    "[dim]Solutions:[/dim]\n"
                    "  • Attendez ~60 secondes avant de réessayer\n"
                    "  • Utilisez [bold]/clear[/bold] pour réduire l'historique\n"
                    "  • Utilisez un modèle plus petit avec [bold]/albert run meta-llama/Llama-3.1-8B-Instruct[/bold]\n"
                )
                return

            # Détecter et sauvegarder les contraintes du modèle
            if self.backend and self.model_metadata.detect_and_save_constraint(
                self.backend.model, error_msg
            ):
                self.console.print(
                    f"\n[bold yellow]⚠ Contrainte détectée:[/bold yellow] {e}\n"
                )
                self.console.print(
                    "[bold green]✓[/bold green] Contrainte sauvegardée automatiquement. "
                    "Veuillez réessayer votre commande.\n"
                )
                return

            # Sinon, afficher l'erreur normalement
            # Échapper le message d'erreur pour éviter les conflits de markup
            error_display = str(e).replace("[", "\\[").replace("]", "\\]")
            self.console.print(f"\n[bold red]Erreur:[/bold red] {error_display}")
            logger.error(f"Backend error in agent loop: {e}", exc_info=True)

            # Vérifier si c'est une erreur de modèle
            error_msg_lower = error_msg.lower()
            if "model" in error_msg_lower or "not found" in error_msg_lower or "404" in error_msg_lower:
                self.console.print(
                    "[bold yellow]⚠ Le modèle semble invalide.[/bold yellow]\n"
                    "[dim]Voulez-vous choisir un autre modèle ? (y/n)[/dim] ",
                    end="",
                )

                # Demander confirmation
                try:
                    choice = input().strip().lower()
                    if choice in ["y", "yes", "o", "oui"]:
                        # Proposer la sélection
                        if await self._verify_model():
                            self.console.print(
                                "[bold green]✓[/bold green] Modèle changé, "
                                "vous pouvez réessayer votre commande\n"
                            )
                        else:
                            self.console.print(
                                "[bold yellow]⚠[/bold yellow] Pas de changement de modèle\n"
                            )
                    else:
                        self.console.print("[dim]→ Vous pouvez continuer avec une nouvelle commande[/dim]\n")
                except Exception as input_error:
                    logger.error(f"Error getting user input: {input_error}")
            else:
                # Autre erreur backend
                self.console.print("[dim]→ Vous pouvez continuer avec une nouvelle commande[/dim]\n")

        except Exception as e:
            # Échapper le message d'erreur pour éviter les conflits de markup
            error_display = str(e).replace("[", "\\[").replace("]", "\\]")
            self.console.print(f"\n[bold red]Erreur:[/bold red] {error_display}")
            self.console.print("[dim]→ Vous pouvez continuer avec une nouvelle commande[/dim]\n")
            logger.error(f"Error in agent loop: {e}", exc_info=True)

    def _cycle_confirmation_mode(self) -> None:
        """Cycle les modes de confirmation et affiche un message."""
        if not self.confirmation_manager:
            return

        # Sauvegarder l'ancien mode pour affichage
        old_mode = self.confirmation_manager.get_mode_display()

        # Cycler
        self.confirmation_manager.cycle_mode()

        # Nouveau mode
        new_mode = self.confirmation_manager.get_mode_display()

        # Afficher le changement (brief, sur une ligne)
        self.console.print(f"[dim]Mode confirmation: {old_mode} → [bold]{new_mode}[/bold][/dim]")

    def _get_bottom_toolbar(self) -> str:
        """Retourne le texte de la barre de statut en bas (bottom toolbar).

        Returns:
            Texte formaté pour la barre de statut
        """
        if not self.prompt_manager.show_info_bar:
            return ""

        # Préparer les informations
        parts = []

        # Workspace (nom court)
        workspace_name = Path.cwd().name if Path.cwd().name else "/"
        parts.append(f"{workspace_name}")

        # Mode d'édition
        parts.append("Enter=send Ctrl+J/Alt+Enter=newline")

        # Debug
        debug_status = "on" if self.debug_mode else "off"
        parts.append(f"debug:{debug_status}")

        # Mode de confirmation
        if self.confirmation_manager:
            conf_mode = self.confirmation_manager.get_mode_display()
            parts.append(f"Conf:{conf_mode}")

        # Backend/Modèle
        if self.backend:
            backend_config = self.config.backends[self.config.default_backend]
            backend_type = backend_config.type
            model = self.backend.model

            # Raccourcir le nom du modèle si trop long
            model_short = model.split(":")[0] if ":" in model else model
            if len(model_short) > 15:
                model_short = model_short[:12] + "..."
            parts.append(f"{backend_type}:{model_short}")

        # Créer la ligne d'information avec séparateurs
        info_line = " │ ".join(parts)

        return info_line

    def _show_help(self, command: str = "/help") -> None:
        """Affiche l'aide générale ou spécifique à un topic.

        Args:
            command: Commande complète (ex: "/help", "/help compress")
        """
        parts = command.split(maxsplit=1)
        topic = parts[1].lower() if len(parts) > 1 else None

        # Aide spécifique à un topic
        if topic:
            self._show_topic_help(topic)
            return

        # Aide générale (succincte)
        help_text = """
# agentichat - Aide Rapide

## Commandes Principales
- `/help <topic>` - Aide détaillée sur un sujet
- `/quit`, `/exit` - Quitter l'application
- `/clear` - Réinitialiser la conversation
- `/info` - Statistiques de la session
- `/compress` - Compresser l'historique
- `/model` - Afficher le modèle actif
- `/! <cmd>` - Exécuter une commande shell

## Topics Disponibles
Tapez `/help <topic>` pour plus d'informations :

- **compress** - Compression de conversation et gestion mémoire
- **config** - Configuration de l'application
- **log** - Visualisation et recherche dans les logs
- **ollama** - Commandes pour backend Ollama
- **albert** - Commandes pour backend Albert
- **prompt** - Personnalisation du prompt
- **tools** - Liste complète des tools disponibles
- **shortcuts** - Raccourcis clavier

## Raccourcis Essentiels
- `Enter` - Envoyer │ `Ctrl+J` / `Alt+Enter` - Nouvelle ligne
- `Ctrl+C` - Annuler traitement │ `Ctrl+D` - Quitter
- `↑` / `↓` - Historique │ `ESC` - Vider saisie

## Exemples
```
> Liste les fichiers Python dans src/
> Crée un fichier hello.py avec Hello World
> Cherche "TODO" dans tout le projet
```

💡 **Astuce:** Tapez `/help compress` pour optimiser votre usage de tokens !
"""
        self.console.print(Markdown(help_text))

    def _show_topic_help(self, topic: str) -> None:
        """Affiche l'aide détaillée pour un topic spécifique.

        Args:
            topic: Nom du topic (compress, config, log, etc.)
        """
        topics = {
            "compress": """
# Compression de Conversation

## Commandes

### /compress
Compresse la conversation en résumant avec le LLM.
- `/compress` - Compresse tous les messages en un résumé
- `/compress --max N` ou `-m N` - Garde max N messages
- `/compress --keep N` - Garde les N derniers messages

### /config compress
Configure la compression automatique.
- `/config compress` - Affiche la configuration
- `/config compress --enable` - Active l'auto-compression
- `/config compress --disable` - Désactive l'auto-compression
- `/config compress --keep N` - Définit le nombre de messages à garder
- `/config compress --auto <seuil> <garde>` - Configure l'auto-compression
  Exemple: `/config compress --auto 20 5` (compresse à 20 msg, garde 5)

## Pourquoi Compresser ?
- **Économise des tokens** (= réduit coûts API)
- **Accélère les réponses** (moins de contexte à traiter)
- **Conserve l'essentiel** (résumé intelligent par le LLM)

## Exemples
```
/compress --keep 10        # Résume tout sauf les 10 derniers
/config compress --auto 20 5   # Auto-compresse à 20 messages, garde 5
```
""",
            "config": """
# Configuration

## Commandes

### /config show
Affiche la configuration actuelle (backend, modèle, debug, etc.)

### /config backend
Gestion des backends LLM.
- `/config backend list` - Liste les backends configurés
- `/config backend <nom>` - Change de backend

### /config debug
Active/désactive les logs détaillés.
- `/config debug on` - Active le mode debug
- `/config debug off` - Désactive le mode debug

### /config compress
Configure la compression (voir `/help compress`)

## Fichier de Configuration
- Local (projet): `.agentichat/config.yaml`
- Global (utilisateur): `~/.agentichat/config.yaml`

Utilisez `nano ~/.agentichat/config.yaml` pour éditer.
""",
            "log": """
# Logs

## Commandes

- `/log` ou `/log show` - Affiche les nouveaux logs
- `/log fullshow` - Affiche tous les logs depuis le dernier clear
- `/log clear` - Marque un point de clear (réinitialise la vue)
- `/log search <texte>` - Recherche dans les logs avec contexte
- `/log config` - Affiche la configuration actuelle
- `/log config show <n>` - Définit le nombre de lignes pour show
- `/log config search <avant> <après>` - Contexte pour search
- `/log status` - Statistiques (taille, lignes, positions)

## Codes Couleur
- 🔴 **Rouge** - ERROR, CRITICAL
- 🟡 **Jaune** - WARNING
- ⚪ **Gris** - DEBUG
- ⚪ **Blanc** - INFO

## Fichier Log
`.agentichat/agentichat.log` (dans le répertoire de travail)
""",
            "ollama": """
# Commandes Ollama

**Note:** Disponible uniquement avec le backend Ollama.

## Commandes

- `/ollama list` - Liste tous les modèles installés
- `/ollama show <model>` - Informations détaillées d'un modèle
- `/ollama run <model>` - Change de modèle Ollama
- `/ollama ps` - Liste les modèles en cours d'exécution
- `/ollama create <nom> <path>` - Crée un modèle depuis Modelfile
- `/ollama cp <src> <dst>` - Copie un modèle
- `/ollama rm <model>` - Supprime un modèle (avec confirmation)

## Exemples
```
/ollama list                     # Voir les modèles disponibles
/ollama run qwen2.5-coder:7b     # Basculer sur un modèle
/ollama ps                       # Voir les modèles chargés
```
""",
            "albert": """
# Commandes Albert

**Note:** Disponible uniquement avec le backend Albert (Etalab).

## Commandes

- `/albert list` - Liste tous les modèles disponibles
- `/albert show <model>` - Informations détaillées d'un modèle
- `/albert run <model>` - Change de modèle Albert
- `/albert usage` - Statistiques d'utilisation (tokens, requêtes, coûts)
- `/albert me` - Informations de compte (email, organisation, quota)

## Tools Supplémentaires Albert
Le backend Albert offre 4 tools additionnels :
- `albert_search` - Recherche dans la base Etalab
- `albert_ocr` - Extraction de texte depuis images
- `albert_transcription` - Transcription audio vers texte
- `albert_embeddings` - Génération d'embeddings

## Exemples
```
/albert list                     # Voir les modèles
/albert run AgentPublic/llama3   # Basculer sur un modèle
/albert usage                    # Voir sa consommation
```
""",
            "prompt": """
# Personnalisation du Prompt

## Commandes

- `/prompt` - Affiche le prompt actuel
- `/prompt list` - Liste les prompts prédéfinis
- `/prompt <texte>` - Définit un prompt personnalisé
- `/prompt <nom>` - Utilise un prompt prédéfini
- `/prompt reset` - Réinitialise au prompt par défaut (>)
- `/prompt toggle` - Active/désactive la barre d'info du bas

## Prompts Prédéfinis
- `classic` → `>`
- `lambda` → `λ`
- `arrow` → `→`
- `sharp` → `#`
- `dollar` → `$`

## Exemples
```
/prompt lambda          # Utilise λ comme prompt
/prompt 🚀             # Prompt personnalisé emoji
/prompt toggle         # Cache la barre d'info
```
""",
            "tools": """
# Tools Disponibles

Le LLM a accès à ces outils pour interagir avec votre système :

## Fichiers (6 tools)
- `list_files` - Liste fichiers/répertoires
- `read_file` - Lit un fichier
- `write_file` - Crée/modifie fichier (⚠ confirmation)
- `delete_file` - Supprime fichier (⚠ confirmation)
- `search_text` - Recherche textuelle (regex)
- `glob_search` - Recherche par pattern (`*.py`, `src/**/*.js`)

## Répertoires (4 tools)
- `create_directory` - Crée un répertoire
- `delete_directory` - Supprime répertoire (⚠ confirmation)
- `move_file` - Déplace/renomme
- `copy_file` - Copie fichier/répertoire

## Web (2 tools)
- `web_fetch` - Récupère contenu d'une URL
- `web_search` - Recherche DuckDuckGo

## Système (1 tool)
- `shell_exec` - Exécute commande shell (⚠ confirmation)

## Productivité (1 tool)
- `todo_write` - Gère une liste de tâches

## Albert Uniquement (4 tools)
- `albert_search`, `albert_ocr`, `albert_transcription`, `albert_embeddings`

## Confirmations
⚠ Les operations destructives nécessitent confirmation (Y/N/A).
""",
            "shortcuts": """
# Raccourcis Clavier

## Édition
- `Enter` - Envoyer le message
- `Ctrl+J` ou `Alt+Enter` - Nouvelle ligne
- `ESC` - Vider la saisie en cours
- `Shift+Tab` - Cycler les modes de confirmation (Ask/Auto/Force)

## Navigation Historique
- `↑` (flèche haut) - Message précédent (si sur première ligne)
- `↓` (flèche bas) - Message suivant (si sur dernière ligne)

## Contrôle
- `Ctrl+C` - Annuler le traitement LLM en cours
- `Ctrl+D` - Quitter l'application

## Modes de Confirmation
Trois modes disponibles (cycle avec `Shift+Tab`) :
- **Ask** - Demander confirmation à chaque fois (défaut)
- **Auto** - Accepter automatiquement (activé après "A")
- **Force** - Toujours accepter sans demander

Lors d'une confirmation (mode Ask) :
- `Y` ou `y` - Accepter cette opération
- `N` ou `n` - Refuser cette opération
- `A` ou `a` - Passer en mode Auto

## Barre d'Info (bas d'écran)
Affiche : workspace, debug, **Conf:mode**, backend/modèle
Toggle avec `/prompt toggle`
""",
        }

        if topic in topics:
            self.console.print(Markdown(topics[topic]))
        else:
            self.console.print(
                f"[yellow]Topic '{topic}' inconnu.[/yellow]\n\n"
                "[bold]Topics disponibles:[/bold]\n"
                "  compress, config, log, ollama, albert, prompt, tools, shortcuts\n\n"
                "[dim]Utilisez /help <topic> pour afficher l'aide détaillée.[/dim]\n"
            )

    async def _handle_config_command(self, command: str) -> None:
        """Gère les commandes /config.

        Args:
            command: Commande complète (ex: "/config show", "/config debug on")
        """
        parts = command.split()

        if len(parts) == 1 or parts[1] == "show":
            # Afficher la configuration actuelle
            self.console.print("\n[bold cyan]=== Configuration ===")
            self.console.print(f"[dim]Mode debug:[/dim] {'activé' if self.debug_mode else 'désactivé'}")
            self.console.print(f"[dim]Backend:[/dim] {self.config.default_backend}")
            if self.backend:
                backend_config = self.config.backends[self.config.default_backend]
                self.console.print(f"[dim]Modèle:[/dim] {backend_config.model}")
                self.console.print(f"[dim]Timeout:[/dim] {backend_config.timeout}s")
            self.console.print(f"[dim]Max iterations:[/dim] {self.config.max_iterations}")
            log_file = self.config.data_dir / "agentichat.log"
            self.console.print(f"[dim]Fichier de log:[/dim] {log_file}\n")

        elif len(parts) >= 2 and parts[1] == "backend":
            # Gestion des backends
            if len(parts) == 2 or (len(parts) == 3 and parts[2] == "list"):
                # Lister les backends disponibles
                self.console.print("\n[bold cyan]=== Backends configurés ===")
                for name, backend_config in self.config.backends.items():
                    # Marquer le backend actuel
                    marker = "[bold green]●[/bold green]" if name == self.config.default_backend else " "
                    self.console.print(
                        f"{marker} {name:15} ({backend_config.type:8}) - {backend_config.url}"
                    )
                self.console.print(
                    f"\n[dim]Backend actuel: {self.config.default_backend}[/dim]"
                )
                self.console.print(
                    "[dim]Utilisation: /config backend <nom>[/dim]\n"
                )
            elif len(parts) >= 3:
                # Changer de backend
                backend_name = parts[2]
                if backend_name in self.config.backends:
                    # Changer de backend
                    await self._switch_backend(backend_name)
                else:
                    # Backend non configuré - afficher aide
                    self.console.print(
                        f"\n[bold red]Erreur:[/bold red] Backend '{backend_name}' non configuré\n"
                    )
                    available = ", ".join(self.config.backends.keys())
                    self.console.print(f"[dim]Backends disponibles: {available}[/dim]\n")

                    # Aide pour configurer un backend
                    self.console.print("[bold]Pour ajouter un backend:[/bold]")
                    self.console.print("  1. Éditer la configuration:")
                    self.console.print("     [cyan]nano ~/.agentichat/config.yaml[/cyan]\n")
                    self.console.print("  2. Ajouter le backend dans la section 'backends:'")
                    self.console.print("     Voir config.example.yaml pour des exemples\n")
                    self.console.print("[bold]Exemples de backends:[/bold]")
                    self.console.print("  - Ollama (local): config.example.yaml")
                    self.console.print("  - Albert (API):   config.albert.example.yaml\n")

        elif len(parts) >= 3 and parts[1] == "debug":
            # Activer/désactiver le mode debug
            action = parts[2].lower()
            if action == "on":
                self._set_debug_mode(True)
                self.console.print("[bold green]✓[/bold green] Mode debug activé\n")
            elif action == "off":
                self._set_debug_mode(False)
                self.console.print("[bold green]✓[/bold green] Mode debug désactivé\n")
            else:
                self.console.print(
                    "[bold red]Erreur:[/bold red] Utilisation: /config debug [on|off]\n"
                )

        elif len(parts) >= 2 and parts[1] == "compress":
            # Gestion de la configuration de compression
            compress_config = self.config.compression

            if len(parts) == 2:
                # Afficher la configuration actuelle
                self.console.print("\n[bold cyan]=== Configuration de Compression ===[/bold cyan]")
                self.console.print(
                    f"[dim]Auto-compression:[/dim] {'activée' if compress_config.auto_enabled else 'désactivée'}"
                )
                self.console.print(f"[dim]Seuil auto:[/dim] {compress_config.auto_threshold} messages")
                self.console.print(f"[dim]Messages à garder:[/dim] {compress_config.auto_keep}")
                self.console.print(
                    f"[dim]Seuil d'avertissement:[/dim] {int(compress_config.warning_threshold * 100)}%"
                )
                if compress_config.max_messages:
                    self.console.print(f"[dim]Limite max:[/dim] {compress_config.max_messages} messages")
                else:
                    self.console.print("[dim]Limite max:[/dim] illimitée")
                self.console.print()
                return

            action = parts[2].lower()

            if action == "--enable":
                compress_config.auto_enabled = True
                self.console.print("[bold green]✓[/bold green] Auto-compression activée\n")

            elif action == "--disable":
                compress_config.auto_enabled = False
                self.console.print("[bold green]✓[/bold green] Auto-compression désactivée\n")

            elif action == "--keep":
                if len(parts) < 4:
                    self.console.print(
                        "[red]Erreur: --keep nécessite une valeur[/red]\n"
                        "[dim]Usage: /config compress --keep <nombre>[/dim]\n"
                    )
                    return
                try:
                    keep_count = int(parts[3])
                    if keep_count < 1:
                        self.console.print("[red]Erreur: La valeur doit être >= 1[/red]\n")
                        return
                    compress_config.auto_keep = keep_count
                    self.console.print(
                        f"[bold green]✓[/bold green] Messages à garder: {keep_count}\n"
                    )
                except ValueError:
                    self.console.print("[red]Erreur: Valeur invalide (nombre entier requis)[/red]\n")

            elif action == "--auto":
                if len(parts) < 5:
                    self.console.print(
                        "[red]Erreur: --auto nécessite deux valeurs[/red]\n"
                        "[dim]Usage: /config compress --auto <seuil> <à_garder>[/dim]\n"
                        "[dim]Exemple: /config compress --auto 20 5 (compresse auto à 20 msg, garde 5)[/dim]\n"
                    )
                    return
                try:
                    threshold = int(parts[3])
                    keep = int(parts[4])
                    if threshold < 1 or keep < 1:
                        self.console.print("[red]Erreur: Les valeurs doivent être >= 1[/red]\n")
                        return
                    if keep >= threshold:
                        self.console.print("[red]Erreur: Le nombre à garder doit être < seuil[/red]\n")
                        return
                    compress_config.auto_threshold = threshold
                    compress_config.auto_keep = keep
                    compress_config.auto_enabled = True
                    self.console.print(
                        f"[bold green]✓[/bold green] Auto-compression configurée: "
                        f"seuil={threshold}, garde={keep}\n"
                    )
                except ValueError:
                    self.console.print("[red]Erreur: Valeurs invalides (nombres entiers requis)[/red]\n")

            else:
                self.console.print(
                    f"[red]Erreur: Option inconnue '{action}'[/red]\n"
                    "[bold yellow]Options disponibles:[/bold yellow]\n"
                    "  /config compress                    - Affiche la configuration\n"
                    "  /config compress --enable           - Active l'auto-compression\n"
                    "  /config compress --disable          - Désactive l'auto-compression\n"
                    "  /config compress --keep <N>         - Définit le nombre de messages à garder\n"
                    "  /config compress --auto <seuil> <N> - Configure l'auto-compression\n"
                )

        else:
            # Commande invalide
            self.console.print(
                "[bold yellow]Commandes /config disponibles:[/bold yellow]\n"
                "  /config show                        - Affiche la configuration actuelle\n"
                "  /config backend list                - Liste les backends disponibles\n"
                "  /config backend <nom>               - Change de backend\n"
                "  /config debug on                    - Active le mode debug\n"
                "  /config debug off                   - Désactive le mode debug\n"
                "  /config compress                    - Configure la compression de conversation\n"
            )

    async def _switch_backend(self, backend_name: str) -> None:
        """Change de backend à la volée.

        Args:
            backend_name: Nom du backend à activer
        """
        if backend_name == self.config.default_backend:
            self.console.print(
                f"[dim]Backend '{backend_name}' déjà actif[/dim]\n"
            )
            return

        backend_config = self.config.backends[backend_name]

        self.console.print(f"\n[cyan]Changement de backend vers '{backend_name}'...[/cyan]")

        # Nettoyer les tools spécifiques à l'ancien backend
        if self.registry:
            # Retirer les tools Albert si on quitte Albert
            if self.config.default_backend == "albert" or (
                self.config.default_backend in self.config.backends
                and self.config.backends[self.config.default_backend].type == "albert"
            ):
                # Retirer les 4 tools Albert
                for tool_name in ["albert_search", "albert_ocr", "albert_transcription", "albert_embeddings"]:
                    if tool_name in self.registry._tools:
                        del self.registry._tools[tool_name]
                        logger.debug(f"Removed tool: {tool_name}")

        # Appliquer les metadata sauvegardées si max_parallel_tools n'est pas configuré
        max_parallel_tools = backend_config.max_parallel_tools
        if max_parallel_tools is None:
            saved_limit = self.model_metadata.get_max_parallel_tools(backend_config.model)
            if saved_limit is not None:
                max_parallel_tools = saved_limit
                logger.info(
                    f"Using saved max_parallel_tools={saved_limit} for model '{backend_config.model}'"
                )

        # Instancier le nouveau backend
        try:
            if backend_config.type == "ollama":
                self.backend = OllamaBackend(
                    url=backend_config.url,
                    model=backend_config.model,
                    timeout=backend_config.timeout,
                    max_tokens=backend_config.max_tokens,
                    temperature=backend_config.temperature,
                    max_parallel_tools=max_parallel_tools,
                )
                # Initialiser le gestionnaire Ollama
                self.ollama_manager = OllamaManager(
                    url=backend_config.url, timeout=backend_config.timeout
                )
                self.albert_manager = None

            elif backend_config.type == "albert":
                self.backend = AlbertBackend(
                    url=backend_config.url,
                    model=backend_config.model,
                    api_key=backend_config.api_key,
                    timeout=backend_config.timeout,
                    max_tokens=backend_config.max_tokens,
                    temperature=backend_config.temperature,
                    max_parallel_tools=max_parallel_tools,
                )
                # Initialiser le gestionnaire Albert
                self.albert_manager = AlbertManager(
                    url=backend_config.url,
                    api_key=backend_config.api_key,
                    timeout=backend_config.timeout,
                )
                self.ollama_manager = None

                # Ajouter les tools Albert
                if self.registry:
                    self.registry.register(
                        AlbertSearchTool(backend_config.url, backend_config.api_key)
                    )
                    self.registry.register(
                        AlbertOCRTool(backend_config.url, backend_config.api_key)
                    )
                    self.registry.register(
                        AlbertTranscriptionTool(backend_config.url, backend_config.api_key)
                    )
                    self.registry.register(
                        AlbertEmbeddingsTool(backend_config.url, backend_config.api_key)
                    )
                    logger.debug("Added 4 Albert tools")

            else:
                self.console.print(
                    f"[bold red]Erreur:[/bold red] Type de backend '{backend_config.type}' "
                    f"non supporté\n"
                )
                return

        except Exception as e:
            self.console.print(
                f"[bold red]Erreur:[/bold red] Impossible d'initialiser le backend: {e}\n"
            )
            logger.error(f"Failed to switch backend: {e}", exc_info=True)
            return

        # Vérifier la connexion
        try:
            if not await self.backend.health_check():
                self.console.print(
                    f"[bold yellow]⚠ Attention:[/bold yellow] Impossible de se connecter à "
                    f"{backend_config.url}\n"
                    f"[dim]Le backend est configuré mais peut ne pas être disponible[/dim]\n"
                )
        except Exception as e:
            self.console.print(
                f"[bold yellow]⚠ Attention:[/bold yellow] Health check échoué: {e}\n"
            )

        # Mettre à jour la config
        old_backend = self.config.default_backend
        self.config.default_backend = backend_name

        # Réinitialiser l'agent avec le nouveau backend
        if self.agent and self.registry:
            self.agent = AgentLoop(
                backend=self.backend,
                registry=self.registry,
                max_iterations=self.config.max_iterations,
                confirmation_callback=self.confirmation_manager.confirm if self.confirmation_manager else None,
            )

        # Afficher le résultat
        tools_count = len(self.registry.list_tools()) if self.registry else 0
        self.console.print(
            f"[bold green]✓[/bold green] Backend changé: {old_backend} → {backend_name}\n"
            f"[dim]Type: {backend_config.type}, Modèle: {backend_config.model}[/dim]\n"
            f"[dim]{tools_count} tools disponibles[/dim]\n"
        )

        logger.info(f"Switched backend from {old_backend} to {backend_name}")

    def _set_debug_mode(self, enabled: bool) -> None:
        """Change le mode debug dynamiquement.

        Args:
            enabled: True pour activer, False pour désactiver
        """
        import logging

        self.debug_mode = enabled
        level = logging.DEBUG if enabled else logging.INFO

        # Mettre à jour tous les loggers
        for logger_name in ["agentichat", "agentichat.cli", "agentichat.backends.ollama", "agentichat.core.agent"]:
            logger_instance = logging.getLogger(logger_name)
            logger_instance.setLevel(level)

            # Mettre à jour le niveau des handlers console (si présents)
            for handler in logger_instance.handlers:
                if isinstance(handler, logging.StreamHandler) and handler.stream.name == '<stderr>':
                    handler.setLevel(level)

        log_file = self.config.data_dir / "agentichat.log"
        logger.info(f"Debug mode {'enabled' if enabled else 'disabled'} dynamically")

        if enabled:
            self.console.print(f"[dim]Logs détaillés dans: {log_file}[/dim]")

    def _handle_log_command(self, command: str) -> None:
        """Gère les commandes /log.

        Args:
            command: Commande complète (ex: "/log show", "/log search error")
        """
        parts = command.split(maxsplit=2)

        # Commande par défaut: show
        if len(parts) == 1:
            parts.append("show")

        subcommand = parts[1].lower()

        if subcommand == "show":
            # Afficher les nouveaux logs
            lines = self.log_viewer.show()
            if not lines:
                self.console.print("[dim]Aucun nouveau log[/dim]\n")
            else:
                self.console.print(f"\n[bold cyan]=== Nouveaux logs ({len(lines)} lignes) ===[/bold cyan]")
                for line in lines:
                    # Colorier selon le niveau de log
                    if "ERROR" in line or "CRITICAL" in line:
                        self.console.print(f"[red]{line}[/red]")
                    elif "WARNING" in line:
                        self.console.print(f"[yellow]{line}[/yellow]")
                    elif "DEBUG" in line:
                        self.console.print(f"[dim]{line}[/dim]")
                    else:
                        self.console.print(line)
                self.console.print()

        elif subcommand == "fullshow":
            # Afficher tous les logs depuis le clear
            lines = self.log_viewer.fullshow()
            if not lines:
                self.console.print("[dim]Aucun log disponible[/dim]\n")
            else:
                self.console.print(f"\n[bold cyan]=== Logs complets ({len(lines)} lignes) ===[/bold cyan]")
                for line in lines:
                    # Colorier selon le niveau de log
                    if "ERROR" in line or "CRITICAL" in line:
                        self.console.print(f"[red]{line}[/red]")
                    elif "WARNING" in line:
                        self.console.print(f"[yellow]{line}[/yellow]")
                    elif "DEBUG" in line:
                        self.console.print(f"[dim]{line}[/dim]")
                    else:
                        self.console.print(line)
                self.console.print()

        elif subcommand == "clear":
            # Marquer le point de clear
            self.log_viewer.clear()
            self.console.print("[bold green]✓[/bold green] Point de clear marqué\n")

        elif subcommand == "search":
            # Rechercher dans les logs
            if len(parts) < 3:
                self.console.print(
                    "[bold red]Erreur:[/bold red] Utilisation: /log search <texte>\n"
                )
                return

            query = parts[2]
            matches = self.log_viewer.search(query)

            if not matches:
                self.console.print(f"[dim]Aucun résultat pour '{query}'[/dim]\n")
            else:
                self.console.print(
                    f"\n[bold cyan]=== Résultats de recherche pour '{query}' "
                    f"({len(matches)} occurrence(s)) ===[/bold cyan]"
                )
                for line_num, context_lines in matches:
                    self.console.print(f"\n[bold yellow]Ligne {line_num}:[/bold yellow]")
                    for ctx_line in context_lines:
                        # Highlight la ligne contenant le match
                        if query.lower() in ctx_line.lower():
                            self.console.print(f"[bold green]> {ctx_line}[/bold green]")
                        else:
                            self.console.print(f"  {ctx_line}")
                self.console.print()

        elif subcommand == "config":
            # Configurer les paramètres
            if len(parts) < 3:
                # Afficher la config actuelle
                status = self.log_viewer.get_status()
                self.console.print("\n[bold cyan]=== Configuration /log ===[/bold cyan]")
                self.console.print(f"[dim]show:[/dim] {status['show_lines_config']} lignes")
                self.console.print(
                    f"[dim]search:[/dim] {status['search_before_config']} avant, "
                    f"{status['search_after_config']} après\n"
                )
                return

            config_parts = parts[2].split()
            if len(config_parts) < 2:
                self.console.print(
                    "[bold red]Erreur:[/bold red] Utilisation:\n"
                    "  /log config show <n>           - Configure le nombre de lignes pour show\n"
                    "  /log config search <avant> <après> - Configure le contexte pour search\n"
                )
                return

            config_type = config_parts[0].lower()

            if config_type == "show":
                try:
                    num_lines = int(config_parts[1])
                    self.log_viewer.set_config_show(num_lines)
                    self.console.print(
                        f"[bold green]✓[/bold green] Config show: {num_lines} lignes\n"
                    )
                except ValueError:
                    self.console.print(
                        "[bold red]Erreur:[/bold red] Nombre invalide\n"
                    )

            elif config_type == "search":
                if len(config_parts) < 3:
                    self.console.print(
                        "[bold red]Erreur:[/bold red] Utilisation: "
                        "/log config search <avant> <après>\n"
                    )
                    return

                try:
                    before = int(config_parts[1])
                    after = int(config_parts[2])
                    self.log_viewer.set_config_search(before, after)
                    self.console.print(
                        f"[bold green]✓[/bold green] Config search: "
                        f"{before} avant, {after} après\n"
                    )
                except ValueError:
                    self.console.print(
                        "[bold red]Erreur:[/bold red] Nombres invalides\n"
                    )

            else:
                self.console.print(
                    "[bold red]Erreur:[/bold red] Type de config invalide "
                    "(show ou search)\n"
                )

        elif subcommand == "status":
            # Afficher les statistiques
            status = self.log_viewer.get_status()
            self.console.print("\n[bold cyan]=== Statistiques des logs ===[/bold cyan]")
            self.console.print(f"[dim]Nombre total de lignes:[/dim] {status['total_lines']}")
            self.console.print(
                f"[dim]Taille du fichier:[/dim] {status['total_size']} octets "
                f"({status['total_size'] / 1024:.1f} KB)"
            )
            self.console.print(f"[dim]Config show:[/dim] {status['show_lines_config']} lignes")
            self.console.print(
                f"[dim]Config search:[/dim] {status['search_before_config']} avant, "
                f"{status['search_after_config']} après"
            )
            self.console.print(f"[dim]Position dernière lecture:[/dim] {status['last_read_position']}")
            self.console.print(f"[dim]Position dernier clear:[/dim] {status['clear_position']}\n")

        else:
            # Commande invalide
            self.console.print(
                "[bold yellow]Commandes /log disponibles:[/bold yellow]\n"
                "  /log [show]                    - Affiche les nouveaux logs\n"
                "  /log fullshow                  - Affiche tous les logs depuis le clear\n"
                "  /log clear                     - Marque un point de clear\n"
                "  /log search <texte>            - Recherche dans les logs\n"
                "  /log config                    - Affiche la configuration\n"
                "  /log config show <n>           - Configure le nombre de lignes pour show\n"
                "  /log config search <avant> <après> - Configure le contexte pour search\n"
                "  /log status                    - Affiche les statistiques\n"
            )

    async def _handle_ollama_command(self, command: str) -> None:
        """Gère les commandes /ollama.

        Args:
            command: Commande complète (ex: "/ollama list", "/ollama run qwen2.5:3b")
        """
        if not self.ollama_manager:
            self.console.print(
                "[bold red]Erreur:[/bold red] Commandes Ollama disponibles "
                "uniquement avec le backend Ollama\n"
            )
            return

        parts = command.split(maxsplit=2)

        if len(parts) < 2:
            # Afficher l'aide
            self.console.print(
                "[bold yellow]Commandes /ollama disponibles:[/bold yellow]\n"
                "  /ollama list                   - Liste tous les modèles\n"
                "  /ollama show <model>           - Info détaillées d'un modèle\n"
                "  /ollama run <model>            - Change de modèle\n"
                "  /ollama ps                     - Liste les modèles en cours\n"
                "  /ollama create <name> <path>   - Crée un modèle depuis Modelfile\n"
                "  /ollama cp <src> <dst>         - Copie un modèle\n"
                "  /ollama rm <model>             - Supprime un modèle\n"
            )
            return

        subcommand = parts[1].lower()

        try:
            if subcommand == "list":
                # Lister les modèles
                models = await self.ollama_manager.list_models()
                if not models:
                    self.console.print("[dim]Aucun modèle disponible[/dim]\n")
                else:
                    self.console.print(f"\n[bold cyan]=== Modèles disponibles ({len(models)}) ===[/bold cyan]")
                    for model in models:
                        name = model.get("name", "unknown")
                        size = model.get("size", 0)
                        size_gb = size / (1024**3)
                        modified = model.get("modified_at", "")

                        # Indiquer le modèle actuel
                        marker = "[bold green]●[/bold green]" if name == self.backend.model else " "
                        self.console.print(f"{marker} {name:30} {size_gb:6.2f} GB  {modified}")
                    self.console.print()

            elif subcommand == "show":
                # Afficher les infos d'un modèle
                if len(parts) < 3:
                    self.console.print(
                        "[bold red]Erreur:[/bold red] Utilisation: /ollama show <model>\n"
                    )
                    return

                model_name = parts[2]
                info = await self.ollama_manager.show_model(model_name)

                self.console.print(f"\n[bold cyan]=== Informations: {model_name} ===[/bold cyan]")

                # Modelfile
                if "modelfile" in info:
                    self.console.print("\n[bold]Modelfile:[/bold]")
                    for line in info["modelfile"].split("\n")[:10]:  # Limiter à 10 lignes
                        self.console.print(f"  {line}")
                    if len(info["modelfile"].split("\n")) > 10:
                        self.console.print("  [dim]...[/dim]")

                # Template
                if "template" in info:
                    self.console.print(f"\n[bold]Template:[/bold] {info['template'][:100]}...")

                # Parameters
                if "parameters" in info:
                    self.console.print(f"\n[bold]Parameters:[/bold] {info['parameters']}")

                self.console.print()

            elif subcommand == "run":
                # Changer de modèle
                if len(parts) < 3:
                    self.console.print(
                        "[bold red]Erreur:[/bold red] Utilisation: /ollama run <model>\n"
                    )
                    return

                model_name = parts[2]

                # Vérifier que le modèle existe
                models = await self.ollama_manager.list_models()
                model_names = [m.get("name") for m in models]

                if model_name not in model_names:
                    self.console.print(
                        f"[bold red]Erreur:[/bold red] Modèle '{model_name}' non trouvé\n"
                        f"[dim]Modèles disponibles: {', '.join(model_names)}[/dim]\n"
                    )
                    return

                # Changer le modèle du backend
                if isinstance(self.backend, (OllamaBackend, AlbertBackend)):
                    old_model = self.backend.model
                    self.backend.set_model(model_name)
                    self.console.print(
                        f"[bold green]✓[/bold green] Modèle changé: "
                        f"{old_model} → {model_name}\n"
                    )
                    logger.info(f"Model switched from {old_model} to {model_name}")

            elif subcommand == "ps":
                # Lister les modèles en cours
                models = await self.ollama_manager.list_running()
                if not models:
                    self.console.print("[dim]Aucun modèle en cours d'exécution[/dim]\n")
                else:
                    self.console.print(
                        f"\n[bold cyan]=== Modèles en cours ({len(models)}) ===[/bold cyan]"
                    )
                    for model in models:
                        name = model.get("name", "unknown")
                        size = model.get("size", 0)
                        size_gb = size / (1024**3)
                        self.console.print(f"  {name:30} {size_gb:6.2f} GB")
                    self.console.print()

            elif subcommand == "create":
                # Créer un modèle depuis Modelfile
                if len(parts) < 3:
                    self.console.print(
                        "[bold red]Erreur:[/bold red] Utilisation: "
                        "/ollama create <nom> <chemin_modelfile>\n"
                    )
                    return

                create_parts = parts[2].split(maxsplit=1)
                if len(create_parts) < 2:
                    self.console.print(
                        "[bold red]Erreur:[/bold red] Chemin du Modelfile manquant\n"
                    )
                    return

                model_name = create_parts[0]
                modelfile_path = Path(create_parts[1])

                self.console.print(
                    f"\n[bold cyan]Création du modèle '{model_name}'...[/bold cyan]"
                )

                # Stream les messages de progression
                async for status in self.ollama_manager.create_model(
                    model_name, path=modelfile_path
                ):
                    self.console.print(f"  {status}")

                self.console.print(
                    f"[bold green]✓[/bold green] Modèle '{model_name}' créé avec succès\n"
                )

            elif subcommand == "cp":
                # Copier un modèle
                if len(parts) < 3:
                    self.console.print(
                        "[bold red]Erreur:[/bold red] Utilisation: "
                        "/ollama cp <source> <destination>\n"
                    )
                    return

                cp_parts = parts[2].split(maxsplit=1)
                if len(cp_parts) < 2:
                    self.console.print(
                        "[bold red]Erreur:[/bold red] Destination manquante\n"
                    )
                    return

                source = cp_parts[0]
                destination = cp_parts[1]

                await self.ollama_manager.copy_model(source, destination)
                self.console.print(
                    f"[bold green]✓[/bold green] Modèle copié: {source} → {destination}\n"
                )

            elif subcommand == "rm":
                # Supprimer un modèle
                if len(parts) < 3:
                    self.console.print(
                        "[bold red]Erreur:[/bold red] Utilisation: /ollama rm <model>\n"
                    )
                    return

                model_name = parts[2]

                # Demander confirmation
                confirm = input(
                    f"Supprimer le modèle '{model_name}' ? (yes/no): "
                ).lower()
                if confirm not in ["yes", "y"]:
                    self.console.print("[dim]Annulé[/dim]\n")
                    return

                await self.ollama_manager.delete_model(model_name)
                self.console.print(
                    f"[bold green]✓[/bold green] Modèle '{model_name}' supprimé\n"
                )

            else:
                # Commande invalide
                self.console.print(
                    f"[bold red]Erreur:[/bold red] Commande inconnue: {subcommand}\n"
                )

        except Exception as e:
            # Échapper le message d'erreur pour éviter les conflits de markup
            error_display = str(e).replace("[", "\\[").replace("]", "\\]")
            self.console.print(f"\n[bold red]Erreur:[/bold red] {error_display}\n")
            logger.error(f"Ollama command error: {e}", exc_info=True)

    async def _handle_albert_command(self, command: str) -> None:
        """Gère les commandes /albert.

        Args:
            command: Commande complète (ex: "/albert list", "/albert run <model>")
        """
        if not self.albert_manager:
            self.console.print(
                "[bold red]Erreur:[/bold red] Commandes Albert disponibles "
                "uniquement avec le backend Albert\n"
            )
            return

        parts = command.split(maxsplit=2)

        if len(parts) < 2:
            # Afficher l'aide
            self.console.print(
                "[bold yellow]Commandes /albert disponibles:[/bold yellow]\n"
                "  /albert list            - Liste tous les modèles disponibles\n"
                "  /albert show <model>    - Informations détaillées d'un modèle\n"
                "  /albert run <model>     - Change de modèle\n"
                "  /albert usage           - Affiche vos statistiques d'utilisation\n"
                "  /albert me              - Affiche vos informations de compte\n"
            )
            return

        subcommand = parts[1].lower()

        try:
            if subcommand == "list":
                # Lister les modèles
                models = await self.albert_manager.list_models()
                if not models:
                    self.console.print("[dim]Aucun modèle disponible[/dim]\n")
                else:
                    self.console.print(
                        f"\n[bold cyan]=== Modèles disponibles ({len(models)}) ===[/bold cyan]"
                    )
                    for model in models:
                        model_id = model.get("id", "unknown")
                        owned_by = model.get("owned_by", "")
                        created = model.get("created", 0)

                        # Indiquer le modèle actuel
                        marker = (
                            "[bold green]●[/bold green]"
                            if model_id == self.backend.model
                            else " "
                        )
                        self.console.print(f"{marker} {model_id:50} {owned_by}")
                    self.console.print()

            elif subcommand == "show":
                # Afficher les infos d'un modèle
                if len(parts) < 3:
                    self.console.print(
                        "[bold red]Erreur:[/bold red] Utilisation: /albert show <model>\n"
                    )
                    return

                model_id = parts[2]
                info = await self.albert_manager.get_model_info(model_id)

                self.console.print(f"\n[bold cyan]=== Informations: {model_id} ===[/bold cyan]")

                # Afficher les informations disponibles
                if "id" in info:
                    self.console.print(f"[bold]ID:[/bold] {info['id']}")
                if "object" in info:
                    self.console.print(f"[bold]Type:[/bold] {info['object']}")
                if "owned_by" in info:
                    self.console.print(f"[bold]Propriétaire:[/bold] {info['owned_by']}")
                if "created" in info:
                    from datetime import datetime

                    created_dt = datetime.fromtimestamp(info["created"])
                    self.console.print(
                        f"[bold]Créé:[/bold] {created_dt.strftime('%Y-%m-%d %H:%M:%S')}"
                    )

                # Context window
                if "context_window" in info:
                    self.console.print(
                        f"[bold]Context window:[/bold] {info['context_window']} tokens"
                    )

                self.console.print()

            elif subcommand == "run":
                # Changer de modèle
                if len(parts) < 3:
                    self.console.print(
                        "[bold red]Erreur:[/bold red] Utilisation: /albert run <model>\n"
                    )
                    return

                model_id = parts[2]

                # Vérifier que le modèle existe
                models = await self.albert_manager.list_models()
                model_ids = [m.get("id") for m in models]

                if model_id not in model_ids:
                    self.console.print(
                        f"[bold red]Erreur:[/bold red] Modèle '{model_id}' non trouvé\n"
                    )
                    self.console.print(
                        "[dim]Modèles disponibles:[/dim]"
                    )
                    for mid in model_ids[:10]:  # Limiter à 10
                        self.console.print(f"  - {mid}")
                    if len(model_ids) > 10:
                        self.console.print(f"  ... et {len(model_ids) - 10} autres")
                    self.console.print()
                    return

                # Changer le modèle du backend
                if isinstance(self.backend, AlbertBackend):
                    old_model = self.backend.model
                    self.backend.set_model(model_id)
                    self.console.print(
                        f"[bold green]✓[/bold green] Modèle changé: "
                        f"{old_model} → {model_id}\n"
                    )
                    logger.info(f"Model switched from {old_model} to {model_id}")

            elif subcommand == "usage":
                # Afficher les statistiques d'utilisation
                usage = await self.albert_manager.get_usage()

                self.console.print("\n[bold cyan]=== Statistiques d'utilisation ===[/bold cyan]")

                if "total_tokens" in usage:
                    self.console.print(f"[bold]Total tokens:[/bold] {usage['total_tokens']}")
                if "total_requests" in usage:
                    self.console.print(
                        f"[bold]Total requêtes:[/bold] {usage['total_requests']}"
                    )
                if "total_cost" in usage:
                    self.console.print(f"[bold]Coût total:[/bold] {usage['total_cost']}")

                self.console.print()

            elif subcommand == "me":
                # Afficher les informations utilisateur
                user_info = await self.albert_manager.get_user_info()

                self.console.print(
                    "\n[bold cyan]=== Informations de compte ===[/bold cyan]"
                )

                if "email" in user_info:
                    self.console.print(f"[bold]Email:[/bold] {user_info['email']}")
                if "organization" in user_info:
                    self.console.print(
                        f"[bold]Organisation:[/bold] {user_info['organization']}"
                    )
                if "quota" in user_info:
                    quota = user_info["quota"]
                    self.console.print(f"[bold]Quota:[/bold] {quota}")

                self.console.print()

            else:
                # Commande invalide
                self.console.print(
                    f"[bold red]Erreur:[/bold red] Commande inconnue: {subcommand}\n"
                )

        except Exception as e:
            # Échapper le message d'erreur pour éviter les conflits de markup
            error_display = str(e).replace("[", "\\[").replace("]", "\\]")
            self.console.print(f"\n[bold red]Erreur:[/bold red] {error_display}\n")
            logger.error(f"Albert command error: {e}", exc_info=True)

    def _handle_prompt_command(self, command: str) -> None:
        """Gère les commandes /prompt.

        Args:
            command: Commande complète (ex: "/prompt λ", "/prompt list")
        """
        parts = command.split(maxsplit=1)

        if len(parts) < 2:
            # Afficher le prompt actuel
            self.console.print(
                f"\n[bold cyan]Prompt actuel:[/bold cyan] [green]{self.prompt_manager.prompt_text}[/green]\n"
            )
            return

        subcommand = parts[1]

        # Commandes spéciales
        if subcommand == "list":
            # Afficher les variantes prédéfinies
            variants = self.prompt_manager.get_prompt_variants()
            self.console.print("\n[bold cyan]=== Prompts prédéfinis ===[/bold cyan]")
            for name, symbol in variants.items():
                current = "●" if symbol == self.prompt_manager.prompt_text else " "
                self.console.print(f"{current} {name:12} → {symbol}")
            self.console.print(
                "\n[dim]Usage: /prompt <nom> ou /prompt <texte_personnalisé>[/dim]\n"
            )

        elif subcommand == "reset":
            # Réinitialiser au prompt par défaut
            self.prompt_manager.set_prompt(">")
            self.console.print("[bold green]✓[/bold green] Prompt réinitialisé: >\n")

        elif subcommand == "toggle":
            # Activer/désactiver la barre d'info
            enabled = self.prompt_manager.toggle_info_bar()
            status = "activée" if enabled else "désactivée"
            self.console.print(
                f"[bold green]✓[/bold green] Barre d'information {status}\n"
            )

        else:
            # Vérifier si c'est un nom de variante prédéfinie
            variants = self.prompt_manager.get_prompt_variants()
            if subcommand in variants:
                symbol = variants[subcommand]
                self.prompt_manager.set_prompt(symbol)
                self.console.print(
                    f"[bold green]✓[/bold green] Prompt changé: {self.prompt_manager.prompt_text}\n"
                )
            else:
                # Utiliser le texte personnalisé directement
                self.prompt_manager.set_prompt(subcommand)
                self.console.print(
                    f"[bold green]✓[/bold green] Prompt personnalisé: {self.prompt_manager.prompt_text}\n"
                )

    def _handle_model_command(self) -> None:
        """Affiche le backend actif et le modèle utilisé."""
        self.console.print("\n[bold cyan]=== Modèle actif ===[/bold cyan]")
        self.console.print(f"[dim]Backend:[/dim] [bold]{self.config.default_backend}[/bold]")

        if self.backend:
            backend_config = self.config.backends[self.config.default_backend]
            self.console.print(f"[dim]Modèle:[/dim] [bold green]{backend_config.model}[/bold green]")
            self.console.print(f"[dim]URL:[/dim] {backend_config.url}")
            self.console.print(f"[dim]Temperature:[/dim] {backend_config.temperature}")
            self.console.print(f"[dim]Max tokens:[/dim] {backend_config.max_tokens}")
            self.console.print(f"[dim]Timeout:[/dim] {backend_config.timeout}s")
        else:
            self.console.print("[yellow]Aucun backend initialisé[/yellow]")

        self.console.print()

    async def _handle_info_command(self) -> None:
        """Affiche les informations sur la session et la conversation en cours."""
        stats = await self.db.get_session_stats()

        if not stats:
            self.console.print("[yellow]Aucune session active[/yellow]\n")
            return

        from datetime import datetime

        self.console.print("\n[bold cyan]=== Informations de Session ===")

        # Informations générales
        created = datetime.fromtimestamp(stats["created_at"]).strftime("%Y-%m-%d %H:%M:%S")
        updated = datetime.fromtimestamp(stats["updated_at"]).strftime("%Y-%m-%d %H:%M:%S")

        self.console.print(f"[dim]Session ID:[/dim] {stats['session_id'][:8]}...")
        self.console.print(f"[dim]Backend:[/dim] {stats['backend']}")
        self.console.print(f"[dim]Modèle:[/dim] {stats['model']}")
        self.console.print(f"[dim]Créée:[/dim] {created}")
        self.console.print(f"[dim]Mise à jour:[/dim] {updated}")

        # Statistiques des messages
        self.console.print("\n[bold cyan]=== Statistiques de Conversation ===[/bold cyan]")
        self.console.print(f"[dim]Messages totaux:[/dim] [bold]{stats['message_count']}[/bold]")
        self.console.print(f"  • Utilisateur: {stats['user_messages']}")
        self.console.print(f"  • Assistant: {stats['assistant_messages']}")

        # Statistiques de taille
        total_chars = stats["total_chars"]
        total_kb = total_chars / 1024
        self.console.print(f"[dim]Taille totale:[/dim] [bold]{total_chars:,}[/bold] caractères ({total_kb:.1f} KB)")

        # Tokens (si disponible)
        if stats["total_tokens"] and stats["total_tokens"] > 0:
            total_tokens = stats["total_tokens"]
            self.console.print(f"[dim]Tokens utilisés:[/dim] [bold]{total_tokens:,}[/bold]")

            # Estimation du coût (pour info, avec Albert)
            if stats["backend"] == "albert":
                # Tarif estimé Albert (à ajuster selon la réalité)
                cost_estimate = (total_tokens / 1_000_000) * 0.5  # ~0.5€/M tokens
                self.console.print(f"[dim]Coût estimé:[/dim] ~{cost_estimate:.4f}€")

        # Messages en mémoire vs base de données
        in_memory = len(self.messages)
        self.console.print(f"\n[dim]En mémoire:[/dim] {in_memory} messages")
        self.console.print(f"[dim]En base:[/dim] {stats['message_count']} messages")

        # Compressions
        if stats["compression_count"] > 0:
            self.console.print(f"[dim]Compressions effectuées:[/dim] {stats['compression_count']}")

        self.console.print()

    async def _handle_compress_command(self, command: str = "/compress") -> None:
        """Compresse la conversation en la résumant avec le LLM.

        Args:
            command: Commande complète (ex: "/compress", "/compress --max 10", "/compress --keep 5")
        """
        if not self.backend or not self.agent:
            self.console.print("[yellow]Backend non initialisé[/yellow]\n")
            return

        # Parser les options
        parts = command.split()
        keep_messages: int | None = None  # Nombre de messages à garder

        # Analyser les options
        i = 1  # Commencer après "/compress"
        while i < len(parts):
            arg = parts[i]
            if arg in ["--max", "-m", "--keep"]:
                # Récupérer la valeur
                if i + 1 >= len(parts):
                    self.console.print(f"[red]Erreur: {arg} nécessite une valeur[/red]\n")
                    self.console.print("[dim]Usage: /compress [--max N | -m N | --keep N][/dim]\n")
                    return
                try:
                    keep_messages = int(parts[i + 1])
                    if keep_messages < 1:
                        self.console.print("[red]Erreur: La valeur doit être >= 1[/red]\n")
                        return
                    i += 2
                except ValueError:
                    self.console.print(f"[red]Erreur: {arg} nécessite un nombre entier[/red]\n")
                    return
            else:
                self.console.print(f"[red]Erreur: Option inconnue '{arg}'[/red]\n")
                self.console.print("[dim]Usage: /compress [--max N | -m N | --keep N][/dim]\n")
                return

        # Vérifier qu'il y a assez de messages
        if len(self.messages) < 4:
            self.console.print(
                "[yellow]Pas assez de messages à compresser (minimum 4)[/yellow]\n"
            )
            return

        # Si keep_messages est spécifié et >= nombre de messages actuels, pas besoin de compresser
        if keep_messages and keep_messages >= len(self.messages):
            self.console.print(
                f"[yellow]Déjà {len(self.messages)} messages (≤ {keep_messages}), compression inutile[/yellow]\n"
            )
            return

        self.console.print(
            "\n[bold yellow]⚡ Compression de la conversation en cours...[/bold yellow]"
        )
        if keep_messages:
            self.console.print(f"[dim]Résumé des anciens messages, conservation des {keep_messages} derniers[/dim]\n")
        else:
            self.console.print("[dim]Le LLM va résumer toute la conversation pour économiser des tokens[/dim]\n")

        # Statistiques avant compression
        original_count = len(self.messages)
        original_chars = sum(len(msg.content or "") for msg in self.messages)

        # Déterminer quels messages compresser
        if keep_messages and keep_messages < len(self.messages):
            # Garder les N derniers, compresser les autres
            messages_to_compress = self.messages[:-keep_messages]
            messages_to_keep = self.messages[-keep_messages:]
        else:
            # Compresser tous les messages
            messages_to_compress = self.messages
            messages_to_keep = []

        # Créer un prompt pour le résumé
        conversation_text = []
        for msg in messages_to_compress:
            role = "Utilisateur" if msg.role == "user" else "Assistant"
            conversation_text.append(f"{role}: {msg.content}")

        summary_prompt = f"""Résume cette conversation de manière concise mais complète.
Conserve tous les points importants, décisions, et contexte nécessaire.
Le résumé sera utilisé comme contexte pour continuer la conversation.

Conversation à résumer:
{chr(10).join(conversation_text)}

Résumé structuré:"""

        try:
            # Demander le résumé au LLM
            summary_message = Message(role="user", content=summary_prompt)
            response = await self.backend.chat(
                messages=[summary_message],
                tools=None,  # Pas besoin de tools pour un résumé
            )

            summary_content = response.content or ""

            if not summary_content:
                self.console.print("[red]Erreur: Le LLM n'a pas généré de résumé[/red]\n")
                return

            # Créer un message système avec le résumé
            compressed_message = Message(
                role="system",
                content=f"[Résumé de la conversation précédente]\n\n{summary_content}\n\n[Fin du résumé - La conversation continue normalement]",
            )

            # Remplacer les messages par: résumé + messages à garder
            self.messages = [compressed_message] + messages_to_keep

            # Statistiques après compression
            compressed_count = len(self.messages)
            compressed_chars = sum(len(msg.content or "") for msg in self.messages)

            # Sauvegarder la compression dans la DB
            await self.db.save_compression(
                original_count=original_count,
                compressed_count=compressed_count,
                summary=summary_content,
            )

            # Afficher les résultats
            self.console.print("[bold green]✓ Compression réussie ![/bold green]\n")
            self.console.print("[bold cyan]=== Résultat de la Compression ===[/bold cyan]")
            self.console.print(
                f"[dim]Messages:[/dim] {original_count} → [bold green]{compressed_count}[/bold green] "
                f"([bold]-{original_count - compressed_count}[/bold], "
                f"{((original_count - compressed_count) / original_count * 100):.1f}%)"
            )
            self.console.print(
                f"[dim]Caractères:[/dim] {original_chars:,} → [bold green]{compressed_chars:,}[/bold green] "
                f"([bold]-{original_chars - compressed_chars:,}[/bold], "
                f"{((original_chars - compressed_chars) / original_chars * 100):.1f}%)"
            )
            if messages_to_keep:
                self.console.print(
                    f"[dim]Messages conservés:[/dim] {len(messages_to_keep)} derniers messages"
                )
            self.console.print(
                f"\n[dim][italic]Le résumé est maintenant en mémoire. "
                f"Vous pouvez continuer la conversation normalement.[/italic][/dim]\n"
            )

        except Exception as e:
            # Échapper le message d'erreur pour éviter les conflits de markup
            error_display = str(e).replace("[", "\\[").replace("]", "\\]")
            self.console.print(f"[red]Erreur lors de la compression: {error_display}[/red]\n")
            logger.error(f"Compression error: {e}", exc_info=True)

    async def _handle_shell_command(self, command: str) -> None:
        """Exécute directement une commande shell.

        Args:
            command: Commande complète (ex: "/! ls -l", "/! pwd")
        """
        # Extraire la commande après "/!"
        shell_cmd = command[2:].strip()

        if not shell_cmd:
            self.console.print("[yellow]Usage:[/yellow] /! <commande_shell>")
            self.console.print("[dim]Exemple: /! ls -l[/dim]\n")
            return

        self.console.print(f"\n[dim]$ {shell_cmd}[/dim]")

        try:
            import subprocess

            # Exécuter la commande
            result = subprocess.run(
                shell_cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )

            # Afficher la sortie
            if result.stdout:
                self.console.print(result.stdout)

            # Afficher les erreurs en rouge
            if result.stderr:
                self.console.print(f"[red]{result.stderr}[/red]")

            # Afficher le code de retour si différent de 0
            if result.returncode != 0:
                self.console.print(f"[yellow]Code de retour: {result.returncode}[/yellow]")

        except subprocess.TimeoutExpired:
            self.console.print("[red]Erreur: Timeout (30s dépassé)[/red]\n")
        except Exception as e:
            # Échapper le message d'erreur pour éviter les conflits de markup
            error_display = str(e).replace("[", "\\[").replace("]", "\\]")
            self.console.print(f"[red]Erreur: {error_display}[/red]\n")

        self.console.print()


async def run_chat(config_path: Path | None = None) -> None:
    """Lance l'application de chat.

    Args:
        config_path: Chemin optionnel vers le fichier de config
    """
    # Charger la configuration
    config = load_config(config_path)

    # Créer et lancer l'application
    app = ChatApp(config)
    await app.initialize()
    await app.run()
