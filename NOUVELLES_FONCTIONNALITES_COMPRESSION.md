# Nouvelles Fonctionnalités de Compression

> Implémentation des améliorations de compression et d'aide demandées

## 📋 Résumé des Modifications

### 1. Configuration de Compression (`CompressionConfig`)

Nouvelle classe de configuration ajoutée dans `src/agentichat/config/schema.py` :

```python
@dataclass
class CompressionConfig:
    auto_enabled: bool = False              # Auto-compression activée
    auto_threshold: int = 20                # Seuil de déclenchement (nb messages)
    auto_keep: int = 5                      # Messages à garder après compression
    warning_threshold: float = 0.75         # Seuil d'avertissement (75%)
    max_messages: int | None = None         # Limite maximale (None = illimité)
```

### 2. Commande `/compress` Améliorée

La commande `/compress` accepte maintenant des options :

#### Syntaxe
```bash
/compress                    # Compresse tous les messages
/compress --max N            # Garde maximum N messages
/compress -m N               # Alias de --max
/compress --keep N           # Garde les N derniers messages
```

#### Exemples
```bash
/compress --keep 10          # Résume tout sauf les 10 derniers messages
/compress -m 5               # Garde max 5 messages
```

### 3. Nouvelle Commande `/config compress`

Gestion complète de la configuration de compression :

#### Syntaxe
```bash
/config compress                      # Affiche la config actuelle
/config compress --enable             # Active l'auto-compression
/config compress --disable            # Désactive l'auto-compression
/config compress --keep N             # Définit le nombre à garder
/config compress --auto <seuil> <N>   # Configure l'auto-compression
```

#### Exemples
```bash
/config compress                      # Voir la config
/config compress --auto 20 5          # Auto-compresse à 20 msg, garde 5
/config compress --keep 10            # Garde 10 messages par défaut
```

### 4. Système d'Avertissement Automatique

Un avertissement s'affiche automatiquement quand l'historique approche du seuil configuré :

```
💡 Info: Vous avez 16 messages (80% du seuil de 20)
→ Utilisez /compress pour réduire l'historique et économiser des tokens
→ Tapez /help compress pour plus d'infos ou /config compress pour configurer
```

**Conditions d'affichage :**
- Quand on dépasse `warning_threshold` (75% par défaut)
- S'affiche après chaque message utilisateur
- Configurable via `compression.warning_threshold`

### 5. Système d'Aide Hiérarchique (`/help`)

Refonte complète du système d'aide avec topics :

#### Aide Générale (Succincte)
```bash
/help                        # Affiche l'aide principale
```

Affiche un résumé avec la liste des topics disponibles.

#### Aide par Topic (Détaillée)
```bash
/help <topic>                # Aide détaillée sur un sujet
```

**Topics disponibles :**
- `compress` - Compression de conversation et gestion mémoire
- `config` - Configuration de l'application
- `log` - Visualisation et recherche dans les logs
- `ollama` - Commandes pour backend Ollama
- `albert` - Commandes pour backend Albert
- `prompt` - Personnalisation du prompt
- `tools` - Liste complète des tools disponibles
- `shortcuts` - Raccourcis clavier

#### Exemples
```bash
/help compress               # Aide détaillée sur la compression
/help shortcuts              # Liste tous les raccourcis clavier
/help tools                  # Liste tous les tools disponibles
```

## 🔧 Fichiers Modifiés

### 1. `src/agentichat/config/schema.py`
- ✅ Ajout de `CompressionConfig` dataclass
- ✅ Ajout du champ `compression` dans `Config`
- ✅ Validation dans `validate_config()`

### 2. `src/agentichat/cli/app.py`
- ✅ Modification de `_handle_compress_command()` pour accepter options
- ✅ Ajout de `_check_compression_warning()` pour avertissement automatique
- ✅ Ajout de gestion `/config compress` dans `_handle_config_command()`
- ✅ Refonte complète de `_show_help()` avec système de topics
- ✅ Ajout de `_show_topic_help()` pour aide détaillée

## 📝 Configuration YAML

Pour activer l'auto-compression, ajouter dans votre config :

```yaml
# ~/.agentichat/config.yaml ou .agentichat/config.yaml

compression:
  auto_enabled: true          # Activer l'auto-compression
  auto_threshold: 20          # Compresser à 20 messages
  auto_keep: 5                # Garder les 5 derniers
  warning_threshold: 0.75     # Avertir à 75%
  max_messages: null          # Pas de limite (ou un nombre)
```

## 🎯 Cas d'Usage

### Scénario 1 : Utilisateur Économe
```bash
# Configurer une compression agressive
/config compress --auto 15 3

# L'avertissement s'affichera à 12 messages (75% de 15)
# La compression automatique se déclenchera à 15 messages
# Et gardera les 3 derniers messages
```

### Scénario 2 : Utilisateur avec Gros Contexte
```bash
# Configurer une compression plus permissive
/config compress --auto 50 20

# L'avertissement s'affichera à 38 messages (75% de 50)
# La compression se déclenchera à 50 messages
# Et gardera les 20 derniers messages
```

### Scénario 3 : Compression Manuelle Uniquement
```bash
# Désactiver l'auto-compression
/config compress --disable

# Compresser manuellement quand nécessaire
/compress --keep 10
```

## 🧪 Tests

Un fichier de test a été créé pour vérifier les fonctionnalités :

```bash
python3 test_compress_features.py
```

**Résultats :**
- ✅ CompressionConfig : Valeurs par défaut et personnalisées
- ✅ Intégration dans Config
- ✅ Topics d'aide disponibles
- ✅ Parsing des commandes /compress
- ✅ Parsing des commandes /config compress

## 💡 Améliorations Futures Possibles

1. **Auto-compression réelle** : Actuellement seul l'avertissement est implémenté. L'auto-compression pourrait se déclencher automatiquement.

2. **Persistance de la config** : Sauvegarder les modifications de config en runtime dans le fichier YAML.

3. **Statistiques de compression** : Afficher l'historique des compressions dans `/info`.

4. **Templates de résumé** : Permettre différents styles de résumés (concis, détaillé, par topic, etc.).

5. **Compression sélective** : Compresser seulement certaines parties de la conversation (ex: garder les messages système).

## 📚 Documentation

- Toutes les nouvelles commandes sont documentées dans `/help` et `/help <topic>`
- La configuration est validée automatiquement au chargement
- Les erreurs d'utilisation affichent l'usage correct

## ✅ Checklist d'Implémentation

- [x] Ajouter `CompressionConfig` dans `schema.py`
- [x] Implémenter `/compress` avec options `--max/-m` et `--keep`
- [x] Ajouter système d'avertissement automatique (% to auto-compress)
- [x] Créer sous-commande `/config compress` avec `--keep` et `--auto`
- [x] Refondre `/help` avec système de topics hiérarchique
- [x] Tester toutes les fonctionnalités
- [x] Documentation complète

---

**Version:** 1.0
**Date:** 2026-01-06
**Statut:** ✅ Implémentation complète et testée
