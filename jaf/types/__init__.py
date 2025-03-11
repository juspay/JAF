import uuid
from abc import abstractmethod
from typing import List, Optional, Dict, Any, Generator

from pydantic import BaseModel, Field
from openai.types.chat import ChatCompletion

from jaf.types.common import Property, LLMContext, QueryFilter, FewShotExample, PropertyConfig, GenerationConfig
from jaf.types.tools import LLMCallableFunction



class TypeBase(BaseModel):
    properties : List[Property] = []

    def add_property(self, property: Property) -> "Chunk":
        if property is None:
            raise ValueError(f"Can not insert empty/none propery.")
        self.properties.append(property)

    def update_property(self, name, value):
        for i in self.properties:
            if i.name == name:
                i.value = value
                return i
        return None
            
    def get_property(self, name):
        for i in self.properties:
            if i.name == name:
                return i
        return None

    def renove_property(self, name, inplace=True):
        # TODO: remove property from the list
        raise NotImplementedError
    
    def db_dump_dict(self) -> dict:
        props = {}
        for p in self.properties:
            if p.persist_to_db:
                props[p.name] = p.value
        
        return props


class Document(TypeBase):
    doc_id : str = Field(default_factory=lambda : uuid.uuid4().hex)
    path : Optional[str] = None
    text : Optional[str] = None
    # Todo: Add support for multi chunk
    property_config : PropertyConfig


class Chunk(TypeBase):
    chunk_id : str  = Field(default_factory=lambda : uuid.uuid4().hex)
    doc_id : Optional[str] = None

class Query(TypeBase):
    prompt : Optional[str] = None 
    system_prompt : Optional[str] = None
    chat_history : Optional[List[str]] = []
    few_shot_examples : Optional[List[FewShotExample]] = []
    retrived_context : Optional[List[LLMContext]] = None
    tools : Optional[LLMCallableFunction] = None
    filters : Optional[List[QueryFilter]] = None
    citations : Optional[Dict[str,Any]] = None
    response : Optional[str| ChatCompletion| Generator] = None
    response_format : Optional[str] = None
    llm_generation_config : GenerationConfig = GenerationConfig()


    def get_few_shots_oai_payload(self):
        payload = []
        for f in self.few_shot_examples:
            payload+=f.to_oai_payload()
        
        return payload
    
    
    def get_few_shots_bedrock_payload(self):
        payload = []
        for f in self.few_shot_examples:
            payload+=f.to_bedrock_payload()
        
        return payload