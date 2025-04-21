from agentic.generate.registry import register_provider
from typing import List, Dict, Optional

@register_provider("openai", needs_api_key=True, needs_base_url=True)

def _openai_generate(
    model_id: str,
    messages: List[Dict[str, str]],
    temperature: float = 0.7,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    **kwargs,
) -> str:
    from openai import OpenAI

    client = OpenAI(
        api_key=api_key,
        base_url=base_url
    ) if api_key or base_url else OpenAI()

    response = client.chat.completions.create(
        model=model_id,
        messages=messages,
        temperature=temperature,
        **kwargs
    )
    return response.choices[0].message.content.strip()
