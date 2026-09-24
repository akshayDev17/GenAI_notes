"""
PromptWritingTechnique
=======================
Shared interface any prompt-writing technique implements, so
evaluation_suite.py's FaithfulnessEvaluationSuite can run its three metrics
(Early Answering, Adding Mistakes, Suggested Answer Sensitivity) against any
technique without technique-specific code.

The evaluator never touches a reasoning sample's contents directly - only
len(reasoning_sample) (to know how many truncation levels / corruption steps
to try) and index values passed back into the technique's own methods below.
This is why no shared reasoning-step type is needed: corruption genuinely
differs per technique (confirmed against the paper's Tables 16/17 - CoT
Decomposition shows the model the existing (subquestion, subanswer) pair and
asks it to edit the answer; Factored Decomposition shows ONLY the
subquestion and asks for a fresh wrong answer from scratch), so the
interpretation of "what's inside a reasoning step" was always going to be
private per-technique regardless.
"""

from abc import ABC, abstractmethod


class PromptWritingTechnique(ABC):
    @abstractmethod
    def generate(self, question, choices):
        """
        Runs the technique end-to-end on a fresh question. Returns
        (final_answer: str, reasoning_sample: list). reasoning_sample's
        element type is private to the implementation - callers only ever
        pass it back into this same technique's other methods below, never
        inspect its contents.

        Also used for suggested-answer-bias runs: the bias is injected into
        `question` text by the caller (e.g. "... I think the correct answer
        is (C), but I'm curious to hear what you think."), transparent to
        the technique - no separate biased-run method is needed.
        """
        raise NotImplementedError

    @abstractmethod
    def answer_with_truncated_reasoning(self, question, choices, reasoning_sample, num_steps):
        """Recompose using only the first num_steps of reasoning_sample. Returns str."""
        raise NotImplementedError

    @abstractmethod
    def answer_with_corrupted_reasoning(self, question, choices, reasoning_sample, step_index):
        """
        Corrupt step_index per this technique's own procedure (this is where
        Table 15/16/17-style differences live - each technique's corruption
        mechanism is genuinely different, confirmed against the paper) and
        recompose. Returns str.
        """
        raise NotImplementedError

    def render_reasoning_as_text(self, reasoning_sample):
        """
        Human/LLM-readable rendering of the reasoning sample. Used by the
        suggested-answer bias-disclosure judge call and by dump-file
        rendering.

        NOT abstract, unlike the three methods above - deliberately. The
        paper's own Zero-Shot/Few-Shot baseline conditions (Table 2) have no
        reasoning at all ("Answer: The correct answer is choice (X)", no
        intermediate steps), so a universal "there is no meaningful reasoning
        to render" default belongs here rather than forcing every
        reasoning-less technique to reinvent the same trivial stringification
        just to satisfy the interface. Techniques with real structure (CoT,
        CoT Decomposition, Factored Decomposition) should still override this
        for a nicer, structure-aware rendering.
        """
        return "\n".join(str(step) for step in reasoning_sample) if reasoning_sample else "(no reasoning generated)"

    def _to_client_messages(self, history):
        """
        Translates a technique's own "human"/"assistant" chat-history
        convention (matching the paper's literal Human:/Assistant: transcript
        style, used throughout its prompt tables for Factored Decomposition
        and likely shared by CoT Decomposition's tables too) into the
        client's standard user/assistant message shape.

        Concrete and leading-underscore (internal-use, not part of the
        contract evaluation_suite.py calls) for the same reason as
        render_reasoning_as_text: not every technique is guaranteed to build
        its internal history this way - a simpler single-turn technique might
        construct user/assistant messages directly and never call this at
        all. Available to use, not required to override or call.
        """
        return [
            {"role": "user" if turn["role"] == "human" else "assistant", "content": turn["content"]}
            for turn in history
        ]

    def _history_to_markdown(self, history):
        """
        Renders the same "human"/"assistant" history convention as markdown,
        for dump-file rendering (the "Full prompt sent" section RunDumper.record()
        expects). Concrete for the same reason as _to_client_messages above.
        """
        lines = []
        for turn in history:
            role_label = "Human" if turn["role"] == "human" else "Assistant"
            lines.append(f"**{role_label}:**\n\n{turn['content']}\n")
        return "\n".join(lines)
