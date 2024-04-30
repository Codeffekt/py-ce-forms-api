from py_ce_forms_api import *

client = CeFormsClient()
forms = client.query().with_root("forms-sample-barcode").with_sub_forms(False).with_limit(10).call()

for form in forms.forms():
    print(form)


