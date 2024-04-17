from ce_forms import *

client = CeFormsClient()
forms = client.query().with_sub_forms(False).with_limit(10).call()

print(forms)

