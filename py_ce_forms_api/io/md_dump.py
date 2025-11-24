from ..form import Form, FormBlock
from ..query import FormsRes, FormsResIterable

class MdDump:
        
   def form_to_str(form: Form):
       return MdDump._dump(form)
    
   def list_to_str(elts: list[Form]):
       return MdDump._dumps(elts)
   
   def res_to_str(res: FormsRes):
       return [MdDump._dump(form) for form in res]   
   
   def iter_to_str(iter: FormsResIterable):       
       return MdDump._dumps([form for forms in iter for form in forms.forms()])
   
   def _dumps(elts: list[Form]):    
       str = '\n'.join([MdDump._dump(form) for form in elts])
       return str
   
   def _dump(form: Form):           
       return '\n'.join([
           MdDump._dump_header(form),
           MdDump._dump_blocks(form),
           MdDump._dump_nodes(form)
       ])
   def _dump_header(form: Form):
       return f'Form {form.get_root()} ({form.id()})'
   
   def _dump_blocks(form: Form):
       elts = [MdDump._dump_block(block) for block in form.get_blocks()]
       return 'Fields ' + ','.join(elts)       

   def _dump_block(block: FormBlock):       
       return f'{block.get_field()} ({block.get_type()})'
   
   def _dump_nodes(form: Form):
       nodes = form.get_nodes_forms()
       elts = [MdDump._dump_header(node) for node in nodes]
       return 'Nodes ' + ','.join(elts)