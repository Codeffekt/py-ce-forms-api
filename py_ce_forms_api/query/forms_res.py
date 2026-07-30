from ..form import Form

class FormsRes():
    """
    An utility class to manage query results on the forms dataset
    """
    
    def __init__(self, res) -> None:
        self.res = res

        if self.res is None:
            raise TypeError('Invalid result type None')

    def forms(self):
        return iter(self)

    def elts(self):
        return self.res['elts']
    
    def total(self):
        return int(self.res['total'])
    
    def limit(self):
        return self.res['limit']

    def offset(self):
        return self.res['offset']

    def __iter__(self):
        return map(lambda f: Form(f), self.elts())

    def __len__(self):
        return len(self.res['elts'])
    
    
            

