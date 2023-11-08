Any LM/LLM predicts the next **token**, could be different from the next english word.

1. Instruction-based fine tuning
    1. provide extra context to the LLM, since the model is trained/tuned in 3 steps (ULMFiT approach):
        - LM pre-training(done by the people who create it, next token prediction problem)
        - LM fine-tuning (for the specific problem, but the next token prediction problem)
        - Classifier tuning (text classification problem)
    2. [Open Orca samples](https://huggingface.co/datasets/Open-Orca/OpenOrca).