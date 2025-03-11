from openai import OpenAI

from jaf.types import Query
from jaf.core.llm.base import LLMBase
from jaf.config.LLMConfig.TogetherConfig import DefaultTogetherAiConfig
from jaf.config.LLMConfig.base import LLMConfig

class TogetherLLMProvider(LLMBase):
    def __init__(self,config :LLMConfig=DefaultTogetherAiConfig ,api_key=None,stream=False,max_tokens=4000) -> None:
        self.api_base = config.api_base
        self.api_key =api_key
        self.model=config.model
        self.client=self.__get_client()
        self.max_tokens = max_tokens
        super().__init__(stream=stream)
        
    def __get_client(self):
        client = OpenAI(api_key=self.api_key,
        base_url=self.api_base,
        )
        return client
    

    def chat_raw(self, system_message, user_message, generation_config={}, **kwargs):
        payload = {
            "max_tokens": self.max_tokens,
            "temperature": 0.2,
            "frequency_penalty": 0,
            "presence_penalty": 0,
            "top_p": 0.95,
            "stop": None,
            "messages": [
                {
                    "role": "system",
                    "content": system_message
                },
                {
                    "role": "user",
                    "content": user_message
                }

            ]
        }
        
        response = self.client.chat.completions.create(
            **payload,
            model=self.model
        )

        if response.choices[0] is not None:
            llm_res = response.choices[0].message

            if llm_res.role == "assistant":
                return llm_res.content

        return "something went wrong, unable to answer right now"


    def chat(self, query:Query, generation_config={}, **kwargs):
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
        
        llm_prompt = query.get_prompt()
        res = self.chat_raw(llm_prompt["system_message"], llm_prompt["user_message"])
        return query.add_property("response", res)


    def stream_chat_completion(self, query:Query):
        llm_prompt = query.get_prompt()
        payload = {
            "max_tokens": self.max_tokens,
            "temperature": 0.2,
            "frequency_penalty": 0,
            "presence_penalty": 0,
            "top_p": 0.95,
            "stop": None,
            "messages": [
                {
                    "role": "system",
                    "content": llm_prompt["system_message"]
                },
                {
                    "role": "user",
                    "content": llm_prompt["user_message"]
                }

            ]
        }

        stream = self.client.chat.completions.create(
            **payload,
            stream=True,
            model=self.model
        )

        return query.add_property("response_stream", stream)


    def set_api_key(self,api_key):
        self.api_key=api_key

    def set_model(self,model):
        self.model=model