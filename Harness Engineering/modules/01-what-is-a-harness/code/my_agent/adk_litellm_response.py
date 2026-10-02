
import os
import asyncio
import json

from dotenv import load_dotenv
load_dotenv()

# BaseLlm: abstract base class, hence can't instantiate an object
from google.adk.models import LiteLlm, llm_request

from google.genai import types



async def run_sample_llm_request(llm: LiteLlm):
    '''
    Run a basic llm request and dump the output to a json to get to know
    what all is part of an LlmResponse from ADK
    '''
    my_llm_request = llm_request.LlmRequest(
            contents=[
                types.Content(
                    role='user',
                    parts=[types.Part.from_text(text='Why is the sky blue?')]
                )]
        )
    
    async for resp in llm.generate_content_async(llm_request=my_llm_request):
        json.dump(resp.model_dump(), open("adk_llm_response_dump.json", "w+"), indent=2)

def main():

    deepseek_llm = LiteLlm(model="deepseek/deepseek-v4-flash", api_key=os.getenv('DEEPSEEK_API_KEY'))
    # print(deepseek_llm.supported_models())

    asyncio.run(run_sample_llm_request(deepseek_llm))

    

if __name__ == '__main__':
    main()