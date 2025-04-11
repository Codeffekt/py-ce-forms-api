import sys
from py_ce_forms_api import *

def main(form_id, field, original_name):
    client = CeFormsClient()
    form = client.forms().get_form(form_id)        
    res = client.assets().get_assets_with_original_name(form.get_asset_array(field), original_name)    
    for forms in res:    
        for form in forms.forms():
            print(form.get_value("originalname"))            
    

if __name__ == '__main__':
    args = sys.argv[1:]
    if len(args) == 3:
        main(args[0], args[1], args[2])
    else:
        print('Invalid number of arguments: <form_id> <field> <original_name>')




