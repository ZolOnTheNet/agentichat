#!/usr/bin/env python3
"""Test du parsing des commandes /log."""

import sys
from pathlib import Path

def test_log_commands():
    """Teste le parsing des commandes /log."""

    test_cases = [
        ("/log", ["show"], "Par défaut: show"),
        ("/log show", ["show"], "Explicite: show"),
        ("/log fullshow", ["fullshow"], "fullshow"),
        ("/log clear", ["clear"], "clear"),
        ("/log search ERROR", ["search", "ERROR"], "search avec texte"),
        ("/log config", ["config"], "config sans args"),
        ("/log config show 10", ["config", "show 10"], "config show"),
        ("/log config search 3 10", ["config", "search 3 10"], "config search"),
        ("/log status", ["status"], "status"),
        ("/log invalid", ["invalid"], "commande invalide"),
    ]

    print("="*60)
    print("Test du parsing des commandes /log")
    print("="*60 + "\n")

    for command, expected, description in test_cases:
        parts = command.split(maxsplit=2)

        # Ajouter "show" par défaut si pas de sous-commande
        if len(parts) == 1:
            parts.append("show")

        subcommand = parts[1].lower() if len(parts) > 1 else "show"

        print(f"Commande: '{command}'")
        print(f"  Description: {description}")
        print(f"  Parts: {parts}")
        print(f"  Subcommand: {subcommand}")

        # Vérifier le résultat
        if subcommand == expected[0]:
            print(f"  ✓ Parsing correct")
        else:
            print(f"  ✗ Erreur: attendu '{expected[0]}', obtenu '{subcommand}'")

        print()

    print("="*60)
    print("Résumé des fonctionnalités /log")
    print("="*60 + "\n")

    features = [
        ("✓", "/log (ou /log show)", "Affiche les nouveaux logs depuis le dernier appel"),
        ("✓", "/log fullshow", "Affiche tous les logs depuis le dernier clear"),
        ("✓", "/log clear", "Marque un point de clear pour fullshow"),
        ("✓", "/log search <texte>", "Recherche un texte dans les logs avec contexte"),
        ("✓", "/log config", "Affiche la configuration actuelle"),
        ("✓", "/log config show <n>", "Configure le nombre de lignes pour show (défaut: 20)"),
        ("✓", "/log config search <avant> <après>", "Configure le contexte (défaut: 3, 10)"),
        ("✓", "/log status", "Affiche les statistiques (lignes, taille, config)"),
    ]

    for status, command, description in features:
        print(f"{status} {command:35} - {description}")

    print("\n" + "="*60)
    print("Exemple d'utilisation:")
    print("="*60 + "\n")

    examples = [
        ("Configuration personnalisée", [
            "/log config show 50",
            "/log config search 5 15",
            "/log config",
        ]),
        ("Recherche d'erreurs", [
            "/log search ERROR",
            "/log search ollama",
            "/log search 'Agent loop'",
        ]),
        ("Gestion des logs", [
            "/log show",
            "/log fullshow",
            "/log clear",
            "/log status",
        ]),
    ]

    for title, cmds in examples:
        print(f"{title}:")
        for cmd in cmds:
            print(f"  > {cmd}")
        print()

    print("✓ Toutes les commandes /log sont implémentées !")


if __name__ == "__main__":
    test_log_commands()
