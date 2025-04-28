from agentic import generate

print(generate(
    model="groq:llama-3.1-8b-instant",
    prompt="Hi there!",
    debug=True
))
