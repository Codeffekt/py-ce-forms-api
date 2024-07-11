import sys
from py_ce_forms_api import *

possible_operations = ["start", "cancel", "status"]

def main(id, operation):
    processing_client = CeFormsClient().processing_client(id)        
    
    if operation == "start":
        print(processing_client.start())
    elif operation == "cancel":
        print(processing_client.cancel())
    elif operation == "status":
        print(processing_client.status())

if __name__ == '__main__':
    args = sys.argv[1:]
    if len(args) == 2 and args[1] in possible_operations:                                    
        main(args[0], args[1])
    else:
        print('Invalid number of arguments: <processing id> <operation = start|cancel|status>')




