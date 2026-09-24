"""
Run Dumper
==========
"Write the complete run transcript to markdown" mechanism, used by any
prompt-writing technique. Only handles accumulation, filename derivation,
and writing the file - the calling script still renders its own "full
prompt sent" text (e.g. history-list style), since that rendering is
call-shape-specific. Kept generic (parameterized by implementation title) so
another decomposition script could reuse it without modification.

The console prints only show the important parts (final output, extracted
subanswer, etc.) - this captures everything, including the full
preamble/few-shot content sent on every call, which the console never prints.
"""

import os
import re

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def _slug(text):
    return re.sub(r'[^A-Za-z0-9._-]', '_', text)


class RunDumper:
    """
    Collects already-rendered markdown sections (one per LLM call) and writes
    them to results_<implementation>_<model-name>[_<run-label>].md at the end
    of a run. No-ops entirely when not enabled, so call sites don't need to
    guard every call themselves.
    """
    def __init__(self, model_name, title, enabled=False, run_label=None):
        self.model_name = model_name
        self.title = title
        self.enabled = enabled
        self.run_label = run_label
        self._sections = []

    def record(self, section_title, full_prompt_markdown, response):
        """
        Prompt and response bodies are wrapped in <details> so a rendered
        dump (GitHub, VS Code preview, etc.) starts collapsed - a dump with
        dozens of calls is unreadable otherwise. The blank line right after
        <summary> is required for GFM to render markdown inside the block
        instead of treating it as opaque HTML.
        """
        if not self.enabled:
            return
        self._sections.append(
            f"## {section_title}\n\n"
            f"### Full prompt sent\n\n"
            f"<details>\n<summary>Expand full prompt</summary>\n\n{full_prompt_markdown}\n</details>\n\n"
            f"### Raw model response\n\n"
            f"<details>\n<summary>Expand raw response</summary>\n\n{response}\n</details>\n\n---\n"
        )

    def _results_md_path(self):
        """
        results_<implementation-slug>_<model-name>[_<run-label>].md, next to this
        script, with filesystem-unsafe chars swapped out. Keyed on the
        implementation and the model so runs of different techniques against the
        same model don't clobber each other's dump file - and optionally on a
        run_label (e.g. "q1", "q2") so multiple runs of the SAME implementation/model
        in one invocation (e.g. one file per question in a batch) don't either.

        Example: title="Factored Decomposition", model_name="llama3.2:latest",
        run_label="q1" -> "results_Factored_Decomposition_llama3.2_latest_q1.md"
        (the ":" in the model name becomes "_" via _slug; run_label is left out
        of the filename entirely when None).
        """
        parts = [_slug(self.title), _slug(self.model_name)]
        if self.run_label:
            parts.append(_slug(self.run_label))
        return os.path.join(SCRIPT_DIR, "results_" + "_".join(parts) + ".md")

    def write(self):
        """Writes the file and returns its path, or None if disabled/nothing recorded."""
        if not self.enabled:
            return None
        path = self._results_md_path()
        header = f"# {self.title} - Full Run Transcript ({self.model_name})"
        if self.run_label:
            header += f" [{self.run_label}]"
        with open(path, "w") as f:
            f.write(header + "\n\n")
            f.write("\n".join(self._sections))
        return path
