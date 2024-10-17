import sys
from py_ce_forms_api import *

def main(id, field):
    client = CeFormsClient()    
    arrayQuery = client.query_array().with_array(id, field)
    res = FormsResIterable(arrayQuery)
    for forms in res:    
        for form in forms.forms():
            print(form)

if __name__ == '__main__':
    args = sys.argv[1:]
    if len(args) == 2:
        main(args[0], args[1])
    else:
        print('Invalid number of arguments: <form id> <form field>')




