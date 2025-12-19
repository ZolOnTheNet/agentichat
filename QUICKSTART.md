# agentichat - Quick Start

## Installation Rapide

```bash
# 1. Créer l'environnement virtuel
uv venv

# 2. Installer le projet
uv pip install -e .

# Configuration automatiquement créée dans : ~/.agentichat/config.yaml
```

## Prérequis

**Ollama doit être installé et lancé :**

```bash
# Vérifier qu'Ollama fonctionne
curl http://localhost:11434/api/tags

# Si besoin, installer Ollama : https://ollama.ai/
# Puis lancer le serveur
ollama serve

# Télécharger un modèle si nécessaire
ollama pull qwen2.5:3b
```

## Utilisation

### Lancer le chat interactif

```bash
.venv/bin/agentichat
```

### Exemples de conversation

**Message simple :**
```
> Bonjour, peux-tu m'expliquer ce qu'est Python en une phrase ?
[Le LLM répond...]
```

**Message multi-ligne (Shift+Enter) :**
```
> Écris-moi un haiku
... sur la programmation
... [Appuyer sur Enter pour envoyer]

[Le LLM répond...]
```

**Utiliser l'historique :**
- Appuyez sur `↑` pour voir le message précédent
- Appuyez sur `↓` pour revenir au message suivant
- Votre brouillon est préservé pendant la navigation

### Commandes disponibles

```
/help       Afficher l'aide
/clear      Réinitialiser la conversation
/quit       Quitter (ou Ctrl+D)
```

### Raccourcis clavier

| Raccourci | Action |
|-----------|--------|
| `Enter` | Envoyer le message |
| `Shift+Enter` | Nouvelle ligne |
| `↑` / `↓` | Naviguer dans l'historique |
| `Ctrl+C` | Annuler la saisie |
| `Ctrl+D` | Quitter |

## Vérifier la configuration

```bash
.venv/bin/agentichat config show
```

Affiche :
- Backend actif (ollama)
- Modèle utilisé (qwen2.5:3b)
- URL du serveur
- Paramètres (timeout, max_tokens, etc.)

## Tests Automatiques

Valider que tout fonctionne :

```bash
.venv/bin/python test_backend.py
```

Résultat attendu :
```
=== Test Backend Ollama ===

1. Test health check...
   ✓ Serveur Ollama accessible

2. Liste des modèles disponibles...
   ✓ 1 modèle(s) trouvé(s): qwen2.5:3b

3. Test chat simple (réponse complète)...
   ✓ Réponse : Paris

4. Test chat streaming...
   ✓ Streaming fonctionnel

=== Tous les tests sont passés ! ===
```

## Résolution de Problèmes

### Erreur : "Impossible de se connecter"

```
Erreur: Impossible de se connecter à http://localhost:11434
```

**Solution :**
1. Vérifier qu'Ollama est lancé : `ollama serve`
2. Vérifier qu'un modèle est disponible : `ollama list`
3. Si besoin, télécharger un modèle : `ollama pull qwen2.5:3b`

### Modifier le modèle

Éditer `~/.agentichat/config.yaml` :

```yaml
backends:
  ollama:
    model: mistral:latest  # Changer ici
```

### Utiliser un serveur Ollama distant

Dans `~/.agentichat/config.yaml` :

```yaml
backends:
  ollama:
    url: http://192.168.1.100:11434  # IP du serveur
    model: qwen2.5:3b
```

## Documentation Complète

- `README.md` - Vue d'ensemble
- `PHASE1_COMPLETE.md` - Récapitulatif détaillé Phase 1
- `PHASE1_TESTING.md` - Guide de tests complet
- `docs/` - Documentation de conception

## Prochaines Phases

**Phase 2 (en cours de développement) :**
- Tools système (read_file, write_file, shell_exec)
- Boucle agentique
- Système de confirmation Y/N/A

**Exemple futur :**
```
> Crée un fichier hello.py avec un Hello World et exécute-le

[Le LLM créera le fichier, demandera confirmation, puis l'exécutera]
```

---

**Bon chat ! 🚀**
