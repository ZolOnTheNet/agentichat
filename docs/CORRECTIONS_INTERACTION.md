# Corrections d'Interaction Utilisateur

## Vue d'ensemble

Suite aux retours utilisateur, trois améliorations majeures ont été apportées au système d'interaction :

1. ✓ Remplacement de `input()` par un prompt interactif dans les confirmations
2. ✓ Amélioration du spinner avec messages variés au lieu du temps écoulé
3. ✓ Clarification des raccourcis clavier (ESC, Ctrl+C)

---

## 1. ✓ Prompt interactif pour les confirmations

### Problème
> "il a fallut que je appuie plusieurs fois sur Y (y ou Y) et fasse entrée pour que cela puisse être pris. La boucle c'est arrêté. En fait, il n'y pas de prompt pour répondre : il faut tapper Y puis faire entrée."

L'utilisation de `input()` standard ne s'intégrait pas bien avec l'interface async de prompt-toolkit, causant :
- Nécessité d'appuyer plusieurs fois sur Y
- Pas de feedback visuel pendant la saisie
- Boucle qui se bloque

### Solution
**Fichier**: `src/agentichat/cli/confirmation.py` (lignes 6-50)

Remplacement de `input()` par `PromptSession` de prompt-toolkit avec validation automatique :

```python
from prompt_toolkit import PromptSession
from prompt_toolkit.key_binding import KeyBindings

class ConfirmationManager:
    def __init__(self, console: Console) -> None:
        self.console = console
        self.passthrough_mode = False
        self.prompt_session = PromptSession()
        self._setup_keybindings()

    def _setup_keybindings(self) -> None:
        """Configure les raccourcis clavier pour la confirmation."""
        self.kb = KeyBindings()

        # Validation automatique sur Y/N/A/? (pas besoin de faire Entrée)
        @self.kb.add("y")
        def _(event):
            event.current_buffer.text = "y"
            event.current_buffer.validate_and_handle()

        @self.kb.add("n")
        def _(event):
            event.current_buffer.text = "n"
            event.current_buffer.validate_and_handle()

        @self.kb.add("a")
        def _(event):
            event.current_buffer.text = "a"
            event.current_buffer.validate_and_handle()

        @self.kb.add("?")
        def _(event):
            event.current_buffer.text = "?"
            event.current_buffer.validate_and_handle()

    async def confirm(self, tool_name: str, arguments: dict[str, Any]) -> bool:
        # ...
        response = await self.prompt_session.prompt_async(
            "\n[Y/A/N/?] ",
            key_bindings=self.kb,
        )
        # ...
```

**Résultat** :
- ✅ Validation automatique : taper Y suffit, pas besoin de faire Entrée
- ✅ Feedback visuel : l'utilisateur voit sa frappe
- ✅ Intégration async propre avec le reste de l'interface
- ✅ Ctrl+C / Ctrl+D pour annuler la confirmation

---

## 2. ✓ Spinner avec messages variés

### Problème
> "Peux ton avoir au lieu du temps qui augmente (cela ne change pas la perception), les tokens utilisé ou autre ?"

Le temps écoulé qui augmente (3.2s... 3.3s... 3.4s...) ne donne pas l'impression de progression, juste que ça prend du temps.

**Note sur les tokens** : L'API Ollama standard ne fournit pas d'information de progression en temps réel. Les statistiques de tokens ne sont disponibles qu'après la réponse complète.

### Solution
**Fichier**: `src/agentichat/cli/app.py` (lignes 252-295)

Remplacement du compteur de temps par des messages qui varient cycliquement :

```python
async def _process_agent_loop(self) -> None:
    # Messages variés pour le spinner
    messages = [
        "Le LLM analyse votre demande",
        "Le LLM génère une réponse",
        "Le LLM prépare les actions",
        "Le LLM organise les outils",
        "Le LLM affine sa réponse",
        "Le LLM réfléchit",
    ]

    spinner = Spinner("dots", text="")
    message_index = 0

    async def update_spinner():
        """Fait varier le message du spinner pour donner l'impression de progression."""
        nonlocal message_index
        while True:
            # Changer de message toutes les 1.5 secondes
            spinner.text = Text(messages[message_index % len(messages)] + "...", style="cyan")
            message_index += 1
            await asyncio.sleep(1.5)

    # Lancer la mise à jour du spinner en arrière-plan
    update_task = asyncio.create_task(update_spinner())

    try:
        with Live(spinner, console=self.console, transient=True, refresh_per_second=4):
            response, updated_messages = await self.agent.run(self.messages)
    finally:
        update_task.cancel()
```

**Résultat** :
- ✅ Messages qui changent toutes les 1.5s donnent l'impression de progression
- ✅ Cycle de 6 messages différents
- ✅ Pas de compteur de temps anxiogène
- ✅ Rafraîchissement à 4 Hz (optimisé pour la perception)

**Exemple d'affichage** :
```
● Le LLM analyse votre demande...
● Le LLM génère une réponse...
● Le LLM prépare les actions...
```

---

## 3. ✓ Clarification des raccourcis clavier

### Problème
> "il faudra aussi voir si les commandes comme ESC sont bien prise (càd en dehors de la saisie), indiquer si elle ont été interceptées par le système"

Manque de clarté sur :
- Quelle touche fait quoi
- Si ESC fonctionne en dehors de la saisie
- Comment annuler un traitement en cours

### Solution

#### A. Message de démarrage amélioré
**Fichier**: `src/agentichat/cli/app.py` (lignes 175-182)

```python
self.console.print("\n[bold cyan]agentichat[/bold cyan] - Mode agentique activé")
self.console.print(
    "[dim]Shift+Enter=nouvelle ligne │ Enter=envoyer │ "
    "ESC=vider saisie │ Ctrl+C=annuler traitement │ Ctrl+D=quitter[/dim]"
)
```

#### B. Gestion de ESC clarifiée
**Fichier**: `src/agentichat/cli/editor.py` (lignes 92-97)

```python
# ESC = annuler la saisie en cours
@kb.add(Keys.Escape)
def _(event):
    """Annule la saisie en cours."""
    event.current_buffer.text = ""
    # Note: L'utilisateur verra le buffer se vider comme feedback visuel
```

**ESC** : Vide le buffer de saisie (feedback immédiat : le texte disparaît)

#### C. Gestion de Ctrl+C pendant le traitement
**Fichier**: `src/agentichat/cli/app.py` (lignes 305-307)

```python
except KeyboardInterrupt:
    self.console.print("\n[yellow]Requête annulée par l'utilisateur[/yellow]\n")
    logger.info("Request cancelled by user")
```

**Ctrl+C** : Annule le traitement du LLM en cours (pendant le spinner)

### Résumé des touches

| Touche | Contexte | Action |
|--------|----------|--------|
| **Shift+Enter** | Pendant saisie | Nouvelle ligne |
| **Enter** | Pendant saisie | Envoyer le message |
| **ESC** | Pendant saisie | Vider le buffer (feedback : texte disparaît) |
| **Ctrl+C** | Pendant traitement LLM | Annuler le traitement en cours |
| **Ctrl+D** | N'importe quand | Quitter l'application |
| **Y/N/A/?** | Confirmation | Validation automatique (pas besoin d'Entrée) |

---

## Tests recommandés

### 1. Test confirmation interactive

```bash
> créer un fichier test.py avec print("hello")

📝 Écriture de fichier
Fichier : test.py
[preview du contenu]

[Y/A/N/?] y    # ← Juste taper Y, validation automatique !
[bold green on black] ✓ OUI - Opération acceptée [/bold green on black]
```

### 2. Test spinner varié

```bash
> écris un programme complexe

● Le LLM analyse votre demande...
● Le LLM génère une réponse...
● Le LLM prépare les actions...
[messages changent toutes les 1.5s]
```

### 3. Test ESC et Ctrl+C

```bash
# Test ESC pendant saisie
> Ceci est un test<ESC>    # ← Texte disparaît immédiatement
>

# Test Ctrl+C pendant traitement
> écris un très long programme
● Le LLM réfléchit...
<Ctrl+C>
Requête annulée par l'utilisateur
```

---

## Fichiers modifiés

1. **`src/agentichat/cli/confirmation.py`**
   - Ajout de `PromptSession` et `KeyBindings`
   - Validation automatique sur touches uniques
   - Gestion async propre

2. **`src/agentichat/cli/app.py`**
   - Spinner avec messages variés (au lieu du temps)
   - Message de démarrage clarifié avec tous les raccourcis
   - Refresh à 4 Hz au lieu de 10 Hz

3. **`src/agentichat/cli/editor.py`**
   - Commentaire clarifié pour ESC
   - Feedback visuel automatique (texte qui disparaît)

---

## Améliorations UX

✅ **Confirmation plus intuitive** : Une seule touche suffit, pas besoin d'Entrée
✅ **Perception de progression** : Messages variés au lieu d'un chronomètre anxiogène
✅ **Raccourcis documentés** : L'utilisateur sait exactement quelles touches utiliser
✅ **Feedback visuel** : ESC vide le buffer instantanément (feedback immédiat)
✅ **Annulation claire** : Ctrl+C pendant traitement avec message explicite

---

## Notes techniques

### Pourquoi pas les tokens en temps réel ?

L'API Ollama standard (`/api/chat`) ne fournit pas de progression en temps réel. Les informations disponibles sont :
- **Après la réponse complète** : `prompt_eval_count`, `eval_count`, etc.
- **En mode streaming** : On reçoit les tokens au fur et à mesure, mais pas de compteur global

Pour afficher les tokens en temps réel, il faudrait :
1. Utiliser le streaming et compter les tokens reçus
2. Ou attendre la fin et afficher le total

Le système actuel (messages variés) offre un meilleur feedback psychologique qu'un compteur qui monte.

### Validation automatique vs Entrée

Les keybindings avec `validate_and_handle()` permettent une UX plus fluide :
- L'utilisateur tape juste **Y** → validation immédiate
- Pas besoin de **Y + Entrée**
- Compatible avec le flow async de prompt-toolkit

---

## Statut

✅ Toutes les corrections appliquées
✅ Interface plus réactive et intuitive
✅ Feedback visuel amélioré sur toutes les interactions
✅ Documentation claire des raccourcis clavier
