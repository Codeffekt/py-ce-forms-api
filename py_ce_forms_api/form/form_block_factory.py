from .form_block import FormBlock
from .form_block_asset_array import FormBlockAssetArray

class FormBlockFactory:
    """
    Manage the creation of specific form block objects
    """
    def create_asset_array(block: FormBlock) -> FormBlockAssetArray:
        return FormBlockAssetArray(block)