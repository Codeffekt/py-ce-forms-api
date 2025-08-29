import sys
from py_ce_forms_api import *

def main(id):
    client = CeFormsClient()        
    form = client.forms().get_form(id)
    form.set_readonly(True)
    client.mutation().update(form)
    print(form)    

if __name__ == '__main__':
    args = sys.argv[1:]
    if len(args) == 1:
        main(args[0])
    else:
        print('Invalid number of arguments: <form id>')




