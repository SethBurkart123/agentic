from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Iterable, TypeVar, Union

T = TypeVar("T")

def loop(iterable: Union[int, Iterable[T]], varname: str = ""):
    """
    Parallel loop decorator.

    Usage:
        @loop(range(5))
        def run(i): ...

        @loop(items, 'item')
        def run(item): ...
    """
    def wrapper(fn: Callable[[T], None]) -> None:
        # Allow `loop(5)` as shorthand for `loop(range(5))`
        if isinstance(iterable, int):
            items = list(range(iterable))
        else:
            items = list(iterable)

        with ThreadPoolExecutor(max_workers=len(items)) as executor:
            executor.map(fn, items)

    return wrapper
