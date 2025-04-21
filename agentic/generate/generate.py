from __future__ import annotations

from .registry import _PROVIDER_REGISTRY
from .prompt_builder import _build_structured_prompt
from typing import (
    Any,
    Dict,
    List,
    Optional,
    Union,
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
    instructions: Optional[List[str]] = None,
    examples: Optional[List[Union[str, BaseModel]]] = None,
    input: Optional[Dict[str, Any]] = None,  # noqa: A002  (shadowed by built‑in)
    # Generation controls
    temperature: float = 0.7,
    **kwargs,
) -> str:
    """
    Generate a response from an LLM.

    Parameters mirror the detailed specification provided in the README /
    design doc.

    Returns
    -------
    str
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
    structured = any([instructions, examples, input])
    if structured:
        final_user_message = _build_structured_prompt(
            instructions=instructions,
            examples=examples,
            user_input=input,
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

    return raw_response
