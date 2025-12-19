#!/usr/bin/env python3
"""Test du PromptManager."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from rich.console import Console
from agentichat.cli.prompt_manager import PromptManager


def test_prompt_manager():
    """Teste le PromptManager."""
    print("="*60)
    print("Test du PromptManager")
    print("="*60 + "\n")

    console = Console()
    manager = PromptManager(console)

    # Test 1: Prompt par défaut
    print("1. Test prompt par défaut")
    prompt = manager.get_prompt()
    print(f"   Prompt: '{prompt}'")
    assert prompt == "> ", "Le prompt par défaut devrait être '> '"
    print("   ✓ Test réussi\n")

    # Test 2: Changer le prompt
    print("2. Test changement de prompt")
    manager.set_prompt("λ")
    prompt = manager.get_prompt()
    print(f"   Nouveau prompt: '{prompt}'")
    assert prompt == "λ ", "Le prompt devrait être 'λ '"
    print("   ✓ Test réussi\n")

    # Test 3: Variantes prédéfinies
    print("3. Test variantes prédéfinies")
    variants = manager.get_prompt_variants()
    print(f"   Nombre de variantes: {len(variants)}")
    for name, symbol in list(variants.items())[:3]:
        print(f"     - {name:12} → {symbol}")
    assert len(variants) > 0, "Il devrait y avoir des variantes"
    assert "classic" in variants, "La variante 'classic' devrait exister"
    assert "lambda" in variants, "La variante 'lambda' devrait exister"
    print("   ✓ Test réussi\n")

    # Test 4: Barre d'information
    print("4. Test barre d'information")
    print("   Affichage:")
    manager.show_info(
        workspace=Path("/home/user/projects/test"),
        debug_mode=True,
        backend_type="ollama",
        model="qwen2.5:3b",
    )
    print("   ✓ Test réussi\n")

    # Test 5: Séparateur
    print("5. Test séparateur")
    print("   Affichage:")
    manager.show_separator()
    print("   ✓ Test réussi\n")

    # Test 6: Toggle barre d'info
    print("6. Test toggle barre d'info")
    enabled = manager.toggle_info_bar()
    print(f"   État après toggle: {enabled}")
    assert enabled == False, "La barre devrait être désactivée"

    enabled = manager.toggle_info_bar()
    print(f"   État après 2e toggle: {enabled}")
    assert enabled == True, "La barre devrait être activée"
    print("   ✓ Test réussi\n")

    # Test 7: Tous les prompts prédéfinis
    print("7. Test affichage de tous les prompts")
    console.print("\n[bold cyan]=== Prompts disponibles ===[/bold cyan]")
    for name, symbol in variants.items():
        console.print(f"  {name:12} → {symbol}")
    print("   ✓ Test réussi\n")

    print("="*60)
    print("✓ Tous les tests sont passés avec succès !")
    print("="*60 + "\n")

    # Démonstration visuelle
    print("="*60)
    print("Démonstration visuelle")
    print("="*60 + "\n")

    for name, symbol in list(variants.items())[:5]:
        manager.set_prompt(symbol)
        manager.show_info(
            workspace=Path("/test/workspace"),
            debug_mode=name == "classic",
            backend_type="ollama",
            model="test-model:latest",
        )
        console.print(f"{manager.get_prompt()}[dim]Exemple de saisie utilisateur...[/dim]")
        console.print("\n[bold green]Assistant:[/bold green] Ceci est une réponse exemple.")
        manager.show_separator()


if __name__ == "__main__":
    test_prompt_manager()
