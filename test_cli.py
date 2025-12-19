#!/usr/bin/env python3
"""Test rapide du CLI sans interaction."""

import asyncio
from src.agentichat.config.loader import load_config
from src.agentichat.cli.app import ChatApp

async def test_init():
    """Test l'initialisation de l'application."""
    config = load_config()
    app = ChatApp(config)
    await app.initialize()
    print("✓ Initialisation réussie sans erreur asyncio")

if __name__ == "__main__":
    asyncio.run(test_init())
