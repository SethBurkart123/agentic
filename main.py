from re import I
from agentic import flow
import time

from agentic.core import loop

def test(time_s: float, message: str) -> float:
    """A simple async function to be tracked within a flow."""
    print(f"Starting test: {message} (will sleep {time_s:.1f}s)")
    time.sleep(time_s)
    print(f"Finished test: {message}")
    return time_s

@flow
def main(query):
    """Main flow orchestrating calls to test."""
    print("--- Starting Flow ---")

    val = test(0.2, "Task A")
    val2 = test(1.0, "Task B")

    items = [1, 2, 3]

    @loop(items, query=query)
    def process_item(item, query):
        print(query)
        return item * 2

    print(process_item)

    return val + val2

main('hi');
