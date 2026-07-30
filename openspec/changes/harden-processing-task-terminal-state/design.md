## Context

Le module `processing/` expose une tâche asynchrone dont le seul canal de communication est le statut d'un formulaire `forms-processing`. La proposal recense neuf chemins par lesquels ce statut reste non terminal. Ce document arrête *comment* les fermer.

Trois contraintes structurent tout le reste :

1. **L'écriture du statut est un appel HTTP synchrone.** `Task.__update_processing_status()` appelle `client.mutation().update_single()`, qui descend jusqu'à `requests.post` — bloquant. Un statut n'est donc jamais « posé » de façon atomique ni garantie : c'est une I/O réseau qui peut échouer, et qui bloque l'event loop pendant sa durée.
2. **`Task.cancel()` s'exécute dans un autre thread que l'event loop.** La route `/cancel/{pid}` est déclarée `def` (non `async`), donc FastAPI l'exécute dans son threadpool. Or `cancel()` lit/écrit l'état de la tâche *et* appelle `self.task.cancel()` sur un objet asyncio — opération qui n'est pas thread-safe.
3. **Plusieurs instances du serveur partagent le même endpoint.** Aucune requête sur le root `forms-processing` ne permet de distinguer « tâche morte » de « tâche vivante sur une autre instance ».

État actuel du flux, avec les points de rupture :

```
   thread event loop                              thread pool FastAPI (route /cancel)
   ────────────────                               ─────────────────────────────────────
   TaskPool.run()
     └─ create_task(__handle_processing)   ← ⚠ F : aucune référence forte gardée
          └─ task = Task(...)              ← ⚠ G : si ça lève, except/finally cassent
             tasks.append(task)
             await task.run()                              │
                  ├─ __start() → RUNNING                   │ ⚠ fenêtre : self.task est None
                  ├─ self.task = create_task(func)  ◄──────┤ → cancel() fait None.cancel()
                  ├─ await self.task                       │
                  │    ⚠ B/C : CancelledError et           │ Task.cancel()
                  │      BaseException traversent          │  ├─ écrit CANCELED
                  │      `except Exception` sans           │  └─ self.task.cancel()  ⚠ pas thread-safe
                  │      écrire de statut                  │
                  └─ __finished() → DONE                   │ ⚠ I : si func est bloquante,
                       ⚠ A : si la mutation échoue,        │      DONE écrase CANCELED
                         le fallback __error() échoue
                         pareil → reste RUNNING
```

## Goals / Non-Goals

**Goals**

- `Task.run()` ne peut pas retourner sans qu'un état terminal ait été **tenté avec insistance**.
- Le premier état terminal écrit est définitif : aucune écriture ultérieure ne peut le contredire.
- Un arrêt maîtrisé du serveur (SIGTERM, reload uvicorn) finalise les tâches en vol.
- Un opérateur dispose d'un outil sûr pour nettoyer les formulaires laissés bloqués par un crash antérieur.
- `ProcessingClient.start()` ne laisse jamais un formulaire dans un état d'où il ne peut plus repartir.
- Rétrocompatibilité : aucune signature existante modifiée, aucun symbole retiré.

**Non-Goals**

- **Mécanisme de lease.** Une règle qui déclarerait mort tout `RUNNING` périmé sans intervention humaine vit côté consommateur, hors SDK. Le heartbeat lui-même, en revanche, existe déjà gratuitement via `mtime` (voir D6bis).
- **Timeout sur la fonction utilisateur (scénario E1).** Écarté sur décision explicite : le délai serait choisi sans connaissance du métier, et tuer une tâche longue légitime est jugé pire que le cas couvert. En E1 le serveur reste vivant, donc `cancel()` est le recours et `reconcile()` le filet.
- **Annulation forcée d'un travail synchrone.** Un thread Python ne se tue pas. Une tâche exécutée via `to_thread` (D11) reçoit bien son statut `CANCELED`, mais le thread poursuit son exécution. Seule une isolation en sous-process permettrait une interruption réelle.
- **Garantie face à SIGKILL.** Aucun code en process ne peut écrire quoi que ce soit. Seule la réconciliation *a posteriori* aide.
- **Refonte du `FastAPI` module-level partagé** par toutes les instances de `Processing` (dette existante, visible dans les tests via `importlib.reload`). On s'y greffe sans y toucher.

## Decisions

### D1 — L'invariant vit dans `Task`, avec un second filet dans `TaskPool`

`Task` est le seul objet qui connaît à la fois le formulaire et l'état déjà écrit ; l'invariant lui appartient. Mais `TaskPool.__handle_processing()` peut échouer *avant* d'entrer dans `run()` (échec de construction, scénario G) : son `finally` vérifie donc, si une `Task` existe, qu'elle est bien terminale, et la finalise sinon.

Défense en profondeur assumée : deux filets valent mieux qu'un pour un invariant dont toute la valeur est de ne jamais céder.

*Alternative écartée* — tout mettre dans `TaskPool` : le pool ne sait pas ce qui a déjà été écrit et ne peut pas distinguer « terminé proprement » de « sorti par une exception ».

### D2 — `first terminal wins`, gardé par un verrou

`Task` porte `self._terminal: str | None`. `__update_processing_status()` devient :

```
si _terminal est déjà posé  → l'écriture est ignorée (journalisée, pas d'exception)
sinon si status est terminal → _terminal = status, puis écriture
sinon                        → écriture simple (progression)
```

Le premier état terminal gagne, définitivement. Cela résout d'un coup :
- `CANCELED` écrasé par `DONE` quand la fonction est bloquante et ignore l'annulation ;
- `RUNNING` réécrit par un `update()` postérieur à un `error()` ;
- l'idempotence de `done()` ;
- la cohabitation du `finally` de `Task` et de celui de `TaskPool` (le second ne fait rien si le premier a réussi).

**Verrouillage.** Le check-and-set est lu depuis deux threads (contrainte 2). Un `threading.Lock` le protège. Le verrou est tenu **pendant l'écriture HTTP**, pas seulement autour du flag : sinon deux écritures terminales concurrentes partiraient toutes deux vers l'API et l'ordre d'arrivée déciderait du statut final — exactement le bug qu'on ferme. Le coût est qu'un `cancel()` peut attendre la fin d'une mutation en cours ; c'est borné par le timeout HTTP et rare.

### D3 — La finalisation est entièrement synchrone, avec retry

C'est la décision la moins évidente et la plus importante.

Le réflexe pour « écrire malgré une annulation » serait `asyncio.shield`. **Il ne fonctionne pas ici** : `shield` protège la coroutine interne d'être annulée, mais l'`await` qui l'attend lève quand même `CancelledError` dès que la tâche englobante est annulée. On n'aurait aucune garantie que l'écriture soit terminée. Plus généralement, tout `await` placé dans un bloc `finally` exécuté sous annulation re-lève immédiatement.

Or l'écriture *est déjà synchrone* (contrainte 1). Le chemin de finalisation reste donc **sans aucun `await`** : un `finally` purement synchrone s'exécute intégralement, même sous `CancelledError`, même sous `KeyboardInterrupt`. Le retry utilise `time.sleep`.

- Retry uniquement sur les **états terminaux**. Un `RUNNING` de progression perdu est sans conséquence ; un terminal perdu, c'est le bug qu'on corrige.
- 3 tentatives, backoff 0.5 s / 1 s / 2 s. Pire cas ≈ 3,5 s de blocage de l'event loop.
- Après épuisement : on journalise en `ERROR` niveau log et on abandonne. Le formulaire reste bloqué — mais seulement si l'API CeForms est indisponible plusieurs secondes d'affilée, ce qui est un incident d'infrastructure, pas un bug de cycle de vie. `reconcile()` (D6) est le rattrapage.

*Trade-off assumé* : bloquer l'event loop quelques secondes dégrade les autres tâches du pool. C'est un chemin d'exception, et la correction de l'état vaut plus que la latence dans ce cas précis.

### D4 — Structure de `Task.run()`

```
async def run():
    capturer la loop courante          # pour D5
    try:
        __start()                      # → RUNNING
        self.task = create_task(func)
        await self.task
        __finished()                   # → DONE (ignoré si done() a déjà été appelé)
    except CancelledError:
        __finalize("CANCELED")
        raise                          # ← re-raise obligatoire, voir ci-dessous
    except BaseException as err:
        __finalize("ERROR", message=str(err))
    finally:
        if _terminal is None:
            __finalize("ERROR", message="task terminated without a final status")
```

Deux points :

- **`except BaseException` et non `except Exception`.** `CancelledError` hérite de `BaseException` depuis Python 3.8 ; `KeyboardInterrupt` et `SystemExit` aussi. C'est la cause directe des scénarios B et C.
- **Le `raise` après `CANCELED` est obligatoire.** Avaler une `CancelledError` supprime l'annulation de la tâche, ce qui fait traîner — voire bloquer — l'arrêt de l'event loop. Le code actuel commet cette faute dans `TaskPool.__handle_processing()`, qui doit être corrigé de la même manière.

Le `finally` ne s'active que si tout le reste a échoué (écriture terminale impossible, chemin imprévu). Il pose `ERROR`, pas `DONE` : arriver là signifie qu'on ne sait pas si le travail a abouti, et un faux `DONE` est bien plus nuisible qu'un faux `ERROR`.

### D5 — `cancel()` traverse correctement la frontière de threads

```
def cancel():
    __finalize("CANCELED")                       # synchrone, sous verrou (D2/D3)
    si self.task et self._loop existent:
        self._loop.call_soon_threadsafe(self.task.cancel)
```

- `call_soon_threadsafe` est la seule façon correcte de toucher un objet asyncio depuis un autre thread. L'appel direct actuel est un bug de concurrence latent.
- Le garde `si self.task` ferme la fenêtre où `cancel()` arrive entre `tasks.append(task)` et l'affectation de `self.task` — aujourd'hui un `AttributeError` sur `None`. Le statut `CANCELED` est posé quoi qu'il arrive, et le garde D2 empêche le `DONE` ultérieur de l'écraser.

### D6 — `reconcile()` est un outil d'inspection avant d'être un outil d'écriture

Contrainte 3 : une requête `root = forms-processing AND status = RUNNING` ramène indistinctement les tâches mortes et celles qui tournent sur les autres instances. Un balayage automatique tuerait la production. D'où :

```
ProcessingTasks.reconcile(pids=None, older_than=None, apply=False) -> list[Form]
```

- **`apply=False` par défaut** : la méthode *retourne* les candidats sans rien écrire. L'opérateur inspecte, puis rappelle avec `apply=True` ou avec une liste `pids` explicite.
- Traite `RUNNING` **et** `PENDING` : le `PENDING` bloqué (scénario H) est justement l'état dont on ne peut pas sortir autrement.
- Exclut systématiquement les `pid` présents dans le pool local — protection minimale, qui ne couvre que l'instance appelante.
- **Filtre `older_than`** sur le `mtime` du formulaire, voir D6bis.
- N'est **jamais** appelée par le SDK, ni au démarrage, ni ailleurs.

*Alternative écartée* — filtrer par endpoint : plusieurs instances partagent le même endpoint, le filtre ne discrimine rien.

### D6bis — `mtime` sert de heartbeat implicite

Le formulaire porte un champ méta `mtime`, déjà exposé par `Form.mtime()`. Chaque `Task.update()` provoque une mutation, donc rafraîchit `mtime`. Une tâche qui rapporte sa progression **entretient déjà un heartbeat**, sans qu'aucun champ ne soit ajouté au root `forms-processing` — ce que les Non-Goals excluaient explicitement.

`reconcile(older_than=timedelta(...))` ne retient donc que les candidats dont le `mtime` est plus ancien que le seuil. C'est la meilleure mitigation disponible du risque multi-instance.

**C'est une heuristique, pas une preuve.** Une tâche vivante qui n'appelle jamais `update()` — un calcul long et silencieux — garde un `mtime` figé à son démarrage et sera considérée à tort comme morte. Le seuil doit donc être choisi largement au-dessus de l'intervalle d'`update()` le plus lent du parc de tâches, et `apply=False` reste le défaut.

Le filtrage se fait **côté client**, après récupération des candidats : `where()` ne pose pas `onMeta: True` et ne peut donc pas porter sur un champ méta comme `mtime`. L'ensemble des formulaires en `RUNNING`/`PENDING` est petit par nature, le coût est négligeable.

*Hypothèse à valider en implémentation* : que le backend bump bien `mtime` à chaque mutation `update`. Si ce n'était pas le cas, `older_than` mesurerait l'ancienneté du démarrage plutôt que celle du dernier signe de vie, et le filtre perdrait tout intérêt.

Un outil dangereux rendu explicite et dry-run par défaut vaut mieux qu'un outil sûr qui n'existe pas : sans `reconcile()`, le seul recours au scénario D reste l'édition manuelle en base.

### D7 — `shutdown()` et branchement sur le cycle de vie

`TaskPool.shutdown()` parcourt les tâches restantes et les finalise en `CANCELED` avec le message « server shutdown ». Synchrone, pour les raisons de D3.

Branchement : `app.add_event_handler("shutdown", ...)` sur l'app existante. On ne passe pas au `lifespan` moderne parce qu'il faudrait le fournir à la construction du `FastAPI`, or l'app est module-level et partagée — hors périmètre (Non-Goals).

`CANCELED` plutôt qu'`ERROR` : rien n'a échoué, l'exécution a été interrompue par le système. Le message porte la distinction pour qui a besoin de la faire.

Uvicorn exécute les handlers de shutdown avant de fermer la boucle, aussi bien sur SIGTERM que sur SIGINT — les tâches en vol sont donc bien finalisées. SIGKILL contourne tout, par définition.

### D8 — `done()` est un raccourci, pas un contrat

```
Task.done(message: str | None = None)
```

Pose `DONE` comme état terminal, en ajoutant `message` au journal du formulaire s'il est fourni. Sémantique **non contraignante** : `run()` continue de poser `DONE` automatiquement quand la fonction se termine sans avoir appelé `done()`.

*Alternative écartée* — rendre `done()` obligatoire (terminer sans l'appeler → `ERROR`). Ce serait une rupture pour tous les usages existants, et surtout cela déplacerait la garantie vers la discipline de celui qui écrit la tâche : précisément la source de bugs que ce changement supprime. La garantie doit venir du `finally`, pas de la mémoire de l'auteur.

Conséquences documentées : `done()` est idempotent ; appelée après `error()` elle est ignorée (une erreur signalée ne doit pas être masquée) ; les `update()` qui suivent un `done()` sont ignorés, la fonction pouvant continuer de tourner après avoir déclaré sa terminaison.

### D9 — `start()` garde son ordre d'écriture, mais rollback

Tentation naturelle : écrire `PENDING` *après* l'appel HTTP réussi. **C'est faux.** `/processing/{pid}` retourne dès que la tâche est planifiée ; le serveur a déjà pu écrire `RUNNING`. Écrire `PENDING` au retour l'écraserait — on remplacerait un bug par une régression.

L'ordre reste donc `PENDING` puis appel, avec un **rollback en `ERROR`** si l'appel échoue, portant le message de l'échec. `ERROR` plutôt qu'un retour au statut précédent : c'est plus honnête (la tentative de démarrage a bien échoué) et cela rend le formulaire immédiatement relançable, puisque `is_started()` retourne alors `False`.

`ProcessingClient.cancel()` cesse d'écrire `PENDING` : le serveur écrit `CANCELED` lui-même. Si l'appel échoue, le statut est laissé intact et l'exception remonte — mieux vaut un formulaire dans son état réel qu'un formulaire dégradé en `PENDING` irrécupérable.

### D10 — Référence forte sur les tâches détachées

`TaskPool` garde un `set` des objets `asyncio.Task` créés par `run()`, avec `add_done_callback(set.discard)`. La documentation asyncio l'exige explicitement : sans référence forte, le ramasse-miettes peut collecter une tâche en cours d'exécution.

### D11 — Les fonctions de tâche synchrones sont exécutées hors de l'event loop

Le scénario E se scinde en deux cas de gravité très différente :

- **E1** — la fonction rend la main (`await`) mais ne se termine jamais. La boucle tourne, le serveur répond, `/cancel` est servi. Seul le formulaire est bloqué. Hors périmètre (Non-Goals).
- **E2** — la fonction ne rend jamais la main : appel bloquant, calcul CPU pur. L'event loop est gelée, **le serveur entier cesse de répondre**, `/cancel` compris. Plus aucun code ne peut s'exécuter en process, donc aucun des filets précédents ne joue.

E2 est le seul scénario du lot qui tue le serveur et pas seulement un formulaire. Il est aussi le seul dont le correctif ne demande ni arbitrage métier ni changement externe.

**La lib pousse actuellement ses utilisateurs vers E2.** `TaskPool` fait `create_task(self.function(self))`, ce qui exige une coroutine : une fonction déclarée `def` lève `TypeError: a coroutine was expected, got …`. Le réflexe de qui rencontre cette erreur est d'ajouter `async` devant sa fonction bloquante — ce qui ne la rend pas non-bloquante, mais l'installe sur la boucle. L'incitation est exactement à l'envers.

Décision :

```
inspect.iscoroutinefunction(self.function)
   ├─ True  → create_task(func(task))                comportement actuel, inchangé
   └─ False → create_task(asyncio.to_thread(func, task))   exécuté hors de la boucle
```

Strictement additif : le chemin `False` ne fait aujourd'hui que crasher. Un utilisateur qui écrit du code bloquant naturel est protégé sans rien savoir d'`asyncio`, et E2 disparaît par construction — sans timeout, sans tuer quoi que ce soit, sans toucher au backend.

**Complément `Task.run_blocking(fn, *args, **kwargs)`** — une fine enveloppe sur `asyncio.to_thread`, pour le cas mixte : une fonction `async def` légitimement asynchrone qui doit sortir un appel bloquant ponctuel de la boucle. Le gain sur un `asyncio.to_thread` écrit à la main est la découvrabilité : la méthode apparaît sur l'objet `task` que l'utilisateur manipule déjà, et sa docstring porte l'explication.

**Interaction avec l'annulation.** `cancel()` sur une tâche en `to_thread` annule la coroutine qui attend le thread : `CANCELED` est écrit, le slot est libéré, `run()` se termine proprement. Le thread, lui, poursuit — Python ne sait pas l'interrompre. S'il appelle `task.update()` en cours de route, le garde D2 neutralise l'écriture et le formulaire reste `CANCELED`. L'état observable est donc toujours correct ; ce qui fuit est le thread et les ressources qu'il retient. C'est nettement préférable à un serveur gelé, mais ce n'est pas une annulation réelle (voir Non-Goals).

*Alternative écartée* — envelopper systématiquement la fonction utilisateur dans un thread : casserait toutes les tâches qui font déjà de l'async correct, et rendrait l'annulation illusoire pour tout le monde.

*Alternative écartée* — se contenter de documenter « utilise `asyncio.to_thread` ». La documentation ne protège que ceux qui la lisent, et l'erreur actuelle (`TypeError`) oriente activement vers la mauvaise correction.

## Risks / Trade-offs

| Risque | Mitigation |
|---|---|
| Le retry synchrone bloque l'event loop jusqu'à ~3,5 s, figeant les autres tâches du pool | Bornes serrées (3 tentatives) ; ne s'active que sur un échec d'écriture terminale, donc sur incident API |
| Le verrou tenu pendant l'I/O fait attendre un `cancel()` concurrent | Attente bornée par le timeout HTTP ; l'alternative (verrou sur le flag seul) réintroduit la course qu'on ferme |
| `reconcile(apply=True)` mal utilisé tue des tâches vivantes d'autres instances | Dry-run par défaut, filtre `older_than` sur `mtime` (D6bis), exclusion du pool local, jamais appelée par le SDK, danger documenté dans la docstring et le spec |
| `older_than` classe morte une tâche vivante mais silencieuse (aucun `update()`) | Seuil à choisir au-dessus de l'intervalle d'`update()` le plus lent ; `apply=False` reste le défaut ; limite documentée dans la docstring |
| Si l'API CeForms est indisponible plus longtemps que le retry, le formulaire reste bloqué | Résiduel et assumé : c'est un incident d'infrastructure. `reconcile()` est le rattrapage |
| Changement observable : une tâche annulée ne peut plus finir en `DONE` | C'est la correction voulue. Signalé dans la proposal et le CHANGELOG |
| `add_event_handler("shutdown")` est l'API historique de Starlette | Toujours supportée ; la migration vers `lifespan` suppose de traiter le `FastAPI` module-level, hors périmètre |
| Le scénario E1 (fonction qui rend la main mais ne finit jamais) reste ouvert | Décision explicite. Le serveur restant vivant, `cancel()` est le recours et `reconcile()` le filet |
| Un thread lancé par `to_thread` continue après un `cancel()` et fuit | Le formulaire reste correct grâce au garde D2 ; limite documentée. L'alternative (sous-process) est hors périmètre |
| Le pool d'exécuteurs par défaut d'asyncio est borné ; des tâches synchrones simultanées peuvent s'y accumuler | `TaskPool.maxLength` vaut 10, en deçà du défaut `min(32, cpu+4)`. À revoir si la capacité du pool augmente |

## Migration Plan

Purement additif : aucune migration de données, aucun changement de schéma, aucune variable d'environnement. Une montée de version du paquet suffit.

**Nettoyage de l'existant** — les formulaires déjà bloqués par les bugs corrigés ne se réparent pas seuls. `reconcile()` couvrant `RUNNING` et `PENDING`, la procédure est : appeler `reconcile()` en dry-run, vérifier qu'aucun candidat ne correspond à une tâche vivante sur une autre instance, rappeler avec `apply=True`.

**Rollback** — revenir à la version précédente du paquet. Aucun état persistant n'est introduit, donc aucun résidu.

## Open Questions

- ~~Existe-t-il un champ de date de modification exploitable ?~~ **Résolu** : `mtime`, voir D6bis. Reste à confirmer en implémentation que le backend le rafraîchit à chaque mutation.
- Faut-il exposer `reconcile()` dans le CLI `py-ce-forms` ? C'est un geste d'exploitation, sa place naturelle est en ligne de commande plutôt que dans un script Python ad hoc.
- Le pire cas de blocage de l'event loop (~3,5 s) est-il acceptable au vu des SLA réels des tâches, ou faut-il réduire à 2 tentatives ?
- Faut-il journaliser un avertissement quand une fonction `async def` est fournie, pour signaler que la lib ne peut pas garantir qu'elle ne bloque pas la boucle ? Utile en diagnostic, potentiellement bruyant pour les tâches correctement écrites.
