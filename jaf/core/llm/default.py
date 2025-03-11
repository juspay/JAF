from jaf.core.llm.openai import AzureGPTLLM
from jaf.core.llm.together import TogetherLLMProvider

import os

def get_llm_instance():
    openai_configs = ['OPENAI_KEY', 'DEPLOYMENT_NAME', 'API_BASE', 'API_VERSION']    
    if all(config in os.environ for config in openai_configs):
        llm = AzureGPTLLM(
            api_key=os.environ['OPENAI_KEY'],
            deployment_name=os.environ['DEPLOYMENT_NAME'],
            api_base=os.environ['API_BASE'],
            api_version=os.environ['API_VERSION'],
            stream=True
        )
        return llm
    elif 'TOGETHER_AI_KEY' in os.environ:
        llm = TogetherLLMProvider(
            api_key=os.environ['TOGETHER_AI_KEY'],
            stream=True
        )
        return llm
    else:
        raise Exception("Neither OPENAI_KEY nor TOGETHER_AI_KEY is set.")