"""Point d'entrée principal de agentichat."""

import asyncio
from pathlib import Path

import click

from .cli.app import run_chat
from .config.loader import load_config


@click.group(invoke_without_command=True)
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True, path_type=Path),
    help="Chemin vers le fichier de configuration",
)
@click.pass_context
def cli(ctx: click.Context, config: Path | None) -> None:
    """agentichat - CLI agentique pour interagir avec des LLMs.

    Exemples:

        agentichat                 Mode interactif
        agentichat config show     Affiche la configuration
    """
    # Si aucune sous-commande n'est spécifiée, lancer le mode interactif
    if ctx.invoked_subcommand is None:
        asyncio.run(run_chat(config))


@cli.group()
def config() -> None:
    """Gestion de la configuration."""
    pass


@config.command("show")
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True, path_type=Path),
    help="Chemin vers le fichier de configuration",
)
def config_show(config: Path | None) -> None:
    """Affiche la configuration actuelle."""
    try:
        cfg = load_config(config)

        click.echo("\n=== Configuration agentichat ===\n")
        click.echo(f"Backend par défaut: {cfg.default_backend}")
        click.echo(f"Répertoire de données: {cfg.data_dir}")
        click.echo(f"Port proxy: {cfg.proxy_port}")
        click.echo(f"Max iterations: {cfg.max_iterations}")

        click.echo("\n--- Backends configurés ---")
        for name, backend in cfg.backends.items():
            marker = "(*)" if name == cfg.default_backend else "   "
            click.echo(f"{marker} {name}:")
            click.echo(f"      Type: {backend.type}")
            click.echo(f"      URL: {backend.url}")
            click.echo(f"      Modèle: {backend.model}")
            click.echo(f"      Timeout: {backend.timeout}s")
            click.echo(f"      Max tokens: {backend.max_tokens}")
            click.echo(f"      Température: {backend.temperature}")

        click.echo("\n--- Sandbox ---")
        click.echo(f"Taille max fichier: {cfg.sandbox.max_file_size} octets")
        click.echo(f"Chemins bloqués: {len(cfg.sandbox.blocked_paths)}")

        click.echo("\n--- Confirmations ---")
        click.echo(
            f"Opérations texte: "
            f"{'activées' if cfg.confirmations.text_operations else 'désactivées'}"
        )
        click.echo(
            f"Commandes shell: "
            f"{'activées' if cfg.confirmations.shell_commands else 'désactivées'}"
        )
        click.echo()

    except Exception as e:
        click.echo(f"Erreur: {e}", err=True)
        raise click.Abort()


@cli.command()
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True, path_type=Path),
    help="Chemin vers le fichier de configuration",
)
def chat(config: Path | None) -> None:
    """Lance le mode chat interactif."""
    asyncio.run(run_chat(config))


@cli.group()
def proxy() -> None:
    """Gestion du daemon proxy (Phase 2+)."""
    click.echo("Commandes proxy non encore implémentées (Phase 2)")


if __name__ == "__main__":
    cli()
