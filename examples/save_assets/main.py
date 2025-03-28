import sys
from py_ce_forms_api import *

def main(form_id, field, dir_path):
    client = CeFormsClient(dir_path=dir_path)
    form = client.forms().get_form(form_id)        
    res = client.assets().get_assets_from_array(form.get_asset_array(field))
    localStorage = client.assets().get_local_storage()
    for forms in res:    
        for form in forms.forms():
            print(form)
            localStorage.save(form.id())
    

if __name__ == '__main__':
    args = sys.argv[1:]
    if len(args) == 3:
        main(args[0], args[1], args[2])
    else:
        print('Invalid number of arguments: <form_id> <field> <output_dir> required')




