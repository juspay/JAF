import configparser
import os
from dataclasses import dataclass

@dataclass
class LLMConfig:
    api_base : str = ""
    model : str = ""
    config_filepath : str = ""