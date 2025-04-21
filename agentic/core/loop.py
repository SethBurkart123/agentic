from typing import Callable, Iterable, TypeVar, overload, Union
from concurrent.futures import ThreadPoolExecutor

T = TypeVar("T")
R = TypeVar("R")

# Global context store (overridden via `with_context(...)`)
_loop_context: dict = {}

def with_context(**context):
    """
    Set global context variables for all upcoming loop() executions.
    Useful when decorating functions that rely on outer-scope variables
    (like those inside a @flow function).
    """
    global _loop_context
    _loop_context = context


@overload
def loop(iterable: int, varname: str = "", **kwargs) -> Callable[[Callable[[int], R]], list[R]]: ...
@overload
def loop(iterable: Iterable[T], varname: str = "", **kwargs) -> Callable[[Callable[[T], R]], list[R]]: ...

def loop(iterable: Union[int, Iterable[T]], varname: str = "", **explicit_context) -> Callable[[Callable[..., R]], list[R]]:
    """
    Execute a function over an iterable in parallel using threads.

    Automatically passes any variables set via `with_context(...)`,
    and also accepts manual keyword arguments to override those.

    Usage:
        with_context(query=query)

        @loop(items)
        def process(item, query):
            ...

    Or:
        @loop(items, query=query)
        def process(item, query):
            ...
    """
    def decorator(fn: Callable[..., R]) -> list[R]:
        if isinstance(iterable, int):
            items: list[T] = list(range(iterable))  # type: ignore
        else:
            items = list(iterable)

        # Merge in context from `with_context(...)` (can be overridden)
        context = {**_loop_context, **explicit_context}

        with ThreadPoolExecutor(max_workers=len(items)) as executor:
            futures = [executor.submit(fn, item, **context) for item in items]
            return [f.result() for f in futures]

    return decorator
