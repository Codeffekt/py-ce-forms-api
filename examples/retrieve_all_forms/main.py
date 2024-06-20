from py_ce_forms_api import *

client = CeFormsClient()
res = FormsResIterable(client.query())

for forms in res:    
    for form in forms.forms():
        print(form)


