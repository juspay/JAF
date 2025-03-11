from typing import Optional

from jaf.types import Chunk, Query
from jaf.core.encode.base import EncoderBase



class HybridEncoder(EncoderBase):
    def __init__(self, dense_encoder:Optional[EncoderBase]=None, sparse_encoder:Optional[EncoderBase]=None) -> None:
        super().__init__()
        
        if not dense_encoder or not sparse_encoder:
            raise ValueError("Either value of dense_encoder or sparse_encoder is not provided")

        self.dense_encoder = dense_encoder
        self.sparse_encoder = sparse_encoder

    def encode(self, query:Query, **kwargs):
        query = self.dense_encoder.encode(query, **kwargs)
        return self.sparse_encoder.encode(query, **kwargs)

