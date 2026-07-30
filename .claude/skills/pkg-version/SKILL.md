---
name: "pkg-version"
description: Créer une nouvelle version de py-ce-forms-api — bump setup.py, mise à jour CHANGELOG, commit/tag git, puis build et publication du package (twine)
---

Crée une nouvelle version du package `py_ce_forms_api` : bump de la version dans `setup.py`, entrée `CHANGELOG.md`, commit et tag git, puis build et publication optionnelle sur un dépôt PyPI.

**Input** : type de bump, version explicite, ou `publish` (optionnel).

Exemples :
- `/pkg-version` — mode interactif, demande le type de bump
- `/pkg-version patch` — bump patch (0.1.17 → 0.1.18)
- `/pkg-version minor` — bump minor (0.1.17 → 0.2.0)
- `/pkg-version major` — bump major (0.1.17 → 1.0.0)
- `/pkg-version 0.2.0` — version explicite
- `/pkg-version publish` — pas de bump : build + publication de la version courante (aller directement à la section 9)

---

## 1. Lire la version actuelle

Lire `setup.py` et extraire la version courante de la ligne :

```python
VERSION = 'X.Y.Z'
```

> La version n'est définie **qu'à cet endroit** (pas de `pyproject.toml`, pas de `__version__` dans le package). Ne pas en introduire d'autre.

Vérifier aussi la version en tête de `CHANGELOG.md` (`## [X.Y.Z]`) :
- Si elle est **identique** à `setup.py` → la version courante est déjà consignée, on bumpe à partir d'elle.
- Si elle est **différente**, signaler l'incohérence à l'utilisateur avant de continuer.

Afficher :
```
Version actuelle : X.Y.Z
```

## 2. Déterminer la nouvelle version

Si l'argument fourni est `patch`, `minor` ou `major`, calculer la nouvelle version par incrémentation sémantique (semver) :
- `patch` : Z → Z+1
- `minor` : Y → Y+1, Z → 0
- `major` : X → X+1, Y → 0, Z → 0

Si l'argument est une version explicite (ex. `0.2.0`), l'utiliser directement.

Si aucun argument n'est fourni, utiliser **AskUserQuestion** avec les options : `patch`, `minor`, `major`, version personnalisée.

Afficher :
```
Nouvelle version : A.B.C
```

## 3. Demander les notes de changelog

Avant de poser la question, lire les commits depuis la dernière version pour proposer un résumé pertinent :

```bash
git log --oneline -20
```

Utiliser **AskUserQuestion** pour demander un résumé des changements à inclure dans le CHANGELOG, en proposant comme première option le résumé déduit des commits.

La réponse peut être courte (ex. "ajout du support des nodes") — l'agent la structurera en entrée CHANGELOG.

## 4. Mettre à jour `setup.py`

Modifier la ligne `VERSION = 'X.Y.Z'` avec la nouvelle version, via l'outil **Edit** (pas de commande shell, pas de `sed`).

## 5. Mettre à jour `CHANGELOG.md`

Insérer une nouvelle section **en tête** du fichier (avant la section de la version précédente ; il n'y a pas de titre `# Changelog` dans ce projet).

Respecter **exactement** le format existant du projet — pas de date, pas de sous-sections, une liste d'items préfixés par un espace puis un tiret, avec un préfixe de type conventionnel (`feat:`, `fix:`, `chore:`, `docs:`) :

```markdown
## [A.B.C]
 - feat: <note 1>
 - fix: <note 2>

```
Une ligne vide sépare les sections. Ne pas ajouter de `---`, ne pas ajouter de date : cela dévierait du format historique du fichier.

Utiliser l'outil **Edit** pour insérer la section.

## 6. Vérification de cohérence

Avant de continuer, vérifier que la version de `setup.py` correspond **exactement** à la section `## [A.B.C]` ajoutée en tête de `CHANGELOG.md`. Corriger immédiatement toute discordance.

## 7. Afficher le diff et demander confirmation

Afficher un récapitulatif des modifications :
```
Modifications prêtes :
  • setup.py          version : X.Y.Z → A.B.C
  • CHANGELOG.md      ajout section [A.B.C]
```

Utiliser **AskUserQuestion** pour confirmer avant de committer.

## 8. Commit et tag git

Sur confirmation :

```bash
git add setup.py CHANGELOG.md
```

### 8a. Construire le message de commit avec le résumé des changes

Le commit ne doit **pas** se limiter au titre : son corps doit reprendre **la section CHANGELOG qui vient d'être insérée** (sans la ligne de titre `## [A.B.C]`), pour que `git log` montre directement les changes de la version.

Écrire le message complet dans un fichier temporaire (via **Write**, dans le répertoire scratchpad), au format :

```
chore(release): vA.B.C

<contenu de la section CHANGELOG insérée, sans la ligne de titre ##>

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
```

> Passer par `git commit -F <fichier>` (et non `-m`) est obligatoire : le corps est multi-lignes et contient des caractères Markdown (`#`, `` ` ``, `*`) qui seraient mal interprétés en `-m` inliné.

### 8b. Committer

```bash
git commit -F <fichier-message-temporaire>
rm <fichier-message-temporaire>
```

Créer le tag **uniquement si le bump est `major`** (i.e. X a été incrémenté) :

```bash
git tag vA.B.C
```

Vérifier que le commit a bien été créé et afficher :
```
✓ Commit : chore(release): vA.B.C
```

Si un tag a été créé, afficher également `✓ Tag    : vA.B.C`, sinon `ℹ Tag ignoré (réservé aux versions major)`.

---

## 9. Build du package

Cette section est aussi le point d'entrée du mode `/pkg-version publish` (sans bump) : dans ce cas, lire d'abord la version courante dans `setup.py` — c'est la version `A.B.C` publiée.

### 9a. Choisir l'interpréteur

Utiliser le venv du projet s'il existe (`.venv/bin/python`), sinon `python3`. Toutes les commandes ci-dessous utilisent cet interpréteur, noté `<py>`.

### 9b. Vérifier les prérequis

```bash
<py> -m twine --version
<py> -c "import wheel, setuptools"
```

Si `twine` ou `wheel` manquent, le signaler et proposer via **AskUserQuestion** :
```bash
<py> -m pip install --upgrade twine wheel setuptools
```
Ne jamais installer sans confirmation.

### 9c. Nettoyer les artefacts précédents

`dist/` est gitignoré mais peut contenir les artefacts de versions antérieures — les laisser ferait échouer (ou déraper) l'upload.

```bash
rm -rf dist build
```

### 9d. Builder

Commande documentée dans le `README.md` :

```bash
<py> setup.py sdist bdist_wheel
```

(Si `setup.py` échoue à cause d'un setuptools récent, replier sur `<py> -m build` après avoir proposé l'installation de `build`.)

### 9e. Vérifier les artefacts

```bash
ls dist
<py> -m twine check dist/*
```

Vérifier que `dist/` contient **exactement** les deux fichiers de la version attendue :
```
py_ce_forms_api-A.B.C-py3-none-any.whl
py_ce_forms_api-A.B.C.tar.gz
```

Si une autre version apparaît dans `dist/`, **s'arrêter** : le build ne correspond pas à la version bumpée.

Afficher :
```
✓ Build  : py_ce_forms_api-A.B.C (sdist + wheel)
```

## 10. Publication

### 10a. Choisir le dépôt cible

Lire les dépôts disponibles dans `~/.pypirc` (uniquement les noms de sections, ne jamais afficher de token) :

```bash
grep -E "^\[" ~/.pypirc
```

Utiliser **AskUserQuestion** pour choisir la cible parmi les sections trouvées, en proposant en premier `pypi` (dépôt public officiel), puis les autres (`testpypi`, `gitlab_ce`, `pypiserver`, …), et une option **Ne pas publier**.

### 10b. Confirmer explicitement

La publication est **irréversible** : une version publiée sur PyPI ne peut être ni remplacée ni ré-uploadée. Avant l'upload, afficher et faire confirmer via **AskUserQuestion** :

```
Publication :
  • package    : py_ce_forms_api A.B.C
  • fichiers   : dist/py_ce_forms_api-A.B.C-py3-none-any.whl, dist/py_ce_forms_api-A.B.C.tar.gz
  • dépôt      : <repository>
```

### 10c. Uploader

Commande documentée dans le `README.md`, restreinte aux fichiers de la version courante (jamais `dist/*` en aveugle) :

```bash
<py> -m twine upload --repository <repository> dist/py_ce_forms_api-A.B.C*
```

En cas d'échec d'authentification, indiquer à l'utilisateur de vérifier la section correspondante de `~/.pypirc` (ou les variables `TWINE_USERNAME`/`TWINE_PASSWORD`) — ne jamais lire ni afficher le contenu des tokens.

Sur succès, afficher :
```
✓ Publié : py_ce_forms_api A.B.C → <repository>
```

Pour une publication sur `pypi`, rappeler le lien de vérification :
`https://pypi.org/project/py-ce-forms-api/A.B.C/`

## 11. Proposer le push git

Utiliser **AskUserQuestion** pour demander si l'utilisateur souhaite pusher (sauter cette étape en mode `/pkg-version publish`).

**Si un tag a été créé (bump major)**, proposer :
- `git push && git push --tags` — pusher le commit et le tag
- `git push` seulement — pusher le commit sans le tag
- Ne pas pusher — terminer sans push

**Sinon (bump minor ou patch)**, proposer :
- `git push` — pusher le commit
- Ne pas pusher — terminer sans push

Exécuter la commande choisie et afficher le résultat. Si l'utilisateur choisit de ne pas pusher, afficher :
```
Prochaine étape : git push pour publier.
```
(ajouter `&& git push --tags` si un tag existe)

---

## Guardrails

- Ne jamais bumper vers une version inférieure ou égale à la version actuelle
- La version n'existe qu'à un seul endroit (`VERSION` dans `setup.py`) : ne pas la dupliquer ailleurs
- Respecter le format historique de `CHANGELOG.md` (`## [X.Y.Z]` sans date, items ` - type: …`) ; ne pas introduire le format « Keep a Changelog »
- Toujours demander confirmation avant le commit, avant le push, et avant la publication
- Si des fichiers non stagés existent en dehors de `setup.py` et `CHANGELOG.md`, ne pas les inclure dans le commit de version
- Le corps du commit de release doit toujours reprendre la section CHANGELOG de la version (cf. 8a) — jamais un corps vide, jamais une reformulation différente
- Toujours `rm -rf dist build` avant de builder, et n'uploader que les fichiers de la version courante (`dist/py_ce_forms_api-A.B.C*`)
- Ne jamais publier avant que le commit de version soit créé (sauf mode `publish` explicite)
- Ne jamais publier une version déjà présente sur le dépôt cible — en cas d'erreur `File already exists`, il faut bumper, pas forcer
- Ne jamais afficher, logger ou copier le contenu de `~/.pypirc` ni un token
- Ne pas installer de dépendance (`twine`, `wheel`, `build`) sans confirmation de l'utilisateur
