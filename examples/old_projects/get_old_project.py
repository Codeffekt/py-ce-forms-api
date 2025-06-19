import sys
from py_ce_forms_api import *
import json

def main(pid):
    old_projects = CeFormsClient().old_projects()
    old_project = old_projects.get_project(pid)

    print(old_project)
    
    print(json.dumps(old_project.form, indent=4))

if __name__ == '__main__':
    args = sys.argv[1:]
    if len(args) == 1:
        main(args[0])
    else:
        print('Invalid number of arguments: <project id>')




