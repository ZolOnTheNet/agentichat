#!/usr/bin/env python3
"""Test de la sérialisation des ToolCall."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from agentichat.backends.base import Message, ToolCall


def test_toolcall_serialization():
    """Teste que les ToolCall peuvent être sérialisés."""
    print("="*60)
    print("Test sérialisation ToolCall")
    print("="*60 + "\n")

    # Créer un message avec tool_calls
    tool_call = ToolCall(
        id="call_123",
        name="write_file",
        arguments={"path": "hello.py", "content": "print('Hello')"},
    )

    message = Message(
        role="assistant",
        content="Je vais créer le fichier",
        tool_calls=[tool_call],
    )

    print("1. Message créé:")
    print(f"   Role: {message.role}")
    print(f"   Content: {message.content}")
    print(f"   Tool calls: {len(message.tool_calls)}")
    print()

    # Simuler la conversion comme dans ollama.py
    print("2. Conversion en dict (comme ollama.py):")
    message_dict = {
        "role": message.role,
        "content": message.content,
    }

    if message.tool_calls:
        message_dict["tool_calls"] = [
            {
                "id": tc.id,
                "type": "function",
                "function": {
                    "name": tc.name,
                    "arguments": tc.arguments,
                },
            }
            for tc in message.tool_calls
        ]

    print(f"   Dict créé: {list(message_dict.keys())}")
    print()

    # Tester la sérialisation JSON
    print("3. Sérialisation JSON:")
    try:
        json_str = json.dumps(message_dict, indent=2)
        print("   ✓ Sérialisation réussie !")
        print()
        print("   JSON:")
        print(json_str)
        print()
    except TypeError as e:
        print(f"   ✗ Erreur: {e}")
        return False

    # Désérialisation
    print("4. Désérialisation:")
    try:
        back = json.loads(json_str)
        print(f"   ✓ Désérialisation réussie !")
        print(f"   Tool call name: {back['tool_calls'][0]['function']['name']}")
        print(f"   Tool call args: {back['tool_calls'][0]['function']['arguments']}")
        print()
    except Exception as e:
        print(f"   ✗ Erreur: {e}")
        return False

    print("="*60)
    print("✓ Test réussi - ToolCall correctement sérialisable")
    print("="*60)
    return True


if __name__ == "__main__":
    success = test_toolcall_serialization()
    sys.exit(0 if success else 1)
