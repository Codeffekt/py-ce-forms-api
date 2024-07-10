import sys
from py_ce_forms_api import *

def main(id, output_file_path):
    client = CeFormsClient()    
    res = client.assets().download_file(id)
    output_file = open(output_file_path, "wb")
    output_file.write(res)
    output_file.close()

if __name__ == '__main__':
    args = sys.argv[1:]
    if len(args) == 2:
        main(args[0], args[1])
    else:
        print('Invalid number of arguments: <asset id> <output file name>')




