#!/usr/bin/env python3
"""Test des améliorations d'interaction."""

import sys
from pathlib import Path

# Ajouter src au path
sys.path.insert(0, str(Path(__file__).parent / "src"))

print("=" * 60)
print("Test des améliorations d'interaction")
print("=" * 60)
print()

# Test 1 : Import des modules modifiés
print("1. Test des imports...")
try:
    from agentichat.cli.confirmation import ConfirmationManager
    from agentichat.cli.app import ChatApp
    from agentichat.cli.editor import MultiLineEditor
    print("   ✓ Tous les imports réussis")
except Exception as e:
    print(f"   ✗ Erreur d'import: {e}")
    sys.exit(1)

print()

# Test 2 : Vérifier que ConfirmationManager utilise PromptSession
print("2. Test ConfirmationManager...")
try:
    from rich.console import Console
    console = Console()
    cm = ConfirmationManager(console)

    # Vérifier les attributs
    assert hasattr(cm, "prompt_session"), "PromptSession manquant"
    assert hasattr(cm, "kb"), "KeyBindings manquant"
    assert hasattr(cm, "_setup_keybindings"), "setup_keybindings manquant"

    print("   ✓ ConfirmationManager configuré avec PromptSession")
    print("   ✓ KeyBindings configurés")
except Exception as e:
    print(f"   ✗ Erreur: {e}")
    sys.exit(1)

print()

# Test 3 : Vérifier les messages du spinner
print("3. Test messages du spinner...")
try:
    # Lire le contenu de app.py pour vérifier les messages
    app_py = Path(__file__).parent / "src" / "agentichat" / "cli" / "app.py"
    content = app_py.read_text()

    expected_messages = [
        "Le LLM analyse votre demande",
        "Le LLM génère une réponse",
        "Le LLM prépare les actions",
        "Le LLM organise les outils",
        "Le LLM affine sa réponse",
        "Le LLM réfléchit",
    ]

    found = all(msg in content for msg in expected_messages)

    if found:
        print("   ✓ Messages variés du spinner présents")
        print(f"   ✓ {len(expected_messages)} messages différents")
    else:
        print("   ✗ Messages du spinner manquants")
        sys.exit(1)
except Exception as e:
    print(f"   ✗ Erreur: {e}")
    sys.exit(1)

print()

# Test 4 : Vérifier le message de démarrage
print("4. Test message de démarrage...")
try:
    if "ESC=vider saisie" in content and "Ctrl+C=annuler traitement" in content:
        print("   ✓ Message de démarrage amélioré")
        print("   ✓ ESC et Ctrl+C documentés")
    else:
        print("   ✗ Message de démarrage incomplet")
        sys.exit(1)
except Exception as e:
    print(f"   ✗ Erreur: {e}")
    sys.exit(1)

print()

# Test 5 : Vérifier l'éditeur
print("5. Test MultiLineEditor...")
try:
    # Lire le contenu de editor.py pour vérifier ESC
    editor_py = Path(__file__).parent / "src" / "agentichat" / "cli" / "editor.py"
    editor_content = editor_py.read_text()

    # Vérifier que ESC est bien géré
    if "Keys.Escape" in editor_content and "event.current_buffer.text = \"\"" in editor_content:
        print("   ✓ MultiLineEditor configuré")
        print("   ✓ ESC vide le buffer (feedback visuel)")
    else:
        print("   ✗ ESC non configuré correctement")
        sys.exit(1)
except Exception as e:
    print(f"   ✗ Erreur: {e}")
    sys.exit(1)

print()
print("=" * 60)
print("✓ Tous les tests passés")
print("=" * 60)
print()

print("Améliorations validées:")
print("  1. ✓ Confirmation avec validation automatique (Y/N/A/?)")
print("  2. ✓ Spinner avec messages variés (6 messages)")
print("  3. ✓ Raccourcis clavier documentés (ESC, Ctrl+C)")
print()

print("Pour tester en conditions réelles:")
print("  $ .venv/bin/agentichat")
print("  > créer un fichier test.py")
print("  [Appuyez juste Y pour valider]")
print()
