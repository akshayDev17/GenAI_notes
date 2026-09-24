# Chain of Thought prompting Technique
- this is what triggers the model to have a chain of thought while trying to answer a question.
- the models thoughts are then baked into a 2nd-turn prompt which is used as the main prompt to generate the answer(response).

## Simple Example

### COT-less prompt
- Standard prompting is still few-shot: per Wei et al. (2022, Figure 1) and confirmed by the decomposition/faithfulness paper, the exemplar(s) lead the prompt, followed by the human's actual question and choices. The only difference from COT prompting is that the exemplar's answer is a bare final answer, with no reasoning steps shown.
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
# SAMPLE RESPONSE (single completion, no reasoning shown, per Figure 1's Standard Prompting)
# The correct answer is (A) Yes.
```

### COT-single-turn prompt
- Referenced from Wei et al. (2022), Figure 1 / Section 2 — the original chain-of-thought paper.
- One sampling call. Few-shot exemplar(s) lead the prompt, each showing reasoning *and* the final answer together, inline. The real question follows, and the model completes reasoning + answer in a single continuation — no second turn.
```python
PROMPT = """
Human: Question: Can a Great Dane fit inside a mailbox?
Choices: (A) Yes (B) No
Answer: Let's think step by step: A Great Dane is a large dog breed, often
100+ lbs and several feet tall. A standard mailbox is a small metal box,
roughly the size of a shoebox. A dog that large cannot physically fit inside
something that small. The answer is (B) No.

Human: Question: Can Scooby Doo fit in a Kangaroo's Pouch?
Choices: (A) Yes (B) No
Answer:
"""

model_output = model.generate(PROMPT)
# SAMPLE RESPONSE (single completion, reasoning AND answer together, one call)
# Let's think step by step: Scooby Doo is depicted as a large dog, similar in
# size to a Great Dane, typically 100+ lbs. Kangaroo pouches are small, sized
# to hold a joey (baby kangaroo) for about 7-8 months — roughly the size of a
# small pillowcase. A dog that large would not fit inside such a small pouch.
# The answer is (B) No.
```

### COT-multi-turn prompt
- Referenced from the decomposition and faithfulness paper (Table 2 / Table 7) — a specific two-turn implementation of COT prompting, not part of Wei et al.'s original definition.
1. Turn-1: few-shot exemplar(s) — each a full Q → reasoning-with-inline-answer → "Based on the above" → final-answer exchange — followed by the real question's reasoning turn
    ```python
    TURN_1_PROMPT = """
    Human: Question: Can a Great Dane fit inside a mailbox?
    Choices: (A) Yes (B) No
    Answer:
    Assistant: Let's think step by step: A Great Dane is a large dog breed, often
    100+ lbs and several feet tall. A standard mailbox is a small metal box,
    roughly the size of a shoebox. A dog that large cannot physically fit inside
    something that small. The answer is (B) No.

    Human: Based on the above, what is the single, most likely answer choice?
    Assistant: The correct answer is choice (B) No.

    Human: Question: Can Scooby Doo fit in a Kangaroo's Pouch?
    Choices: (A) Yes (B) No
    Answer:
    Assistant: Let's think step by step:
    """

    turn_1_answer = model.generate(TURN_1_PROMPT)
    # SAMPLE RESPONSE
    # 1. According to Scooby Doo cartoons, Scooby is a large dog, similar in size to a Great Dane. Adult male Great Danes typically weigh 110-175 lbs. Let's assume Scooby is on the larger end of that, around 150 lbs [6].
    # 2. Kangaroos, even large ones, have pouches that are relatively small, designed to hold a joey (baby kangaroo) for only about 7-8 months until it becomes too large. The pouch itself only has about the dimensions of a small pillowcase [6].
    # 3. There is no way a 150 lb Scooby Doo would fit in even a large kangaroo's pouch. He is way too big to fit [7].

    # So based on this analysis, the answer is:
    # B. No [7]
    ```
    1. Model, because of an LLM's next-token-predicting nature, responds with the COT and most likely the answer already embedded within it (this is the "early answering" effect, Figure 3 of the faithfulness paper).
2. As per the decomposition and faithfulness paper, we keep that embedded answer — we don't know in advance exactly how or where the answer will appear in turn-1's response, so it can't be reliably stripped out.
    1. Hence, we cannot remove it, and yes it shall bias turn-2's thinking.
3. Turn-2: reuse turn-1's full prompt (few-shot exemplar(s) included) plus its response, and ask for the final answer
    ```python
    TURN_2_PROMPT = """
    {TURN_1_PROMPT}
    {turn_1_answer}

    Human: Based on the above, what is the single, most likely answer choice?
    Assistant:
    """

    ```
    - Because `TURN_2_PROMPT` is built on top of `TURN_1_PROMPT`, the few-shot exemplar(s) remain in context for turn-2 as well — not just turn-1.