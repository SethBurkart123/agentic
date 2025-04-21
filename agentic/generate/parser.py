from __future__ import annotations
from xml.sax.saxutils import unescape
from pydantic import BaseModel
import inspect
import re
import json
import xmltodict
from typing import (
    Any,
    List,
    Literal,
    Type,
    TypeVar,
    Union,
    Optional,
    get_args,
    get_origin,
)

def _sanitize_xml(xml: str) -> str:
    # only replace "&" that's not part of an existing entity (like &amp;)
    return re.sub(r'&(?!\w+;)', '&amp;', xml)

def _desanitize_xml(xml: str) -> str:
    return unescape(xml)

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

T = TypeVar("T", bound=BaseModel)

def parse_response(
    raw: str,
    output_schema: Optional[Type[BaseModel] | Type[List[BaseModel]]] = None,
    fmt: Literal["xml", "json"] = "xml",
) -> Union[str, BaseModel, List[BaseModel], dict, list]:
    """
    Convert the provider’s raw text into structured data, optionally validating against a Pydantic schema.
    """
    origin = get_origin(output_schema) if output_schema else None

    if fmt == "json":
        parsed_json = json.loads(raw)
        if output_schema:
            if origin is list:
                item_type = get_args(output_schema)[0]
                return [
                    item_type.parse_obj(item)
                    if isinstance(item, (dict, list))
                    else item_type.parse_raw(item)
                    for item in parsed_json
                ]
            return _parse_single(parsed_json, output_schema)
        return parsed_json

    if fmt == "xml":
        cleaned = _extract_possible_xml(raw)
        sanitized = _sanitize_xml(cleaned)
        print("Sanitized XML input:")
        print(sanitized)

        parsed_xml = xmltodict.parse(sanitized)

        if output_schema:
            if origin is list:
                item_type = get_args(output_schema)[0]

                def find_first_list(node: Any):
                    if isinstance(node, list) and all(isinstance(i, dict) for i in node):
                        return node
                    if isinstance(node, dict):
                        for v in node.values():
                            found = find_first_list(v)
                            if found is not None:
                                return found
                    return None

                items = find_first_list(parsed_xml)
                if items is None:
                    raise ValueError("Expected a list of objects, but none was found.")
                return [item_type.parse_obj(item) for item in items]

            return _parse_single(parsed_xml, output_schema)

        return parsed_xml

    return raw
