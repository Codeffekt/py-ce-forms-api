import sys
from py_ce_forms_api import *

def main(rid, field, root, name, type):
    client = CeFormsClient()
    res = client.query().with_root(rid).with_node(FormQueryNode(field,root,name,type))
    res = FormsResIterable(res)

    print(MdDump.iter_to_str(res))


if __name__ == '__main__':
    args = sys.argv[1:]
    if len(args) == 5:
        main(args[0], args[1], args[2], args[3], args[4])
    else:
        print('Invalid number of arguments: <field> <root> <name> <type>')




