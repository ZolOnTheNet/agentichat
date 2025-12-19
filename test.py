#!/usr/bin/env python3
"""
Fichier de test simple pour agentichat.

Ce programme affiche un message de bienvenue et calcule
quelques opérations mathématiques basiques.
"""


def calculer_somme(a: int, b: int) -> int:
    """Calcule la somme de deux nombres.

    Args:
        a: Premier nombre
        b: Deuxième nombre

    Returns:
        La somme de a et b
    """
    return a + b


def main():
    """Fonction principale."""
    print("=== Programme de test agentichat ===")
    print()

    # Calculs simples
    resultat = calculer_somme(10, 20)
    print(f"10 + 20 = {resultat}")

    resultat = calculer_somme(5, 7)
    print(f"5 + 7 = {resultat}")

    # Multiplication
    resultat_mult = 6 * 7
    print(f"6 * 7 = {resultat_mult}")

    print()
    print("Programme terminé avec succès!")


if __name__ == "__main__":
    main()
