import logging
from typing import Any


from jaf.types import Query,Chunk


class Hook:
    def __init__(self, hook_name : str) -> None:
        self.hook_name = hook_name

    def process_hook(self, query:Query, **kwargs:Any) -> Query:
        raise NotImplementedError
    
    def __call__(self, query:Query | Chunk, **kwargs: Any) -> Query:
        res = Query()
        if not isinstance(query, Query | Chunk):
            raise Exception(f"Input to hook {self.hook_name} should be of type Query, but found {type(query)}")
        
        try:
            res = self.process_hook(query, **kwargs)
        except Exception as err:
            logging.exception(f"Exception occured while running hook - {self.hook_name}")

        if not isinstance(res, Query | Chunk):
            raise Exception(f"Output of hook {self.hook_name} should be of type Query, but found {type(res)}")

        return res