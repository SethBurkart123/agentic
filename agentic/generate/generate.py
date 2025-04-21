from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel

from .registry import _PROVIDER_REGISTRY
from .prompt_builder import _build_structured_prompt

try:
    from rich.console import Console
    console = Console()
except ImportError:
    console = None  # Rich is optional

###############################################################################
# Public generate() API
###############################################################################

def generate(
    *,
    model: str,
    prompt: Optional[str] = None,
    system: Optional[str] = None,
    chat_history: Optional[List[Dict[str, str]]] = None,
    instructions: Optional[List[str]] = None,
    examples: Optional[List[Union[str, BaseModel]]] = None,
    input: Optional[Dict[str, Any]] = None,
    temperature: float = 0.7,
    debug: bool = False,
    max_retries: int = 3,
    retry_backoff_base: float = 1.5,
    **kwargs,
) -> str:
    """
    Generate a response from an LLM.

    If `debug` is True, prints detailed logs using rich.

    Returns
    -------
    str
    """
    if ":" not in model:
        raise ValueError("`model` must be in the format '<provider>:<model-id>'")
    provider_name, model_id = model.split(":", 1)

    provider = _PROVIDER_REGISTRY.get(provider_name)
    if provider is None:
        raise ValueError(
            f"No provider named '{provider_name}' registered. "
            f"Available providers: {', '.join(_PROVIDER_REGISTRY)}"
        )

    structured = any([instructions, examples, input])
    if structured:
        final_user_message = _build_structured_prompt(
            instructions=instructions,
            examples=examples,
            user_input=input,
            fmt="json" if kwargs.get("format") == "json" else "xml",
        )
    else:
        if prompt is None:
            raise ValueError("`prompt` is required when not using structured prompt options.")
        final_user_message = prompt

    messages: List[Dict[str, str]] = []
    if chat_history:
        messages.extend([dict(m) for m in chat_history])

    if system is not None:
        messages.append({"role": "system", "content": system})

    messages.append({"role": "user", "content": final_user_message})

    # ------------------------------------------------------------------ call provider with retry
    attempt = 0
    while attempt < max_retries:
        try:
            if debug and console:
                console.log(f"[bold blue]Attempt {attempt+1}[/] → Calling provider '{provider_name}'")

            raw_response: str = provider.generate(
                model_id,
                messages,
                temperature=temperature,
                **kwargs,
            )

            if debug and console:
                console.log("[green]Success[/] ✅ Response received.")
            return raw_response

        except Exception as e:
            wait_time = retry_backoff_base ** attempt
            if debug and console:
                console.log(f"[yellow]Warning[/]: Attempt {attempt+1} failed with error: {e}")
                if attempt < max_retries - 1:
                    console.log(f"[italic]Retrying in {wait_time:.1f} seconds...[/]")
            time.sleep(wait_time)
            attempt += 1

    # Final failure
    error_message = f"Error: Failed to generate response from provider '{provider_name}' after {max_retries} attempts."
    if debug and console:
        console.log(f"[red]{error_message}[/]")

    raise RuntimeError(error_message)
