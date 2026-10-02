
import os
import asyncio
import re

from dotenv import load_dotenv
load_dotenv()

from google.genai import types

# BaseLlm: abstract base class, hence can't instantiate an object
from google.adk.models import LiteLlm
from google.adk.agents.llm_agent import Agent
from google.adk.runners import Runner
from google.adk.agents.run_config import RunConfig
from google.adk.agents._streaming_mode import StreamingMode

from google.adk.sessions import DatabaseSessionService


APP_NAME = "my-first-agent-app"
USER_ID = "my-user-id"


local_database_session_service = DatabaseSessionService(
    db_url="sqlite+aiosqlite:///./session_with_runner.db"
)

root_agent = Agent(
    name='root_agent',
    model=LiteLlm(model='deepseek/deepseek-v4-flash', api_key=os.getenv('DEEPSEEK_API_KEY')),
    description='A helpful assistant for user questions.',
    instruction='Answer user questions to the best of your knowledge'
)

# runner = Runner(
#     app_name = APP_NAME,
#     agent = root_agent,
#     session_service=local_database_session_service
# )
runner = Runner(
    app_name = APP_NAME,
    agent = root_agent,
    session_service=local_database_session_service,
    auto_create_session=True
)
print(f"Runner created for agent '{runner.agent.name}'.")

async def call_agent_async(query: str, runner: Runner, run_config: RunConfig, 
                           user_id, session_id):
    """
    """

    content = types.Content(role='user', parts = [types.Part(text=query)])

    # total N events, N-1: partials, N'th: final.
    events_partial, events_final = 0, 0
    think_block_just_started, resp_block_just_started = True, True
    async for event in runner.run_async(
        user_id = user_id, session_id=session_id, new_message=content,
        run_config=run_config):
        if event.partial:
            for part in getattr(event.content, 'parts') or []:
                text_to_print = part.text
                if part.thought:
                    text_to_print = ("\n  [Thinking]: " if think_block_just_started else "") + text_to_print
                    
                    # grey and italicised thinking blocks.
                    text_to_print = f"\033[2;3m{text_to_print}\033[0m"

                    think_block_just_started = False
                    resp_block_just_started = True

                else:
                    text_to_print = ("\n\n[Agent]: " if resp_block_just_started else "") + text_to_print
                    think_block_just_started = True
                    resp_block_just_started = False
                print(text_to_print, end="", flush=True)


async def main():
    session_id = 'session-001'

    streaming_run_config = RunConfig(streaming_mode=StreamingMode.SSE)

    try:
        # delete the session so that this script-run starts with a fresh one.
        try:
            await runner.session_service.delete_session(
                app_name=APP_NAME,
                user_id=USER_ID,
                session_id=session_id
            )
        except Exception as _:
            pass
        while True:
            query = await asyncio.to_thread(input, "\n[user]: ")
            query = query.strip()
            if not query:
                # empty input, or only enters
                continue
            elif query.lower() in ['exit', 'quit']:
                break
            else:
                await call_agent_async(query=query, runner=runner, 
                    run_config = streaming_run_config, user_id=USER_ID, 
                    session_id=session_id)
    except (KeyboardInterrupt, EOFError):
        print("\nBye 👋🏽👋🏽👋🏽.")



if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, EOFError):
        print("\nBye 👋🏽👋🏽👋🏽.")
    except Exception as e:
        print(f"Unknown exception encountered from chat session: \n{e}")

# - session.db created inside ./.adk houses both: commandline based sessions started
#    due to `adk run my_agent` and those started from the web portal via `adk web --port 8000`.
# - notice that `adk web` is same as `dsh web`.