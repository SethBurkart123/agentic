import os
from typing import Any, Dict, List, Callable
from dotenv import load_dotenv
from openai.types.chat import ChatCompletionMessageParam

load_dotenv()

_ProviderFn = Callable[[str, List[ChatCompletionMessageParam]], str]

class _Provider:
    def __init__(self, name: str, generate_fn: _ProviderFn, config: Dict[str, Any] | None = None):
        self.name = name
        self._generate_fn = generate_fn
        self._config: Dict[str, Any] = config or {}

    def generate(self, model_id: str, messages: List[ChatCompletionMessageParam], **kwargs) -> str:
        combined_kwargs = {**self._config, **kwargs}
        return self._generate_fn(model_id, messages, **combined_kwargs)

    def configure(self, **kwargs):
        self._config.update(kwargs)

_PROVIDER_REGISTRY: Dict[str, _Provider] = {}

def register_provider(
    name: str,
    *,
    needs_api_key: bool = False,
    needs_base_url: bool = False
):
    def _decorator(func: _ProviderFn):
        default_config: Dict[str, Any] = {}

        if needs_api_key:
            env_key = f"{name.upper()}_API_KEY"
            default_config["api_key"] = os.getenv(env_key)

        if needs_base_url:
            env_base = f"{name.upper()}_BASE_URL"
            default_config["base_url"] = os.getenv(env_base)

        _PROVIDER_REGISTRY[name] = _Provider(name, func, default_config)
        return func

    return _decorator

def configure_provider(name: str, **kwargs):
    provider = _PROVIDER_REGISTRY.get(name)
    if not provider:
        raise ValueError(f"No provider named '{name}' registered.")
    provider.configure(**kwargs)

def register_provider_alias(
    name: str,
    *,
    type: str,
    **config
):
    base = _PROVIDER_REGISTRY.get(type)
    if not base:
        raise ValueError(f"No provider named '{type}' registered.")

    _PROVIDER_REGISTRY[name] = _Provider(
        name=name,
        generate_fn=base._generate_fn,
        config={**base._config, **config}
    )
