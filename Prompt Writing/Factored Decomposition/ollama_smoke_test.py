"""
Ollama Smoke Test
=================
Minimal script to confirm we can reach the local Ollama server and get a
completion back, before wiring up the real factored-decomposition pipeline
against it.
"""

import ollama

PROMPT = "In one sentence, explain what chain-of-thought prompting is."


def select_model():
    """Prompts the user to pick from whatever models are currently pulled in local Ollama."""
    available = ollama.list().models
    if not available:
        raise SystemExit("No local Ollama models found. Run `ollama pull <model>` first.")

    print("\nAvailable local Ollama models:")
    for i, m in enumerate(available, start=1):
        size_gb = m.size / (1024 ** 3)
        print(f"  {i}. {m.model}  ({m.details.parameter_size}, {size_gb:.1f} GB)")

    while True:
        choice = input(f"Select a model [1-{len(available)}]: ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(available):
            return available[int(choice) - 1].model
        print("Invalid selection, try again.")


def main():
    model = select_model()
    response = ollama.chat(
        model=model,
        messages=[{"role": "user", "content": PROMPT}],
        # Reasoning models (e.g. qwen3) think by default, emitting a <think>...</think>
        # block before the real answer. think=False suppresses it - confirmed empirically:
        # response["message"]["thinking"] comes back None and content has no <think> block.
        think=False,
    )
    print(f"[MODEL]: {model}")
    print(f"[PROMPT]: {PROMPT}")
    print(f"[THINKING]: {response['message'].get('thinking')!r}")
    print(f"[RESPONSE]: {response['message']['content']}")


if __name__ == "__main__":
    main()
