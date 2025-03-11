import re
from enum import Enum, auto
from typing import List, Tuple, Optional


from jaf.parser.parser_base import ParserBase
from jaf.parser.utils import read
from jaf.types import Document
from jaf.types.common import Property


class MarkdownElementType(Enum):
    title = auto()
    text = auto()
    code = auto()
    subtitle = auto()
    image = auto()
    table = auto()
    url = auto()

class MarkdownElement:
    def __init__(self, type: MarkdownElementType, element:str, title_level:int=-1) -> None:
        self.type = type
        self.element = element
        self.title_level = title_level

    def __repr__(self) -> str:
        return f"type: {self.type}\ncontent: {self.element}" + (f"\ntitle-level: {self.title_level}" if self.title_level > -1 else "")


class MarkdownParserV2(ParserBase):
    def __init__(self, ignore_elements:List[MarkdownElementType] = [], split_on_elements:List[MarkdownElementType] = [MarkdownElementType.title], metadata_parser=None, include_ancestor_headings=True) -> None:
        """
            arguments: 
            1. remove_image: default True, If False, will add image as base64 string in metadata with key "images"
            2. remove_urls: default False, If True, will add urls to metadata "urls" : []
            3. 
        """
        self.ignore_elements = ignore_elements
        self.split_on_elements = split_on_elements 
        self.metadata_parser = metadata_parser
        # self.header_regex = r"^#+\s" if split_on_subheading else r"^#\s"
        self.include_ancestor_headings = include_ancestor_headings
        super().__init__()

    def parse(self, document: Document):
        markdown_text = document.text 
        document_path = document.path
        property_config = document.property_config

        if markdown_text is None:
            if document_path is None:
                raise ValueError("document_text and document_path is not set in Document")
            markdown_text = read(document_path)
            document.text = markdown_text

        
        if markdown_text is None:
            raise Exception("Some issue while reading file")

        doc_metadata = {}
        if self.metadata_parser is not None:
            doc_metadata = self.metadata_parser(markdown_text)

        elements = self.parse_elements(markdown_text)

        # ignore elements
        filtered_eles = [ele for ele in elements if ele.type not in self.ignore_elements]

        # combine elements, split only based on split_on_elements
        current_text = ""
        docs : List[Document] = []

        for element in filtered_eles:
            if element.type in self.split_on_elements and len(current_text) > 0:
                # only split doc with main title
                if (MarkdownElementType.title in self.split_on_elements 
                    and element.type == MarkdownElementType.title 
                    and element.title_level == 1):
                    current_text += "\n" + element.element
                    continue
                doc = Document(path=document_path,text=current_text,property_config=property_config)
                docs.append(doc)
                current_text = ""
            else:
                current_text += "\n" + element.element
        doc = Document(path=document_path,text=current_text,property_config=property_config)
        docs.append(doc)
        
        return docs

    def parse_elements(self, markdown_text:str) -> List[MarkdownElement]:
        """        
        modified logic from 
        llama-index-core/llama_index/core/node_parser/relational/markdown_element.py
        """
        lines = markdown_text.split("\n")
        currentElement = None

        elements: List[MarkdownElement] = []
        # Then parse the lines
        for line in lines:
            if line.startswith("```"):
                # check if this is the end of a code block
                if currentElement is not None and currentElement.type == MarkdownElementType.code:
                    elements.append(currentElement)
                    currentElement = None
                    # if there is some text after the ``` create a text element with it
                    if len(line) > 3:
                        elements.append(
                            MarkdownElement(
                                type=MarkdownElementType.text,
                                element=line.lstrip("```"),
                            )
                        )

                elif line.count("```") == 2 and line[-3] != "`":
                    # check if inline code block (aka have a second ``` in line but not at the end)
                    if currentElement is not None:
                        elements.append(currentElement)
                    currentElement = MarkdownElement(
                        type=MarkdownElementType.code,
                        element=line.lstrip("```"),
                    )
                elif currentElement is not None and currentElement.type == MarkdownElementType.text:
                    currentElement.element += "\n" + line
                else:
                    if currentElement is not None:
                        elements.append(currentElement)
                    currentElement = MarkdownElement(
                         type=MarkdownElementType.text, 
                         element=line
                    )

            elif currentElement is not None and currentElement.type == MarkdownElementType.code:
                currentElement.element += "\n" + line

            elif line.startswith("|"):
                if currentElement is not None and currentElement.type != MarkdownElementType.table:
                    if currentElement is not None:
                        elements.append(currentElement)
                    currentElement = MarkdownElement(
                         type=MarkdownElementType.table, 
                         element=line
                    )
                elif currentElement is not None:
                    currentElement.element += "\n" + line
                else:
                    currentElement = MarkdownElement(
                        type=MarkdownElementType.table, 
                        element=line
                    )
            elif line.startswith("#"):
                if currentElement is not None:
                    elements.append(currentElement)
                
                
                currentElement = MarkdownElement(
                    type=MarkdownElementType.title,
                    element=line.lstrip("#"),
                    title_level=len(line) - len(line.lstrip("#")),
                )
            else:
                if currentElement is not None and currentElement.type != MarkdownElementType.text:
                    elements.append(currentElement)
                    currentElement = MarkdownElement(
                        type=MarkdownElementType.text, 
                        element=line
                    )
                elif currentElement is not None:
                    currentElement.element += "\n" + line
                else:
                    currentElement = MarkdownElement(
                        type=MarkdownElementType.text, 
                        element=line
                    )
        if currentElement is not None:
            elements.append(currentElement)

        # for idx, element in enumerate(elements):
        #     if element.type == MarkdownElementType.table:
        #         should_keep = True
        #         # perfect_table = True

        #         # verify that the table (markdown) have the same number of columns on each rows
        #         table_lines = element.element.split("\n")
        #         # table_columns = [len(line.split("|")) for line in table_lines]
        #         # if len(set(table_columns)) > 1:
        #         #     # if the table have different number of columns on each rows, it's not a perfect table
        #         #     # we will store the raw text for such tables instead of converting them to a dataframe
        #         #     perfect_table = False

        #         # verify that the table (markdown) have at least 2 rows
        #         if len(table_lines) < 2:
        #             should_keep = False

        #         # apply the table filter, now only filter empty tables
        #         # if should_keep and perfect_table and table_filters is not None:
        #         #     should_keep = all(tf(element) for tf in table_filters)

        #         # if the element is a table, convert it to a dataframe
        #         if should_keep:
        #             # and give it a different type to differentiate it from perfect tables
        #             elements[idx] = MarkdownElement(
        #                 type=MarkdownElementType.table,
        #                 element=element.element,
        #             )
        #         else:
        #             elements[idx] = MarkdownElement(
        #                 type=MarkdownElementType.text,
        #                 element=element.element,
        #             )
            # else:
            #     # if the element is not a table, keep it as to text
            #     elements[idx] = Element(
            #         id=f"id_{node_id}_{idx}" if node_id else f"id_{idx}",
            #         type="text",
            #         element=element.element,
            #     )
                    # merge consecutive text elements together for now
        merged_elements: List[MarkdownElement] = []
        for element in elements:
            if (
                len(merged_elements) > 0
                and element.type == MarkdownElementType.text
                and merged_elements[-1].type == MarkdownElementType.text
            ):
                merged_elements[-1].element += "\n" + element.element
            else:
                merged_elements.append(element)

        return merged_elements





class MarkdownParser(ParserBase):
    def __init__(self, remove_image=True, remove_urls=True,cleaner=None, metadata_parser=None, split_on_subheading=True,include_ancestor_headings=True) -> None:
        """ Parse markdown and return list dict with header of text and content
        """
        self.remove_image = remove_image
        self.remove_urls=remove_urls
        self.cleaner=cleaner or (lambda x: x)
        self.metadata_parser = metadata_parser
        self.header_regex = r"^#+\s" if split_on_subheading else r"^#\s"
        self.include_ancestor_headings=include_ancestor_headings
        super().__init__()

    def parse(self, document:Document, **kwargs) -> List[Tuple[Optional[str], str, Optional[str]]]:
        """
            {   
                heading : ""
                chunk : ""
            }
        """
        markdown_text = document.get_property("document_text")

        if markdown_text is None:
            markdown_text = read(document.get_property("document_path"))
        
        if markdown_text is None:
            raise Exception("Some issue while reading file")

        #TODO: FIX: markdown parser do not respect codeblock and consider python code comment as heading, should ignore code blocks
        markdown_tups: List[Tuple[Optional[str], str]] = []        
        global_metadata = self.metadata_parser(markdown_text) if self.metadata_parser else {}
        lines = markdown_text.split("\n")
        parent_headings=self.get_heading_ancestors(markdown_text) if  self.include_ancestor_headings else {}
        current_header = None
        current_text = ""

        for line in lines:
            header_match = re.match(self.header_regex, line)
            if header_match:
                if current_header is not None:
                    if current_text == "" or None:
                        continue
                    current_header=parent_headings.get(current_header,current_header)
                    markdown_tups.append(self.__create_key_val_tup(current_header, current_text, self.remove_image, self.remove_urls, global_metadata))

                current_header = line
                current_text =  "\n"
            else:
                current_text += line + "\n"

        current_header=parent_headings.get(current_header,current_header)
        markdown_tups.append(self.__create_key_val_tup(current_header, current_text, self.remove_image, self.remove_urls, global_metadata))
        
        if current_header is not None:
            # pass linting, assert keys are defined
            markdown_tups = [
                self.create_document(Document(**document.get_all_properties()),index,key, re.sub(r"<.*?>", "", value), metadata)
                for index,(key, value, metadata) in enumerate(markdown_tups)
                if None not in (value,key)            
            ]
        else:
            markdown_tups = [
                self.create_document(Document(**document.get_all_properties()),index,key, re.sub("<.*?>", "", value), metadata) 
                for index,(key, value, metadata) in enumerate(markdown_tups)
            ]

        return markdown_tups
    
    def __create_key_val_tup(self, key, val, remove_images=None, remove_urls=None, metadata={}):
        if remove_images:
            val = self.remove_images(val)

        if remove_urls:
            val = self.remove_hyperlinks(val)
        val=self.cleaner(val)
        return (key, val, metadata)
    
    def remove_images(self, content: str) -> str:
        """Get a dictionary of a markdown file from its path."""
        pattern = r"!{1}\[\[(.*)\]\]"
        content = re.sub(pattern, "", content)
        return content

    def remove_hyperlinks(self, content: str) -> str:
        """Get a dictionary of a markdown file from its path."""
        pattern = r"\[(.*?)\]\((.*?)\)"
        content = re.sub(pattern, r"\1", content)
        return content
    
    def get_heading_ancestors(self,content):
        headings = re.findall(r'^(#+)\s+(.+)$', content, re.MULTILINE)
        hierarchy = []
        result = {}

        for level, heading in headings:
            heading_level = len(level)
            full_heading = level + " " + heading
            if heading_level == 1:
                hierarchy = [full_heading]
            else:
                while len(hierarchy) >= heading_level:
                    hierarchy.pop()
                hierarchy.append(full_heading)            
            hierarchy_string = '\n'.join([h.replace(' ', '') for h in hierarchy]) 
            result[full_heading] = hierarchy_string
        return result