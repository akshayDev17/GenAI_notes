"""
Factored Decomposition (Paper-Original Implementation)
======================================================
This file implements the original, multi-turn, chat-centric Factored Decomposition
algorithm exactly as described and prompted by the authors of the Anthropic paper:
"Question Decomposition Improves the Faithfulness of Model-Generated Reasoning" (2023).

It implements PromptWritingTechnique so it can be evaluated generically by
evaluation_suite.py, or run standalone via this file's own __main__.

It features:
1. Verbatim Preamble & Few-Shot Prompts (Tables 9, 10, 11, 12, and 17 from the paper
   Appendix) - these live in factored_decomposition_prompts.py, imported below, so this
   file stays orchestration logic only.
2. The exact multi-turn conversational loop, where the Planner acts as a state machine,
   manually re-writing and rephrasing remaining subquestions in response to injected answers.
3. A Mock LLM Client that simulates Claude's completions so the script can run
   out-of-the-box, showing the exact token-rich chat sequence.
"""

import argparse
import re

from ollama_client import OllamaLlmClient
from prompt_writing_technique import PromptWritingTechnique
from run_dumper import RunDumper

# Verbatim paper prompts (Tables 9, 10, 11, 12, 17) live in their own module -
# see factored_decomposition_prompts.py. This file stays orchestration logic only.
from factored_decomposition_prompts import (
    DECOMPOSITION_PREAMBLE,
    DECOMPOSITION_ACK,
    DECOMP_FEW_SHOT_1,
    DECOMP_FEW_SHOT_2,
    DECOMP_FEW_SHOT_3,
    ANSWERING_PREAMBLE,
    ANSWERING_ACK,
    ANSWERING_FEW_SHOT,
    RECOMPOSITION_PREAMBLE,
    RECOMPOSITION_ACK,
    RECOMPOSITION_FEW_SHOT,
    CORRUPTION_PREAMBLE,
    CORRUPTION_ACK,
    CORRUPTION_FEW_SHOT,
)


class FactoredDecomposition(PromptWritingTechnique):
    """
    Implements PromptWritingTechnique via the paper's original multi-turn,
    chat-centric Factored Decomposition algorithm. Coordinates three chat
    histories: the Planner, the Answering Agent, and the Recomposition Agent.
    """
    def __init__(self, llm_client, dump_to_markdown=False, run_label=None, title="Factored Decomposition"):
        self.llm = llm_client
        self.dumper = RunDumper(
            model_name=getattr(llm_client, "model", "unknown-model"),
            title=title,
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
        self.dumper.record(title, self._history_to_markdown(history), response)

    def write_dump(self):
        """
        Public - called automatically at the end of generate(), and also
        callable externally (e.g. by evaluation_suite.py after a truncation/
        corruption sweep that never calls generate() itself, so the dumper
        would otherwise never get flushed to disk).
        """
        path = self.dumper.write()
        if path:
            print(f"\n[DUMP] Full history written to {path}")

    def generate(self, question, choices):
        print(f"\n[SYSTEM] Starting Paper-style Factored Decomposition execution.")
        print(f"Parent Question: '{question}'")

        planner_history = [
            {"role": "human", "content": DECOMPOSITION_PREAMBLE},
            {"role": "assistant", "content": DECOMPOSITION_ACK}
        ]
        planner_history.extend(DECOMP_FEW_SHOT_1)
        planner_history.extend(DECOMP_FEW_SHOT_2)
        planner_history.extend(DECOMP_FEW_SHOT_3)

        formatted_question = f"Question: {question}\nChoices: {', '.join(choices)}"
        planner_history.append({"role": "human", "content": formatted_question})

        completed_qa_tuples = []
        turn_counter = 1

        while True:
            print(f"\n--- [TURN {turn_counter}] QUERYING STATEFUL PLANNER AGENT ---")

            token_count = self._estimate_tokens(planner_history)
            print(f"[TOKEN WATCH] Context window contains ~{token_count} tokens.")

            planner_response = self.llm.chat(self._to_client_messages(planner_history))
            print(f"[PLANNER OUTPUT]: {planner_response}")
            self._record_dump(f"Turn {turn_counter} - Planner Call", planner_history, planner_response)

            if "<FIN></FIN>" in planner_response:
                print(f"[STATE] <FIN></FIN> detected! Terminating decomposition loop.")
                break

            sub_q_matches = re.findall(r'<sub q (\d+)>(.*?)</sub q \1>', planner_response)

            ready_subquestions = []
            for q_id, q_text in sub_q_matches:
                has_placeholders = re.search(r'<sub a \d+>', q_text)
                if not has_placeholders:
                    ready_subquestions.append((int(q_id), q_text))

            if not ready_subquestions:
                print("[ERROR] No self-contained subquestions were generated. Breaking to prevent lock.")
                break

            human_answers_payload = ""
            for q_id, q_text in ready_subquestions:
                print(f"\n  [SUB-STAGE] Routing Sub-Q {q_id} to Isolated Answering context...")
                sub_answer = self._query_isolated_answering_agent(q_text)
                print(f"  [ANSWER RECEIVED]: {sub_answer}")

                completed_qa_tuples.append((q_text, sub_answer))

                human_answers_payload += f"<sub a {q_id}>{sub_answer}</sub a {q_id}> "

            planner_history.append({"role": "assistant", "content": planner_response})
            planner_history.append({"role": "human", "content": human_answers_payload.strip()})
            turn_counter += 1

        print(f"\n--- [STAGE 3] EXECUTING DEFERENTIAL RECOMPOSITION ---")
        final_prediction = self._query_recomposition_agent(question, choices, completed_qa_tuples)
        print(f"\n[SYSTEM] Execution Complete! Final Choice: {final_prediction}")
        self.write_dump()
        return final_prediction, completed_qa_tuples

    def answer_with_truncated_reasoning(self, question, choices, reasoning_sample, num_steps):
        return self._query_recomposition_agent(question, choices, reasoning_sample[:num_steps])

    def answer_with_corrupted_reasoning(self, question, choices, reasoning_sample, step_index):
        orig_q, orig_a = reasoning_sample[step_index]
        corrupted_a = self._query_corruptor(orig_q)
        corrupted_sample = list(reasoning_sample)
        corrupted_sample[step_index] = (orig_q, corrupted_a)
        return self._query_recomposition_agent(question, choices, corrupted_sample)

    def render_reasoning_as_text(self, reasoning_sample):
        if not reasoning_sample:
            return "(no reasoning generated)"
        return "\n".join(f"Q: {q}\nA: {a}" for q, a in reasoning_sample)

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

        raw_response = self.llm.chat(self._to_client_messages(answering_history))
        self._record_dump(f"Isolated Answering Call - '{subquestion}'", answering_history, raw_response)

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

        sub_qa_text = ""
        for q, a in qa_tuples:
            sub_qa_text += f"Question: {q} Answer: {a}\n"

        target_prompt = (
            f"Question: {question}\n"
            f"Choices: {', '.join(choices)}\n"
            f"Subquestions and answers:\n{sub_qa_text.strip()}"
        )
        recomposition_history.append({"role": "human", "content": target_prompt})

        response = self.llm.chat(self._to_client_messages(recomposition_history))
        self._record_dump("Recomposition Call", recomposition_history, response)
        return response

    def _query_corruptor(self, subquestion):
        """
        Real call asking the model to answer the subquestion WRONG, from scratch -
        Table 17's actual procedure. The correct subanswer is never shown to the
        model at all; it's not an edit-this-answer task.
        """
        history = [
            {"role": "human", "content": CORRUPTION_PREAMBLE},
            {"role": "assistant", "content": CORRUPTION_ACK},
        ]
        history.extend(CORRUPTION_FEW_SHOT)
        history.append({"role": "human", "content": f"Question: {subquestion}"})

        raw_response = self.llm.chat(self._to_client_messages(history))
        self._record_dump(f"Corruption Call - '{subquestion}'", history, raw_response)

        result_match = re.search(r'<result>(.*?)</result>', raw_response, re.DOTALL)
        return result_match.group(1).strip() if result_match else raw_response.strip()

    def _estimate_tokens(self, history):
        """Helper to approximate context window consumption."""
        text = " ".join([turn["content"] for turn in history])
        return len(text.split())


# ==========================================
# 3. HIGH-FIDELITY LOCAL SIMULATION RUNNER
# ==========================================

class MockFactoredDecompositionClient:
    """
    Simulates a stateful conversational response sequence for the LeBron James
    question to allow this file to run offline. Adapted to the new single-
    chat()-method client shape: since there's no longer a separate method
    name per role (planner/answering/recomposition), the mock detects which
    "mode" is active by checking for each mode's distinguishing preamble text
    in the message history - each of the three preambles is verbatim and
    mutually exclusive across the three call types, so this is unambiguous.
    """
    def chat(self, messages):
        joined = " ".join(m["content"] for m in messages)
        last_content = messages[-1]["content"]

        if ANSWERING_PREAMBLE in joined:
            return self._answering_response(last_content)
        elif RECOMPOSITION_PREAMBLE in joined:
            return self._recomposition_response()
        elif CORRUPTION_PREAMBLE in joined:
            return self._corruption_response(last_content)
        else:
            return self._planner_response(last_content)

    def _planner_response(self, last_content):
        if "all-time scoring record" in last_content:
            return (
                "<sub q 1>Which NBA player has the all-time scoring record?</sub q 1> "
                "<sub q 2>Who is the wife of <sub a 1></sub a 1>?</sub q 2> "
                "<sub q 3>What is the maiden name of <sub a 2></sub a 2>?</sub q 3>"
            )
        elif "<sub a 1>" in last_content and "<sub a 2>" not in last_content:
            return (
                "<sub q 2>Who is the wife of LeBron James?</sub q 2> "
                "<sub q 3>What is the maiden name of <sub a 2></sub a 2>?</sub q 3>"
            )
        elif "<sub a 2>" in last_content:
            return "<sub q 3>What is the maiden name of Savannah James?</sub q 3>"
        elif "<sub a 3>" in last_content:
            return "<FIN></FIN>"
        return "<FIN></FIN>"

    def _answering_response(self, last_content):
        if "all-time scoring record" in last_content:
            return "Based on statistical metrics, LeBron James surpassed Kareem Abdul-Jabbar.\n<result>LeBron James</result>"
        elif "wife of LeBron James" in last_content:
            return "LeBron James married his high school sweetheart Savannah Brinson.\n<result>Savannah James</result>"
        elif "maiden name of Savannah James" in last_content:
            return "Her maiden name is Brinson.\n<result>Brinson</result>"
        return "<result>Unknown</result>"

    def _recomposition_response(self):
        return "Based on the provided subanswers, Savannah James' maiden name is Brinson. The correct answer is choice (C) Brinson."

    def _corruption_response(self, last_content):
        return "<result>Wilt Chamberlain</result>"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the paper-faithful factored decomposition against a local Ollama model.")
    parser.add_argument(
        "--dump-results",
        action="store_true",
        help="Dump the complete, unabridged prompt/response history for every call to results_<model-name>.md "
             "(the console prints only show the important parts, not full prompts).",
    )
    parser.add_argument(
        "--model", type=str, default=None, metavar="NAME",
        help="Ollama model to use, e.g. 'llama3.2:latest'. Skips the interactive picker. "
             "Use this for any scripted or reproducible run: the picker lists models ordered by "
             "modification time, so pulling or using a model renumbers the menu - piping a fixed "
             "index can silently select a different model than it did last week.",
    )
    args = parser.parse_args()

    selected_model = OllamaLlmClient.resolve_model(args.model) if args.model else OllamaLlmClient.select_model()
    client = OllamaLlmClient(model=selected_model)
    technique = FactoredDecomposition(client, dump_to_markdown=args.dump_results)

    # Deliberately NOT one of the DECOMP_FEW_SHOT_* questions (LeBron/Brinson,
    # Michael Jackson, prime/odd sum) - reusing one of those as the live
    # question would let the model "recognize" it from its own few-shot
    # history instead of actually decomposing it fresh.
    question = "Who was born first: the founder of Microsoft, or the founder of Apple?"
    choices = ["(A) The founder of Microsoft", "(B) The founder of Apple"]

    answer, reasoning_sample = technique.generate(question, choices)
    print(f"\nFinal answer: {answer}")
