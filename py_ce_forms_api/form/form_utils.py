import re

class FormUtils:
    """
    Some utils functions
    """
    def __match_func(match_obj: re.Match[str], form) -> str:          
        field = match_obj.group(1)
        if field.startswith('$'):
            meta_field = field[1:]            
            return form.form[meta_field]
        block = form.get_block(field)
        value = block.get_value()
        return value if value is not None else ''
    
    
    def eval(form, value: str) -> str:
        return re.sub('{(\$?\w+)}', lambda m: FormUtils.__match_func(m, form), value)
    