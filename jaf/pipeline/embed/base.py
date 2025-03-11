import logging
from enum import Enum

from jaf.pipeline.base import Pipeline
from jaf.pipeline.type import PipelineTypeEnum

__all__ = ["IndexPipeline", "IndexPipeEnum"]


class IndexPipeEnum(Enum):
    READ = 0
    PARSE = 1
    CHUNK = 2
    ENCODE = 3
    INSERT = 4


class IndexPipeline(Pipeline):
    def __init__(self) -> None:
        super().__init__(PipelineTypeEnum.INDEX_PIPELINE)

    def validate_pipe(self):
        logging.warn("Validate pipe is not implented for indexpipeline")
        return True

    def get_call_sequence(self):
        return [IndexPipeEnum.PARSE, IndexPipeEnum.CHUNK, IndexPipeEnum.ENCODE, IndexPipeEnum.INSERT]
        
    