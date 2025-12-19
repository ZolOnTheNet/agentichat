#!/usr/bin/env python3
"""Script de test pour valider le backend Ollama."""

import asyncio

from src.agentichat.backends.base import Message
from src.agentichat.backends.ollama import OllamaBackend


async def test_ollama():
    """Test basique du backend Ollama."""
    print("=== Test Backend Ollama ===\n")

    # Configuration
    backend = OllamaBackend(
        url="http://localhost:11434",
        model="qwen2.5:3b",
    )

    # Test 1 : Health check
    print("1. Test health check...")
    is_healthy = await backend.health_check()
    if is_healthy:
        print("   ✓ Serveur Ollama accessible\n")
    else:
        print("   ✗ Serveur Ollama non accessible")
        print("   Assurez-vous qu'Ollama est lancé : ollama serve")
        return

    # Test 2 : Liste des modèles
    print("2. Liste des modèles disponibles...")
    try:
        models = await backend.list_models()
        print(f"   ✓ {len(models)} modèle(s) trouvé(s):")
        for model in models:
            print(f"     - {model}")
        print()
    except Exception as e:
        print(f"   ✗ Erreur : {e}\n")
        return

    # Test 3 : Chat simple (non-streaming)
    print("3. Test chat simple (réponse complète)...")
    messages = [
        Message(role="user", content="Réponds en un mot : quelle est la capitale de la France ?")
    ]
    try:
        response = await backend.chat(messages, stream=False)
        print(f"   ✓ Réponse : {response.content}")
        print(f"   Raison d'arrêt : {response.finish_reason}\n")
    except Exception as e:
        print(f"   ✗ Erreur : {e}\n")
        return

    # Test 4 : Chat streaming
    print("4. Test chat streaming...")
    messages = [
        Message(role="user", content="Compte de 1 à 5, un nombre par ligne.")
    ]
    try:
        print("   Réponse : ", end="", flush=True)
        response_stream = await backend.chat(messages, stream=True)
        async for chunk in response_stream:
            print(chunk, end="", flush=True)
        print("\n   ✓ Streaming fonctionnel\n")
    except Exception as e:
        print(f"\n   ✗ Erreur : {e}\n")
        return

    print("=== Tous les tests sont passés ! ===")


if __name__ == "__main__":
    asyncio.run(test_ollama())
