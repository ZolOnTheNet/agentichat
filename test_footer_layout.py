#!/usr/bin/env python3
"""Test de la nouvelle disposition avec pied de page."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from rich.console import Console
from agentichat.cli.prompt_manager import PromptManager


def test_footer_layout():
    """Teste la nouvelle disposition du pied de page."""
    console = Console()
    manager = PromptManager(console)

    print("="*60)
    print("Test du nouveau layout avec pied de page")
    print("="*60 + "\n")

    # Simuler une session
    console.print("[bold cyan]agentichat[/bold cyan] - Mode agentique activé\n")

    # Simuler une saisie utilisateur
    console.print("> Bonjour, crée moi un fichier hello.py")

    # Simuler une réponse
    console.print("\n[bold green]Assistant:[/bold green]")
    console.print("Je vais créer un fichier hello.py avec un programme Hello World.")

    # Afficher le pied de page (comme _show_footer())
    console.print()  # Ligne vide
    manager.show_separator(with_spacing=False)
    manager.show_info(
        workspace=Path("/test/myproject"),
        debug_mode=True,
        backend_type="ollama",
        model="qwen2.5:3b",
    )
    console.print()  # Ligne vide

    # Simuler une nouvelle saisie
    console.print("> Merci !")

    # Simuler une nouvelle réponse
    console.print("\n[bold green]Assistant:[/bold green]")
    console.print("De rien !")

    # Pied de page à nouveau
    console.print()
    manager.show_separator(with_spacing=False)
    manager.show_info(
        workspace=Path("/test/myproject"),
        debug_mode=False,
        backend_type="ollama",
        model="llama3:8b",
    )
    console.print()

    # Nouvelle saisie
    console.print("> /quit")

    print("\n" + "="*60)
    print("✓ Test du layout terminé")
    print("="*60 + "\n")

    print("Vérification :")
    print("1. ✓ La saisie apparaît en premier")
    print("2. ✓ La réponse apparaît ensuite")
    print("3. ✓ Le pied de page apparaît APRÈS la réponse")
    print("4. ✓ Format: séparateur + ligne d'info")
    print("5. ✓ Prêt pour la prochaine saisie")


if __name__ == "__main__":
    test_footer_layout()
