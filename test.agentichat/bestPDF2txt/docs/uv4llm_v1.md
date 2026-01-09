# uv - Gestionnaire de Packages Python Ultra-Rapide

> 📦 Documentation destinée aux LLMs pour comprendre et utiliser `uv` dans le projet agentichat

## Qu'est-ce que uv ?

**uv** est un gestionnaire de packages et d'environnements Python **extrêmement rapide**, écrit en Rust. C'est une alternative moderne à `pip` et `pip-tools`.

### Caractéristiques Principales

- ⚡ **10-100x plus rapide** que pip
- 🦀 Écrit en Rust pour des performances optimales
- 🔒 Résolution de dépendances déterministe
- 🎯 Compatible avec pip (même syntaxe)
- 📦 Gère les environnements virtuels automatiquement

### Pourquoi uv dans ce Projet ?

Dans **agentichat**, nous utilisons `uv` à la place de `pip` car :
1. **Installation plus rapide** des dépendances (important pour le développement)
2. **Compatible pip** : peut utiliser les mêmes fichiers `requirements.txt` et `pyproject.toml`
3. **Déjà installé** sur la machine de l'utilisateur

## Installation de uv

Si `uv` n'est pas installé :

```bash
# Linux/macOS
curl -LsSf https://astral.sh/uv/install.sh | sh

# Avec pip (si nécessaire)
pip install uv
```

Vérifier l'installation :
```bash
uv --version
```

## Commandes Principales

### 1. Installation de Packages

**Syntaxe identique à pip :**

```bash
# Installer un package
uv pip install <package>

# Installer depuis requirements.txt
uv pip install -r requirements.txt

# Installer en mode éditable (développement)
uv pip install -e .

# Installer avec des extras
uv pip install -e ".[dev]"
```

**Exemples pour agentichat :**

```bash
# Installation normale
uv pip install -e .

# Avec dépendances de développement
uv pip install -e ".[dev]"

# Avec support embeddings
uv pip install -e ".[embeddings]"
```

### 2. Gestion d'Environnement Virtuel

```bash
# Créer un venv
uv venv

# Créer avec une version spécifique de Python
uv venv --python 3.11

# Activer le venv (même commande que d'habitude)
source .venv/bin/activate    # Linux/macOS
.venv\Scripts\activate       # Windows
```

### 3. Lister les Packages

```bash
# Lister les packages installés
uv pip list

# Format freeze
uv pip freeze
```

### 4. Désinstaller

```bash
# Désinstaller un package
uv pip uninstall <package>
```

### 5. Synchroniser (Advanced)

```bash
# Synchroniser l'environnement avec pyproject.toml
uv pip sync
```

## Différences avec pip

| Aspect | pip | uv |
|--------|-----|-----|
| **Commande** | `pip install` | `uv pip install` |
| **Vitesse** | Normal | 10-100x plus rapide |
| **Résolution** | Peut varier | Déterministe |
| **Cache** | Limité | Efficace et partagé |
| **Langage** | Python | Rust |

## Équivalences pip ↔ uv

```bash
# Installation
pip install package        →  uv pip install package
pip install -r req.txt     →  uv pip install -r req.txt
pip install -e .           →  uv pip install -e .

# Listage
pip list                   →  uv pip list
pip freeze                 →  uv pip freeze

# Désinstallation
pip uninstall package      →  uv pip uninstall package

# Environnements
python -m venv .venv       →  uv venv
```

## Utilisation dans agentichat

### Workflow de Développement Typique

```bash
# 1. Créer l'environnement virtuel (si pas déjà fait)
uv venv

# 2. Activer l'environnement
source .venv/bin/activate

# 3. Installer le projet en mode éditable
uv pip install -e .

# 4. Installer les dépendances de développement (optionnel)
uv pip install -e ".[dev]"

# 5. Après modifications du code, réinstaller
uv pip install -e .
```

### Installation Rapide (One-liner)

```bash
uv venv && source .venv/bin/activate && uv pip install -e .
```

### Réinstallation Après Modifications

Après avoir modifié le code source de `agentichat` :

```bash
# Option 1 : Réinstaller (rapide avec uv)
uv pip install -e .

# Option 2 : Forcer la reconstruction
uv pip install -e . --force-reinstall --no-deps
```

## Cas d'Usage Spécifiques

### 1. Tester une Nouvelle Dépendance

```bash
# Installer temporairement pour tester
uv pip install nouvelle-lib

# Si ça marche, l'ajouter à pyproject.toml
# puis réinstaller
uv pip install -e .
```

### 2. Nettoyage Complet

```bash
# Supprimer le venv et recommencer
rm -rf .venv
uv venv
source .venv/bin/activate
uv pip install -e .
```

### 3. Debug des Dépendances

```bash
# Voir la version installée
uv pip show <package>

# Voir toutes les dépendances
uv pip list

# Format requirements.txt
uv pip freeze > requirements-current.txt
```

## Performance : uv vs pip

**Exemple réel dans agentichat :**

```bash
# Avec pip (temps typique)
time pip install -e .
# → ~8-12 secondes

# Avec uv (temps typique)
time uv pip install -e .
# → ~1-2 secondes ⚡
```

**Économie de temps sur 10 installations :**
- pip : 100 secondes
- uv : 15 secondes
- **Gain : 85 secondes**

## Résolution de Problèmes

### Erreur : uv command not found

```bash
# Solution 1 : Installer uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Solution 2 : Utiliser pip classique
pip install -e .
```

### Erreur : Failed to hardlink files

```bash
# Warning normal sur filesystems différents
# Solution : ignorer ou définir
export UV_LINK_MODE=copy
uv pip install -e .
```

### Cache prend trop de place

```bash
# Nettoyer le cache uv
uv cache clean
```

## Intégration CI/CD

Pour les pipelines de tests automatisés :

```yaml
# .github/workflows/test.yml (exemple)
- name: Install uv
  run: pip install uv

- name: Install dependencies
  run: uv pip install -e ".[dev]"

- name: Run tests
  run: pytest
```

## Commandes Avancées

### Créer un requirements.txt depuis pyproject.toml

```bash
uv pip compile pyproject.toml -o requirements.txt
```

### Mettre à jour toutes les dépendances

```bash
uv pip install -e . --upgrade
```

### Installer avec contraintes

```bash
uv pip install -e . -c constraints.txt
```

## Références

- **Site officiel** : https://github.com/astral-sh/uv
- **Documentation** : https://github.com/astral-sh/uv#readme
- **Astral** (créateurs) : https://astral.sh

## Résumé pour LLM

**Quand recommander uv :**
- ✅ Installation de packages Python
- ✅ Développement actif (modifications fréquentes)
- ✅ Environnements virtuels
- ✅ Compatible avec pip (drop-in replacement)

**Syntaxe clé à retenir :**
```bash
uv pip install <package>    # Identique à pip
uv pip install -e .          # Mode développement
uv venv                      # Créer un venv
```

**Note importante :** Si `uv` n'est pas disponible sur le système, on peut toujours fallback sur `pip` classique (même syntaxe sans le préfixe `uv`).

---

**Dernière mise à jour** : 2026-01-06
**Version uv utilisée** : 0.1.x+
**Projet** : agentichat
