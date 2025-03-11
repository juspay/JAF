from jaf.pipeline.base import Pipeline
from jaf.pipeline.code.fdep.base import FDepBase
from jaf.pipeline import Hook
from jaf.pipeline.type import PipelineTypeEnum
from jaf.types import Query
from typing import Literal
import json
from jaf.parser.haskell_treesitter.treesitter_hs import TreesitterHaskell
from jaf.types.common import Property

class FDepCodeCommentInsertionPipeline(FDepBase, Pipeline):
    def __init__(self, comment_json_path: str, repo_path :str ,insertion_param: Literal["comment","code_block"], retries=[], skip_module_patterns=[], overwrite=False) -> None:
        self.node_comment_dict = {}
        self.tree = TreesitterHaskell()
        self.insertion_param = insertion_param
        self.comment_json_path = comment_json_path
        self.repo_path = repo_path
        Pipeline.__init__(self, PipelineTypeEnum.CODE_COMMENT_PIPELINE)
        self.pre_hooks = []
        self.retries = retries
        self.skip_module_patterns = skip_module_patterns
        self.overwrite = overwrite

    def validate_pipe(self):
        return True

    def __run_pipeline(self, q:Query, **kwargs) -> Query:
        if self.insertion_param == "comment":
            module_name = q.get_property("module_name").value
            self.traverse_json_and_insert(self.comment_json_path, self.repo_path,ignore_infix_regex="(_ | $sel)", module_name = module_name, retries=self.retries, skip_module_patterns=self.skip_module_patterns, overwrite=self.overwrite)
        else:
            print("Other Insertion Params are not Implemented Yet")
        Pipeline.__call__(self, q, **kwargs)
        return q


    def __call__(self, module_name=None, **kwargs) -> Query: 
        q = Query()
        p = Property(name="module_name", value=module_name)
        q.add_property(p)
        return self.__run_pipeline(q, **kwargs)
    
