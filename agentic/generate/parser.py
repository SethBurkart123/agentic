from typing import Type, Any
from pydantic import BaseModel
import inspect

def _parse_single(data: Any, output: Type[BaseModel]):
    if inspect.isclass(output) and issubclass(output, BaseModel):
        # Single instance
        if isinstance(data, str):
            return output.parse_raw(data)
        return output.parse_obj(data)
    raise TypeError("`output` must be a BaseModel subclass or List[BaseModel]")
