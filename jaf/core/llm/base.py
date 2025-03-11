from enum import Enum

from jaf.types import Query


class LLMModeEnum(Enum):
    CHAT_COMPLETION = "chat_completion"




class LLMBase:
    def __init__(self, mode=LLMModeEnum.CHAT_COMPLETION, stream=False) -> None:
        self.mode = mode
        self.stream = stream

    def chat(self, query, context)->Query:
        raise NotImplementedError
    
    def stream_chat_completion(self):
        raise NotImplementedError 
    
    def __call__(self, x, **kwargs)->Query:
        
        if self.mode == LLMModeEnum.CHAT_COMPLETION:
            if self.stream:
                return self.stream_chat_completion(x, **kwargs)
            else:
                return self.chat(x, **kwargs)
        else:
            raise "No other mode for LLM is supported"


