from ..core import FormCore
from ..query import FormsRes, FormsResIterable
import json

JSON_IDENT = 4

class JsonDump:
        
   def form_to_str(form: FormCore):
       return JsonDump._dumps(form.get_form())
   
   def form_to_file(form: FormCore, file):
       return JsonDump._dump(form.get_form(), file)
    
   def list_to_str(elts: list[FormCore]):
       return JsonDump._dumps([form.get_form() for form in elts])
   
   def list_to_file(elts: list[FormCore], file):
       return JsonDump._dump([form.get_form() for form in elts], file)
   
   def res_to_str(res: FormsRes):
       return JsonDump._dumps([form.get_form() for form in res])
   
   def res_to_file(res: FormsRes, file):
       return JsonDump._dump([form.get_form() for form in res], file)
   
   def iter_to_str(iter: FormsResIterable):       
       return JsonDump._dumps([form.get_form() for forms in iter for form in forms.forms()])
   
   def iter_to_file(iter: FormsResIterable, file):
       return JsonDump._dump([form.get_form() for forms in iter for form in forms.forms()], file)
   
   def _dumps(elt: dict):
       return json.dumps(elt, indent=JSON_IDENT)
   
   def _dump(elt: dict, file):
       return json.dump(elt, file, indent=JSON_IDENT)
    