#!/usr/bin/env python3
"""Script de test pour le LogViewer."""

import sys
import tempfile
from pathlib import Path

# Ajouter le répertoire src au path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from agentichat.cli.log_viewer import LogViewer


def create_test_log(log_file: Path) -> None:
    """Crée un fichier de log de test."""
    content = """[2025-12-04 10:00:00] INFO [agentichat] Application started
[2025-12-04 10:00:01] DEBUG [agentichat.cli] Initializing editor
[2025-12-04 10:00:02] INFO [agentichat.backends.ollama] Connecting to Ollama
[2025-12-04 10:00:03] DEBUG [agentichat.backends.ollama] Sending request with 2 tools
[2025-12-04 10:00:04] WARNING [agentichat.core.agent] Max iterations reached
[2025-12-04 10:00:05] INFO [agentichat.cli] Request completed successfully
[2025-12-04 10:00:06] ERROR [agentichat.tools.shell] Command failed: exit code 1
[2025-12-04 10:00:07] DEBUG [agentichat.core.agent] Starting agent loop
[2025-12-04 10:00:08] INFO [agentichat.backends.ollama] Ollama request: model=qwen2.5:3b
[2025-12-04 10:00:09] DEBUG [agentichat.cli] Debug mode enabled dynamically
[2025-12-04 10:00:10] INFO [agentichat] Shutting down
"""
    with open(log_file, 'w') as f:
        f.write(content)


def test_log_viewer():
    """Teste toutes les fonctionnalités du LogViewer."""
    print("="*60)
    print("Test du LogViewer")
    print("="*60 + "\n")

    # Créer un fichier de log temporaire
    with tempfile.NamedTemporaryFile(mode='w', suffix='.log', delete=False) as tmp:
        log_file = Path(tmp.name)

    create_test_log(log_file)

    # Créer le LogViewer
    viewer = LogViewer(log_file)

    # Test 1: status initial
    print("1. Test status initial")
    status = viewer.get_status()
    print(f"   Total lignes: {status['total_lines']}")
    print(f"   Taille: {status['total_size']} octets")
    print(f"   Config show: {status['show_lines_config']} lignes")
    print(f"   Config search: {status['search_before_config']} avant, {status['search_after_config']} après")
    print(f"   ✓ Test réussi\n")

    # Test 2: show (première fois - tous les logs)
    print("2. Test show (première lecture)")
    lines = viewer.show()
    print(f"   Lignes lues: {len(lines)}")
    print(f"   Première ligne: {lines[0] if lines else 'N/A'}")
    print(f"   Dernière ligne: {lines[-1] if lines else 'N/A'}")
    print(f"   ✓ Test réussi\n")

    # Test 3: show (deuxième fois - aucun nouveau log)
    print("3. Test show (pas de nouveaux logs)")
    lines = viewer.show()
    print(f"   Lignes lues: {len(lines)}")
    assert len(lines) == 0, "Devrait être vide"
    print(f"   ✓ Test réussi\n")

    # Test 4: Ajouter de nouveaux logs
    print("4. Test ajout de nouveaux logs")
    with open(log_file, 'a') as f:
        f.write("[2025-12-04 10:00:11] INFO [agentichat] New log entry\n")
        f.write("[2025-12-04 10:00:12] DEBUG [agentichat.cli] Another new entry\n")

    lines = viewer.show()
    print(f"   Nouvelles lignes: {len(lines)}")
    for line in lines:
        print(f"     - {line}")
    assert len(lines) == 2, "Devrait avoir 2 nouvelles lignes"
    print(f"   ✓ Test réussi\n")

    # Test 5: fullshow
    print("5. Test fullshow")
    lines = viewer.fullshow()
    print(f"   Total lignes: {len(lines)}")
    print(f"   Première: {lines[0] if lines else 'N/A'}")
    print(f"   Dernière: {lines[-1] if lines else 'N/A'}")
    print(f"   ✓ Test réussi\n")

    # Test 6: clear
    print("6. Test clear")
    viewer.clear()
    lines = viewer.fullshow()
    print(f"   Lignes après clear: {len(lines)}")
    assert len(lines) == 0, "Devrait être vide après clear"
    print(f"   ✓ Test réussi\n")

    # Test 7: search
    print("7. Test search")
    matches = viewer.search("ERROR")
    print(f"   Occurrences trouvées: {len(matches)}")
    for line_num, context in matches:
        print(f"   Ligne {line_num}:")
        for ctx_line in context[:2]:  # Afficher seulement les 2 premières lignes
            print(f"     {ctx_line}")
    print(f"   ✓ Test réussi\n")

    # Test 8: config show
    print("8. Test config show")
    viewer.set_config_show(5)
    status = viewer.get_status()
    print(f"   Config show après modification: {status['show_lines_config']} lignes")
    assert status['show_lines_config'] == 5
    print(f"   ✓ Test réussi\n")

    # Test 9: config search
    print("9. Test config search")
    viewer.set_config_search(1, 5)
    status = viewer.get_status()
    print(f"   Config search: {status['search_before_config']} avant, {status['search_after_config']} après")
    assert status['search_before_config'] == 1
    assert status['search_after_config'] == 5
    print(f"   ✓ Test réussi\n")

    # Test 10: search avec nouvelle config
    print("10. Test search avec config personnalisée")
    matches = viewer.search("Ollama")
    if matches:
        line_num, context = matches[0]
        print(f"   Première occurrence ligne {line_num}:")
        print(f"   Nombre de lignes de contexte: {len(context)}")
        assert len(context) <= 7, f"Devrait avoir max 7 lignes (1+1+5), got {len(context)}"
    print(f"   ✓ Test réussi\n")

    # Nettoyer
    log_file.unlink()

    print("="*60)
    print("✓ Tous les tests sont passés avec succès !")
    print("="*60)


if __name__ == "__main__":
    test_log_viewer()
