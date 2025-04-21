from typing import List, Optional, Union, Dict, Any, Type, Literal
from pydantic import BaseModel
import json
from rich import print
from xml.dom import minidom


def _prettify_xml(xml_str: str) -> str:
    """Helper function to properly indent XML string with consistent spacing."""
    parsed = minidom.parseString(xml_str)

    def _format_node(node, level=0):
        result = []
        if node.nodeType == node.TEXT_NODE:
            text = node.data.strip()
            if text:
                result.append(" " * (level * 2) + text)
        else:
            if node.childNodes:
                has_text_only = all(child.nodeType == child.TEXT_NODE for child in node.childNodes)

                if has_text_only:
                    text_content = "".join(child.data for child in node.childNodes).strip()
                    result.append(" " * (level * 2) + f"<{node.tagName}>{text_content}</{node.tagName}>")
                else:
                    result.append(" " * (level * 2) + f"<{node.tagName}>")
                    for child in node.childNodes:
                        result.extend(_format_node(child, level + 1))
                    result.append(" " * (level * 2) + f"</{node.tagName}>")
            else:
                result.append(" " * (level * 2) + f"<{node.tagName}></{node.tagName}>")

        return result

    root = parsed.documentElement
    formatted_lines = _format_node(root)

    return "\n".join(formatted_lines)


def _dict_to_xml(data: Dict[str, Any], parent_tag: str = "") -> str:
    """
    Convert a dictionary to XML format.
    Handles nested dictionaries, lists, and primitive types.
    """
    xml_parts = []

    for key, value in data.items():
        if isinstance(value, dict):
            inner_xml = _dict_to_xml(value)
            xml_parts.append(f"<{key}>{inner_xml}</{key}>")
        elif isinstance(value, list):
            list_parts = []
            for item in value:
                if isinstance(item, dict):
                    list_parts.append(f"<{key[:-1] if key.endswith('s') else 'item'}>{_dict_to_xml(item)}</{key[:-1] if key.endswith('s') else 'item'}>")
                else:
                    list_parts.append(f"<{key[:-1] if key.endswith('s') else 'item'}>{item}</{key[:-1] if key.endswith('s') else 'item'}>")
            xml_parts.append(f"<{key}>{''.join(list_parts)}</{key}>")
        else:
            xml_parts.append(f"<{key}>{value}</{key}>")

    return "".join(xml_parts)

def _model_dump(model: BaseModel) -> Dict[str, Any]:
    return model.model_dump() if hasattr(model, "model_dump") else model.dict()

def _build_structured_prompt(
    *,
    instructions: Optional[List[str]],
    examples: Optional[List[Union[str, BaseModel]]],
    user_input: Optional[Dict[str, Any]],
    fmt: Literal["xml", "json"],
) -> str:
    """Convert structured‑prompt kwargs into a single user‑message string."""
    if fmt not in ("xml", "json"):
        raise ValueError("format must be 'xml' or 'json'")

    # ------------------------------------------------------------------ JSON
    if fmt == "json":
        payload: Dict[str, Any] = {}
        if instructions:
            payload["instructions"] = instructions
        if examples:
            payload["examples"] = [
                _model_dump(ex) if isinstance(ex, BaseModel) else ex for ex in examples
            ]
        if user_input:
            payload["input"] = user_input
        return json.dumps(payload, indent=2)

    # ------------------------------------------------------------------- XML
    root_elements = []

    if instructions:
        instructions_xml = "<instructions>"
        for ins in instructions:
            instructions_xml += f"<instruction>{ins}</instruction>"
        instructions_xml += "</instructions>"
        root_elements.append(instructions_xml)

    if examples:
        examples_xml = "<examples>"
        for ex in examples:
            if isinstance(ex, BaseModel):
                model_data = _model_dump(ex)

                try:
                    inner_xml = _dict_to_xml(model_data)
                    examples_xml += f"<example>{inner_xml}</example>"
                except Exception as e:
                    print(f"Warning: Error formatting example model {type(ex).__name__} as XML ({e}), falling back to JSON CDATA.")
                    ex_json = json.dumps(model_data)
                    examples_xml += f"<example>{ex_json}</example>"
            else:
                examples_xml += f"<example>{ex}</example>"
        examples_xml += "</examples>"
        root_elements.append(examples_xml)

    if user_input is not None:
        input_xml = _dict_to_xml(user_input)
        root_elements.append(f"<input>{input_xml}</input>")

    combined_xml = "".join(root_elements)
    wrapped_xml = f"<root>{combined_xml}</root>"

    pretty_xml = _prettify_xml(wrapped_xml)

    lines = pretty_xml.splitlines()

    formatted_lines = []
    for line in lines[1:-1]:
        if line.startswith("  "):
            formatted_lines.append(line[2:])
        else:
            formatted_lines.append(line)

    final_xml = "\n".join(formatted_lines)

    return final_xml
