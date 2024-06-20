from .forms_query import FormsQuery

class FormsResIterable():
    """
    An utility class to iterate over a forms query
    """

    def __init__(self, query: FormsQuery) -> None:
        self.query = query        
        self.res = None

    def __iter__(self):        
        return self

    def _next__(self): 
        if self.res is None:       
            self.res = self.query.call()
            return self.res
        else:
            limit = self.res.limit()
            offset = self.res.offset()
            total = self.res.total()
            if limit == 0 or (offset + limit) >= total or (len(self.res) < limit):
                return StopIteration
            else:
                self.query.with_offset(offset + limit)
                self.res = self.query.call()
                return self.res
            