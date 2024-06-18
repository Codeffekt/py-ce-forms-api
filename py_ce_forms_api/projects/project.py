from ..form import Form

class Project:
    """
    An utility class to manipulate form project
    """

    asset_field = "_assets"

    def __init__(self, form: Form) -> None:
        self.form = form
    
    def get_asset_ref(self) -> str:
        return self.form.get_value(self.asset_field)