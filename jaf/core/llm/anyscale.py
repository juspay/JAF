from openai import OpenAI
from jaf.core.llm.base import LLMBase
from jaf.config.LLMConfig.AnyscaleConfig import DefaultAnyScaleConfig

class AnyscaleLLMProvider(LLMBase):
    def __init__(self,config :DefaultAnyScaleConfig ,api_key=None,api_base=None,model=None) -> None:
        self.api_base = config.api_base or api_base
        self.api_key = api_key 
        self.model=config.model or model
        self.client=self.__get_client()
        super().__init__()

    def __get_client(self):
        client = OpenAI(api_key=self.api_key,
        base_url=self.api_base,
        )
        return client
    
    def chat(self, system_message, user_message, **kwargs):
        """ 
            GenerationConfig = {
                "temperature" : "",
                "top_p" = 0.5,
                "max_tokens":100
                "stop": ["goodbye"],
                "frequency_penalty": 0
                "presence_penalty" : 0
                ""
            }
        """
        
        chat_completion = self.client.chat.completions.create(
                messages=[
                    {
                    "role": "user",
                    "content": user_message,
                    },
                    {
                    "role": "system",
                    "content": system_message
                    }
                ],
                model=self.model,
                max_tokens=1024,
                temperature=0.1,
                top_p=0.95,
                )
        return chat_completion.choices[0].message.content

    def stream_chat_completion(self):
        raise NotImplementedError



    



    