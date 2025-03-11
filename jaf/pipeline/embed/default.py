import os
import re
import json

from jaf.parser import MarkdownParser
from jaf.chunking import BasicChunking
from jaf.pipeline.embed import IndexPipeline
from jaf.types import Document


from jaf.db.vector_db import WeavaiteDBV3



def get_default_db():
    with open("examples/weaviate/default_class_objs.json", "r") as f:
        class_objs = json.load(f)

    ret_config = {
        "hybrid_search_columns" : ['processed_text'],
        "retrieve_columns": ['chunk', 'processed_text', 'document_path']
    }

    oai_keys = os.environ["AZURE_OAI_API_KEY"]
    return WeavaiteDBV3(class_objs=class_objs, retrieve_config=ret_config, oai_api_key=oai_keys)


def get_chunk_metadata(markdown):
    return {"url":re.search(r'source:\s*(https?://\S+)', markdown).group(1)}


# TODO: Can be done in better way
class DefaultIndexPipeLine:
    _instance=None
    
    def __new__(cls, *args, **kwargs):
        db = get_default_db()

        if not cls._instance:
            cls._instance = super(DefaultIndexPipeLine, cls).__new__(cls, *args, **kwargs)
            cls._instance.idx_pipe = IndexPipeline()
            cls._instance.idx_pipe.add(MarkdownParser(metadata_parser=get_chunk_metadata))
            cls._instance.idx_pipe.add(BasicChunking())
            cls._instance.idx_pipe.add(db.as_indexer("DefaultTable"))
        return cls._instance
    
    def __call__(self,doc_path):
        if not os.path.exists(doc_path):
            raise FileNotFoundError("Invalid File or Folder Path")
        
        if os.path.isfile(doc_path):
            self.idx_pipe((Document(file,document_path=file)))
        if os.path.isdir(doc_path):
            files = [os.path.join(doc_path, f) for f in os.listdir(doc_path) if os.path.isfile(os.path.join(doc_path, f))]
            for file in files:
                self.idx_pipe((Document(file)))
        else:
            ValueError("Invalid File or Folder Path")