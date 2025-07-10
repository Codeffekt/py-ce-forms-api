from py_ce_forms_api import *

def main():
    old_projects = CeFormsClient().old_projects()
    projects = old_projects.get_all()

    print(JsonDump.list_to_str(projects))

if __name__ == '__main__':
    main()




