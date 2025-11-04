import sys
from py_ce_forms_api import *

def main(rid):
    client = CeFormsClient()
    res = client.query().with_root(rid).with_node(FormQueryNode(field="site",root="trias-project",name="project",type="index"))
    res = FormsResIterable(res)

    print(JsonDump.iter_to_str(res))


if __name__ == '__main__':
    args = sys.argv[1:]
    if len(args) == 1:
        main(args[0])
    else:
        print('Invalid number of arguments: <root id>')




