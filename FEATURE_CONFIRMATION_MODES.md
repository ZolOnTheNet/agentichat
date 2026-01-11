# Feature : 3 Modes de Confirmation + Shift+Tab + Affichage Barre

## 🎯 Fonctionnalité Implémentée

### Trois Modes de Confirmation

L'utilisateur peut maintenant choisir entre **3 modes** de gestion des confirmations :

| Mode | Description | Comportement |
|------|-------------|--------------|
| **Ask** | Demander à chaque fois (défaut) | Demande confirmation pour chaque opération sensible |
| **Auto** | Accepter automatiquement (après "A") | Accepte automatiquement après avoir tapé "A" une fois |
| **Force** | Toujours accepter | Accepte toujours toutes les opérations sans demander |

### Navigation Cyclique avec Shift+Tab

**Raccourci clavier :** `Shift+Tab`

**Cycle :** Ask → Auto → Force → Ask

L'utilisateur peut **changer de mode à tout moment** pendant la saisie en tapant `Shift+Tab`.

### Affichage dans la Barre du Bas

Le mode actuel est affiché dans la **bottom toolbar** :

```
workspace │ Enter=send... │ debug:off │ Conf:Ask │ ollama:qwen2.5
```

L'indicateur change en temps réel quand on cycle avec `Shift+Tab`.

## 📝 Modifications Apportées

### 1. `src/agentichat/cli/confirmation.py`

#### Ajout de l'Enum `ConfirmationMode`

```python
class ConfirmationMode(Enum):
    """Modes de confirmation disponibles."""
    ASK = "ask"      # Demander confirmation (défaut)
    AUTO = "auto"    # Accepter automatiquement (après un "A")
    FORCE = "force"  # Toujours accepter sans demander
```

#### Remplacement de `passthrough_mode: bool` par `mode: ConfirmationMode`

**Avant :**
```python
self.passthrough_mode = False  # Bool simple
```

**Après :**
```python
self.mode = ConfirmationMode.ASK  # Enum avec 3 états
```

#### Nouvelle Méthode : `cycle_mode()`

```python
def cycle_mode(self) -> None:
    """Change de mode de confirmation (cyclique).

    ASK → AUTO → FORCE → ASK
    """
    if self.mode == ConfirmationMode.ASK:
        self.mode = ConfirmationMode.AUTO
    elif self.mode == ConfirmationMode.AUTO:
        self.mode = ConfirmationMode.FORCE
    else:  # FORCE
        self.mode = ConfirmationMode.ASK
```

#### Nouvelle Méthode : `get_mode_display()`

```python
def get_mode_display(self) -> str:
    """Retourne l'affichage du mode actuel pour la barre de statut.

    Returns:
        Chaîne formatée (ex: "Ask", "Auto", "Force")
    """
    if self.mode == ConfirmationMode.ASK:
        return "Ask"
    elif self.mode == ConfirmationMode.AUTO:
        return "Auto"
    else:  # FORCE
        return "Force"
```

#### Modification de `confirm()`

**Avant :**
```python
if self.passthrough_mode:
    return True
```

**Après :**
```python
if self.mode in [ConfirmationMode.AUTO, ConfirmationMode.FORCE]:
    return True
```

#### Ajout de `reset_mode()` + Alias

```python
def reset_mode(self) -> None:
    """Réinitialise le mode de confirmation à ASK."""
    self.mode = ConfirmationMode.ASK

# Compatibility alias (pour ne pas casser le code existant)
def reset_passthrough(self) -> None:
    """Alias pour reset_mode() (compatibilité)."""
    self.reset_mode()
```

### 2. `src/agentichat/cli/editor.py`

#### Ajout du paramètre `on_shift_tab`

**Constructeur :**
```python
def __init__(
    self,
    history_file: Path | None = None,
    bottom_toolbar=None,
    on_shift_tab=None  # Nouveau
) -> None:
```

#### Ajout du Keybinding Shift+Tab

```python
# Shift+Tab = Cycler les modes de confirmation
@kb.add(Keys.BackTab)  # BackTab = Shift+Tab
def _(event):  # type: ignore
    """Cycle les modes de confirmation (Ask → Auto → Force → Ask)."""
    if self.on_shift_tab:
        self.on_shift_tab()
```

#### Mise à jour de `create_editor()`

```python
def create_editor(
    history_file: Path | None = None,
    bottom_toolbar=None,
    on_shift_tab=None  # Nouveau
) -> MultiLineEditor:
    return MultiLineEditor(
        history_file=history_file,
        bottom_toolbar=bottom_toolbar,
        on_shift_tab=on_shift_tab  # Nouveau
    )
```

### 3. `src/agentichat/cli/app.py`

#### Création de l'éditeur avec callback

**Avant :**
```python
self.editor = create_editor(
    history_file=history_file,
    bottom_toolbar=self._get_bottom_toolbar
)
```

**Après :**
```python
self.editor = create_editor(
    history_file=history_file,
    bottom_toolbar=self._get_bottom_toolbar,
    on_shift_tab=self._cycle_confirmation_mode  # Nouveau
)
```

#### Nouvelle Méthode : `_cycle_confirmation_mode()`

```python
def _cycle_confirmation_mode(self) -> None:
    """Cycle les modes de confirmation et affiche un message."""
    if not self.confirmation_manager:
        return

    # Sauvegarder l'ancien mode pour affichage
    old_mode = self.confirmation_manager.get_mode_display()

    # Cycler
    self.confirmation_manager.cycle_mode()

    # Nouveau mode
    new_mode = self.confirmation_manager.get_mode_display()

    # Afficher le changement (brief, sur une ligne)
    self.console.print(
        f"[dim]Mode confirmation: {old_mode} → [bold]{new_mode}[/bold][/dim]"
    )
```

#### Affichage dans le Bottom Toolbar

**Ajout dans `_get_bottom_toolbar()` :**
```python
# Mode de confirmation
if self.confirmation_manager:
    conf_mode = self.confirmation_manager.get_mode_display()
    parts.append(f"Conf:{conf_mode}")
```

## 🎨 Expérience Utilisateur

### Scénario 1 : Mode Ask (défaut)

```bash
agentichat

# Le LLM veut créer un fichier
[Y/A/N/?] y  ← L'utilisateur doit confirmer

# Barre du bas affiche: Conf:Ask
```

### Scénario 2 : Passer en mode Auto avec "A"

```bash
# Le LLM veut créer un fichier
[Y/A/N/?] a  ← Tape "A" (Always)

✓ OUI À TOUT - Mode AUTO activé (Shift+Tab pour changer)

# Barre du bas affiche maintenant: Conf:Auto
# Plus de confirmations demandées
```

### Scénario 3 : Cycler avec Shift+Tab

```bash
> ← En train de taper un message
[Shift+Tab]  ← Tape Shift+Tab

Mode confirmation: Ask → Auto

# Barre du bas: Conf:Auto

[Shift+Tab]  ← Re-tape Shift+Tab

Mode confirmation: Auto → Force

# Barre du bas: Conf:Force

[Shift+Tab]  ← Re-tape Shift+Tab

Mode confirmation: Force → Ask

# Barre du bas: Conf:Ask
```

### Scénario 4 : Différence Auto vs Force

#### Mode **Auto**
- Activé après avoir tapé "A" lors d'une confirmation
- Persiste pour toute la session
- Reset avec `/clear`

#### Mode **Force**
- Activé manuellement avec `Shift+Tab`
- Toujours accepter, même sans avoir été demandé
- Ne nécessite pas de confirmation initiale

## 🔧 Cas d'Usage

### Pour un Développeur Pressé
```bash
# Activer mode Force au début
[Shift+Tab] [Shift+Tab]  # Ask → Auto → Force

# Maintenant tout est accepté automatiquement
# Pas de popups de confirmation
```

### Pour un Utilisateur Prudent
```bash
# Garder mode Ask (défaut)
# Confirmer manuellement chaque opération
[Y/N] selon l'opération
```

### Pour une Session de Génération de Code
```bash
# Demander au LLM de générer plusieurs fichiers
> Crée file1.py, file2.py, file3.py

# Première confirmation
[Y/A/N/?] a  ← "A" pour tout accepter

# Mode Auto activé
# Tous les fichiers créés sans redemander
```

## 📊 Tableau des Modes

| Mode | Confirmations | Activation | Reset |
|------|---------------|------------|-------|
| **Ask** | Demande à chaque fois | Défaut | - |
| **Auto** | Accepte automatiquement | Taper "A" lors d'une confirmation | `/clear` |
| **Force** | Toujours accepter | `Shift+Tab` x2 | `Shift+Tab` x1 |

## 🎓 Détails Techniques

### Enum vs Bool

**Avantage de l'Enum :**
- ✅ Extensible (facile d'ajouter un 4ème mode si besoin)
- ✅ Type-safe (pas d'erreurs de valeurs invalides)
- ✅ Auto-documenté (les valeurs sont explicites)
- ✅ Facile à afficher (`mode.value`)

**Vs Bool précédent :**
- ❌ Limité à 2 états (True/False)
- ❌ Pas extensible
- ❌ Nom peu clair (`passthrough_mode`)

### Keybinding Shift+Tab

**Pourquoi `Keys.BackTab` ?**

Dans prompt-toolkit, `Shift+Tab` est représenté par `Keys.BackTab` (backtab = tab inversé).

**Pourquoi pas Ctrl+T ou autre ?**
- `Ctrl+T` pourrait être utilisé pour d'autres fonctions
- `Shift+Tab` est intuitif (Tab inverse = cycle inverse conceptuellement)
- Rarement utilisé ailleurs dans les terminaux

### Bottom Toolbar Dynamique

Le bottom toolbar est une **fonction** appelée à chaque rafraîchissement :

```python
bottom_toolbar=self._get_bottom_toolbar
```

Cela permet d'afficher **en temps réel** le mode actuel sans besoin de rafraîchir manuellement.

## ✅ Checklist de Validation

- [x] Ajouter `ConfirmationMode` enum
- [x] Remplacer `passthrough_mode` par `mode`
- [x] Ajouter `cycle_mode()`
- [x] Ajouter `get_mode_display()`
- [x] Modifier `confirm()` pour supporter 3 modes
- [x] Ajouter keybinding `Shift+Tab` dans editor
- [x] Ajouter callback `on_shift_tab` dans editor
- [x] Ajouter `_cycle_confirmation_mode()` dans app
- [x] Afficher mode dans bottom toolbar
- [x] Vérifier syntaxe Python
- [x] Documenter
- [ ] Tester manuellement (à faire par l'utilisateur)

## 🚀 Pour Tester

### Test 1 : Mode Ask (défaut)
```bash
agentichat

# Vérifier barre du bas: Conf:Ask

> Crée test.py
# Vérifier qu'une confirmation est demandée
```

### Test 2 : Cycler avec Shift+Tab
```bash
> ← Commencer à taper
[Shift+Tab]  # Devrait afficher: Ask → Auto
# Vérifier barre: Conf:Auto

[Shift+Tab]  # Devrait afficher: Auto → Force
# Vérifier barre: Conf:Force

[Shift+Tab]  # Devrait afficher: Force → Ask
# Vérifier barre: Conf:Ask
```

### Test 3 : Mode Auto avec "A"
```bash
> Crée file1.py, file2.py
[Y/A/N/?] a  # Taper "A"

# Vérifier: "Mode AUTO activé"
# Vérifier barre: Conf:Auto
# Vérifier: plus de confirmations pour file2.py
```

### Test 4 : Mode Force
```bash
[Shift+Tab] [Shift+Tab]  # Passer en Force

# Vérifier barre: Conf:Force

> Crée plusieurs fichiers
# Vérifier: aucune confirmation demandée
```

---

**Version:** 1.0
**Date:** 2026-01-06
**Type:** Feature + UX Improvement
**Priorité:** Haute (amélioration UX majeure)
**Statut:** ✅ Implémenté, tests manuels requis
