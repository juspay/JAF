from jaf.types import Chunk, Document
from jaf.types.common import Property
from jaf.chunking.base import ChunkingBase



class BasicChunking(ChunkingBase):
    def __init__(self, chunk_size=1500, overlap=100, min_chunk_len=5, split_func=None, add_properties={}, chunk_property_name="chunk", include_ancestor_headings=True) -> None:
        """ split text into chunk of words of with given chunk size length, llm token size is ignored.

            Inspired by LangChain's recursive text splitter
        """
        if chunk_size <= overlap:
            raise f"Chunksize can not be less than or equal to overlap, chunksize: {chunk_size}, overlap: {overlap}"
        
        if chunk_size < min_chunk_len:
            raise f"Chunksize can not be less than min_chunk_len, chunksize: {chunk_size}, min_chunk_len: {min_chunk_len}"

        self.min_chunk_len = min_chunk_len
        self.overlap = overlap
        self.split_func = split_func or (lambda x : x.split(" "))
        self.add_properties = add_properties
        self.include_ancestor_headings=include_ancestor_headings
        super().__init__(chunk_size, chunk_property_name)

    
    def chunk_text(self, document:Document, metadata={},**kwargs):
        """ split long text to chunk of text with given chunk size

            words will be split based on split func

            heading is ignored in basic chunking
        """
        chunks = []
        indexconfig = document.property_config.index_config
        key = document.property_config.key

        def add_overlap_to_context(chunk, overlap):
            return  " ".join(overlap) + " " + " ".join(chunk) 
        
        def add_chunk(curr_chunk, overlap_chunk):
            if len(curr_chunk) + self.overlap > self.min_chunk_len:
                chunk_text = add_overlap_to_context(curr_chunk, overlap_chunk)
                chunk = Chunk(properties=[Property(name=key,value=chunk_text,index_config=indexconfig)])    
                chunks.append(chunk)

        curr_chunk = []
        overlap_chunk = []
        
        for word in self.split_func(document.text):
            if len(curr_chunk) + self.overlap < self.chunk_size:
                curr_chunk.append(word)
            else:
                add_chunk(curr_chunk, overlap_chunk)
                overlap_chunk = curr_chunk[-self.overlap:]
                curr_chunk = []

        add_chunk(curr_chunk, overlap_chunk)
        return chunks        
        


        

        
