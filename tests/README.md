# Tests

## Lancer les tests

```bash
make venv     # .venv + dépendances (une seule fois)
make test     # suite complète
make test-cov # avec rapport de couverture (term + htmlcov/)
```

Ou directement :

```bash
.venv/bin/pytest
.venv/bin/pytest tests/test_form.py -k timestamp -v
```

## Principes

- **Aucun test ne sort sur le réseau.** Deux niveaux de doublure :
  - `mocked_responses` (lib [`responses`](https://github.com/getsentry/responses)) intercepte
    les appels `requests` — utilisé pour tester `APIClient` et les parcours bout en bout.
  - `FakeAPIClient` (dans `conftest.py`) remplace `APIClient` pour tout ce qui est au-dessus
    du transport : il enregistre les appels (`client.calls`, `client.last_call`) et rejoue des
    réponses fournies au constructeur, ex. `fake_client(call_mutation={...})`.
- **L'environnement est isolé.** La fixture autouse `clean_env` supprime les variables
  `CE_FORMS_*` : les tests ne dépendent jamais de la config locale du développeur.
- **Les payloads sont construits par fabrique**, pas copiés à la main :
  `make_form_dict()` / `make_block()` dans `conftest.py` (exposés aussi via les fixtures
  `form_factory` / `block_factory`).

## Organisation

| Fichier | Couvre |
| --- | --- |
| `test_api_client.py` | transport HTTP : env vars, enveloppe JSON, auth, upload/download, erreurs |
| `test_form.py` | `Form` : valeurs, blocs, sous-formulaires, nodes, timestamps |
| `test_form_block.py` | `FormBlock` (typage des valeurs) et `FormUtils.eval` |
| `test_query.py` | `FormsQuery`, `FormsQueryArray`, `FormQueryNode`, `FormsRes`, pagination |
| `test_mutation.py` | `FormMutate` : create / update / delete / copy |
| `test_assets.py` | buckets, upload, download, asset arrays, cache local |
| `test_client.py` | câblage de `CeFormsClient`, `Forms`, `Roots`, `Accounts`, `OldProjects` |
| `test_io.py` | `JsonDump` / `MdDump` |
| `test_processing.py` | `Task`, `TaskPool`, `ProcessingTasks` et l'app FastAPI |
| `test_processing_client.py` | `ProcessingClient` (start / cancel / status) |
| `test_end_to_end.py` | parcours complets à travers la vraie pile, seul HTTP est simulé |

## Marqueur `integration`

Les tests marqués `@pytest.mark.integration` visent un vrai backend CeForms et sont
désélectionnés par défaut (`addopts = -m "not integration"` dans `pytest.ini`).
Pour les exécuter :

```bash
export CE_FORMS_BASE_URL=... CE_FORMS_TOKEN=...
.venv/bin/pytest -m integration
```

Attention : la fixture autouse `clean_env` efface les variables `CE_FORMS_*`. Un test
d'intégration doit donc lire sa configuration via `os.environ` **avant** cette fixture,
ou la demander explicitement (voir `pytest.ini` si le besoin se présente).

## Tests `xfail`

Aucun pour l'instant. Convention : un bug connu mais non corrigé se documente avec
`@pytest.mark.xfail(strict=True, reason=...)`. `strict=True` fait échouer la suite le jour
où le bug est corrigé — c'est le signal pour retirer le marqueur.
