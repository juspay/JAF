import logging
from typing import List

from typing import Dict, Any

from jaf.types import Query
from jaf.pipeline.hooks import Hook
import gc

class Pipeline:
    def __init__(self, pipeline_enum) -> None:
        """
            func = {
                "func" : "",
                "only_run_once": "",
                "validate" : ""
            }
        """

        if pipeline_enum is None:
            raise f"pipeline_name is not set for {self.get_pipeline_class_name()}"

        self.pipeline_enum = pipeline_enum
        self.funcs = []
        self.runs = []
        self.pre_hooks : List[Hook] = []
        self.post_hooks : List[Hook] = []

    def validate_pipe(self):
        raise NotImplementedError

    def get_pipeline_class_name(self):
        return type(self).__name__

    def add(self, func, additional_args={}, callback_func=None, callback_func_args={}):
        setattr(func, "pipeline_enum", self.pipeline_enum)
        self.funcs.append({"func": func,
                           "additional_args": additional_args,
                           "callback_func": callback_func,
                           "callback_func_args": callback_func_args})
        return self

    def add_pre_hook(self, func:Hook) -> None:
        """ pre-hook func should always take query as input and return query as output
        """
        self.pre_hooks.append(func)
        return self

    def add_post_hook(self, func:Hook) -> None:
        """ pre-hook func should always take query as input and return query as output
        """
        self.post_hooks.append(func)
        return self

    def decide(self):
        """function to decide next action for chain node o/p
            should return one of following decisions

            MOVE_NEXT
            STOP
            REASK
            STOP_AND_CHECKPOINT
        """

        raise NotImplementedError

    def validate(self):
        """function to validate llm outputs"""
        raise NotImplementedError

    def _run_hooks(self, hooks: List[Hook], query:Query, **kwargs):
        for hook in hooks:
            query = hook(query, cls=self, **kwargs)
        return query

    def __call_pipeline_funcs(self, query: Query, func_dict:Dict[str, Any], **kwargs):
        func = func_dict.get("func")
        additional_args = func_dict.get("additional_args", {})
        callback_func = func_dict.get("callback_func")
        callback_func_args = func_dict.get("callback_func_args", {})

        out = func(query, **additional_args, **kwargs)

        if callback_func is not None:
            try:
                callback_func(pipeline_output=out, **callback_func_args)
            except Exception as e:
                logging.error("Exception occured while calling callback in pipleine ", e)
                raise

        return out


    def __call__(self, x:Query, prev_outputs=[], **kwargs) -> Query:
        """Run all the funcs in sequentially, may use output of prev run"""
        if not self.validate_pipe():
            raise "Pipeline Validation failed."

        # running pre hooks
        x = self._run_hooks(self.pre_hooks, x, **kwargs)
        
        prev_output = x

        for idx, func_dict in enumerate(self.funcs):
            # TODO: Add support for user intervation required etc.
            try:
                x = self.__call_pipeline_funcs(prev_output, func_dict, **kwargs)
                prev_output = x
            except Exception as err:
                logging.error("Got exception while running pipeline", err)
                raise

        # running post hooks
        prev_output = self._run_hooks(self.post_hooks, prev_output, **kwargs)
        gc.collect()
        return prev_output

    def skip_step(idx, task):
        raise NotImplementedError