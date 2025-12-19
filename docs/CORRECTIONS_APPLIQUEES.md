# Corrections appliquées - agentichat

## Vue d'ensemble

Deux corrections importantes ont été appliquées suite aux retours utilisateur:
1. Déplacement de la barre d'information en pied de page
2. Correction de l'erreur JSON lors des appels de tools

---

## 1. ✓ Ordre d'affichage - Pied de page

### Problème
La barre d'information s'affichait AVANT la zone de saisie (en-tête), ce qui était visuellement confus.

### Avant (incorrect)
```
────────────────────────────────────────────────────────────────
myproject | Enter=send Shift+Enter=newline | debug:on | ollama:qwen2.5
> Bonjour