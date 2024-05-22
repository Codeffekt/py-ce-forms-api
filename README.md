# Py Ce Forms Api

## Quickstart

### Introduction

The `py-ce-forms-api` module allows you to interact with the CeForms API for form management. Before getting started, ensure you have obtained the necessary credentials:

- **CE_FORMS_BASE_URL**: The base URL for the CeForms API.
- **CE_FORMS_TOKEN**: Your authentication token for accessing the CeForms API.
 
### Installation

You can install `py-ce-forms-api` via pip:

```bash
pip install py-ce-forms-api
```

### Usage

Once installed, you can start using the module in your Python code:

```python
from py_ce_forms_api import CeFormsClient

# Initialize the client
ce_forms_client = CeFormsClient(base_url=<CE_FORMS_BASE_URL>, token=<CE_FORMS_TOKEN>)

# Example: Retrieve a list of forms
forms = ce_forms_client.query().with_sub_forms(False).with_limit(10).call()
for form in forms:
    print(form)
```

Replace <CE_FORMS_BASE_URL> and <CE_FORMS_TOKEN> with your actual base URL and authentication token, respectively.

## SDK Documentation

See *[CeForms SDK for Python](https://py-ce-forms-api.readthedocs.io/en/latest/index.html)*

## Development

 > pip install -e .

### package building

 > python3 setup.py sdist bdist_wheel

### package publishing

 > python3 -m twine upload --repository <repository> dist/*
