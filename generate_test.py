from agentic import generate, register_provider_alias
from pydantic import BaseModel

class NestedModel(BaseModel):
    input: str
    output: int

class ExampleModel(BaseModel):
    input: str
    output: int
    # nested type
    nestExample: NestedModel | None = None

example_model_instance = ExampleModel(
    input="hello world",
    output=2,
    nestExample=NestedModel(input="nested", output=1)
)

register_provider_alias("ollama", type="openai", base_url="http://localhost:11434/v1", api_key="ollama")

test = generate(
    model="ollama:dolphin3:latest",
    instructions=[
        "Write a function that takes a string and returns the number of words in it."
    ],
    #examples=[
    #    example_model_instance
    #],
    system="You are a pirate. ARRRR! Respond as a pirate!"
)

print(test)
