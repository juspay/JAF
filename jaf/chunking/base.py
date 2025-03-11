from uuid import uuid4

from jaf.types import Document

class ChunkingBase:
    def __init__(self, chunk_size=258, chunk_property_name="chunk") -> None:
        self.chunk_size = chunk_size
        self.chunk_property_name = chunk_property_name
    
    def chunk_text(self, document, **kwargs):
        return NotImplementedError

    def chunk_text_list(self, documents, **kwargs):
        chunks = []
        for doc in documents:
            chunks += self.chunk_text(doc, **kwargs)
        return chunks

    def __call__(self, documents, **kwargs):
        """ From texts return list of chunks

            format of text will be [(heading, text)]
        """
        if isinstance(documents, list):
            return self.chunk_text_list(documents, **kwargs)
        
        return self.chunk_text(documents, **kwargs)
    
    # def create_chunk_dict(self, document_id, chunk, metadata={}, additional_cols={}, **kwargs):
    #     return {
    #         "document_id": document_id,
    #         "chunk_id": str(uuid4()),
    #         "chunk": chunk,
    #         "metadata": metadata,
    #         **additional_cols
    #     }
        


