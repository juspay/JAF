from jaf.pipeline.base import Pipeline
from jaf.pipeline.type import PipelineTypeEnum


class CommentEmbedPipeline(Pipeline):
    def __init__(self) -> None:
        super().__init__(PipelineTypeEnum.COMMENT_EMBED_PIPELINE)

    def validate_pipe(self):
        return True