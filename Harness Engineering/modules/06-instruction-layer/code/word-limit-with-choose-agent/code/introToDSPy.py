"""
After having used the `knowAllDSPyModelStrings.py` to know valid deepseek 
model strings, start with exploring capabilities offered by DSPy.

Supported types:
https://github.com/stanfordnlp/dspy/blob/main/dspy/adapters/types/__init__.py

Modules used:
https://dspy.ai/current/api/modules/
- BestOfN, COT, CodeAct, Flex, Module, Predict, MultiChainComparison

"""

import os
from dotenv import load_dotenv
load_dotenv()

from typing import Literal

import dspy


lm = dspy.LM("deepseek/deepseek-v4-flash", api_key = os.getenv('DEEPSEEK_API_KEY'))
# lm = dspy.LM("deepseek/deepseek-v4-flash", api_key = os.getenv('DEEPSEEK_API_KEY'), temperature=1)

# sets our LM as the default provider for every DSPy program in the process
dspy.configure(lm=lm, track_usage=True)
# dspy.configure(lm=lm, track_usage=True, enable_disk_cache = False, enable_memory_cache = False)

'''
string form of DSPy Signature: (input params list) -> (output params list)
'''

joke_signature = "topic -> joke"
comedian = dspy.Predict(signature=joke_signature)
result = comedian(topic="politician")

# # purely to present the joke
print(f"\nTokens used = {result.get_lm_usage()}\n\nJoke:\n{result.joke}\n\n{'-'*80}\n")

# full conversation history
print(dspy.inspect_history(n=1), f"\n\n{'-'*50}\n\n")

true_or_false_signature = "statement: str -> true_or_false: bool"
true_or_false_test = dspy.Predict(signature=true_or_false_signature)

# typing the fields forces keyword arg based calling and not position-arg based
true_or_false_result = true_or_false_test(statement = "You get green when you mix blue with red.")
print(dspy.inspect_history(n=1)) # get history of this turn only
# print(dspy.inspect_history(n=2)) # get history of both this turn and joke creation
# print(dspy.inspect_history(n=3)) # no more than 2 msgs in total history, hence
                                 # only two msgs seen

'''
class form of Signature
'''
JokeMood = Literal["Saracasm", "Tongue in Cheek", "Analogy-based", "Aggressive", "Slapstick"]
class Joke(dspy.Signature):
    topic: str = dspy.InputField(desc="Topic on which the comedian should crack a joke")
    mood: JokeMood = dspy.InputField(desc="Use this mood to setup the joke")
    joke: str = dspy.OutputField()

comedian = dspy.Predict(Joke)(topic = "Indian Politics", mood = "Saracasm")
print(f"\n\tClass Comedian joke = {comedian.joke}\n")

# violate the allowed mood, warning is thrown, BUT question is still answered.
comedian_violating_allowed_moods = dspy.Predict(Joke)(topic = "USA Oil Greed", mood = "Serious")
print(f"\n\tClass Comedian that violates mood-set joke = {comedian_violating_allowed_moods.joke}\n")

# print instructions for all comedians
print(f"{'-'*30}\tInstructions for Joke as Signature Class\t{'-'*30}\n\n{Joke.instructions}\n\n{'-'*60}\n")

