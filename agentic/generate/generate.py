"""
agentic.generate
~~~~~~~~~~~~~~~~
Unified, ergonomic interface for calling LLM providers with optional
structured‑prompt building and typed response parsing.

The public ``generate`` function exposes the following signature::

    generate(
        model="openai:gpt-4o",
        prompt="Hi!",
        # …see docstring for all args
    )

It supports:
* Plain prompts
* Optional ``system`` + ``chat_history``
* Structured prompts built from ``instructions`` / ``examples`` / ``input`` /
  ``output`` (pydantic schema) with XML or JSON formatting
* Automatic provider resolution (default: ``openai``)
* Automatic parsing back into ``BaseModel`` / ``List[BaseModel]`` when an
  ``output`` schema is supplied.
"""
from __future__ import annotations

from .registry import _PROVIDER_REGISTRY
from .prompt_builder import _build_structured_prompt
from .parser import _parse_single, _extract_possible_xml

import xmltodict
import json
from typing import (
    Any,
    Dict,
    List,
    Literal,
    Optional,
    Type,
    Union,
    get_args,
    get_origin,
)
from pydantic import BaseModel

###############################################################################
# Public generate() API
###############################################################################

def generate(
    *,
    model: str,
    prompt: Optional[str] = None,
    system: Optional[str] = None,
    chat_history: Optional[List[Dict[str, str]]] = None,
    # Structured prompt options
    output: Optional[Type[BaseModel]] = None,
    instructions: Optional[List[str]] = None,
    examples: Optional[List[Union[str, BaseModel]]] = None,
    input: Optional[Dict[str, Any]] = None,  # noqa: A002  (shadowed by built‑in)
    format: Literal["xml", "json", "raw"] = "xml",
    # Generation controls
    temperature: float = 0.7,
    **kwargs,
) -> Union[str, BaseModel, List[BaseModel]]:
    """
    Generate a response from an LLM.

    Parameters mirror the detailed specification provided in the README /
    design doc.

    Returns
    -------
    Union[str, BaseModel, List[BaseModel]]
        * Raw string if no ``output`` schema supplied.
        * Parsed ``BaseModel`` or list thereof when ``output`` is provided.
    """
    # ------------------------------------------------------------------ setup
    if ":" not in model:
        raise ValueError("`model` must be in the format '<provider>:<model-id>'")
    provider_name, model_id = model.split(":", 1)

    provider = _PROVIDER_REGISTRY.get(provider_name)
    if provider is None:
        raise ValueError(
            f"No provider named '{provider_name}' registered. "
            f"Available providers: {', '.join(_PROVIDER_REGISTRY)}"
        )

    # ------------------------------------------------------------------ build final user message
    structured = any([instructions, examples, input, output])
    if structured:
        final_user_message = _build_structured_prompt(
            instructions=instructions,
            examples=examples,
            user_input=input,
            output_schema=output,
            fmt="json" if format == "json" else "xml",
        )
    else:
        if prompt is None:
            raise ValueError("`prompt` is required when not using structured prompt options.")
        final_user_message = prompt

    # ------------------------------------------------------------------ assemble chat
    messages: List[Dict[str, str]] = []
    if chat_history:
        # Make a shallow copy to avoid mutating caller's list
        messages.extend([dict(m) for m in chat_history])

    if system is not None:
        messages.append({"role": "system", "content": system})

    messages.append({"role": "user", "content": final_user_message})

    # ------------------------------------------------------------------ call provider
    raw_response: str = provider.generate(
        model_id,
        messages,
        temperature=temperature,
        **kwargs,
    )

    # ------------------------------------------------------------------ no post‑processing requested
    if output is None:
        return raw_response

    # ------------------------------------------------------------------ parse typed output
    origin = get_origin(output)

    # -------- JSON formatted output ----------------------------------------------------
    if format == "json":
        parsed_json = json.loads(raw_response)

        if origin is list:
            item_type = get_args(output)[0]  # type: ignore[index]
            return [
                item_type.parse_obj(item)  # type: ignore[attr-defined]
                if isinstance(item, (dict, list))
                else item_type.parse_raw(item)  # type: ignore[attr-defined]
                for item in parsed_json
            ]
        return _parse_single(parsed_json, output)

    # -------- XML formatted output -----------------------------------------------------
    if format == "xml":
        cleaned_response = _extract_possible_xml(raw_response)
        parsed_xml = xmltodict.parse(cleaned_response)

        origin = get_origin(output)

        if origin is list:
            item_type = get_args(output)[0]  # type: ignore[index]

            # Recursively find the first list of dicts
            def find_first_list_of_dicts(obj):
                if isinstance(obj, list) and all(isinstance(i, dict) for i in obj):
                    return obj
                if isinstance(obj, dict):
                    for v in obj.values():
                        found = find_first_list_of_dicts(v)
                        if found:
                            return found
                return None

            items = find_first_list_of_dicts(parsed_xml)
            if not items:
                raise ValueError("Could not find a list of dicts to parse into BaseModel list")

            return [
                item_type.parse_obj(item)  # type: ignore[attr-defined]
                for item in items
            ]

        return _parse_single(parsed_xml, output)

    # ------------------------------------------------------------------ raw fallback
    return raw_response
