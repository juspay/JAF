from typing import List

from jaf.types import Query, FewShotExample
from jaf.pipeline import Hook
from jaf.pipeline.type import PipelineTypeEnum
from jaf.pipeline.base import Pipeline
from jaf.pipeline.code.fdep.base import FDepBase
from jaf.pipeline.code.fdep.utils import CODE_REFACTOR_SYSTEM_PROMPT, CODE_REFACTOR_SYSTEM_PROMPT_INSTRUCTIONS



class FDepCodeRefactorPipeline(FDepBase, Pipeline):
    def __init__(self, data_json_path: str) -> None:
        self.system_prompt = CODE_REFACTOR_SYSTEM_PROMPT
        self.system_prompt_instructions = CODE_REFACTOR_SYSTEM_PROMPT_INSTRUCTIONS
        self.few_shot_examples = []

        FDepBase.__init__(self, data_json_path)
        Pipeline.__init__(self, PipelineTypeEnum.CODE_REFACTOR_PIPELINE)
    
    def validate_pipe(self):
        return True

    def what_to_do(self, text:str) -> None:
        self.system_prompt = text
    
    def what_you_have(self, text:str) -> None:
        self.system_prompt_instructions = text

    def how_to_do(self, examples:List[FewShotExample]) -> None:
        self.few_shot_examples = examples
    
    def __run_pipeline(self, query:Query, **kwargs) -> Query:    
        query.system_prompt = self.system_prompt + "\n\n" + self.system_prompt_instructions

        if len(self.few_shot_examples) > 0:
            query.few_shot_examples = self.few_shot_examples

        return Pipeline.__call__(self, query, **kwargs)


    def __call__(self, query:Query, **kwargs) -> Query: 
        return self.__run_pipeline(query, **kwargs)