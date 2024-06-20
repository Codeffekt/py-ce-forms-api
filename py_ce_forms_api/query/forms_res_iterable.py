from .forms_query import FormsQuery

class FormsResIterable():
    """
    An utility class to iterate over a forms query
    """

    def __init__(self, query: FormsQuery) -> None:
        self.query = query        
        self.res = None

    def __iter__(self):          
        if self.res is None:       
            self.res = self.query.call()
            yield self.res

        if self.res.limit() == 0:
            return

        limit = self.res.limit()
        offset = self.res.offset()
        total = self.res.total()                
        
        while (offset + limit) < total and (len(self.res) == limit):
            self.query.with_offset(offset + limit)
            self.res = self.query.call()
            limit = self.res.limit()
            offset = self.res.offset()
            total = self.res.total()                     
            yield self.res                                        
        
            