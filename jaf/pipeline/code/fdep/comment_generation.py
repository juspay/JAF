from typing import Optional

from jaf.pipeline.base import Pipeline
from jaf.pipeline.code.fdep.utils import CODE_COMMENT_SYSTEM_PROMPT, CODE_COMMENT_SYSTEM_PROMPT_INSTRUCTIONS
from jaf.pipeline.type import PipelineTypeEnum
from jaf.pipeline.code.fdep.base import FDepBase
from jaf.types import Query
from jaf.types.common import Property

# TODO: Add support for few shot examples
class FDepCodeCommentGenerationPipeline(FDepBase, Pipeline):
    def __init__(self, data_json_path: str, ignore_infix_regex:Optional[str]=None, module_name:Optional[str]= None) -> None:
        self.system_prompt = CODE_COMMENT_SYSTEM_PROMPT
        self.system_prompt_instructions = CODE_COMMENT_SYSTEM_PROMPT_INSTRUCTIONS
        self.pre_hooks = []
        self.post_hooks = []

        FDepBase.__init__(self, data_json_path, ignore_infix_regex, module_name)
        Pipeline.__init__(self, PipelineTypeEnum.CODE_COMMENT_PIPELINE)

    def validate_pipe(self):
        return True

    def what_to_do(self, text:str) -> None:
        self.system_prompt = text

    def when_to_do(self, text:str) -> None:
        self.system_prompt_instructions = text
    
    def __run_pipeline(self, query:Query, **kwargs) -> Query:
        query.system_prompt = self.system_prompt + "\n\n" + self.system_prompt_instructions
        return Pipeline.__call__(self, query, **kwargs)

    def __call__(self, query:Query, **kwargs) -> Query: 
        return self.__run_pipeline(query, **kwargs) 