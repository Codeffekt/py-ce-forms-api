import sys
from py_ce_forms_api import *

def main(pid, fid):
    client = CeFormsClient()
    forms = client.query().with_root(root).with_sub_forms(False).with_limit(10).call()

    for form in forms.forms():
        print(form)

if __name__ == '__main__':
    args = sys.argv[1:]
    if len(args) == 2:
        main(args[0], args[1])
    else:
        print('Invalid number of arguments: <project id> <form assoc field id>')




