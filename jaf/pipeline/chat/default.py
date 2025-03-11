import os
import re
import json

from jaf.pipeline.chat import ChatPipeline
from jaf.db.vector_db import WeavaiteDBV3
from jaf.core.encode import HFEncoder
from jaf.core.augment_prompt import ChatAugmentPromptWithContext
from jaf.core.llm.default import get_llm_instance
from jaf.types import Query



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

class DefaultChatPipeline:
    _instance = None
    def __new__(cls, *args, **kwargs):
        db = get_default_db()

        if not cls._instance:
            cls._instance = super(DefaultChatPipeline, cls).__new__(cls, *args, **kwargs)
            cls._instance.chat_pipe = ChatPipeline()
            cls._instance.chat_pipe.add(HFEncoder())
            cls._instance.chat_pipe.add(db.as_hybrid_retriever("DefaultTable"))
            cls._instance.chat_pipe.add(ChatAugmentPromptWithContext())
            cls._instance.chat_pipe.add(get_llm_instance())
        return cls._instance
    
    def __call__(self, query, *args, **kwds) -> None:
        streaming_res = self.chat_pipe(Query(query, chat_history=[]))
        res = ""
        for t in streaming_res.get_property("response_stream"):
            choices = t.choices
            if len(choices)>0:
                res = choices[0].delta.content or ""
                print(res, end="")
    