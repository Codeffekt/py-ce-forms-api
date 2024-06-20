import sys
from py_ce_forms_api import *

def main(fid, aid):
    client = CeFormsClient()
    form = client.forms().get_form(fid)
    res = client.forms().get_form_assoc(form.get_assoc(aid))    

    for forms in res:    
        for form in forms.forms():
            print(form)

if __name__ == '__main__':
    args = sys.argv[1:]
    if len(args) == 2:
        main(args[0], args[1])
    else:
        print('Invalid number of arguments: <form id> <form assoc field id>')




