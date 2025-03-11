from jaf.parser.markdown import MarkdownParser
from jaf.parser.rich_text import RichTextParser
from jaf.parser.html import HTMLParser
from jaf.parser.text import TextParser
# from jaf.parser.google_doc import GoogleDocParser


parser_dict = {
    "md" : MarkdownParser,
    "rtf" : RichTextParser,
    "html": HTMLParser,
    "txt" : TextParser,
}

def get_parser(file_path):
    ext = file_path.split(".")[-1]
    return parser_dict.get(ext, None)   # return generic parser if extension is not supported

    

    

    