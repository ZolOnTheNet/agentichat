# Commande /prompt - Personnalisation du prompt et barre d'information

La commande `/prompt` permet de personnaliser l'apparence du prompt et de gérer l'affichage de la barre d'information contextuelle.

## Fonctionnalités

### 1. Barre d'information contextuelle

Avant chaque prompt, agentichat affiche une barre d'information compacte avec:

```
────────────────────────────────────────────────────────────────
agentichat │ Enter=send Shift+Enter=newline │ debug:on │ ollama:qwen2.5
>
```

**Informations affichées:**
- **Workspace**: Nom du répertoire de travail actuel
- **Mode d'édition**: Rappel des touches Enter et Shift+Enter
- **Debug**: État du mode debug (on/off)
- **Backend/Modèle**: Type de backend et modèle actuel

**Avantages:**
- Visibilité immédiate du contexte
- Délimitation claire entre requête et réponse
- Informations essentielles toujours visibles
- S'adapte à la largeur du terminal

---

### 2. Prompt personnalisable

Le symbole de prompt peut être personnalisé selon vos préférences.

#### Afficher le prompt actuel

```bash
> /prompt

Prompt actuel: >
```

#### Prompts prédéfinis

8 variantes de prompt sont disponibles:

```bash
> /prompt list

=== Prompts prédéfinis ===
● classic      → >
  lambda       → λ
  arrow        → →
  chevron      → »
  prompt       → $
  hash         → #
  star         → ★
  minimal      → ·

Usage: /prompt <nom> ou /prompt <texte_personnalisé>
```

#### Changer de prompt

```bash
# Utiliser un prompt prédéfini
> /prompt lambda

✓ Prompt changé: λ

# Le nouveau prompt est actif
λ Bonjour
```

```bash
# Utiliser un prompt personnalisé
> /prompt 🚀

✓ Prompt personnalisé: 🚀

🚀 Test
```

#### Réinitialiser le prompt

```bash
> /prompt reset

✓ Prompt réinitialisé: >
```

---

### 3. Gestion de la barre d'information

#### Activer/désactiver la barre

```bash
> /prompt toggle

✓ Barre d'information désactivée
```

Lorsque désactivée, seul le prompt s'affiche (mode minimaliste):

```
> Bonjour
```

Pour réactiver:

```bash
> /prompt toggle

✓ Barre d'information activée
```

---

## Exemples d'utilisation

### Exemple 1: Style développeur

```bash
# Prompt lambda pour un style fonctionnel
> /prompt lambda

✓ Prompt changé: λ

────────────────────────────────────────────────────────────────
myproject │ Enter=send Shift+Enter=newline │ debug:off │ ollama:qwen2.5
λ Explique-moi les monades
```

### Exemple 2: Style minimaliste

```bash
# Prompt minimal + barre désactivée
> /prompt minimal

✓ Prompt changé: ·

> /prompt toggle

✓ Barre d'information désactivée

· Liste les fichiers Python
```

### Exemple 3: Style personnalisé

```bash
# Emoji ou texte personnalisé
> /prompt 🤖

✓ Prompt personnalisé: 🤖

────────────────────────────────────────────────────────────────
agentichat │ Enter=send Shift+Enter=newline │ debug:on │ ollama:llama3
🤖 Bonjour !
```

### Exemple 4: Style shell

```bash
# Prompt $ comme un shell
> /prompt prompt

✓ Prompt changé: $

────────────────────────────────────────────────────────────────
workspace │ Enter=send Shift+Enter=newline │ debug:off │ ollama:qwen2.5
$ ls
```

---

## Barre d'information détaillée

### Workspace

Affiche le nom du répertoire de travail actuel:

```
myproject │ ...
```

- Court et lisible
- S'adapte au répertoire actuel
- Utile pour savoir où on travaille

### Mode d'édition

Rappel permanent des touches importantes:

```
... │ Enter=send Shift+Enter=newline │ ...
```

- **Enter**: Envoie le message
- **Shift+Enter**: Nouvelle ligne dans le message

### État debug

Indique si le mode debug est actif:

```
... │ debug:on │ ...   (mode debug actif - logs détaillés)
... │ debug:off │ ...  (mode normal)
```

- **on** (vert): Logs de debug actifs
- **off** (grisé): Mode normal

Changer avec: `/config debug on` ou `/config debug off`

### Backend et modèle

Affiche le backend utilisé et le modèle actuel:

```
... │ ollama:qwen2.5
... │ ollama:llama3
```

- **Backend**: Type (ollama, openai, etc.)
- **Modèle**: Nom du modèle (raccourci si trop long)
- Change avec: `/ollama run <model>`

---

## Séparateur de réponse

Après chaque réponse du LLM, un séparateur visuel est affiché:

```
Assistant: Voici ma réponse...

────────────────────────────────────────────────────────────────

```

**Avantages:**
- Délimitation claire entre les réponses
- Facilite la lecture de conversations longues
- S'adapte à la largeur du terminal

---

## Compatibilité multi-environnement

Le système de prompt est conçu pour fonctionner sur différents environnements:

### Terminaux supportés

- **Linux**: Gnome Terminal, Konsole, xterm, etc.
- **macOS**: Terminal.app, iTerm2
- **Windows**: Windows Terminal, PowerShell, cmd (avec support UTF-8)

### Adaptation automatique

- Détection automatique de la largeur du terminal
- Fallback à 80 colonnes si détection impossible
- Prompts Unicode (λ, →, ★) avec fallback ASCII

### Caractères spéciaux

Les prompts utilisent des caractères Unicode:

| Prompt | Caractère | Support |
|--------|-----------|---------|
| classic | `>` | Universel |
| lambda | `λ` | UTF-8 requis |
| arrow | `→` | UTF-8 requis |
| chevron | `»` | UTF-8 requis |
| star | `★` | UTF-8 requis |
| minimal | `·` | UTF-8 requis |

Si les caractères ne s'affichent pas correctement, utilisez:
```bash
> /prompt classic
```

---

## Architecture technique

```
PromptManager
├── prompt_text: str            # Symbole du prompt
├── show_info_bar: bool         # État de la barre d'info
│
├── get_prompt() → str          # Retourne le prompt formaté
├── set_prompt(text)            # Change le prompt
├── show_info(...)              # Affiche la barre d'info
├── show_separator()            # Affiche le séparateur
├── toggle_info_bar() → bool    # Active/désactive la barre
└── get_prompt_variants() → dict # Prompts prédéfinis

ChatApp
├── prompt_manager: PromptManager
│
└── _handle_prompt_command()    # Handler de /prompt
    ├── list                    # Liste les variantes
    ├── reset                   # Réinitialise
    ├── toggle                  # Active/désactive barre
    └── <text>                  # Change le prompt
```

---

## Commandes disponibles

```bash
/prompt                         # Affiche le prompt actuel
/prompt list                    # Liste les prompts prédéfinis
/prompt <nom>                   # Utilise un prompt prédéfini
/prompt <texte>                 # Définit un prompt personnalisé
/prompt reset                   # Réinitialise au prompt par défaut (>)
/prompt toggle                  # Active/désactive la barre d'info
```

---

## Cas d'usage

### 1. Développeur fonctionnel
```bash
/prompt lambda
# Prompt λ pour un style fonctionnel
```

### 2. Mode focus (minimal)
```bash
/prompt minimal
/prompt toggle
# Prompt discret sans barre d'info
```

### 3. Debugging
```bash
/config debug on
# La barre d'info montre debug:on
# Les logs détaillés sont visibles avec /log show
```

### 4. Multi-projets
```bash
cd project1/
# Barre d'info montre: project1 │ ...

cd ../project2/
# Barre d'info montre: project2 │ ...
```

### 5. Test de modèles
```bash
/ollama run qwen2.5:3b
# Barre d'info montre: ollama:qwen2.5

/ollama run llama3:8b
# Barre d'info montre: ollama:llama3
```

---

## Personnalisation future

Le système est extensible pour de futures améliorations:

### Prévues
- Configuration persistante du prompt dans config.yaml
- Templates de barre d'info personnalisables
- Couleurs configurables
- Plus de variantes prédéfinies

### Exemples de futurs prompts
```bash
/prompt coding      →  </>
/prompt thinking    →  💭
/prompt question    →  ❓
/prompt command     →  ⌘
```

---

## Résolution de problèmes

### Les caractères Unicode ne s'affichent pas

**Symptôme**: Les caractères λ, →, ★ apparaissent comme □ ou ?

**Solution**:
```bash
# Utiliser un prompt ASCII
> /prompt classic

# Ou vérifier l'encoding du terminal
$ echo $LANG
# Devrait afficher UTF-8
```

### La barre d'info est trop large

**Symptôme**: La barre dépasse la largeur du terminal

**Solution**:
```bash
# Agrandir le terminal
# Ou désactiver la barre
> /prompt toggle
```

### Le prompt ne change pas

**Symptôme**: Le prompt reste identique après `/prompt <text>`

**Solution**:
```bash
# Vérifier que la commande a bien été exécutée
> /prompt lambda

✓ Prompt changé: λ  # Ce message doit apparaître

# Le nouveau prompt apparaît à la prochaine saisie
```

---

## Aide rapide

```bash
/prompt              # Voir le prompt actuel
/prompt list         # Voir tous les prompts
/prompt lambda       # Changer vers λ
/prompt 🚀          # Prompt personnalisé
/prompt toggle       # Masquer/afficher barre d'info
/prompt reset        # Revenir à >
```

Pour plus d'informations: `/help`
