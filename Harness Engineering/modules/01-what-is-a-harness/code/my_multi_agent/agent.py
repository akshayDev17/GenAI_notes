"""

"""

import os
import asyncio

import uuid

from dotenv import load_dotenv
load_dotenv()



import async_to_sync

import questionary

from google.genai import types

from google.adk.agents.llm_agent import Agent
from google.adk.runners import Runner
from google.adk.agents import RunConfig
from google.adk.agents._streaming_mode import StreamingMode
from google.adk.models import LiteLlm
from google.adk.sessions import DatabaseSessionService


USER_ID = "akshay"
APP_NAME = "multi-agent-team"
NEW_SESSION_CHOICE = "Create a new Session ➕"

session_service = DatabaseSessionService(db_url = "sqlite+aiosqlite:///./session.db")

root_agent = Agent(
    model=LiteLlm(model='deepseek/deepseek-v4-flash', api_key=os.getenv('DEEPSEEK_API_KEY')),
    name='root_agent',
    description='A helpful assistant for user questions.',
    instruction='Answer user questions to the best of your knowledge',
)

async def get_async_agent_response(query: str, runner: Runner, run_config: RunConfig, 
                             user_id, session_id):
    """
    """

    new_msg = types.Content(role = 'user', parts = [types.Part(text=query)])
    
    thinking_just_started, main_resp_just_started = True, True

    async for event in runner.run_async(user_id=user_id, session_id=session_id, 
                                        new_message=new_msg,
                                        run_config=run_config):
        if event.partial:
            for part in getattr(event.content, 'parts') or []:
                text_to_print = part.text
                if part.thought:
                    text_to_print = ("\n  [Thinking]: " if thinking_just_started else "") + text_to_print
                    thinking_just_started = False
                    main_resp_just_started = True

                    # grey and italicised thinking blocks.
                    text_to_print = f"\033[2;3m{text_to_print}\033[0m"
                else:
                    text_to_print = ("\n\n[Agent]: " if main_resp_just_started else "") + text_to_print
                    main_resp_just_started = False
                    thinking_just_started = True

                print(text_to_print, end="", flush=True)


async def main(session_id: str):
    """
    Run the main agentic loop in an asynchronous manner
    Args:
        session_id: str
        session id of the session a user wants to either continue or start from scratch.
    """

    runner = Runner(
        app_name = APP_NAME,
        agent = root_agent,
        session_service=session_service,
        auto_create_session=True
    )
    run_config = RunConfig(streaming_mode=StreamingMode.SSE)

    # check if session exists, and retrieve last 5 messages to be displayed.
    try:
        session = await session_service.get_session(
            app_name=APP_NAME, user_id=USER_ID, session_id = session_id
        )
        if session:
            invocations = {}
            for event in getattr(session, 'events'):
                if event.invocation_id not in invocations:
                    invocations[event.invocation_id] = event.timestamp
                else:
                    invocations[event.invocation_id] = max(event.timestamp, invocations[event.invocation_id])

            last_5_invocations = [x[0] for x in sorted(invocations.items(), key=lambda x: x[1], reverse=True)][:5][::-1]

            thinking_just_started, main_resp_just_started = True, True

            for event in getattr(session, 'events'):
                if event.invocation_id in last_5_invocations:
                    for part in getattr(event.content, 'parts') or []:
                        text_to_print = part.text
                        if event.content.role == "user":
                            text_to_print = ("\n[user]: ") + text_to_print
                        else:
                            if part.thought:
                                text_to_print = ("\n  [Thinking]: " if thinking_just_started else "") + text_to_print
                                thinking_just_started = False
                                main_resp_just_started = True
            
                                # grey and italicised thinking blocks.
                                text_to_print = f"\033[2;3m{text_to_print}\033[0m"
                            else:
                                text_to_print = ("\n\n[Agent]: " if main_resp_just_started else "") + text_to_print
                                main_resp_just_started = False
                                thinking_just_started = True
        
                        print(text_to_print, end="", flush=True)
    except Exception as excp:
        print(excp)



    try:
        while True:
            # asyncio.to_thread(func, *args) runs func(*args) in a separate worker thread, 
            #   and returns an awaitable that completes when the function returns.
            # await suspends main() until that thread finishes, then gives you 
            #   the returned string in query.
            query = await asyncio.to_thread(input, "\n[user]: ")
            query = query.strip()
            if not query:
                continue
            if query in ('exit', 'quit'):
                print("\nBye. 👋🏽👋🏽👋🏽")
                break
            await get_async_agent_response(query=query, runner=runner, 
                run_config=run_config, user_id=USER_ID, session_id = session_id)
    except (KeyboardInterrupt, EOFError):
        print("\nBye. 👋🏽👋🏽👋🏽")
    except Exception as e:
        print(f"\n-- Exception = {e}\n")


if __name__ == '__main__':
    sessions_list = async_to_sync.function(session_service.list_sessions)(app_name=APP_NAME)
    session_ids = [session.id for session in sessions_list.sessions]

    # choose between continuing existing sessions or beginning one from scratch.
    choice = questionary.select("Choose a session:", choices = session_ids+[NEW_SESSION_CHOICE]).ask()

    session_id = None

    if choice == NEW_SESSION_CHOICE:
        session_id = f"session-{uuid.uuid4().hex}"
    else:
        session_id = choice

    try:
        asyncio.run(main(session_id))
    except (KeyboardInterrupt, EOFError):
        print("\nBye. 👋🏽👋🏽👋🏽")
    except Exception as e:
        print(f"\n-- Exception = {e}\n")