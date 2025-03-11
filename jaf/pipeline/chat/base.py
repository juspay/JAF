import logging
from enum import Enum

from jaf.pipeline.base import Pipeline
from jaf.pipeline.type import PipelineTypeEnum


class ChatPipeEnum(Enum):
    ENCODE = 0
    SEMANTIC_ROUTING = 1
    RETRIVE = 2
    AUGMENT = 3
    GENERATE = 4
    STORE_HISTORY = 5


class ChatPipeline(Pipeline):
    def __init__(self) -> None:
        super().__init__(PipelineTypeEnum.CHAT_PIPELINE)

    def validate_pipe(self):
        logging.warning("Validate pipe is not implented for ragpipeline")
        return True