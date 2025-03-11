
from typing import Any, List

from jaf.pipeline.type import PipelineTypeEnum
from jaf.types import Chunk
from jaf.types.common import Property, IndexConfig, RetrieveConfig

class EncoderBase:
    def __init__(self) -> None:
        pass

    def encode_chunk(self, chunk, **kwargs):
        """should return vector of query as a list"""
        raise NotImplementedError

    def encode(self, chunk, **kwargs):
        raise NotImplementedError

    def get_config(self, property:Property) -> List[IndexConfig | RetrieveConfig]:
        configs = property.index_config or property.retrieve_config

        if not isinstance(configs, list):
            return [configs]
        return configs


    def __batch_encode_call(self, chunks, **kwargs):
        embeddings = []
        for chunk in chunks:
            embeddings.append(self.__encode_call(chunk, **kwargs))

        return embeddings

    def __encode_call(self, chunk, **kwargs):
        return self.encode(chunk, **kwargs)


    def __call__(self, chunk, **kwargs) -> Any:
        """
            text either will be list of text or just text to encode

            [text1, text2, ....]
        """
        if isinstance(chunk, list):
            return self.__batch_encode_call(chunk, **kwargs)

        return self.__encode_call(chunk, **kwargs)

    def create_embedding_obj(self, document_id, chunk_id, chunk, embedding, metadata={}, **kwarg):
        return {
            "document_id" : document_id,
            "chunk_id":chunk_id,
            "chunk" : chunk,
            "embedding" : embedding,
            "metadata": metadata
        }