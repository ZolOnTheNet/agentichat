#!/bin/bash
# Test du footer avec debug activé

cd /mnt/datahd1/Samba/svg/garrigues/devLog/python/llmchat

# Créer un fichier d'entrée test
echo "/config debug on" > /tmp/test_input.txt
echo "dis moi bonjour" >> /tmp/test_input.txt
echo "exit" >> /tmp/test_input.txt

# Lancer llmchat avec l'entrée test
.venv/bin/llmchat < /tmp/test_input.txt

# Afficher les derniers logs
echo ""
echo "=== DERNIERS LOGS ==="
tail -50 ~/.llmchat/llmchat.log | grep -E "(footer|show_info|show_separator)"
