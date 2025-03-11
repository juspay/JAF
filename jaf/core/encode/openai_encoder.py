from typing import List, Any
from openai import OpenAI, AzureOpenAI

from jaf.types import Chunk, Query
from jaf.types.common import EmbeddingVec, Property, VectorType
from jaf.core.encode.base import EncoderBase
from jaf.utils import get_network_proxy

class OAIEncoderBase(EncoderBase):
    def __init__(self, model_name:str, client:OpenAI|AzureOpenAI) -> None:
        super().__init__()
        self.model_name = model_name
        self.client = client

    def __encode(self, properties : List[Property]):
        for property in properties:
            for config in self.get_config(property):
                val = property.value
                if config is None or config.skip_index:
                    continue
                if config.index_type == VectorType.DENSE:
                    emb = self.client.embeddings.create(input = val, model=self.model_name).data[0].embedding
                    vec_name = config.column_name if config.column_name else property.name
                    property.vectors.append(EmbeddingVec(vec_name=vec_name, value=emb, type=VectorType.DENSE))
            
        return properties

    def encode(self, input:Query|Chunk, **kwargs):
        props = self.__encode(input.properties)
        input.properties = props
        return input

    def get_vector_embedding(self,text):
        return self.client.embeddings.create(input = [text], model=self.model_name).data[0].embedding


class OpenAIEncoder(OAIEncoderBase):
    def __init__(self, model_name="text-embedding-3-small",api_key=None) -> None:
        client = OpenAI(api_key=api_key)
        super().__init__(model_name, client)

class AzureOpenAIEncoder(OAIEncoderBase):
    def __init__(self, deployment_name=None, api_base=None, api_version=None, api_key=None) -> None:
        client = AzureOpenAI(
            azure_endpoint= api_base,
            azure_deployment= deployment_name,
            api_version= api_version,
            api_key= api_key,
            http_client=get_network_proxy(__name__)
        )
        super().__init__(deployment_name, client)
