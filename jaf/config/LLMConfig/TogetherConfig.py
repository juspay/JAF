from jaf.config.LLMConfig.base import LLMConfig
from dataclasses import dataclass

@dataclass 
class DefaultTogetherAiConfig(LLMConfig):
    api_base=  "https://api.together.xyz"
    model = "mistralai/Mixtral-8x7B-Instruct-v0.1"
    