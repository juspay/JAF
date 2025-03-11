from typing import List, Dict, Optional
import boto3
from botocore.exceptions import ClientError

from jaf.core.llm.base import LLMBase, LLMModeEnum
from jaf.types import Query
from jaf.logger import init_logger

logger = init_logger(__name__)

class BedrockLLM(LLMBase):
    def __init__(self, deployment_name, stream=False) -> None:
        self.deployment_name= deployment_name
        self.client = boto3.client(
            service_name="bedrock-runtime"
        )
        self.function_list = []     #TODO: Add support for function call
        super().__init__(stream=stream)
    
    def create_role_payload(self, role, content):
        return {"role": role, "content": {"text":content}}
    
    def _create_chat_payload(self, system_message, messages, generation_config={}) -> dict:
        chat_payload = {
            "modelId": self.deployment_name,
            "messages": messages,
            "system": {
                "text": system_message
            },
            "inferenceConfig": generation_config
        }
        return chat_payload
    
    def _call_llm(self, chat_payload:dict, tool_choice:str="auto",  stream:bool = False, response_format:Optional[str] = None):
        # if len(self.function_list) > 0:
        #     chat_payload['tools'] = [func.json_schema for func in self.function_list]
        #     chat_payload['tool_choice'] = tool_choice
        #     if stream:
        #         logger.warning("Function calling is not supported for streaming response")

        if self.stream or stream:
            return self.client.converse_stream(**chat_payload)
        
        
        response = self.client.converse(
                **chat_payload
        )
        return response
    
    def call_llm(self, system_message:str, user_message:str, examples:list=[], generation_config:dict={}, stream:bool=False, response_format:Optional[str]=None):
        user_message = self.create_role_payload("user", user_message)

        # Include examples if provided
        messages = examples.copy()
        messages.append(user_message)

        chat_payload = self._create_chat_payload(system_message, messages, generation_config)
        return self._call_llm(chat_payload, generation_config, stream=stream, response_format = response_format)
        
    def _chat(self, query:Query, examples: List[Dict], stream=True):
        system_message = query.system_prompt
        user_message = query.prompt
        inference_config = query.llm_generation_config.model_dump_bedrock()
        examples = query.get_few_shots_bedrock_payload()
        
        return self.call_llm(system_message, user_message, examples, inference_config, stream=stream)
        
    def stream_chat_completion(self, query: Query, examples: List[Dict] = None):
        res = self._chat(query, examples, stream=True)
        query.response = res
        return query

    def chat(self, query: Query, examples: List[Dict] = None, **kwargs) -> Query:
        res = self._chat(query, examples, stream=False)
        try:
            res = res.get("output")
            if res:
                content = res.get("message", {}).get("content", [])
                content = "".join([c["text"] for c in content])
                query.response = content if content else None
        except:
            logger.exception(f"Exception occured while reading LLM response - {res}")
            query.response = None
        return query
    
        
"""
# bedrock output format
    {
    'output': {
        'message': {
            'role': 'user'|'assistant',
            'content': [
                {
                    'text': 'string',
                    'toolUse': {
                        'toolUseId': 'string',
                        'name': 'string',
                        'input': ""
                    },
                    'toolResult': {
                        'toolUseId': 'string',
                        'content': [],
                        'status': 'success'|'error'
                    }
                },
            ]
        }
    },
    'stopReason': 'end_turn'|'tool_use'|'max_tokens'|'stop_sequence'|'guardrail_intervened'|'content_filtered',
}
"""
