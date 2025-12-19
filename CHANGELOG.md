# Changelog

## Phase 2 - v0.2.0 (2025-12-03)

### Implémenté

#### Sandbox de Sécurité
- Validation des chemins (jail workspace)
- Blocage fichiers sensibles (.env, *.key, etc.)
- Limite taille fichiers (1 MB par défaut)
- Protection path traversal

#### Tools Système
- `list_files` - Liste fichiers/répertoires
- `read_file` - Lecture fichiers avec plages de lignes
- `write_file` - Création/modification fichiers (confirmation requise)
- `delete_file` - Suppression fichiers (confirmation requise)
- `search_text` - Recherche textuelle (grep-like) avec regex
- `shell_exec` - Exécution commandes shell (confirmation requise)

#### Registre des Tools
- Interface abstraite `Tool`
- Registre central `ToolRegistry`
- Exécution des tools
- Génération schémas JSON pour LLM

#### Boucle Agentique
- Détection tool calls du LLM
- Exécution itérative (max 10 itérations)
- Gestion des confirmations
- Gestion des erreurs et rejets utilisateur

#### Système de Confirmation
- Affichage formaté avec Rich (panels, syntax highlighting)
- Options Y/A/N/? avec aide contextuelle
- Mode "Oui à tout" (passthrough)
- Prévisualisation contenu fichiers
- Reset passthrough par requête

#### Intégration CLI
- Mode agentique activé par défaut
- Initialisation automatique sandbox + tools
- Aide mise à jour avec liste des tools
- Affichage confirmations interactif

### Tests
- `test_phase2.py` - Tests automatisés de tous les tools
- Validation sandbox, registre, exécution
- Tests shell_exec, file_ops, search

## Phase 1 - v0.1.0 (2025-12-03)

### Implémenté

#### Configuration
- Système de configuration YAML avec validation
- Support des variables d'environnement (OLLAMA_HOST, etc.)
- Priorité : local (.agentichat/config.yaml) > global (~/.agentichat/config.yaml)
- Commande `agentichat config show`

#### Backend Ollama
- Interface abstraite Backend extensible
- Client Ollama complet
- Streaming des réponses en temps réel
- Health check au démarrage
- Liste des modèles disponibles
- Gestion d'erreurs robuste

#### Éditeur Multi-ligne
- Saisie multi-ligne avec `Shift+Enter`
- Navigation intelligente dans l'historique (↑/↓)
- Historique persistant (~/.agentichat/history.txt)
- Préservation du brouillon pendant navigation
- Raccourcis clavier complets (Ctrl+C, Ctrl+D, etc.)

#### CLI
- Mode interactif par défaut
- Commandes in-chat : `/help`, `/clear`, `/quit`
- Affichage formaté avec Rich
- Streaming en temps réel des réponses

#### Tests
- Tests automatisés du backend (`test_backend.py`)
- Tests : health check, modèles, chat, streaming

### Corrigé

#### Asyncio Event Loop Error
**Problème :** `asyncio.run() cannot be called from a running event loop`

**Cause :** Utilisation de la méthode synchrone `prompt()` de `PromptSession` dans un contexte async, créant un conflit entre les boucles d'événements.

**Solution :**
- Conversion de `MultiLineEditor.prompt()` en méthode async
- Utilisation de `prompt_async()` au lieu de `prompt()`
- Ajout de `await` dans l'appel depuis `ChatApp.run()`

**Fichiers modifiés :**
- `src/agentichat/cli/editor.py` : Méthode `prompt()` → async
- `src/agentichat/cli/app.py` : Ajout `await` sur `self.editor.prompt()`

**Commit :** Fix asyncio event loop conflict with prompt_toolkit

#### Streaming HTTP Connection
**Problème :** Session HTTP se fermait avant la fin du streaming Ollama.

**Solution :**
- Création de `_stream_chat()` qui maintient la session ouverte
- Séparation des chemins stream/non-stream dans `chat()`

**Fichiers modifiés :**
- `src/agentichat/backends/ollama.py`

### Documentation
- `README.md` - Vue d'ensemble du projet
- `QUICKSTART.md` - Guide de démarrage rapide
- `PHASE1_COMPLETE.md` - Récapitulatif détaillé Phase 1
- `PHASE1_TESTING.md` - Guide de tests complet
- `CHANGELOG.md` - Ce fichier

## Phase 2 (À venir)

### Planifié
- Tools système (read_file, write_file, delete_file, list_files, search_text, shell_exec)
- Boucle agentique avec tool calls
- Système de confirmation Y/N/A
- Sandbox de sécurité
- Sessions persistantes

### Critère de succès Phase 2
```
> Crée un fichier hello.py avec un Hello World et exécute-le

[Le LLM utilisera write_file + shell_exec avec confirmations]
```
