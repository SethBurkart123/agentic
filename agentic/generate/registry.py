from typing import Any, Dict, List

###############################################################################
# Provider registry
###############################################################################

_ProviderFn = Any  # ``Callable[[str, List[Dict[str, str]]], str]``  – kept loose


class _Provider:
    """Thin wrapper around a provider generation function."""

    def __init__(self, name: str, generate_fn: _ProviderFn):
        self.name = name
        self._generate_fn = generate_fn

    def generate(
        self,
        model_id: str,
        messages: List[Dict[str, str]],
        **kwargs,
    ) -> str:
        return self._generate_fn(model_id, messages, **kwargs)


_PROVIDER_REGISTRY: Dict[str, _Provider] = {}


def register_provider(name: str):
    """Decorator to register a provider by name."""

    def _decorator(func: _ProviderFn):
        _PROVIDER_REGISTRY[name] = _Provider(name, func)
        return func

    return _decorator
