import inspect
from pydantic import BaseModel
from typing import Callable


class LLMCallableFunction(BaseModel):
    function : Callable
    name : str 
    description : str 
    json_schema : str 
        
    def invoke(self,*args,**kwargs):
        return self.function(*args,**kwargs)

def get_json_for_function(function:Callable):
    func_name = function.__name__
    func_doc = inspect.getdoc(function)
    func_params = inspect.signature(function).parameters
    json_structure = {
        "type": "function",
        "function": {
            "name": func_name,
            "description": func_doc,
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }
    
    for name, param in func_params.items():
        param_info = {
            "type": "string" if param.annotation is inspect._empty else param.annotation,
            "description": f"The {name} parameter"
        }
        if param.default is not inspect._empty:
            param_info["default"] = param.default
        if param.annotation is not inspect._empty and hasattr(param.annotation, "__dict__") and "__members__" in param.annotation.__dict__:
            param_info["enum"] = list(param.annotation.__members__.keys())
        json_structure["function"]["parameters"]["properties"][name] = param_info
        if param.default is inspect._empty:
            json_structure["function"]["parameters"]["required"].append(name)
    return json_structure


def get_function_type(function:Callable, description:str=None):
    return LLMCallableFunction(
        function=function,
        name=function.__name__,
        description= description or function.__doc__,
        json_schema=get_json_for_function(function)
    )
