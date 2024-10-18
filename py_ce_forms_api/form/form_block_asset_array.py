from .form_block import FormBlock

class FormBlockAssetArray:
    """
    An utility class to manipulate a form block of type asset array
    """
    def __init__(self, form_block: FormBlock) -> None:
        if form_block.get_type() != FormBlock.ASSET_ARRAY_TYPE:
            raise TypeError(f"Block must be of type {FormBlock.ASSET_ARRAY_TYPE}")
        
        self.form_block = form_block        
    
    def get_ref(self) -> str:        
        return self.form_block.get_value()