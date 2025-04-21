from agentic import generate
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

test = generate(
    model="openai:gpt-3.5-turbo",
    instructions=[
        "Write a function that takes a string and returns the number of words in it."
    ],
    examples=[
        example_model_instance
    ],
    system="You are a helpful assistant."
)

# You might want to print or inspect the 'test' variable
print(test)
