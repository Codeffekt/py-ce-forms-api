import sys
from py_ce_forms_api import *

def main(root):
    client = CeFormsClient()
    forms = client.query().with_root(root).with_limit(10).call()

    for form in forms.forms():
        print(form)

if __name__ == '__main__':
    args = sys.argv[1:]
    if len(args) == 1:
        main(args[0])
    else:
        print('Invalid number of arguments: root id')




