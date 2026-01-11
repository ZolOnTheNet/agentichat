# Bugfix : Confirmations "Always" et Affichage des Warnings

## 🐛 Problèmes Identifiés

### Problème 1 : Mode "Always" ne persiste pas

**Symptôme :**
- L'utilisateur tape "A" (Always) pour accepter toutes les confirmations
- Fonctionne pour la requête en cours
- Mais à la **prochaine requête**, le système redemande confirmation

**Comportement attendu :**
- Quand l'utilisateur tape "A", il ne veut **plus jamais** être dérangé
- Le mode "Always" devrait persister pour **toute la session**
- Seulement reset avec `/clear` (nouvelle conversation)

### Problème 2 : Affichage du pourcentage inversé

**Symptôme :**
```
💡 Info: Vous avez 26 messages (130% du seuil de 20)
```

**Problème :**
- Mathématiquement correct (26/20 = 1.3 = 130%)
- Mais message confus et contre-intuitif
- L'utilisateur s'attend à voir "26/20 messages (seuil dépassé)"

## ✅ Solutions Implémentées

### Solution 1 : Mode "Always" persistant

#### Avant
```python
# app.py ligne 467-469
# Réinitialiser le mode passthrough pour cette requête
if self.confirmation_manager:
    self.confirmation_manager.reset_passthrough()
```

**Comportement :**
- ❌ Reset à **chaque nouvelle requête** utilisateur
- ❌ "Always" ne dure qu'une seule requête

#### Après
```python
# app.py ligne 467-468
# Note: Le mode passthrough (Always) persiste pour toute la session
# et n'est pas réinitialisé entre les requêtes
```

**Comportement :**
- ✅ Mode "Always" persiste **toute la session**
- ✅ Seulement reset avec `/clear`

#### Mise à Jour de la Documentation

```python
# confirmation.py ligne 200-202 - Avant
[yellow]A[/yellow] / [yellow]All[/yellow]
    Accepte cette opération ET toutes les suivantes
    (active le mode passthrough jusqu'à la fin de la requête)

# Après
[yellow]A[/yellow] / [yellow]All[/yellow]
    Accepte cette opération ET toutes les suivantes
    (active le mode passthrough pour toute la session)
```

#### Reset avec /clear

```python
# app.py ligne 413-419
if user_input == "/clear":
    self.messages = []
    # Réinitialiser aussi le mode passthrough (nouvelle conversation)
    if self.confirmation_manager:
        self.confirmation_manager.reset_passthrough()
    self.console.print("[dim]Conversation réinitialisée[/dim]\n")
    continue
```

Logique : **nouvelle conversation = reset des préférences**

### Solution 2 : Affichage du Warning amélioré

#### Avant
```python
# app.py ligne 519-523
pct_display = int(current_pct * 100)
self.console.print(
    f"\n[bold yellow]💡 Info:[/bold yellow] Vous avez {message_count} messages "
    f"({pct_display}% du seuil de {threshold})"
)
```

**Exemples d'affichage :**
- 26 messages / seuil 20 → "26 messages (130% du seuil de 20)" ❌ Confus
- 15 messages / seuil 20 → "15 messages (75% du seuil de 20)" ❌ Verbeux

#### Après
```python
# app.py ligne 518-532
pct_display = int(current_pct * 100)

# Message adapté selon si on a dépassé le seuil ou pas
if message_count >= threshold:
    # Dépassé
    over_pct = int((current_pct - 1) * 100)
    status = f"[bold red]seuil dépassé de {over_pct}%[/bold red]" if over_pct > 0 else "[bold red]seuil atteint[/bold red]"
else:
    # Proche mais pas encore dépassé
    status = f"{pct_display}% du seuil"

self.console.print(
    f"\n[bold yellow]💡 Info:[/bold yellow] Vous avez {message_count}/{threshold} messages "
    f"({status})"
)
```

**Nouveaux exemples d'affichage :**
- 26 messages / seuil 20 → "26/20 messages ([bold red]seuil dépassé de 30%[/bold red])" ✅ Clair
- 20 messages / seuil 20 → "20/20 messages ([bold red]seuil atteint[/bold red])" ✅ Précis
- 15 messages / seuil 20 → "15/20 messages (75% du seuil)" ✅ Lisible
- 18 messages / seuil 20 → "18/20 messages (90% du seuil)" ✅ Alerte claire

## 📊 Impact des Changements

### Problème 1 - Mode "Always"

#### Avant
```
Session:
1. User: "crée file1.py"
   → LLM veut write_file
   → Demande confirmation → User tape "A" ✅
   → Mode passthrough activé

2. User: "crée file2.py"
   → LLM veut write_file
   → Mode passthrough reset ❌
   → Redemande confirmation ❌
```

#### Après
```
Session:
1. User: "crée file1.py"
   → LLM veut write_file
   → Demande confirmation → User tape "A" ✅
   → Mode passthrough activé

2. User: "crée file2.py"
   → LLM veut write_file
   → Mode passthrough toujours actif ✅
   → Pas de confirmation ✅

3. User: "/clear"
   → Mode passthrough reset
   → Nouvelle conversation, redemandera confirmation
```

### Problème 2 - Affichage Warning

#### Avant
```
Seuil: 20, Warning: 75% (15 msg)

15 messages → Pas d'affichage (< 75%)
16 messages → "16 messages (80% du seuil de 20)"
20 messages → "20 messages (100% du seuil de 20)"
26 messages → "26 messages (130% du seuil de 20)" ❌ Confus
```

#### Après
```
Seuil: 20, Warning: 75% (15 msg)

15 messages → Pas d'affichage (< 75%)
16 messages → "16/20 messages (80% du seuil)" ✅
20 messages → "20/20 messages (seuil atteint)" ✅ Rouge
26 messages → "26/20 messages (seuil dépassé de 30%)" ✅ Rouge + clair
```

## 🧪 Scénarios de Test

### Test 1 : Mode "Always" persiste

```bash
# Lancer agentichat
agentichat

# Demander création de plusieurs fichiers
> Crée file1.py, file2.py et file3.py

# Première confirmation
[Y/A/N/?] A  ← Taper "A"

# Vérifier qu'aucune autre confirmation n'est demandée ✅

# Nouvelle requête
> Crée file4.py et file5.py

# Vérifier qu'aucune confirmation n'est demandée ✅

# Reset avec /clear
/clear

# Nouvelle requête
> Crée file6.py

# Vérifier qu'une confirmation est demandée ✅ (après /clear)
```

### Test 2 : Affichage Warning

```bash
# Configurer un seuil bas pour tester
/config compress --auto 10 3

# Envoyer 8 messages (80% du seuil)
> message 1
> message 2
...
> message 8

# Vérifier affichage: "8/10 messages (80% du seuil)" ✅

# Envoyer 2 messages de plus (atteindre le seuil)
> message 9
> message 10

# Vérifier affichage: "10/10 messages (seuil atteint)" ✅ Rouge

# Envoyer 3 messages de plus (dépasser)
> message 11
> message 12
> message 13

# Vérifier affichage: "13/10 messages (seuil dépassé de 30%)" ✅ Rouge
```

## 📝 Fichiers Modifiés

### 1. `src/agentichat/cli/app.py`

**Ligne 467-468 :** Suppression du reset passthrough entre requêtes
```python
# Avant: reset à chaque requête
# Après: commentaire explicatif, pas de reset
```

**Ligne 413-419 :** Ajout reset avec `/clear`
```python
if user_input == "/clear":
    # ... reset messages ...
    if self.confirmation_manager:
        self.confirmation_manager.reset_passthrough()
```

**Ligne 518-532 :** Amélioration affichage warning
```python
# Distinction entre "dépassé" et "proche du seuil"
# Format "X/Y messages" au lieu de "X messages (Z%)"
# Couleur rouge quand dépassé
```

### 2. `src/agentichat/cli/confirmation.py`

**Ligne 200-202 :** Mise à jour documentation
```python
# Avant: "jusqu'à la fin de la requête"
# Après: "pour toute la session"
```

## 🎓 Leçons Apprises

### Design Pattern : Stateful Confirmations

Le mode "Always" est un **état de session** qui devrait :
1. ✅ Persister entre les requêtes de l'utilisateur
2. ✅ Reset seulement lors d'actions explicites (`/clear`)
3. ✅ Être clairement documenté dans l'aide (`?`)

### UX : Messages Clairs

Les messages de warning doivent :
1. ✅ Utiliser un format lisible (ex: "X/Y" au lieu de "%")
2. ✅ Adapter le message selon le contexte (proche vs dépassé)
3. ✅ Utiliser des couleurs pour attirer l'attention (rouge = urgent)

## ✅ Checklist de Validation

- [x] Identifier les deux problèmes
- [x] Corriger le mode "Always" persistant
- [x] Ajouter reset avec `/clear`
- [x] Améliorer l'affichage du warning
- [x] Mettre à jour la documentation
- [x] Vérifier la syntaxe Python
- [x] Documenter les changements
- [ ] Tester manuellement (à faire par l'utilisateur)

## 🚀 Pour Tester

1. **Lancer agentichat**
2. **Tester "Always"** : Demander plusieurs créations de fichiers avec "A"
3. **Vérifier persistence** : Nouvelle requête ne doit pas redemander
4. **Tester /clear** : Après `/clear`, doit redemander
5. **Tester warning** : Configurer seuil bas et vérifier l'affichage

---

**Version:** 1.0
**Date:** 2026-01-06
**Type:** Bugfix + UX Improvement
**Priorité:** Haute (UX majeure)
**Statut:** ✅ Implémenté, tests manuels requis
