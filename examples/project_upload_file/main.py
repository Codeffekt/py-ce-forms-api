import sys
from py_ce_forms_api import *

def main(pid, file_path):
    client = CeFormsClient()
    res = client.projects().upload_file(pid, file_path)
    print(res)

if __name__ == '__main__':
    args = sys.argv[1:]
    if len(args) == 2:
        main(args[0], args[1])
    else:
        print('Invalid number of arguments: pid and file_path required')




