## 1. Noyau de terminaison dans `Task`

- [x] 1.1 Ajouter à `Task` l'état interne de terminaison : `_terminal: str | None`, un `threading.Lock`, et la constante des statuts terminaux (`DONE`, `ERROR`, `CANCELED`)
- [x] 1.2 Réécrire `__update_processing_status()` en `first terminal wins` : sous verrou, ignorer et journaliser toute écriture si `_terminal` est déjà posé, sinon enregistrer le terminal puis écrire — verrou tenu pendant l'appel HTTP (design D2)
- [x] 1.3 Ajouter le helper de finalisation synchrone avec retry (3 tentatives, backoff 0.5/1/2 s, `time.sleep`), sans aucun `await`, appliqué aux seuls statuts terminaux ; en cas d'épuisement, journaliser sans lever (design D3)
- [x] 1.4 Réécrire `Task.run()` selon la structure du design D4 : capture de la loop, `except CancelledError` → `CANCELED` + `raise`, `except BaseException` → `ERROR`, `finally` → `ERROR` « terminated without a final status » si aucun terminal
- [x] 1.5 Ajouter `Task.done(message: str | None = None)` avec docstring Sphinx couvrant l'idempotence, l'absence d'effet après `error()`, et l'inefficacité des `update()` postérieurs (design D8)
- [x] 1.6 Réécrire `Task.cancel()` : finalisation `CANCELED` synchrone puis `loop.call_soon_threadsafe(self.task.cancel)`, avec garde si `self.task` ou la loop sont absents (design D5)
- [x] 1.7 Ajouter `Task.run_blocking(fn, *args, **kwargs)` — enveloppe awaitable sur `asyncio.to_thread` — avec docstring expliquant quand l'utiliser (appel bloquant ponctuel dans une fonction `async def`) (design D11)
- [x] 1.8 Supprimer `Task.__failed()` (code mort)

## 2. Robustesse de `TaskPool`

- [x] 2.1 Garder un `set` des `asyncio.Task` créées par `run()`, avec `add_done_callback` pour le nettoyage (design D10)
- [x] 2.2 Initialiser `task = None` avant le `try` de `__handle_processing()` et garder tous les accès à `task` dans `except`/`finally`, pour supprimer l'`UnboundLocalError`
- [x] 2.3 Faire remonter `CancelledError` dans `__handle_processing()` après journalisation, au lieu de l'avaler
- [x] 2.4 Ajouter le filet de second niveau dans le `finally` de `__handle_processing()` : si la `Task` existe et n'est pas terminale, la finaliser en `ERROR` (design D1)
- [x] 2.5 Ajouter `TaskPool.shutdown()` : finalisation synchrone en `CANCELED` de toutes les tâches en vol, message identifiant l'arrêt du serveur
- [x] 2.6 Dispatcher sur `inspect.iscoroutinefunction(self.function)` dans `Task.run()` : coroutine → `create_task(func(task))` comme aujourd'hui, fonction ordinaire → `create_task(asyncio.to_thread(func, task))` (design D11)

## 3. Réconciliation et exposition

- [x] 3.1 Ajouter `ProcessingTasks.reconcile(pids=None, older_than=None, apply=False)` : requête `with_root("forms-processing")` filtrée sur `RUNNING` puis `PENDING`, exclusion des pid détenus par le pool local, retour des candidats sans écriture si `apply=False` (design D6)
- [x] 3.2 Implémenter le filtre `older_than` côté client sur `Form.mtime()` — `where()` ne pose pas `onMeta: True` et ne peut pas porter sur un champ méta ; exclure les formulaires sans `mtime` (design D6bis)
- [ ] 3.3 Vérifier sur un backend réel que `mtime` est bien rafraîchi à chaque mutation `update` — si ce n'est pas le cas, `older_than` mesure l'ancienneté du démarrage et perd son intérêt (hypothèse D6bis)
- [x] 3.4 Écrire la docstring de `reconcile()` en avertissant explicitement du danger en déploiement multi-instance, en documentant le mode dry-run comme usage nominal et la limite du heartbeat implicite (tâche vivante mais silencieuse)
- [x] 3.5 Ajouter `ProcessingTasks.shutdown()` déléguant à `TaskPool.shutdown()`
- [x] 3.6 Brancher `app.add_event_handler("shutdown", ...)` dans `Processing.__init__` sur `self.shutdown` (design D7)

## 4. `ProcessingClient`

- [x] 4.1 Ajouter le rollback de `start()` : conserver l'ordre `PENDING` puis appel, et sur échec écrire `ERROR` avec le message d'échec avant de propager (design D9)
- [x] 4.2 Retirer l'écriture de `PENDING` dans `cancel()` et laisser le statut intact quand l'appel échoue

## 5. Tests

- [x] 5.1 Étendre `FakeCeFormsClient` dans `tests/test_processing.py` pour pouvoir simuler l'échec des mutations (échec ponctuel, échec permanent) et compter les tentatives
- [x] 5.2 Tests de l'invariant de terminaison : fin normale, `Exception`, `CancelledError` externe, `BaseException`, et le chemin `finally` de dernier recours
- [x] 5.3 Tests du garde `first terminal wins` : `DONE` après `CANCELED`, `update()` après `error()`, `done()` appelée deux fois, `done()` après `error()`, `update()` après `done()`
- [x] 5.4 Tests du retry : succès à la seconde tentative, épuisement sans exception qui s'échappe, absence de retry sur une écriture de progression
- [x] 5.5 Tests d'annulation : annulation d'une tâche en cours, annulation dans la fenêtre où `self.task` est encore `None`, non-suppression de la `CancelledError`
- [x] 5.6 Tests de `TaskPool` : libération du slot quand la construction de `Task` échoue, référence forte conservée, `shutdown()` avec tâches en vol et avec une tâche déjà terminée
- [x] 5.6b Tests des fonctions synchrones : une fonction `def` va bien en `DONE`, une qui lève va en `ERROR`, une fonction `async def` conserve son chemin actuel, et l'annulation d'une tâche synchrone donne `CANCELED` avec neutralisation des écritures du thread survivant
- [x] 5.6c Test que la boucle reste réactive pendant l'exécution d'une fonction `def` bloquante (une autre coroutine progresse en parallèle), et test de `Task.run_blocking()` en retour de valeur et en propagation d'exception
- [x] 5.7 Tests de `reconcile()` : dry-run sans mutation, `apply=True`, exclusion des pid du pool local, ciblage par `pids`, filtre `older_than` (candidat récent exclu, candidat sans `mtime` exclu), et absence de réconciliation au démarrage de `Processing`
- [x] 5.8 Tests de `ProcessingClient` dans `tests/test_processing_client.py` : rollback en `ERROR` sur échec de `start()`, formulaire relançable ensuite, absence d'écriture après un `start()` réussi, `cancel()` qui n'écrit pas `PENDING` et laisse le statut intact en cas d'échec
- [ ] 5.9 Vérifier que la suite passe sur Python 3.10, 3.11 et 3.12 (`make test`)

## 6. Documentation

- [x] 6.1 Mettre à jour `examples/simple_processing_task/main.py` pour illustrer `task.done("End of processing")`
- [x] 6.2 Ajouter un exemple `examples/reconcile_processing/main.py` montrant le cycle dry-run puis `apply=True`
- [x] 6.3 Documenter dans le README la garantie de terminaison, `done()`, `shutdown()` et `reconcile()`, en signalant que le scénario E1 (fonction qui rend la main mais ne se termine jamais) reste couvert par `cancel()` et `reconcile()` seulement
- [x] 6.3b Documenter le contrat d'écriture d'une fonction de tâche : `def` pour du travail bloquant (la lib l'exécute hors de la boucle), `async def` pour du travail réellement asynchrone, `task.run_blocking()` pour le cas mixte — avec un exemple de chaque
- [x] 6.4 Ajouter l'entrée `CHANGELOG.md` en signalant les changements de comportement observables : une tâche annulée ne finit plus en `DONE`, un arrêt du serveur produit `CANCELED`, un `start()` en échec produit `ERROR` au lieu de `PENDING`, une fonction de tâche `def` est désormais acceptée au lieu de lever `TypeError`
- [ ] 6.5 Bump de `VERSION` dans `setup.py` en accord avec le CHANGELOG
