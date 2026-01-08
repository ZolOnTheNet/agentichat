#!/bin/bash
# Test du footer avec debug activé

cd /mnt/datahd1/Samba/svg/garrigues/devLog/python/agentichat

# Créer un fichier d'entrée test
echo "/config debug on" > /tmp/test_input.txt
echo "dis moi bonjour" >> /tmp/test_input.txt
echo "exit" >> /tmp/test_input.txt

# Lancer agentichat avec l'entrée test
.venv/bin/agentichat < /tmp/test_input.txt

# Afficher les derniers logs
echo ""
echo "=== DERNIERS LOGS ==="
tail -50 ~/.agentichat/agentichat.log | grep -E "(footer|show_info|show_separator)"
