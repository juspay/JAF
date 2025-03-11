from typing import List, Optional

from enum import Enum
from pydantic import BaseModel

from jaf.logger import init_logger
logger = init_logger(__name__)

class Role(str, Enum):
    ASSISTANT = "assistant"
    USER = "user"


class VectorType(str, Enum):
    DENSE = "dense"
    SPARSE = "sparse"


class IndexConfig(BaseModel):
    column_name : str
    index_type : VectorType  =  None
    skip_index : bool = False

class RetrieveConfig(BaseModel):
    column_name : str
    index_type : VectorType = None
    filter : Optional[dict] = None
    score_threshold : Optional[float | None] = None
    skip_index : bool = False

class PropertyConfig(BaseModel):
    key : str
    index_config : Optional[IndexConfig | list[IndexConfig]] = None
    retrieve_config : Optional[RetrieveConfig | list[RetrieveConfig]] = None

class EmbeddingVec(BaseModel):
    vec_name : str
    type : VectorType
    value : List[float]|List[List[float]]

class Property(BaseModel):
    name : str
    value : Optional[str|dict|float] = None
    vectors : List[EmbeddingVec] = []
    index_config : Optional[IndexConfig| List[IndexConfig]] = None
    retrieve_config : Optional[RetrieveConfig| List[RetrieveConfig]] = None
    use_in_llm : bool = True
    persist_to_db : bool = True

class LLMContext(BaseModel):
    data : dict
    score : float
    vec_name : str
    point_id : str

class NormalizedLLMContext(BaseModel):
    data : dict
    score : float
    point_id : str
    normalized_info : Optional[List[dict]]

class QueryFilter(BaseModel):
    filter : dict
    pass


class ConversationTurn(BaseModel):
    role : Role
    message : str

    def __repr__(self) -> str:
        return f"{self.role}: {self.message}"


class FewShotExample(BaseModel):
    user : str
    assistant : str

    def to_oai_payload(self):
        return [
            {
                "role": "user",
                "content": self.user
            },
            {
                "role": "assistant",
                "content": self.assistant
            }
        ]
        
    def to_bedrock_payload(self):
        return [
            {
                "role": "user",
                "content": {
                    "text" : self.user
                }
            },
            {
                "role": "assistant",
                "content": {
                    "text": self.assistant
                    }
            }
        ]

    def __repr__(self) -> str:
        return str(vars(self))

class GenerationConfig(BaseModel):
    max_tokens: int = 4000
    temperature: float =  0.01
    frequency_penalty: int = 0
    presence_penalty: int= 0
    top_p: float = 0.95
    stop : Optional[str] = None
    
    def model_dump_bedrock(self):
        if self.frequency_penalty or self.presence_penalty:
            logger.warning("`frequency_penalty` and `presence_penalty` are not supported in amazon bedrock")
        return {
            "maxTokens": self.max_tokens,
            'temperature': self.temperature, 
            'topP': self.top_p,
        }