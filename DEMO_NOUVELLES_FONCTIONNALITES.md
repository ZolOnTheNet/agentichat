# Nouvelles fonctionnalités agentichat

## 1. Commandes /config - Configuration dynamique

### Configuration du mode debug
```bash
# Activer le mode debug à la volée
> /config debug on

# Désactiver le mode debug
> /config debug off

# Afficher la configuration actuelle
> /config show
```

**Fonctionnalités:**
- ✓ Active/désactive les logs de debug dynamiquement (sans redémarrer)
- ✓ Change le niveau de tous les loggers en temps réel
- ✓ Affiche la configuration complète (backend, modèle, timeout, debug)
- ✓ Indique le chemin du fichier de log

---

## 2. Commandes /log - Visualisation des logs

### /log show (ou simplement /log)
Affiche les **nouveaux logs** depuis le dernier appel de /log show

```bash
> /log
# ou
> /log show
```

**Caractéristiques:**
- Affiche uniquement les nouveaux logs (différentiel)
- Limité par défaut à 20 lignes (configurable)
- Coloration syntaxique:
  - ERROR/CRITICAL → rouge
  - WARNING → jaune
  - DEBUG → grisé
  - INFO → normal

### /log fullshow
Affiche **tous les logs** depuis le dernier /log clear (ou depuis le début)

```bash
> /log fullshow
```

### /log clear
Marque un point de départ pour /log fullshow

```bash
> /log clear
# Les prochains /log fullshow ne montreront que les logs après ce point
```

### /log search &lt;texte&gt;
Recherche un texte dans les logs avec contexte

```bash
# Rechercher "ERROR" dans les logs
> /log search ERROR

# Rechercher "ollama"
> /log search ollama

# Rechercher "Agent loop"
> /log search Agent loop
```

**Caractéristiques:**
- Recherche insensible à la casse
- Affiche le contexte autour de chaque occurrence
- Par défaut: 3 lignes avant, 10 lignes après (configurable)
- Highlight la ligne contenant le match

### /log config
Configure les paramètres d'affichage

```bash
# Afficher la configuration actuelle
> /log config

# Configurer le nombre de lignes pour /log show
> /log config show 50

# Configurer le contexte pour /log search
# Format: /log config search <lignes_avant> <lignes_après>
> /log config search 5 15
```

**Paramètres par défaut:**
- show: 20 lignes
- search: 3 lignes avant, 10 lignes après

### /log status
Affiche les statistiques des logs

```bash
> /log status
```

**Informations affichées:**
- Nombre total de lignes dans le fichier de log
- Taille du fichier (octets et KB)
- Configuration actuelle (show, search)
- Position de la dernière lecture
- Position du dernier clear

---

## 3. Touche ESC - Annulation améliorée

**ESC** → Annule la saisie en cours (vide l'éditeur)
**Ctrl+C** → Annule la requête LLM en cours d'exécution

### Avant
- Ctrl+C annulait la saisie (comportement confus)

### Maintenant
- ESC: vide l'éditeur (annulation de frappe)
- Ctrl+C: interruption de la requête LLM

---

## 4. Autres améliorations

### Timeout augmenté
- Timeout passé de 30s à **300s (5 minutes)**
- Permet de gérer les requêtes complexes avec tools

### Spinner animé
- Affichage d'un spinner avec points pendant le traitement LLM
- Message: "Le LLM réfléchit..."
- Indication visuelle de l'activité

### Système de logging complet
- Logs dans `~/.agentichat/agentichat.log`
- Niveaux: DEBUG, INFO, WARNING, ERROR
- Rotation automatique (si configuré)
- Visible avec les commandes /log

---

## Exemples de workflow

### Workflow 1: Debugging d'un problème
```bash
# 1. Activer le debug
> /config debug on

# 2. Exécuter des commandes...
> Liste les fichiers Python

# 3. Consulter les logs de debug
> /log show

# 4. Rechercher des erreurs
> /log search ERROR

# 5. Désactiver le debug
> /config debug off
```

### Workflow 2: Configuration personnalisée
```bash
# 1. Configurer l'affichage (50 dernières lignes)
> /log config show 50

# 2. Configurer la recherche (plus de contexte)
> /log config search 10 20

# 3. Vérifier la configuration
> /log config

# 4. Utiliser les commandes
> /log show
> /log search ollama
```

### Workflow 3: Maintenance des logs
```bash
# 1. Voir les statistiques
> /log status

# 2. Marquer un point de départ
> /log clear

# 3. Exécuter des opérations...

# 4. Voir uniquement les nouveaux logs
> /log fullshow
```

---

## Aide rapide

```bash
# Configuration
/config show              # Affiche la config
/config debug on/off      # Active/désactive debug

# Logs
/log                      # Nouveaux logs
/log fullshow            # Tous les logs
/log clear               # Marque un point
/log search <texte>      # Recherche
/log config              # Config logs
/log status              # Statistiques

# Navigation
Enter                    # Envoyer
Shift+Enter             # Nouvelle ligne
ESC                     # Annuler saisie
Ctrl+C                  # Annuler requête
Ctrl+D                  # Quitter
```

---

## Fichiers créés/modifiés

### Nouveaux fichiers
- `src/agentichat/cli/log_viewer.py` - Classe LogViewer pour gérer les logs
- `src/agentichat/utils/logger.py` - Système de logging centralisé

### Fichiers modifiés
- `src/agentichat/cli/app.py` - Ajout des commandes /config et /log
- `src/agentichat/cli/editor.py` - Touche ESC pour annulation
- `config.example.yaml` - Timeout augmenté à 300s
- `~/.agentichat/config.yaml` - Idem

---

## Tests effectués

✓ Tous les imports réussis
✓ LogViewer: 10/10 tests passés
✓ Parsing des commandes /log: tous corrects
✓ Parsing des commandes /config: tous corrects
✓ Application démarre correctement
✓ Spinner fonctionne pendant requêtes LLM
✓ Logs écrits dans ~/.agentichat/agentichat.log

---

## Architecture

```
ChatApp
├── LogViewer (nouveau)
│   ├── show() - Nouveaux logs
│   ├── fullshow() - Tous les logs
│   ├── clear() - Marque point
│   ├── search() - Recherche
│   ├── set_config_show() - Config
│   ├── set_config_search() - Config
│   └── get_status() - Stats
│
├── _handle_log_command() (nouveau)
│   ├── show
│   ├── fullshow
│   ├── clear
│   ├── search
│   ├── config
│   └── status
│
└── _handle_config_command() (nouveau)
    ├── show
    └── debug on/off

Configuration dynamique
└── _set_debug_mode() (nouveau)
    └── Change niveau loggers en temps réel
```
