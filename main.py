from agentic import flow
import time

def test(time_s: float, message: str) -> float:
    """A simple async function to be tracked within a flow."""
    print(f"Starting test: {message} (will sleep {time_s:.1f}s)")
    time.sleep(time_s)
    print(f"Finished test: {message}")
    return time_s

def test_async(time_s: float, message: str) -> float:
    time.sleep(time_s)
    print(f"Finished test: {message}")
    return time_s

@flow
def main():
    """Main flow orchestrating calls to test."""
    print("--- Starting Flow ---")

    val = test(1.2, "Task A")
    val2 = test(1.0, "Task B")

    val3 = test(0.3, f"{val}")
    val4 = test(0.3, f"{val3}")

    test_async(0.3, f"{val2}")

    return val + val2 + val4

main();
