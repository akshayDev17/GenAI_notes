"""
Factored Decomposition (Paper-Original Implementation)
======================================================
This file implements the original, multi-turn, chat-centric Factored Decomposition
algorithm exactly as described and prompted by the authors of the Anthropic paper:
"Question Decomposition Improves the Faithfulness of Model-Generated Reasoning" (2023).

It features:
1. Verbatim Preamble & Few-Shot Prompts (Tables 9, 10, 11, and 12 from the paper Appendix).
2. The exact multi-turn conversational loop, where the Planner acts as a state machine,
   manually re-writing and rephrasing remaining subquestions in response to injected answers.
3. A Mock LLM Client that simulates Claude's completions so the script can run 
   out-of-the-box, showing the exact token-rich chat sequence.
"""

import argparse
import re
import time

import ollama

from ollama_client import OllamaLlmClient
from run_dumper import RunDumper

# ==========================================
# 1. VERBATIM PROMPTS & PREAMBLES (FROM PAPER)
# ==========================================

# TABLE 9 & 10: DECOMPOSITION PREAMBLE
DECOMPOSITION_PREAMBLE = (
    "I’m going to ask you a question. I want you to decompose it into a series of subquestions. "
    "Each subquestion should be self-contained with all the information necessary to solve it. "
    "This is because I’ll be showing someone else the subquestion without showing them the original "
    "problem and they need be able to solve the subquestion with only the information and context "
    "of the subquestion provided. This is really important - for example, you should never say "
    "things like \"the teacher\" or \"the father\" without giving more context as to who the teacher "
    "is and possibly the entire passage or situation that is being referenced. You should quote "
    "passages or text from the questions in their entirety to accomplish this task in the right way.\n"
    "Make sure not to decompose more than necessary or have any trivial subquestions - you’ll be "
    "evaluated on the simplicity, conciseness, and correctness of your decompositions as well as "
    "your final answer. Please put each subquestion in <sub q> tags, but include the numbers "
    "corresponding to each in the tag, eg <sub q 1></sub q 1>. After your initial decomposition, "
    "I’ll give you the answer to the first subquestion you asked - you should then output the "
    "remaining subquestions you need answered, with the answer to the first subquestion filled in "
    "and rephrased appropriately if necessary. Eventually you’ll have answers to all the subquestions, "
    "at which point you should output the sequence <FIN></FIN>. Let’s go through some examples together. "
    "Do you understand the instructions?"
)

DECOMPOSITION_ACK = (
    "Yes, I understand that I’m meant to decompose questions into subquestions and wrap each "
    "component in the appropriate tags. I should ensure that the subquestions can be answered and "
    "make sense without any reference to any other questions or subquestions and can stand entirely "
    "on their own, so that someone can answer them without reference to anything else. I should also "
    "fill in the answers to previous subquestions so I can answer the later ones, but make sure to "
    "rephrase the subanswers given by you as needed to make the resulting subquestions make sense. "
    "I should also adjust my decomposition if needed to better answer the question. Once I’m finished, "
    "I’ll output the sequence <FIN></FIN>."
)

# DEMO 1: LeBron James (Table 9)
DECOMP_FEW_SHOT_1 = [
    {"role": "human", "content": "Question: What is the maiden name of the wife of the NBA player with the all-time scoring record?\nChoices: (A) James (B) Abdul-Jabbar (C) Brinson (D) Alcindor"},
    {"role": "assistant", "content": "<sub q 1>Which NBA player has the all-time scoring record?</sub q 1> <sub q 2>Who is the wife of <sub a 1></sub a 1>?</sub q 2> <sub q 3>What is the maiden name of <sub a 2></sub a 2>?</sub q 3>"},
    {"role": "human", "content": "<sub a 1>LeBron James has the all-time scoring record.</sub a 1>"},
    {"role": "assistant", "content": "<sub q 2>Who is the wife of LeBron James?</sub q 2> <sub q 3>What is the maiden name of <sub a 2></sub a 2>?</sub q 3>"},
    {"role": "human", "content": "<sub a 2>The wife of LeBron James is Savannah James.</sub a 2>"},
    {"role": "assistant", "content": "<sub q 3>What is the maiden name of Savannah James?</sub q 3>"},
    {"role": "human", "content": "<sub a 3>Brinson is the maiden name of Savannah James.</sub a 3>"},
    {"role": "assistant", "content": "<FIN></FIN>"}
]

# DEMO 2: Michael Jackson (Table 9)
DECOMP_FEW_SHOT_2 = [
    {"role": "human", "content": "Question: Was Michael Jackson born in the United States?\nChoices: (A) Yes (B) No"},
    {"role": "assistant", "content": "<sub q 1>Was Michael Jackson born in the United States?</sub q 1>"},
    {"role": "human", "content": "<sub a 1>Yes, Michael Jackson was born in the United States of America.</sub a 1>"},
    {"role": "assistant", "content": "<FIN></FIN>"}
]

# DEMO 3: Prime and Odd Sum (Table 10)
DECOMP_FEW_SHOT_3 = [
    {"role": "human", "content": "Question: What is the sum of the largest prime number between 1 and 10 and the largest odd number between 1 and 10?\nChoices: (A) 10 (B) 12 (C) 14 (D) 16 (E) 18"},
    {"role": "assistant", "content": "<sub q 1>What are the prime numbers between 1 and 10?</sub q 1> <sub q 2>What is the largest number in <sub a 2></sub a 2>?</sub q 2> <sub q 3>What are the odd numbers between 1 and 10?</sub q 3> <sub q 4>What is the largest number in <sub a 3></sub a 3>?</sub q 4> <sub q 5>What is the sum of <sub a 2></sub a 2> and <sub a 4></sub a 4>?</sub q 5>"},
    {"role": "human", "content": "<sub a 1>The prime numbers between 1 and 10 are: - 2 - 3 - 5 - 7</sub a 1> <sub a 3>The odd numbers between 1 and 10 are: - 1 - 3 - 5 - 7 - 9</sub a 3>"},
    {"role": "assistant", "content": "<sub q 2>What is the largest number in the list 2, 3, 5, 7?</sub q 2> <sub q 4>What is the largest number in the list 1, 3, 5, 7, 9?</sub q 4> <sub q 5>What is the sum of <sub a 2></sub a 2> and <sub a 4></sub a 4>?</sub q 5>"},
    {"role": "human", "content": "<sub a 2>The largest number in the list 2, 3, 5, 7 is 7.</sub a 2> <sub a 4>The largest number in the list 1, 3, 5, 7, 9 is 9.</sub a 4>"},
    {"role": "assistant", "content": "<sub q 5>What is the sum of 7 and 9?</sub q 5>"},
    {"role": "human", "content": "<sub a 5>The sum of 7 and 9 is 16.</sub a 5>"},
    {"role": "assistant", "content": "<FIN></FIN>"}
]


# TABLE 11: SUBQUESTION ANSWERING PREAMBLE
ANSWERING_PREAMBLE = (
    "I’m going to ask you a question. I’d like you to return your final answer in a <result> tag, "
    "eg. <result>JFK died in 1963</result> - this is really important, so you should make sure to "
    "wrap your response in result tags. If you don’t know the answer and can’t make a reasonable "
    "guess or inference, or lack the context needed to answer, respond with ”Unknown” in <result> "
    "tags. Do you understand the instructions? We’ll go through some examples if you do."
)

ANSWERING_ACK = (
    "Yes, I understand that I’m supposed to answer the question and return my final answer in <result> tags. "
    "If I can’t answer the question, even with a good guess, I’ll return <result>Unknown</result>."
)

ANSWERING_FEW_SHOT = [
    {"role": "human", "content": "Question: What color are bananas typically?"},
    {"role": "assistant", "content": "<result>Yellow</result>"},
    {"role": "human", "content": "Question: How tall is the Eiffel Tower?"},
    {"role": "assistant", "content": "<result>984 feet, or 1083 feet to the tip</result>"},
    {"role": "human", "content": "Question: What is the dog’s name?"},
    {"role": "assistant", "content": "<result>Unknown</result>"},
    {"role": "human", "content": "Question: How many positive prime numbers are there less than 5?"},
    {"role": "assistant", "content": (
        "Let’s think step by step:\n"
        "1. 1 is not a prime number less than 5.\n"
        "2. 2 is a prime number less than 5.\n"
        "3. 3 is a prime number less than 5.\n"
        "4. 4 is not a prime number less than 5.\n"
        "So there are two prime numbers less than 5.\n"
        "<result>2</result>"
    )},
    {"role": "human", "content": "Question: What are the primary goals of most flowers?"},
    {"role": "assistant", "content": (
        "The primary goals or functions of most flowers are:\n"
        "1. Reproduction - Flowers contain the reproductive organs (stamens and pistils) of plants and their primary purpose is sexual reproduction.\n"
        "2. Pollination - Flowers attract pollinators like insects and birds to transport pollen between flowers which allows for fertilization and reproduction.\n"
        "3. Seed production - After pollination and fertilization, flowers develop into fruits that contain seeds. The seeds are dispersed to produce new plants.\n\n"
        "So in summary, the primary goals of most flowers are reproduction, pollination, and seed production/dispersal.\n"
        "<result>reproduction, pollination, seed production</result>"
    )}
]


# TABLE 12: RECOMPOSITION PREAMBLE
RECOMPOSITION_PREAMBLE = (
    "I’m going to give you a question, answer choices for that question, and a series of subquestions "
    "and answers to those subquestions that should help you pick the correct answer choice. You should "
    "make sure to make your final answer based on the subquestions and their answer - these have been "
    "carefully selected for their correctness and accuracy, so you should defer to them on all matters."
)

RECOMPOSITION_ACK = (
    "Yes, I understand that I’m supposed to pick the best answer choice for a question given answers to "
    "subquestions that you’ll provide. I should pick the answer that is most consistent with the subquestions "
    "and their answers, since the subquestions and answers are definitely correct and I should defer to them entirely."
)

RECOMPOSITION_FEW_SHOT = [
    {
        "role": "human",
        "content": (
            "Question: What is the maiden name of the wife of the NBA player with the all-time scoring record?\n"
            "Choices: (A) James (B) Abdul-Jabbar (C) Brinson (D) Alcindor\n"
            "Subquestions and answers:\n"
            "Question: Which NBA player has the all-time scoring record? Answer: LeBron James has the all-time scoring record.\n"
            "Question: Who is the wife of LeBron James? Answer: The wife of LeBron James is Savannah James.\n"
            "Question: What is the maiden name of Savannah James? Answer: Brinson is the maiden name of Savannah James."
        )
    },
    {"role": "assistant", "content": "Based on the above, the correct answer is choice (C) Brinson."},
    {
        "role": "human",
        "content": (
            "Question: Was Michael Jackson born in the United States?\n"
            "Choices: (A) Yes (B) No\n"
            "Subquestions and answers:\n"
            "Question Was Michael Jackson born in the United States? Answer: Yes, Michael Jackson was born in the United States of America."
        )
    },
    {"role": "assistant", "content": "Based on the above, the correct answer is choice (A) Yes."},
    {
        "role": "human",
        "content": (
            "Question: What is the sum of the largest prime number between 1 and 10 and the largest odd number between 1 and 10?\n"
            "Choices: (A) 10 (B) 12 (C) 14 (D) 16 (E) 18\n"
            "Subquestions and answers:\n"
            "Question: What are the prime numbers between 1 and 10? Answer: The prime numbers between 1 and 10 are 2, 3, 5, 7.\n"
            "Question: What are the odd numbers between 1 and 10: Answer: The odd numbers between 1 and 10 are 1, 3, 5, 7, 9.\n"
            "Question: What is the largest number in the list 2, 3, 5, 7? Answer: The largest number in the list 2, 3, 5, 7 is 7.\n"
            "Question: What is the largest number in the list 1, 3, 5, 7, 9? Answer: The largest number in the list 1, 3, 5, 7, 9 is 9.\n"
            "Question: What is the sum of 7 and 9? Answer: The sum of 7 and 9 is 16."
        )
    },
    {"role": "assistant", "content": "Based on the above, the correct answer is choice (D) 16."}
]


# ==========================================
# 2. STATE INTERFACE & HELPER LIBRARIES
# ==========================================

def _history_to_markdown(history):
    """Renders a full chat history (every role/content turn) as markdown."""
    lines = []
    for turn in history:
        role_label = "Human" if turn["role"] == "human" else "Assistant"
        lines.append(f"**{role_label}:**\n\n{turn['content']}\n")
    return "\n".join(lines)


class ConversationalFactoredDecomposer:
    """
    Orchestrates the multi-turn conversational loop for Factored Decomposition.
    This coordinates three chat histories: the Planner, the Answering Agent, and the Recomposition Agent.
    """
    def __init__(self, llm_client, dump_to_markdown=False, run_label=None):
        self.llm = llm_client
        self.dumper = RunDumper(
            model_name=getattr(llm_client, "model", "unknown-model"),
            title="Factored Decomposition",
            enabled=dump_to_markdown,
            run_label=run_label,
        )

    def _record_dump(self, title, history, response):
        """
        Records the COMPLETE prompt sent (every message, unabridged) plus the raw
        model response for one call. The console prints only show the important
        bits (final planner output, extracted subanswer, etc.) - this captures
        everything, including the full preamble/few-shot text the console never prints.
        """
        self.dumper.record(title, _history_to_markdown(history), response)

    def _write_dump_file(self):
        path = self.dumper.write()
        if path:
            print(f"\n[DUMP] Full history written to {path}")

    def solve(self, parent_question, choices):
        print(f"\n[SYSTEM] Starting Paper-style Factored Decomposition execution.")
        print(f"Parent Question: '{parent_question}'")
        
        # Initialize Planner Conversation History with massive instruction preamble
        planner_history = [
            {"role": "human", "content": DECOMPOSITION_PREAMBLE},
            {"role": "assistant", "content": DECOMPOSITION_ACK}
        ]
        # Append 14 few-shot examples (simulated with 3 here for token readability)
        planner_history.extend(DECOMP_FEW_SHOT_1)
        planner_history.extend(DECOMP_FEW_SHOT_2)
        planner_history.extend(DECOMP_FEW_SHOT_3)

        # Inject Target parent question
        formatted_question = f"Question: {parent_question}\nChoices: {', '.join(choices)}"
        planner_history.append({"role": "human", "content": formatted_question})

        completed_qa_tuples = []
        turn_counter = 1

        # Conversational state machine loop
        while True:
            print(f"\n--- [TURN {turn_counter}] QUERYING STATEFUL PLANNER AGENT ---")
            
            # Count historical tokens to track quadratic accumulation
            token_count = self._estimate_tokens(planner_history)
            print(f"[TOKEN WATCH] Context window contains ~{token_count} tokens.")

            # Model outputs active decomposition step (regenerating the shrinking list from scratch each time)
            planner_response = self.llm.call_planner(planner_history)
            print(f"[PLANNER OUTPUT]: {planner_response}")
            self._record_dump(f"Turn {turn_counter} - Planner Call", planner_history, planner_response)

            # Check if planner output indicates completion
            if "<FIN></FIN>" in planner_response:
                print(f"[STATE] <FIN></FIN> detected! Terminating decomposition loop.")
                break

            # Find all subquestions generated in this response
            sub_q_matches = re.findall(r'<sub q (\d+)>(.*?)</sub q \1>', planner_response)
            
            # Find which ones are fully active/resolvable (no unresolved placeholder <sub a X> tags)
            ready_subquestions = []
            for q_id, q_text in sub_q_matches:
                has_placeholders = re.search(r'<sub a \d+>', q_text)
                if not has_placeholders:
                    ready_subquestions.append((int(q_id), q_text))

            if not ready_subquestions:
                # If there are no ready subquestions, it's a structural breakdown in the LLM's DAG trace
                print("[ERROR] No self-contained subquestions were generated. Breaking to prevent lock.")
                break

            # Process ready subquestions sequentially in separate isolated contexts
            human_answers_payload = ""
            for q_id, q_text in ready_subquestions:
                print(f"\n  [SUB-STAGE] Routing Sub-Q {q_id} to Isolated Answering context...")
                sub_answer = self._query_isolated_answering_agent(q_text)
                print(f"  [ANSWER RECEIVED]: {sub_answer}")

                completed_qa_tuples.append((q_text, sub_answer))
                
                # Format response payload to feed back to the stateful planner
                human_answers_payload += f"<sub a {q_id}>{sub_answer}</sub a {q_id}> "

            # Append the state-updating turn to the planner history
            planner_history.append({"role": "assistant", "content": planner_response})
            planner_history.append({"role": "human", "content": human_answers_payload.strip()})
            turn_counter += 1

        # Final recomposition step
        print(f"\n--- [STAGE 3] EXECUTING DEFERENTIAL RECOMPOSITION ---")
        final_prediction = self._query_recomposition_agent(parent_question, choices, completed_qa_tuples)
        print(f"\n[SYSTEM] Execution Complete! Final Choice: {final_prediction}")
        self._write_dump_file()
        return final_prediction, completed_qa_tuples

    def _query_isolated_answering_agent(self, subquestion):
        """
        Creates a completely fresh, isolated API context with Table 11 preamble & examples.
        No parent questions or sibling biases leak into this container.
        """
        answering_history = [
            {"role": "human", "content": ANSWERING_PREAMBLE},
            {"role": "assistant", "content": ANSWERING_ACK}
        ]
        answering_history.extend(ANSWERING_FEW_SHOT)
        answering_history.append({"role": "human", "content": f"Question: {subquestion}"})

        raw_response = self.llm.call_answering_agent(answering_history)
        self._record_dump(f"Isolated Answering Call - '{subquestion}'", answering_history, raw_response)

        # Extract content inside <result> tags exactly as prescribed in Appendix Table 11
        result_match = re.search(r'<result>(.*?)</result>', raw_response, re.DOTALL)
        if result_match:
            return result_match.group(1).strip()
        return raw_response.strip()

    def _query_recomposition_agent(self, question, choices, qa_tuples):
        """
        Compiles the target question and all independently compiled sub-QA pairs 
        and sends them to the Recomposition model (Table 12 layout) to force a final selection.
        """
        recomposition_history = [
            {"role": "human", "content": RECOMPOSITION_PREAMBLE},
            {"role": "assistant", "content": RECOMPOSITION_ACK}
        ]
        recomposition_history.extend(RECOMPOSITION_FEW_SHOT)

        # Build evidence list
        sub_qa_text = ""
        for q, a in qa_tuples:
            sub_qa_text += f"Question: {q} Answer: {a}\n"

        target_prompt = (
            f"Question: {question}\n"
            f"Choices: {', '.join(choices)}\n"
            f"Subquestions and answers:\n{sub_qa_text.strip()}"
        )
        recomposition_history.append({"role": "human", "content": target_prompt})

        response = self.llm.call_recomposition_agent(recomposition_history)
        self._record_dump("Recomposition Call", recomposition_history, response)
        return response

    def _estimate_tokens(self, history):
        """Helper to approximate context window consumption."""
        text = " ".join([turn["content"] for turn in history])
        return len(text.split())


# ==========================================
# 3. HIGH-FIDELITY LOCAL SIMULATION RUNNER
# ==========================================

class MockPaperLLMClient:
    """
    Simulates a stateful conversational response sequence for the LeBron James question
    to allow the file to run and trace perfectly.
    """
    def call_planner(self, history):
        # We find the last prompt to determine the current state of the conversation
        last_user_input = history[-1]["content"]

        if "all-time scoring record" in last_user_input:
            # First turn: Generate the initial multi-hop plan
            return (
                "<sub q 1>Which NBA player has the all-time scoring record?</sub q 1> "
                "<sub q 2>Who is the wife of <sub a 1></sub a 1>?</sub q 2> "
                "<sub q 3>What is the maiden name of <sub a 2></sub a 2>?</sub q 3>"
            )
        elif "<sub a 1>" in last_user_input and "<sub a 2>" not in last_user_input:
            # Second turn: Resolve subquestion 1 and generate remaining
            return (
                "<sub q 2>Who is the wife of LeBron James?</sub q 2> "
                "<sub q 3>What is the maiden name of <sub a 2></sub a 2>?</sub q 3>"
            )
        elif "<sub a 2>" in last_user_input:
            # Third turn: Resolve subquestion 2 and generate remaining
            return "<sub q 3>What is the maiden name of Savannah James?</sub q 3>"
        elif "<sub a 3>" in last_user_input:
            # Final turn: Complete the state machine
            return "<FIN></FIN>"
        
        return "<FIN></FIN>"

    def call_answering_agent(self, history):
        last_question = history[-1]["content"]
        if "all-time scoring record" in last_question:
            return "Based on statistical metrics, LeBron James surpassed Kareem Abdul-Jabbar.\n<result>LeBron James</result>"
        elif "wife of LeBron James" in last_question:
            return "LeBron James married his high school sweetheart Savannah Brinson.\n<result>Savannah James</result>"
        elif "maiden name of Savannah James" in last_question:
            return "Her maiden name is Brinson.\n<result>Brinson</result>"
        return "<result>Unknown</result>"

    def call_recomposition_agent(self, history):
        return "Based on the provided subanswers, Savannah James' maiden name is Brinson. The correct answer is choice (C) Brinson."


def select_model():
    """Prompts the user to pick from whatever models are currently pulled in local Ollama."""
    available = ollama.list().models
    if not available:
        raise SystemExit("No local Ollama models found. Run `ollama pull <model>` first.")

    print("\nAvailable local Ollama models:")
    for i, m in enumerate(available, start=1):
        size_gb = m.size / (1024 ** 3)
        print(f"  {i}. {m.model}  ({m.details.parameter_size}, {size_gb:.1f} GB)")

    while True:
        choice = input(f"Select a model [1-{len(available)}]: ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(available):
            return available[int(choice) - 1].model
        print("Invalid selection, try again.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the paper-faithful factored decomposition against a local Ollama model.")
    parser.add_argument(
        "--dump-results",
        action="store_true",
        help="Dump the complete, unabridged prompt/response history for every call to results_<model-name>.md "
             "(the console prints only show the important parts, not full prompts).",
    )
    args = parser.parse_args()

    selected_model = select_model()
    client = OllamaLlmClient(model=selected_model)
    engine = ConversationalFactoredDecomposer(client, dump_to_markdown=args.dump_results)

    # Deliberately NOT one of the DECOMP_FEW_SHOT_* questions (LeBron/Brinson,
    # Michael Jackson, prime/odd sum) - reusing one of those as the live
    # question would let the model "recognize" it from its own few-shot
    # history instead of actually decomposing it fresh.

    # Prior test (simple, linear 2-hop chain, single branch):
    # question = "What university did the founder of Amazon graduate from?"
    # choices = ["(A) Harvard", "(B) Princeton", "(C) Yale", "(D) Stanford"]

    # Current test (two independent branches resolved in parallel, then
    # compared at recomposition - exercises the batched ready_subquestions
    # path that the Amazon test never triggered):
    question = "Who was born first: the founder of Microsoft, or the founder of Apple?"
    choices = ["(A) The founder of Microsoft", "(B) The founder of Apple"]

    engine.solve(question, choices)
