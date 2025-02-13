import sys
from py_ce_forms_api import *

def main(form_id, field, asset_id):
    client = CeFormsClient()
    form = client.forms().get_form(form_id)
    res = client.assets().delete_asset_array(        
        form.get_asset_array(field), 
        asset_id
        )
    print(res)

if __name__ == '__main__':
    args = sys.argv[1:]
    if len(args) == 3:
        main(args[0], args[1], args[2])
    else:
        print('Invalid number of arguments: <form_id> <field> <asset_id> required')




