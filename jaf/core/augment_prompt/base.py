

from typing import Any


class AugmentPromptBase:
    def __init__(self, chunk_property_name="chunk") -> None:
        self.chunk_property_name = chunk_property_name
        pass

    def generate_prompt(self, query, **kwargs):
        raise NotImplementedError

    def __call__(self, query, **kwargs) -> Any:
        return self.generate_prompt(query, **kwargs)