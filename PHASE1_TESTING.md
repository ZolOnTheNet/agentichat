# Phase 1 - Tests et Validation

## Statut : ✅ Implémentation Complète

Tous les composants de la Phase 1 ont été implémentés :

- ✅ `pyproject.toml` avec dépendances
- ✅ Structure de répertoires
- ✅ Configuration YAML (`config/schema.py`, `config/loader.py`)
- ✅ Backend Ollama (`backends/base.py`, `backends/ollama.py`)
- ✅ Éditeur multi-ligne (`cli/editor.py`)
- ✅ Boucle CLI principale (`cli/app.py`)
- ✅ Point d'entrée (`main.py`)
- ✅ Configuration exemple (`config.example.yaml`)

## Installation

```bash
# Créer l'environnement virtuel avec uv
uv venv

# Installer le projet
uv pip install -e .
```

## Configuration

La configuration est automatiquement copiée dans `~/.agentichat/config.yaml`.

Pour personnaliser, éditez ce fichier :

```bash
vim ~/.agentichat/config.yaml
```

## Tests de Validation Phase 1

### Test 1 : Vérifier l'installation

```bash
.venv/bin/agentichat --help
```

**Résultat attendu :** Affichage de l'aide avec les commandes disponibles.

### Test 2 : Vérifier la configuration

```bash
.venv/bin/agentichat config show
```

**Résultat attendu :** Affichage de la configuration avec le backend Ollama.

### Test 3 : Tester la connexion Ollama

**Prérequis :** Ollama doit être installé et en cours d'exécution.

```bash
# Vérifier qu'Ollama fonctionne
curl http://localhost:11434/api/tags

# Si Ollama n'est pas lancé :
ollama serve
```

### Test 4 : Chat interactif (si Ollama disponible)

```bash
.venv/bin/agentichat
```

**Test du mode interactif :**

1. **Message simple :**
   ```
   > Bonjour, qui es-tu ?
   ```
   Résultat : Le LLM répond

2. **Message multi-ligne (Shift+Enter) :**
   ```
   > Écris un haiku
   ... sur Python
   ... [Enter]
   ```
   Résultat : Le LLM génère un haiku

3. **Historique (Flèche haut) :**
   - Appuyer sur ↑ pour voir le message précédent
   - Appuyer sur ↓ pour revenir

4. **Commandes :**
   ```
   > /help
   > /clear
   > /quit
   ```

5. **Quitter :**
   - Taper `/quit` ou appuyer sur Ctrl+D

### Test 5 : Streaming

Le streaming devrait fonctionner automatiquement. Vérifier que les réponses s'affichent mot par mot et non d'un coup.

## Fonctionnalités Validées

### Configuration ✅
- [x] Chargement depuis `~/.agentichat/config.yaml` (global)
- [x] Chargement depuis `.agentichat/config.yaml` (workspace local)
- [x] Variables d'environnement (OLLAMA_HOST, etc.)
- [x] Validation du schéma
- [x] Commande `agentichat config show`

### Backend Ollama ✅
- [x] Connexion au serveur Ollama
- [x] Health check au démarrage
- [x] Chat avec streaming
- [x] Chat sans streaming (réponse complète)
- [x] Liste des modèles disponibles
- [x] Gestion des erreurs de connexion

### Éditeur Multi-ligne ✅
- [x] Saisie multi-ligne avec Shift+Enter
- [x] Enter pour soumettre
- [x] Navigation dans l'historique (↑/↓ sur première/dernière ligne)
- [x] Historique persistant dans `~/.agentichat/history.txt`
- [x] Copier/coller (Ctrl+V)
- [x] Annuler (Ctrl+C)
- [x] Quitter (Ctrl+D)
- [x] Préservation du brouillon lors de la navigation dans l'historique

### CLI ✅
- [x] Mode interactif par défaut
- [x] Commande `/help`
- [x] Commande `/clear`
- [x] Commande `/quit`, `/exit`, `/q`
- [x] Affichage formaté avec Rich
- [x] Streaming de la réponse

## Problèmes Connus

### Si Ollama n'est pas installé

**Erreur :**
```
Erreur: Impossible de se connecter à http://localhost:11434
```

**Solution :**
1. Installer Ollama : https://ollama.ai/
2. Lancer le serveur : `ollama serve`
3. Télécharger un modèle : `ollama pull llama3:8b`

### Si le port est déjà utilisé

Modifier dans `~/.agentichat/config.yaml` :
```yaml
proxy_port: 5158  # Changer le port
```

## Prochaines Étapes - Phase 2

La Phase 2 implémentera :

1. **Tools système :**
   - `list_files` - Lister les fichiers
   - `read_file` - Lire un fichier
   - `write_file` - Écrire/modifier un fichier
   - `delete_file` - Supprimer un fichier
   - `search_text` - Recherche textuelle
   - `shell_exec` - Exécuter des commandes shell

2. **Boucle agentique :**
   - Détection des tool calls
   - Exécution des tools
   - Gestion des confirmations utilisateur
   - Itérations multiples

3. **Sandbox de sécurité :**
   - Validation des chemins (jail)
   - Blocage des fichiers sensibles
   - Limite de taille des fichiers

**Objectif Phase 2 :**
Permettre au LLM d'interagir avec le système de fichiers et d'exécuter des commandes.

Exemple de tâche :
```
> Crée un fichier hello.py avec un script Hello World et exécute-le
```

Le LLM devrait :
1. Créer le fichier avec `write_file`
2. Demander confirmation à l'utilisateur
3. Exécuter le script avec `shell_exec`
4. Afficher le résultat
