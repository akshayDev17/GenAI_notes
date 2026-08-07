# Writing Principles

1. Coherence: Proper structure: Context followed by explanation followed by examples followed by Actual question followed by expected response schema.
2. Conciseness: Short sentences, to the point, focused, only key info to models, least no. of unnecessary words.
3. Clarity : Simple language and phrases, no complex and confusing phrases
4. Consistency: Similar formatting, terminology and tone across prompts for a given model.

## My Doubts
- how to evaluate different language models based on these principles?
- how to test models upon test cases which violate one or more of these principles and then conclude which performed the best?
- how to know which model works on which combination of principles, where the principles are not limited to only these 4, but model-tailored?
- why does XML formatting work with some models and doesn't work as well with some other models?
  - Not inherent to XML — it's a training-data artifact. Claude was fine-tuned on heavily XML-tagged data, so it learned a strong prior to treat `<tag>...</tag>` as one coherent unit. Other model families weren't reinforced on XML the same way (GPT leans Markdown/JSON instead) — so the "best" delimiter format is model-specific and should be tested per model, not assumed.
  - Sources: [Prompting best practices - Claude Platform Docs](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices), [12 prompt engineering tips to boost Claude's output quality](https://www.vellum.ai/blog/prompt-engineering-tips-for-claude), [Prompt Engineering with Anthropic Claude](https://medium.com/promptlayer/prompt-engineering-with-anthropic-claude-5399da57461d)

## Simple

```python
SYSTEM = """
Human: I need you to decide wehther the item is relevant to the user query.

Here is the user query:

<user_query>
{USER_REQUEST}
</user_query>

Here is the item description:
<item>
{ITEM}
</item>

Is item relevant or should be recommended to there user based on the user's query? Answer YES or NO.
Please, write the answer in <answer> tags.
Assistant: <answer>
"""
```
**Advice to follow**: **XML** tag-like usage, remember also done during XPO (few-shot prompts as well) and Runwhen (Sobrain prompts).

## Long Context QA
- models might ignore classic Chain-of-thought related instructions provided, hence **better to use Decomposition-based methods for QA tasks**
- the latter have high faithfulness compared to the former (model's reasoning may have completely ignored the reasoning provided in the CoT-prompt, but CoT-prompting assumes both are the same, hence a case of low faithfulness) 