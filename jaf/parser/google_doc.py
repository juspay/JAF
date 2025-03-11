from typing import List, Any
from enum import Enum, auto

from jaf.parser.parser_base import ParserBase
from jaf.types import Document
from jaf.parser.markdown import MarkdownParserV2,MarkdownElementType

class GoogleDocType(Enum):
    title = auto()
    text = auto()
    code = auto()
    subtitle = auto()
    image = auto()
    table = auto()
    url = auto()


class GoogleDocElement:
    def __init__(self, type:GoogleDocType, element:str, title_level:int=-1) -> None:
        self.type = type
        self.element = element
        self.title_level = title_level

    def __repr__(self) -> str:
        return f"type: {self.type}\ncontent: {self.element}" + (f"\ntitle-level: {self.title_level}" if self.title_level > -1 else "")
    
class GoogleDocParser(ParserBase):
    def __init__(self,ignore_elements:List[GoogleDocType] = []) -> None:
        self.ignore_elements = ignore_elements
        super().__init__()

    def parse(self,document: Document):
        doc_text = document.get_property("document_text")

        try:
            import pypandoc
        except ModuleNotFoundError as e:
            print("Module `pypandoc` not found, run `pip3 install pypandoc_binary>=1.13` to install it")

        if doc_text is None:
            doc_text = pypandoc.convert_file(document.get_property("document_path"),'md')
        else:
            doc_text = pypandoc.convert_file(doc_text,'md')
        
        if doc_text is None:
            raise Exception("Some issue while reading file")
        
        ignore_elements = [getattr(MarkdownElementType,item) for item in self.ignore_elements]
       
        obj = MarkdownParserV2(ignore_elements=ignore_elements)
        return obj.parse(Document(document_text=doc_text))