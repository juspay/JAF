import json
from typing import List, Dict, Optional
from openai import AzureOpenAI, OpenAI
from openai.types.chat import ChatCompletion

from jaf.core.llm.base import LLMBase
from jaf.types import LLMCallableFunction, Query
from jaf.utils import get_network_proxy
from jaf.logger import init_logger

logger = init_logger(__name__)

class OpenAIBase(LLMBase):
    def __init__(self, model_name = None, stream=False, max_tokens=1000, functions: List[LLMCallableFunction] = []) -> None:
        self.max_tokens = max_tokens
        self.function_list = functions
        self.available_functions_dict = {func.name: func for func in self.function_list}
        self.model_name = model_name
        self.client = None
        super().__init__(stream=stream)

    def create_role_payload(self, role, content):
        return {"role": role, "content": content}

    def call_llm(self, system_message:str, user_message:str, examples:list=[], generation_config:dict={}, stream:bool=False, response_format:Optional[str]=None) -> ChatCompletion:
        system_message = self.create_role_payload("system", system_message)
        user_message = self.create_role_payload("user", user_message)

        # Include examples if provided
        messages = examples.copy()
        messages.append(system_message)
        messages.append(user_message)

        chat_payload = self._create_chat_payload(messages, generation_config)
        return self._call_llm(chat_payload, generation_config, stream=stream, response_format = response_format)

    def handle_chat_response(self, response:ChatCompletion, user_message:str) -> ChatCompletion:
        initial_response_message = response.choices[0].message
        tool_calls = initial_response_message.tool_calls

        if tool_calls:
            messages = [user_message, initial_response_message]

            for tool_call in tool_calls:
                function_name = tool_call.function.name
                llm_callable_function = self.available_functions_dict[function_name]
                function_args = json.loads(tool_call.function.arguments)

                try:
                    # validate_arguments(function_args, llm_callable_function.json_schema)
                    # TODO: Write a better validation function
                    function_response = llm_callable_function.function(**function_args)
                except ValueError as e:
                    function_response = f"Parsed arguments for function {function_name} are not correct: {e}"

                messages.append(
                    {
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": function_response,
                    }
                )

            second_response = self.client.chat.completions.create(model=self.deployment_name, messages=messages)
            return second_response

        return response

    def _chat(self, query: Query, examples: List[Dict] = None, stream=False, **kwargs) -> ChatCompletion:
        system_message = query.system_prompt
        user_message = query.prompt
        generation_config = query.llm_generation_config.model_dump()
        examples = query.get_few_shots_oai_payload()

        res = self.call_llm(system_message,user_message, examples, stream=stream, response_format=query.response_format, generation_config=generation_config)

        if stream:
            return res
        return self.handle_chat_response(res,user_message)

    def chat(self, query: Query, examples: List[Dict] = None, **kwargs) -> Query:
        res = self._chat(query, examples, stream=False)
        try:
            query.response = res.choices[0].message.content
        except:
            logger.exception(f"Exception occured while reading LLM response - {res}")
            query.response = None
        return query

    def stream_chat_completion(self, query: Query, examples: List[Dict] = None):
        res = self._chat(query, examples, stream=True)
        query.response = res
        return query

    def _call_llm(self, chat_payload:dict, tool_choice:str="auto", stream:bool=False, response_format:Optional[str] = None) -> ChatCompletion:
        if len(self.function_list) > 0:
            chat_payload['tools'] = [func.json_schema for func in self.function_list]
            chat_payload['tool_choice'] = tool_choice
            if stream:
                logger.warning("Function calling is not supported for streaming response")

        response = self.client.chat.completions.create(
                **chat_payload,
                model=self.model_name,
                stream=stream,
                response_format= { "type": response_format } if response_format else None
        )
        return response

    def _create_chat_payload(self, messages, generation_config={}) -> dict:
        chat_payload = {
            "messages": messages,
            **generation_config
        }
        return chat_payload


class OpenAILLM(OpenAIBase):
    def __init__(self, model_name= None, base_url=None, api_key=None, stream=False, max_tokens=1000, functions: List[LLMCallableFunction] = []) -> None:
        super().__init__(model_name, stream=stream, max_tokens=max_tokens, functions=functions)

        self.base_url = base_url
        self.api_key = api_key
        self.max_tokens = max_tokens
        self.function_list = functions

        self.client = OpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
            http_client=get_network_proxy(__name__)
        )


class AzureGPTLLM(OpenAIBase):
    def __init__(self, deployment_name=None, api_base=None, api_version=None, api_key=None, stream=False, max_tokens=1000, functions: List[LLMCallableFunction] = []) -> None:
        super().__init__(model_name=deployment_name, stream=stream, max_tokens=max_tokens, functions=functions)

        self.deployment_name = deployment_name
        self.api_base = api_base
        self.api_version = api_version
        self.api_key = api_key
        self.max_tokens = max_tokens
        self.function_list = functions

        self.client = AzureOpenAI(
            azure_endpoint=self.api_base,
            azure_deployment=self.deployment_name,
            api_version=self.api_version,
            api_key=self.api_key,
            http_client=get_network_proxy(__name__)
        )

