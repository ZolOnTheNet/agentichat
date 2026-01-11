# Support du Format XML de Qwen3 pour Tool Calls

## 🎯 Problème Résolu

Le modèle **Qwen/Qwen3-Coder-30B-A3B-Instruct** sur Albert API génère les tool calls dans un **format XML propriétaire** qui n'était pas supporté.

### Symptôme
```
A:
Je vais analyser le programme dans le répertoire courant.
<tool_call>
<function=list_files>
<parameter=path>
.
</parameter>
</function>
</tool_call>
```

Le LLM générait correctement l'intention de tool call, mais **rien ne s'exécutait** car le format n'était pas reconnu.

## ✅ Solution Implémentée

Ajout du **Format 4** dans `src/agentichat/backends/albert.py` : parser XML pour Qwen3.

### Format XML Supporté

```xml
<tool_call>
  <function=nom_du_tool>
    <parameter=nom_param1>valeur1</parameter>
    <parameter=nom_param2>valeur2</parameter>
  </function>
</tool_call>
```

### Exemples Supportés

#### Tool call simple
```xml
<tool_call>
<function=list_files>
<parameter=path>.</parameter>
</function>
</tool_call>
```
→ Exécute `list_files(path=".")`

#### Tool call avec plusieurs paramètres
```xml
<tool_call>
<function=read_file>
<parameter=path>/home/user/test.py</parameter>
<parameter=encoding>utf-8</parameter>
</function>
</tool_call>
```
→ Exécute `read_file(path="/home/user/test.py", encoding="utf-8")`

#### Plusieurs tool calls dans la même réponse
```xml
<tool_call>
<function=list_files>
<parameter=path>.</parameter>
</function>
</tool_call>

<tool_call>
<function=read_file>
<parameter=path>README.md</parameter>
</function>
</tool_call>
```
→ Exécute les deux tool calls séquentiellement

## 📝 Modification du Code

### Fichier : `src/agentichat/backends/albert.py`

**Fonction modifiée :** `_extract_tool_calls_from_text()`

**Ajout du Format 4 :** (lignes ~182-209)

```python
# Format 4: Format XML de Qwen3 - <tool_call><function=...><parameter=...>
xml_pattern = r'<tool_call>\s*<function=(\w+)>(.*?)</function>\s*</tool_call>'
xml_matches = re.finditer(xml_pattern, content, re.DOTALL)

for match in xml_matches:
    tool_name = match.group(1)
    params_block = match.group(2)

    # Parser les paramètres - format: <parameter=name>value</parameter>
    arguments = {}
    param_pattern = r'<parameter=(\w+)>(.*?)</parameter>'
    param_matches = re.finditer(param_pattern, params_block, re.DOTALL)

    for param_match in param_matches:
        param_name = param_match.group(1)
        param_value = param_match.group(2).strip()
        arguments[param_name] = param_value

    tool_call = ToolCall(
        id=str(uuid.uuid4()),
        name=tool_name,
        arguments=arguments,
    )
    tool_calls.append(tool_call)
    logger.info(f"Extracted tool call from XML format (Qwen3): {tool_name}")
```

## 🧪 Tests

### Fichier de Test : `test_qwen3_xml_format.py`

**Tests couverts :**
1. ✅ Format XML simple avec 1 paramètre
2. ✅ Format XML avec plusieurs paramètres
3. ✅ Format XML avec espaces et indentation
4. ✅ Plusieurs tool calls dans le même texte
5. ✅ Compatibilité avec les formats existants (JSON, etc.)

**Résultat :**
```
======================================================================
✅ TOUS LES TESTS SONT PASSÉS !
======================================================================
```

## 📊 Formats Supportés au Total

Le backend Albert supporte maintenant **4 formats** de tool calls :

### 1. Format `[TOOL_CALLS]` (Custom)
```
[TOOL_CALLS]list_files{"path": "."}
```

### 2. Format JSON Markdown (Standard)
```markdown
```json
{"name": "list_files", "arguments": {"path": "."}}
```
```

### 3. Format JSON Direct (Standard)
```json
{"name": "list_files", "arguments": {"path": "."}}
```

### 4. Format XML Qwen3 (Nouveau ✨)
```xml
<tool_call>
<function=list_files>
<parameter=path>.</parameter>
</function>
</tool_call>
```

## 🚀 Utilisation

### Modèles Compatibles

Vous pouvez maintenant utiliser **tous les modèles Qwen3** sur Albert :

```bash
# Dans agentichat
/albert run Qwen/Qwen3-Coder-30B-A3B-Instruct

# Tester
> dis moi ce que fait le programme dans le répertoire courant
```

Le LLM va maintenant **exécuter les tool calls** correctement au lieu de juste afficher le XML.

### Autres Modèles Recommandés

Si vous rencontrez des problèmes avec Qwen3, ces modèles utilisent le format JSON standard :

- ✅ `meta-llama/Llama-3.1-8B-Instruct` (Recommandé, léger)
- ✅ `mistralai/Mistral-Small-3.2-24B-Instruct-2512` (Puissant)
- ✅ `Qwen/Qwen2.5-Coder-32B-Instruct-AWQ` (Version AWQ)

## 📈 Impact

### Avant
- ❌ Qwen3 générait du XML non-exécuté
- ❌ Tool calls ignorés
- ❌ Pas d'interaction avec le système de fichiers

### Après
- ✅ Format XML reconnu et parsé
- ✅ Tool calls exécutés correctement
- ✅ Compatibilité totale avec Qwen3-Coder-30B
- ✅ Rétro-compatible avec tous les formats existants

## 🔍 Détails Techniques

### Regex Utilisée

**Pattern principal :**
```python
r'<tool_call>\s*<function=(\w+)>(.*?)</function>\s*</tool_call>'
```
- Capture le nom du tool dans `<function=NOM>`
- Capture tout le bloc de paramètres entre `<function>` et `</function>`

**Pattern des paramètres :**
```python
r'<parameter=(\w+)>(.*?)</parameter>'
```
- Capture chaque paire nom/valeur
- Supporte les espaces et retours à la ligne dans les valeurs

### Robustesse

- ✅ Supporte les espaces et indentations
- ✅ Supporte les valeurs multilignes
- ✅ Supporte les caractères spéciaux dans les valeurs
- ✅ Génère des UUIDs uniques pour chaque tool call
- ✅ Logging détaillé (`logger.info`)

## 📚 Documentation Mise à Jour

- ✅ `CLAUDE.md` - À mettre à jour avec le nouveau format
- ✅ `.claude/INSTRUCTIONS.md` - Déjà à jour
- ✅ Ce document (`FEATURE_QWEN3_XML_SUPPORT.md`)

## 🎓 Pour les Développeurs

### Ajouter un Nouveau Format

Si un autre modèle utilise un format différent, suivez ce pattern dans `_extract_tool_calls_from_text()` :

```python
# Format 5: Votre nouveau format
pattern = r'...'  # Votre regex
matches = re.finditer(pattern, content, re.DOTALL)

for match in matches:
    # Parser le match
    tool_name = ...
    arguments = {}

    # Créer le ToolCall
    tool_call = ToolCall(
        id=str(uuid.uuid4()),
        name=tool_name,
        arguments=arguments,
    )
    tool_calls.append(tool_call)
    logger.info(f"Extracted tool call from NEW format: {tool_name}")
```

### Tests

Toujours créer un test dans `test_*.py` pour valider le nouveau format.

---

**Version:** 1.0
**Date:** 2026-01-06
**Auteur:** Claude Code + garrigues
**Statut:** ✅ Implémenté et testé
**Impact:** Compatibilité avec Qwen3-Coder-30B sur Albert API
