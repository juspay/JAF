from jaf.config.LLMConfig.base import LLMConfig
from dataclasses import dataclass

@dataclass 
class DefaultAnyScaleConfig(LLMConfig):
    api_base= "https://api.endpoints.anyscale.com/v1"
    model = "mistralai/Mixtral-8x7B-Instruct-v0.1"
    