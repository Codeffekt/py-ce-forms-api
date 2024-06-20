from .form_block import FormBlock

class FormBlockAssoc:
    """
    An utility class to manipulate a form block of type assoc
    """
    def __init__(self, form_block: FormBlock) -> None:
        self.form_block = form_block
        
    def get_root(self) -> str:
        return self.form_block.get_block_attr("root")
    
    def get_ref(self) -> str:
        try:
            return self.form_block.get_block_attr("ref")
        except KeyError:
            return f'{self.form_block.get_field()}-{self.form_block.get_form().id()}'
        
    