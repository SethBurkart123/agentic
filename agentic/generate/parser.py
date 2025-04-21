from typing import Type, Any
from pydantic import BaseModel
import inspect
import re

def _parse_single(data: Any, output: Type[BaseModel]):
    if inspect.isclass(output) and issubclass(output, BaseModel):
        # Single instance
        if isinstance(data, str):
            return output.parse_raw(data)
        return output.parse_obj(data)
    raise TypeError("`output` must be a BaseModel subclass or List[BaseModel]")

def _extract_possible_xml(text: str) -> str:
    """
    Attempts to extract the most plausible XML content from a given string,
    even if it's not inside fences or has surrounding explanation text.
    """
    # 1. Try to extract from a fenced block first (```xml or ```):
    fenced = re.search(r"```(?:xml)?\s*(<.*?>.*?)```", text, re.DOTALL)
    if fenced:
        return fenced.group(1).strip()

    # 2. Try to extract a top-level XML tag by guessing (starts with < and ends with >)
    tag_match = re.search(r"(<[a-zA-Z][\s\S]*?>)", text.strip())
    if not tag_match:
        return text.strip()  # fallback: return whole text

    # 3. Try to find matching start + end tag
    start_tag = re.search(r"<([a-zA-Z_][\w\-]*)[^>]*>", text)
    if start_tag:
        tag = start_tag.group(1)
        pattern = fr"<{tag}[\s\S]*?</{tag}>"
        full_xml = re.search(pattern, text, re.DOTALL)
        if full_xml:
            return full_xml.group(0).strip()

    # 4. Fallback: just trim surrounding text, hope for the best
    likely_xml = text.strip()
    return likely_xml
