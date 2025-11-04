from ..core import FormCore
from ..query import FormsRes, FormsResIterable

class MdDump:
        
   def form_to_str(form: FormCore):
       return MdDump._dumps(form.get_form())
    
   def list_to_str(elts: list[FormCore]):
       return MdDump._dumps([form.get_form() for form in elts])
   
   def res_to_str(res: FormsRes):
       return MdDump._dumps([form.get_form() for form in res])
   
   def res_to_file(res: FormsRes, file):
       return MdDump._dump([form.get_form() for form in res], file)
   
   def iter_to_str(iter: FormsResIterable):       
       return MdDump._dumps([form.get_form() for forms in iter for form in forms.forms()])
   
   def iter_to_file(iter: FormsResIterable, file):
       return MdDump._dump([form.get_form() for forms in iter for form in forms.forms()], file)
   
   def _dumps(elt: dict):
       return json.dumps(elt, indent=JSON_IDENT)
   
   def _dump(elt: dict, file):
       return json.dump(elt, file, indent=JSON_IDENT)
    