"""OpenRouter-powered Code Writer that proposes, but does not apply, a patch."""

from difflib import unified_diff
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from multi_agent_system.langgraph_workflow import AgentState
from multi_agent_system.openrouter_client import get_openrouter_client_and_model
from multi_agent_system.repository_reader import MAX_SELECTED_FILES

MAX_PATCH_ATTEMPTS = 2
MAX_PATCH_OUTPUT_TOKENS = 4_500
MAX_REPLACEMENT_CHARS = 4_000
MAX_REPLACEMENT_LINES = 80


class FileEdit(BaseModel):
    """One bounded line-range replacement proposed by the model."""

    model_config = ConfigDict(extra="forbid")

    path: str = Field(description="Exact path from the selected-files list")
    start_line: int = Field(ge=1, description="First numbered line to replace")
    end_line: int = Field(ge=1, description="Last numbered line to replace")
    replacement: str = Field(
        description="Concise replacement text",
        min_length=1,
        max_length=MAX_REPLACEMENT_CHARS,
    )


class PatchOutput(BaseModel):
    """The structured edits required from the model."""

    model_config = ConfigDict(extra="forbid")

    summary: str = Field(description="A concise summary of the proposed change")
    edits: list[FileEdit] = Field(
        description="Small bounded line-range replacements",
        min_length=1,
        max_length=MAX_SELECTED_FILES,
    )


def _patch_messages(
    state: AgentState, retry: bool, failure_reason: str = ""
) -> list[dict[str, str]]:
    """Build the prompt, making a retry explicitly shorter."""
    selected_files = state["selected_files"]
    context_sections: list[str] = []
    for path in selected_files:
        snippet = state["selected_file_contents"].get(path, "")
        numbered_lines = "\n".join(
            f"{number}: {line}"
            for number, line in enumerate(snippet.splitlines(), start=1)
        )
        context_sections.append(f"### {path}\n{numbered_lines}")
    numbered_context = "\n\n".join(context_sections)
    retry_instruction = ""
    if retry:
        retry_instruction = (
            " Your previous response was incomplete or invalid. Return a much "
            "smaller edit and ensure the JSON object is fully closed. "
            f"Validation feedback: {failure_reason}"
        )

    human_feedback = state.get("approval_feedback", "")
    revision_instruction = ""
    if human_feedback:
        revision_instruction = (
            " This is a revision. Follow the human review feedback exactly: "
            + human_feedback
        )

    return [
        {
            "role": "system",
            "content": (
                "You are a careful software engineer. Return small line-range "
                "replacements that follow the plan. start_line and end_line "
                "are inclusive and must refer to the numbered context. Change "
                "only paths in the "
                "selected-files list. Keep replacement text under 80 lines "
                "and 4000 characters. Prefer concise documentation. Python "
                "will generate the unified diff, so do not return diff syntax."
                + revision_instruction
                + retry_instruction
            ),
        },
        {
            "role": "user",
            "content": (
                f"Issue:\n{state['issue']}\n\n"
                f"Selected files:\n{chr(10).join(selected_files)}\n\n"
                f"Numbered code context:\n{numbered_context}\n\n"
                f"Plan summary:\n{state['plan']}\n\n"
                "Plan steps:\n- "
                + "\n- ".join(state.get("plan_steps", []))
                + "\n\nRisks:\n- "
                + "\n- ".join(state.get("plan_risks", []))
            ),
        },
    ]


def _build_patch(
    content: str, state: AgentState
) -> tuple[PatchOutput, list[str], str]:
    """Validate model edits and deterministically create a unified diff."""
    proposal = PatchOutput.model_validate_json(content)
    allowed_files = set(state["selected_files"])
    snippets = state["selected_file_contents"]
    repository = Path(state["repo_path"]).resolve()
    originals: dict[str, str] = {}
    edits_by_path: dict[str, list[FileEdit]] = {}

    for edit in proposal.edits:
        if edit.path not in allowed_files:
            raise ValueError("An edit targets a file outside the selection.")
        snippet_lines = snippets.get(edit.path, "").splitlines(keepends=True)
        if edit.start_line > edit.end_line:
            raise ValueError("start_line must not be after end_line.")
        if edit.end_line > len(snippet_lines):
            raise ValueError("An edit range exceeds the supplied context.")
        edits_by_path.setdefault(edit.path, []).append(edit)

    updated: dict[str, str] = {}
    for relative_path, file_edits in edits_by_path.items():
        path = (repository / relative_path).resolve()
        if repository not in path.parents:
            raise ValueError("An edit path escapes the repository.")
        original = path.read_text(encoding="utf-8")
        snippet = snippets[relative_path]
        if not original.startswith(snippet):
            raise ValueError("The selected context no longer matches the file.")

        ordered_edits = sorted(
            file_edits, key=lambda item: item.start_line, reverse=True
        )
        for earlier, later in zip(ordered_edits, ordered_edits[1:]):
            if later.end_line >= earlier.start_line:
                raise ValueError("Proposed line ranges overlap.")

        updated_lines = original.splitlines(keepends=True)
        for edit in ordered_edits:
            replacement = edit.replacement.rstrip() + "\n"
            updated_lines[edit.start_line - 1 : edit.end_line] = (
                replacement.splitlines(keepends=True)
            )
        originals[relative_path] = original
        updated[relative_path] = "".join(updated_lines)

    changed_files = list(edits_by_path)
    diff_sections: list[str] = []
    for path in changed_files:
        if originals[path] == updated[path]:
            raise ValueError("The proposed edits produced no file change.")
        diff_sections.append(
            "".join(
                unified_diff(
                    originals[path].splitlines(keepends=True),
                    updated[path].splitlines(keepends=True),
                    fromfile=f"a/{path}",
                    tofile=f"b/{path}",
                )
            )
        )

    generated_diff = "".join(diff_sections)
    if not generated_diff:
        raise ValueError("The proposed edits produced no patch.")
    return proposal, changed_files, generated_diff


def llm_code_writer(state: AgentState) -> AgentState:
    """Generate a validated patch proposal without changing files on disk."""
    client, model = get_openrouter_client_and_model()
    selected_files = state["selected_files"]
    last_failure = "No valid structured edit was returned."

    for attempt in range(MAX_PATCH_ATTEMPTS):
        completion = client.chat.completions.create(
            model=model,
            max_tokens=MAX_PATCH_OUTPUT_TOKENS,
            messages=_patch_messages(
                state, retry=attempt > 0, failure_reason=last_failure
            ),
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "patch_proposal",
                    "strict": True,
                    "schema": PatchOutput.model_json_schema(),
                },
            },
            extra_body={"provider": {"require_parameters": True}},
        )

        content = completion.choices[0].message.content
        try:
            if not content:
                raise ValueError("The model returned no content.")
            proposal, changed_files, generated_diff = _build_patch(content, state)
            if any(
                len(edit.replacement) > MAX_REPLACEMENT_CHARS
                or len(edit.replacement.splitlines()) > MAX_REPLACEMENT_LINES
                for edit in proposal.edits
            ):
                raise ValueError("Replacement text exceeds the concise edit limit.")
        except ValidationError:
            last_failure = "The response was incomplete or did not match the schema."
            continue
        except (OSError, UnicodeError):
            last_failure = "A selected file could not be read as text."
            continue
        except ValueError as error:
            last_failure = str(error)
            continue

        return {
            "patch_summary": proposal.summary,
            "changed_files": changed_files,
            "patch": generated_diff,
            "code_generation_status": "generated",
            "code_generation_error": "",
            "execution_log": ["llm_code_writer"],
        }

    return {
        "patch_summary": "Code generation failed.",
        "changed_files": [],
        "patch": "",
        "code_generation_status": "failed",
        "code_generation_error": (
            "OpenRouter did not produce a valid edit after two attempts. "
            f"Last validation result: {last_failure}"
        ),
        "execution_log": ["llm_code_writer"],
    }


def route_after_code_writer(
    state: AgentState,
) -> Literal["test_writer", "end"]:
    """Stop cleanly when no validated code patch was generated."""
    if state.get("code_generation_status") == "failed":
        return "end"
    return "test_writer" if state.get("patch") else "end"
