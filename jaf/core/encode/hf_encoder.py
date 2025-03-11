from jaf.types import Chunk, Query
from jaf.core.encode.base import EncoderBase

class HFEncoder(EncoderBase):
    def __init__(self, model="thenlper/gte-base") -> None:
        super().__init__()

        try:
            from sentence_transformers import SentenceTransformer
        except ModuleNotFoundError as e:
            print("Module `sentence-transformers` not found, run `pip3 install sentence-transformers==3.0.0` to install it")

        self.model_name = model
        self.model = SentenceTransformer(model)
        self.embedding_dim=self.model._first_module().get_word_embedding_dimension()
    def encode_chunk(self, chunk:Chunk, **kwargs):
        text = chunk.get_chunk_text()
        emb = self.model.encode(text).tolist()
        return chunk.add_vector(emb)

    def encode(self, query:Query, **kwargs):
        # repr_text = query.get_property("rephrased_query")

        # if repr_text:
        #     text = repr_text[0]
        # else:
        text = query.get_query()

        emb = self.model.encode(text).tolist()
        return query.add_vector(emb)
    
    def get_vector_embedding(self,text):
        return self.model.encode(text).tolist()


    
    