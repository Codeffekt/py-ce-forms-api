from ..form import Form
class Project:
    """
    An utility class to manipulate form project
    """

    asset_field = "_assets"

    def __init__(self, form: Form) -> None:
        
        if form is None:
            raise TypeError("Invalid none Form object passed, maybe the underlying form was not found")
        
        self.form = form         
    
    def id(self) -> str:
        return self.form.id()
    
    def get_block(self, bid) -> str:
        return self.form.get_block(bid)
    
    def get_asset_ref(self) -> str:
        return self.form.get_value(self.asset_field)
        