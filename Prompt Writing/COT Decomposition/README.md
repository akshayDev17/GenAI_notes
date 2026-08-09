# Chain-of-Thought Decomposition prompting Technique
- Referenced from the decomposition and faithfulness paper (Table 8) — an alternative to writing a free-text chain of thought: the model decomposes the question into subquestions, answers each one inline (in the same sampling call, wrapped in `<sub_q></sub_q>` / `<sub_a></sub_a>` tags), then a forced final-answer turn commits to a choice.
- Structurally two-turn, same shape as `COT-multi-turn` in the sibling [ChainofThought](../ChainofThought/README.md) directory — but turn-1 produces a structured decomposition instead of free-text reasoning.

## Simple Example (Scooby Doo / Kangaroo pouch)

### Standard prompt
- Few-shot exemplar leads the prompt, bare final answer, single turn — no reasoning, no decomposition shown.
```python
PROMPT = """
Human: Question: Can a Great Dane fit inside a mailbox?
Choices: (A) Yes (B) No
Answer: The correct answer is (B) No.

Human: Question: Can Scooby Doo fit in a Kangaroo's Pouch?
Choices: (A) Yes (B) No
Answer:
"""

model_output = model.generate(PROMPT)
# SAMPLE RESPONSE (single completion, no reasoning, no decomposition)
# The correct answer is (A) Yes.
```

### COT Decomposition prompt
1. Turn-1: instructions + a few-shot exemplar (each showing a full decomposition), followed by the real question's decomposition turn
    ```python
    TURN_1_PROMPT = """
    Human: I'm going to ask you a question. I want you to decompose it into a series of subquestions. Each subquestion should be self-contained with all the
    information necessary to solve it. Make sure not to decompose more than necessary or have any trivial subquestions - you'll be evaluated on the
    simplicity, conciseness, and correctness of your decompositions as well as your final answer. You should wrap each subquestion in <sub_q></sub_q> tags.
    After each subquestion, you should answer the subquestion and put your subanswer in <sub_a></sub_a> tags. Once you have all the information you need
    to answer the question, output <FIN></FIN> tags.
    Let's go through some examples together. Do you understand the instructions?
    Assistant: Yes, I understand that I'm meant to decompose questions into subquestions and wrap each component in the appropriate tags. Once I have all
    the information I need, I'll output <FIN></FIN> tags.

    Human: Question: Can a Great Dane fit inside a mailbox?
    Choices: (A) Yes (B) No
    Answer:
    Assistant:
    <sub_q>How big is a Great Dane, roughly?</sub_q>
    <sub_a>A large dog breed, often 100+ lbs and several feet tall.</sub_a>
    <sub_q>How big is a standard mailbox?</sub_q>
    <sub_a>A small metal box, roughly the size of a shoebox.</sub_a>
    <FIN></FIN>

    Human: Based on the above, what is the single, most likely answer choice?
    Assistant: The correct answer is choice (B) No.

    Human: Question: Can Scooby Doo fit in a Kangaroo's Pouch?
    Choices: (A) Yes (B) No
    Answer:
    Assistant:
    """

    turn_1_answer = model.generate(TURN_1_PROMPT)
    # SAMPLE RESPONSE
    # <sub_q>How big is Scooby Doo, roughly?</sub_q>
    # <sub_a>Depicted as a large dog, similar in size to a Great Dane - 100+ lbs.</sub_a>
    # <sub_q>How big is a kangaroo's pouch?</sub_q>
    # <sub_a>Small - sized to hold a joey (baby kangaroo) for about 7-8 months, roughly the size of a small pillowcase.</sub_a>
    # <FIN></FIN>
    ```
2. Turn-2: reuse turn-1's full prompt (instructions + few-shot exemplar included) plus its response, and ask for the final answer
    ```python
    TURN_2_PROMPT = """
    {TURN_1_PROMPT}
    {turn_1_answer}

    Human: Based on the above, what is the single, most likely answer choice?
    Assistant:
    """

    # SAMPLE RESPONSE
    # The correct answer is choice (B) No.
    ```
    - Same as `COT-multi-turn`, the few-shot exemplar(s) remain in context for turn-2 too, since `TURN_2_PROMPT` is built on top of `TURN_1_PROMPT`.

## How this differs from `COT-multi-turn`
- Turn-1's output is a structured sequence of subquestion/subanswer pairs, not free-text prose reasoning.
- Per the faithfulness paper (§2.3), this structuring is hypothesized to reduce "biased reasoning" relative to plain CoT, since each subquestion is more self-contained and less likely to inherit biasing context wholesale.
