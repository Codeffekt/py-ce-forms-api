## Why

Une tâche de processing communique son avancement au formulaire `forms-processing` via un statut (`PENDING` → `RUNNING` → `DONE` | `ERROR` | `CANCELED`). L'implémentation actuelle laisse le formulaire **bloqué en `RUNNING` pour toujours** dans au moins huit scénarios distincts, et **bloqué en `PENDING` sans aucune issue possible** dans un neuvième. Un formulaire coincé dans un état non terminal n'est ni relançable (`ProcessingClient.start()` refuse de démarrer ce qu'il croit déjà démarré) ni annulable (`cancel()` réécrit `PENDING` puis échoue) : il faut une intervention manuelle en base.

Les causes racines :

| # | Scénario | Emplacement | État bloqué |
|---|---|---|---|
| A | La fonction se termine bien mais la mutation `DONE` échoue ; le fallback `__error()` refait une mutation qui échoue aussi | `task.py` `run()` | `RUNNING` |
| B | `CancelledError` externe (shutdown uvicorn, `loop.close()`, reload) — c'est une `BaseException`, non rattrapée par `except Exception` | `task.py` `run()`, `task_pool.py` `__handle_processing()` | `RUNNING` |
| C | Autres `BaseException` : `KeyboardInterrupt`, `SystemExit` | idem | `RUNNING` |
| D | Process tué : SIGKILL, OOM, crash, redéploiement conteneur | — | `RUNNING` |
| E1 | Fonction utilisateur qui rend la main mais ne se termine jamais (boucle sur une condition qui n'arrive pas). Le serveur reste vivant, `/cancel` est servi | — | `RUNNING` |
| E2 | Fonction utilisateur qui **ne rend jamais la main** (appel bloquant, calcul CPU pur). L'event loop est gelée : le serveur entier cesse de répondre, `/cancel` compris. Rien ne peut plus s'exécuter en process | — | `RUNNING`, serveur mort |
| F | `asyncio.create_task()` fire-and-forget sans référence forte : le GC peut collecter la tâche en vol | `task_pool.py` `run()` | `RUNNING` |
| G | Si `Task(...)` lève à la construction, les blocs `except`/`finally` référencent `task` non liée → `UnboundLocalError` | `task_pool.py` `__handle_processing()` | `RUNNING` |
| H | `start()` écrit `PENDING` **avant** l'appel HTTP, sans rollback si l'appel échoue ; `is_started()` traite `PENDING` comme démarré | `processing_client.py` | `PENDING`, sans issue |
| I | Aucun garde d'état terminal : `update()` après `error()` réécrit `RUNNING` ; un `cancel()` sur du code bloquant finit écrasé par `DONE` | `task.py` | état faux |

## What Changes

- **Invariant de terminaison** : `Task.run()` ne peut plus retourner sans avoir écrit un état terminal. Rattrapage de `CancelledError` (→ `CANCELED`, puis re-raise) et de `BaseException` (→ `ERROR`), plus un `finally` qui force `ERROR` si aucun terminal n'a été posé. Couvre B, C, G.
- **Garde d'état terminal** : une fois un terminal écrit, plus aucune écriture non terminale n'est acceptée. Élimine les inversions `CANCELED` → `DONE` et `ERROR` → `RUNNING` (I).
- **Nouvelle méthode publique `Task.done(message=None)`** : termine explicitement la tâche en `DONE`, idempotente. Non contraignante — `run()` continue de poser `DONE` automatiquement si la fonction se termine sans l'appeler. **Rétrocompatible.**
- **Écriture fiable de l'état terminal** : retry avec backoff sur la mutation d'un état terminal, et chemin de finalisation entièrement synchrone — sans aucun `await` — pour que `CANCELED`/`ERROR` puissent partir même pendant une annulation. Couvre A.
- **Arrêt propre du serveur** : `TaskPool.shutdown()` finalise en `CANCELED` toutes les tâches encore en vol, branché sur le cycle de vie FastAPI de `Processing`. Couvre B et C sur un arrêt maîtrisé.
- **Réconciliation explicite** : `ProcessingTasks.reconcile()` requête les formulaires `forms-processing` restés en `RUNNING` ou `PENDING` et les repasse en `ERROR` (« interrompu par un redémarrage »). Seul recours possible pour D. Utilise `with_root()` + `where()` et le champ méta `mtime`, **déjà disponibles** — aucun changement côté serveur. **Jamais automatique** : plusieurs instances partagent le même endpoint, un balayage au démarrage tuerait les tâches vivantes des autres instances. Dry-run par défaut, filtre `older_than` sur `mtime` que chaque `update()` rafraîchit.
- **Support natif des fonctions de tâche synchrones** : `TaskPool` détecte une fonction déclarée `def` (et non `async def`) et l'exécute via `asyncio.to_thread`, hors de l'event loop. Couvre E2 **par construction** : du code bloquant écrit naturellement ne gèle plus le serveur, et `/cancel` reste servi. Aujourd'hui ce chemin ne fait que lever `TypeError: a coroutine was expected` — le changement est donc strictement additif, et il corrige une incitation perverse : l'utilisateur qui se prenait cette erreur ajoutait `async` devant sa fonction bloquante, ce qui ne la rendait pas non-bloquante mais la déplaçait sur la boucle.
- **Nouvelle méthode `Task.run_blocking(fn, *args, **kwargs)`** : fine enveloppe sur `asyncio.to_thread`, pour qu'une fonction `async def` puisse sortir un appel bloquant ponctuel de la boucle sans que l'appelant ait à connaître `asyncio`. Découvrable par autocomplétion et documentée.
- **Correction du blocage `PENDING`** : `ProcessingClient.start()` conserve l'écriture de `PENDING` avant l'appel — le serveur peut déjà avoir écrit `RUNNING` au retour — mais bascule le formulaire en `ERROR` si l'appel échoue ; `cancel()` n'écrit plus `PENDING`. Couvre H.
- **Corrections annexes** : référence forte sur la tâche créée par `TaskPool.run()` (F) ; `task` initialisée avant le `try` (G) ; `CancelledError` re-levée après traitement dans `__handle_processing` ; suppression du code mort `Task.__failed()`.

**Hors périmètre, assumé**

- *Pas de heartbeat dédié.* Aucun champ n'est ajouté au root `forms-processing` : le champ méta `mtime`, rafraîchi par chaque `update()`, fait office de heartbeat implicite et suffit à `reconcile()`. Ce qui reste hors périmètre est le mécanisme de *lease* — une règle côté consommateur qui déclarerait mort tout `RUNNING` périmé, sans intervention. La réconciliation couvre « le process a crashé, un opérateur nettoie », pas « le process disparaît définitivement et personne ne regarde ».
- *Pas de timeout (scénario E1).* Une fonction qui rend la main mais ne se termine jamais reste en `RUNNING`. Décision assumée : un timeout imposerait un délai à choisir sans connaissance du métier des tâches, et le risque de tuer une tâche longue légitime est jugé supérieur au risque couvert. Le serveur restant vivant en E1, `cancel()` est le recours, et `reconcile()` le filet. À noter qu'un timeout n'aurait de toute façon jamais couvert E2 : `asyncio.wait_for` s'appuie sur un timer géré par l'event loop, qui ne se déclenche pas quand celle-ci est gelée.
- *Pas d'annulation forcée du travail synchrone.* Un thread Python ne se tue pas. Sur une tâche exécutée via `to_thread`, `cancel()` écrit bien `CANCELED` et libère le slot, mais le thread poursuit son exécution en fuite ; ses `update()` ultérieurs sont neutralisés par le garde d'état terminal. Seule une isolation en sous-process permettrait une interruption réelle — hors périmètre.

## Capabilities

### New Capabilities
- `processing-task-lifecycle`: garanties de cycle de vie d'une tâche de processing — transitions de statut, terminaison garantie, annulation, exécution des fonctions bloquantes, arrêt du serveur et réconciliation explicite.
- `processing-client-control`: contrat côté appelant pour démarrer, annuler et interroger une tâche sans laisser le formulaire dans un état non terminal irrécupérable.

### Modified Capabilities
<!-- Aucune : openspec/specs/ est vide, ce sont les deux premières specs du projet. -->

## Impact

**Code affecté**
- `py_ce_forms_api/processing/task.py` — cœur du changement (invariant, garde terminal, `done()`, retry, `run_blocking()`).
- `py_ce_forms_api/processing/task_pool.py` — référence forte, `UnboundLocalError`, propagation de `CancelledError`, `shutdown()`, dispatch `def` / `async def`.
- `py_ce_forms_api/processing/processing_tasks.py` — exposition de `shutdown()` et de `reconcile()`.
- `py_ce_forms_api/processing/processing.py` — branchement de l'événement d'arrêt FastAPI.
- `py_ce_forms_api/processing_client/processing_client.py` — rollback de `start()`, `cancel()` n'écrit plus `PENDING`.
- `tests/test_processing.py`, `tests/test_processing_client.py` — couverture des dix scénarios.
- `examples/simple_processing_task/main.py` — illustration de `done()`.

**Surface publique** (toutes additives, **rétrocompatible**)
- `Task.done(message=None)`, `Task.run_blocking(fn, *args, **kwargs)` — nouvelles méthodes.
- `TaskPool.shutdown()`, `ProcessingTasks.shutdown()` — nouvelles méthodes.
- `ProcessingTasks.reconcile(pids=None, older_than=None, apply=False)` — nouvelle méthode, appelée explicitement par l'opérateur, jamais par le SDK.
- Une fonction de tâche déclarée `def` devient acceptée, là où elle levait `TypeError`.
- Aucun symbole exporté supprimé ou renommé ; aucun changement de signature existante.

**Changement de comportement observable** (voulu, non couvert par la rétrocompat stricte)
- Une tâche annulée ne peut plus finir en `DONE`.
- Une tâche interrompue par un shutdown termine désormais en `CANCELED` au lieu de rester en `RUNNING`.
- `ProcessingClient.start()` bascule le formulaire en `ERROR` au lieu de le laisser en `PENDING` quand l'appel échoue.
- Une fonction de tâche synchrone s'exécute désormais au lieu de lever `TypeError`.

**Dépendances et configuration**
- Aucune nouvelle dépendance runtime.
- Aucune nouvelle variable d'environnement.
- Aucun changement du schéma des formulaires ni de l'API CeForms.
