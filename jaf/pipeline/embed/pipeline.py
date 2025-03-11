from jaf.pipeline.embed.base import IndexPipeline


"""
    1. create vector db, once
    2. Parse document
"""



class DefaultIndexPipeline(IndexPipeline):
    def __init__(self, configs) -> None:
        super().__init__(config=configs)

    def validate_pipe(self):
        return 
    
    

