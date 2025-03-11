from typing import Any
from jaf.types import Document
import copy
class ParserBase:
    def __init__(self) -> None:
        pass
        
    def __call__(self, document:Document, **kwargs) -> Any:
        return self.parse(document, **kwargs)

    def parse(self):
        raise NotImplementedError
    
    def create_document(self, doc:Document,subdoc_id, header, chunk, metadata={}):
        doc.add_property("subdoc_id",subdoc_id)
        doc.add_property("text", chunk)
        doc.add_property("metadata", metadata)  # fix this hack
        doc.add_metadata("header", header)
        return copy.deepcopy(doc)