from openai.types.chat import ChatCompletionMessageParam
from agentic.generate.registry import register_provider
from typing import List, Optional

@register_provider("groq", needs_api_key=True)
def _groq_generate(
    model_id: str,
    messages: List[ChatCompletionMessageParam],
    temperature: float = 0.7,
    api_key: Optional[str] = None,
    **kwargs,
) -> str:
    from openai import OpenAI

    client = OpenAI(
        api_key=api_key,
        base_url="https://api.groq.com/openai/v1"
    ) if api_key else OpenAI()

    response = client.chat.completions.create(
        model=model_id,
        messages=messages,
        temperature=temperature,
        **kwargs
    )
    return response.choices[0].message.content.strip()
