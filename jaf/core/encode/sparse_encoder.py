from typing import List
import torch
from transformers import AutoModelForMaskedLM, AutoTokenizer

from jaf.types import Chunk, Query
from jaf.types.common import Property, EmbeddingVec, VectorType
from jaf.core.encode.base import EncoderBase


class SparseEncoder(EncoderBase):
    def __init__(self, model_id = "naver/splade-cocondenser-ensembledistil") -> None:
        super().__init__()
        self.model_id = model_id
        self.tokenizer = AutoTokenizer.from_pretrained(model_id)
        self.model = AutoModelForMaskedLM.from_pretrained(model_id)
        self.model.eval()

    def compute_vector(self,text):
        """
        Computes a vector from logits and attention mask using ReLU, log, and max operations.
        """
        tokens = self.tokenizer(text, return_tensors="pt", truncation=True, max_length=500)
        with torch.no_grad():
            output = self.model(**tokens)
        logits, attention_mask = output.logits, tokens.attention_mask
        # TODO: Move this to numpy
        relu_log = torch.log(1 + torch.relu(logits))
        weighted_log = relu_log * attention_mask.unsqueeze(-1)
        max_val, _ = torch.max(weighted_log, dim=1)
        vec = max_val.squeeze()

        return vec, tokens

    def __encode(self, properties: List[Property]):
        for property in properties:
            for config in self.get_config(property):
                val = property.value
                if config is None or config.skip_index:
                    continue
                if config.index_type == VectorType.SPARSE:
                    vec, _ = self.compute_vector(val)
                    vec_name = config.column_name if config.column_name else property.name
                    query_indices = vec.nonzero().numpy().flatten()
                    query_values = vec.detach().numpy()[query_indices]
                    property.vectors.append(EmbeddingVec(vec_name=vec_name, value=[query_indices, query_values], type=VectorType.SPARSE))
        return properties

    def encode(self, input:Query|Chunk, **kwargs):
        props = self.__encode(input.properties)
        input.properties = props
        return input