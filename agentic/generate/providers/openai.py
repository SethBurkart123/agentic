from agentic.generate.registry import register_provider
from typing import List, Dict

@register_provider("openai")
def _openai_generate(
    model_id: str,
    messages: List[Dict[str, str]], # { "role": "system", "content": "You are a helpful assistant." }, { "role": "user", "content": "Hello!" }...
    temperature: float = 0.7,
    **kwargs,
) -> str:  # pragma: no cover – executes only if openai installed
    """
    Minimal OpenAI ChatCompletion wrapper.

    Requires ``openai`` to be installed and an ``OPENAI_API_KEY`` env var.
    """
    print(messages)
    try:
        import openai  # type: ignore[import]  # pragma: no cover
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "Provider 'openai' requires the `openai` package. "
            "Install it with `pip install openai`."
        ) from exc

    response = openai.ChatCompletion.create(
        model=model_id,
        messages=messages,
        temperature=temperature,
        **kwargs,
    )
    # Compatible with both v1 & v2 style returns
    if isinstance(response, dict) and "choices" in response:
        return response["choices"][0]["message"]["content"]
    # Older versions return an OpenAIObject
    if hasattr(response, "choices"):
        return response.choices[0].message["content"]
    raise RuntimeError("Unsupported OpenAI response format.")
