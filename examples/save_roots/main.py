import sys
from py_ce_forms_api import *

def main():
    client = CeFormsClient()
    query = client.query().with_func("getFormsRootQuery")

    res = FormsResIterable(query)

    JsonDump.iter_to_file(res, sys.stdout)    

if __name__ == '__main__':
    main()




