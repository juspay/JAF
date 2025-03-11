
from jaf.parser.parser_base import ParserBase



class HTMLParser(ParserBase):
    def __init__(self) -> None:
        super().__init__()


    def parse(self):
        """ 
            TODO: Parse HTML page, returns metadata with table in structure etc
        """
        raise NotImplementedError