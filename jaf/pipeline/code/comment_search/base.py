from jaf.pipeline.base import Pipeline
from jaf.pipeline.type import PipelineTypeEnum


class CommentSearchPipeline(Pipeline):
    def __init__(self) -> None:
        super().__init__(PipelineTypeEnum.COMMENT_SEARCH_PIPELINE)

    def validate_pipe(self):
        return True