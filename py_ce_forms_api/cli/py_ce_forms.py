import argparse

from ..client import CeFormsClient
from .form_info import FormInfo

def cli():    
    parser = argparse.ArgumentParser(
        prog='py-ce-forms',
        usage='%(prog)s [options]',
        description='A Python CLI for ce-forms API'
    )
    parser.add_argument('id', help='The form/root id', type=str)
    parser.add_argument('-w', '--with-root', help='View the root of the specified form', action='store_true')
    args = parser.parse_args()

    client = CeFormsClient()
        
    try:         
        info = FormInfo(client, args.id)
        if args.with_root:
            print(info.get_root())
        else:
            print(info.get_summary())
    except TypeError:
        print(f"Error with form id {args.id}.")
        exit(1)
    