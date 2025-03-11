from typing import List, Dict, Optional
import json
import requests

from jaf.logger import init_logger
from jaf.core.llm.base import LLMBase, LLMModeEnum
from jaf.types import Query
from jaf.logger import init_logger

logger = init_logger(__name__)

class LocalLLM(LLMBase):
    def __init__(self, url, verify_ssl=False) -> None:
        self.url = url
        self.verify_ssl = verify_ssl
        super().__init__( stream=False)
        
    def create_role_payload(self, role, content):
        return {"role": role, "content": content}
    
    def _create_chat_payload(self, messages, generation_config={}) -> dict:
        chat_payload = {
            "messages": messages,
            **generation_config
        }
        return chat_payload
    
    
    def _call_llm(self, chat_payload:dict, response_format:Optional[str] = None):
        payload = {
            **chat_payload,
            response_format : { "type": response_format } if response_format else None
        }
        
        res = requests.post(
            self.url,
            json=payload,
            verify=self.verify_ssl
        )
        
        return res.json()
    
    def call_llm(self, system_message:str, user_message:str, examples:list=[], generation_config:dict={}, stream:bool=False, response_format:Optional[str]=None):
        system_message = self.create_role_payload("system", system_message)
        user_message = self.create_role_payload("user", user_message)

        # Include examples if provided
        messages = examples.copy()
        messages.append(system_message)
        messages.append(user_message)

        chat_payload = self._create_chat_payload(messages, generation_config)
        try:
            return self._call_llm(chat_payload, response_format = response_format)
        except Exception as err:
            logger.exception(f"Error occured while calling local llm at {self.url}")

    
    def _chat(self, query: Query, examples: List[Dict] = None, stream=False, **kwargs):
        system_message = query.system_prompt
        user_message = query.prompt
        generation_config = query.llm_generation_config.model_dump()
        examples = query.get_few_shots_oai_payload()

        return self.call_llm(system_message,user_message, examples, stream=stream, response_format=query.response_format, generation_config=generation_config)
    
    
    def chat(self, query: Query, examples: List[Dict] = None, **kwargs) -> Query:
        res = self._chat(query, examples, stream=False)
        try:
            choices = res.get("choices", [])
            if choices:
                query.response = choices[0].get("message", {}).get("content", None)
            else:
                logger.warning(f"Empty choices from Local LLM {choices}")
        except:
            logger.exception(f"Exception occured while reading LLM response - {res}")
            query.response = None
        return query