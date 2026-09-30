"""
Know all model strings allowed.
- As per DSPy documentation, litellm supported model strings are what shall be
used with dspy. https://dspy.ai/current/api/models/LM/
"""

import dspy

import json
from functools import lru_cache
import urllib.request 

REGISTRY_URL = ("https://raw.githubusercontent.com/BerriAI/litellm/main/"
                "model_prices_and_context_window.json")

@lru_cache(maxsize=1)
def load_registry(path=None):
    """
    """
    with urllib.request.urlopen(REGISTRY_URL, timeout=60) as r:
        return json.load(r)

def main():
    """
    """
    litellm_model_registry = load_registry()
    # deepseek_registry = {}
    deepseek_provider_registry = {}
    for model_name in list(litellm_model_registry.keys()):
        # if 'deepseek' in model_name.lower():
        #     deepseek_registry[model_name] = litellm_model_registry[model_name]
        if litellm_model_registry.get(model_name, {}).get('litellm_provider', {}) == 'deepseek':
            deepseek_provider_registry[model_name] = litellm_model_registry[model_name]
    # print(json.dumps(deepseek_registry, indent=2), file=open("deepseek_litellm_model_registries.json", "w+"))
    print(json.dumps(deepseek_provider_registry, indent=2), file=open("deepseek_provider_litellm_model_registries.json", "w+"))

if __name__=='__main__':
    main()
