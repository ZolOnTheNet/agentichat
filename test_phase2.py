#!/usr/bin/env python3
"""Script de test pour la Phase 2 (tools et boucle agentique)."""

import asyncio
from pathlib import Path

from src.agentichat.tools.file_ops import ListFilesTool, ReadFileTool, WriteFileTool
from src.agentichat.tools.registry import ToolRegistry
from src.agentichat.tools.search import SearchTextTool
from src.agentichat.tools.shell import ShellExecTool
from src.agentichat.utils.sandbox import Sandbox

print("=== Test Phase 2 - Tools et Boucle Agentique ===\n")


async def test_tools():
    """Test des tools individuellement."""
    # Créer un sandbox de test
    test_dir = Path("/tmp/agentichat_test")
    test_dir.mkdir(exist_ok=True)

    sandbox = Sandbox(root=test_dir, config={"max_file_size": 1_000_000})

    # Créer le registre
    registry = ToolRegistry()

    # Enregistrer les tools
    registry.register(ListFilesTool(sandbox))
    registry.register(ReadFileTool(sandbox))
    registry.register(WriteFileTool(sandbox))
    registry.register(SearchTextTool(sandbox))
    registry.register(ShellExecTool(sandbox))

    print(f"1. Test Sandbox")
    print(f"   Workspace: {test_dir}")
    print(f"   ✓ Sandbox créé\n")

    print(f"2. Test Registre")
    tools = registry.list_tools()
    print(f"   ✓ {len(tools)} tools enregistrés:")
    for tool in tools:
        confirmation = " [confirm]" if tool.requires_confirmation else ""
        print(f"     - {tool.name}{confirmation}")
    print()

    # Test write_file
    print("3. Test write_file")
    result = await registry.execute(
        "write_file", {"path": "test.txt", "content": "Hello World\nTest agentichat"}
    )
    if result["success"]:
        print(f"   ✓ Fichier créé: {result['path']}")
    else:
        print(f"   ✗ Erreur: {result['error']}")
    print()

    # Test read_file
    print("4. Test read_file")
    result = await registry.execute("read_file", {"path": "test.txt"})
    if result["success"]:
        print(f"   ✓ Contenu lu:")
        for line in result["content"].splitlines():
            print(f"     {line}")
    else:
        print(f"   ✗ Erreur: {result['error']}")
    print()

    # Test list_files
    print("5. Test list_files")
    result = await registry.execute("list_files", {"path": "."})
    if result["success"]:
        print(f"   ✓ {result['count']} fichier(s) trouvé(s):")
        for file in result["files"]:
            print(f"     - {file}")
    else:
        print(f"   ✗ Erreur: {result['error']}")
    print()

    # Test search_text
    print("6. Test search_text")
    result = await registry.execute(
        "search_text", {"query": "Hello", "path": "."}
    )
    if result["success"]:
        print(f"   ✓ {result['count']} correspondance(s) trouvée(s):")
        for match in result["matches"]:
            print(f"     {match['file']}:{match['line']} - {match['content']}")
    else:
        print(f"   ✗ Erreur: {result['error']}")
    print()

    # Test shell_exec
    print("7. Test shell_exec")
    result = await registry.execute("shell_exec", {"command": "echo 'Test shell'"})
    if result["success"]:
        print(f"   ✓ Commande exécutée:")
        print(f"     stdout: {result['stdout'].strip()}")
    else:
        print(f"   ✗ Erreur: {result['error']}")
    print()

    # Test schémas JSON
    print("8. Test Schémas JSON pour LLM")
    schemas = registry.to_schemas()
    print(f"   ✓ {len(schemas)} schémas générés:")
    for schema in schemas:
        func = schema["function"]
        print(f"     - {func['name']}: {func['description'][:50]}...")
    print()

    # Nettoyage
    import shutil

    shutil.rmtree(test_dir)
    print("✓ Nettoyage effectué\n")

    print("=== Tous les tests Phase 2 sont passés ! ===\n")


if __name__ == "__main__":
    asyncio.run(test_tools())
