import logging
from enum import Enum

from jaf.pipeline.base import Pipeline
from jaf.pipeline.type import PipelineTypeEnum

class RAGPipeEnum(Enum):
    ENCODE = 0
    RETRIVE = 1
    AUGMENT = 2
    GENERATE = 3


class RAGPipeline(Pipeline):
    def __init__(self) -> None:
        super().__init__(PipelineTypeEnum.RAG_PIPELINE)

    def validate_pipe(self):
        logging.warning("Validate pipe is not implented for ragpipeline")
        return True
    