import sys
from py_ce_forms_api import *

def main(pid, field):
    old_projects = CeFormsClient().old_projects()    
    res = old_projects.get_project_forms(pid, field)
    
    print(JsonDump.iter_to_str(res))

if __name__ == '__main__':
    args = sys.argv[1:]
    if len(args) == 2:
        main(args[0], args[1])
    else:
        print('Invalid number of arguments: <project id> <field>')




