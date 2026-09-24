"""
Ollama LLM Client
==================
Generic chat client for any prompt-writing technique. No technique-specific
method names - every technique builds its own messages and calls chat()
directly.

Disables thinking mode (think=False) - reasoning models like qwen3 otherwise
prepend a <think>...</think> block that can confuse regex-based tag
extraction techniques rely on (<sub q>, <result>, <FIN>, etc.).
"""

import ollama


class OllamaLlmClient:
    """Generic local-model client. One method: chat(messages)."""

    def __init__(self, model="llama3.2:latest"):
        self.model = model

    def chat(self, messages):
        """
        messages: list of {"role": "user"/"assistant"/"system", "content": str} -
        standard Ollama/OpenAI message shape.
        """
        response = ollama.chat(model=self.model, messages=messages, think=False)
        return response["message"]["content"]

    @staticmethod
    def available_models():
        """Names of every model currently pulled in local Ollama."""
        return [m.model for m in ollama.list().models]

    @staticmethod
    def resolve_model(name):
        """
        Validates an explicitly-named model, so a typo or an un-pulled model
        fails immediately with the list of real options instead of surfacing
        as an obscure error on the first chat() call.
        """
        available = OllamaLlmClient.available_models()
        if name not in available:
            raise SystemExit(
                f"Model {name!r} is not pulled in local Ollama.\n"
                f"Available: {', '.join(available) if available else '(none - run `ollama pull <model>`)'}"
            )
        return name

    @staticmethod
    def select_model():
        """
        Prompts the user to pick from whatever models are currently pulled in
        local Ollama. A staticmethod, not an instance method - the model name
        is needed BEFORE a client exists (to construct one), so there's no
        self to hang this on yet. Lives on the class it configures rather
        than a separate module since it's a small, single-purpose helper
        whose only consumer pattern is feeding this class's constructor.

        Interactive only. Do NOT script this by piping an index: Ollama
        returns models ordered by modification time, so pulling or touching
        any model renumbers the whole menu - an index that meant llama3.2
        yesterday can mean something else today, silently running an
        experiment against the wrong model. Scripted and reproducible runs
        should pass an explicit model name instead (see --model).
        """
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
