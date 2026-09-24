"""
Ollama LLM Client
==================
Real local-model client backing paper_factored_decomposition.py's history-list,
multi-turn conversational interface (call_planner / call_answering_agent /
call_recomposition_agent).

Every call disables thinking mode (think=False) - reasoning models like qwen3 otherwise
prepend a <think>...</think> block that can confuse the regex-based tag extraction
(<sub q>, <result>, <FIN>) the script relies on.
"""

import ollama


class OllamaLlmClient:
    """Real local-model client for paper_factored_decomposition.py."""

    def __init__(self, model="llama3.2:latest"):
        self.model = model

    def _chat(self, messages):
        response = ollama.chat(model=self.model, messages=messages, think=False)
        return response["message"]["content"]

    def _complete(self, history):
        messages = [
            {"role": "user" if turn["role"] == "human" else "assistant", "content": turn["content"]}
            for turn in history
        ]
        return self._chat(messages)

    def call_planner(self, history):
        return self._complete(history)

    def call_answering_agent(self, history):
        return self._complete(history)

    def call_recomposition_agent(self, history):
        return self._complete(history)
