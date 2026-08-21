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


class FileEdit(BaseModel):
    """One exact search-and-replace operation proposed by the model."""

    model_config = ConfigDict(extra="forbid")

    path: str = Field(description="Exact path from the selected-files list")
    old_text: str = Field(
        min_length=1,
        description="Exact existing text copied from the supplied code context",
    )
    new_text: str = Field(
        description="Concise replacement text",
        max_length=MAX_REPLACEMENT_CHARS,
    )


class PatchOutput(BaseModel):
    """The structured edits required from the model."""

    model_config = ConfigDict(extra="forbid")

    summary: str = Field(description="A concise summary of the proposed change")
    edits: list[FileEdit] = Field(
        description="Small exact search-and-replace edits",
        min_length=1,
        max_length=MAX_SELECTED_FILES,
    )


def _patch_messages(
    state: AgentState, retry: bool, failure_reason: str = ""
) -> list[dict[str, str]]:
    """Build the prompt, making a retry explicitly shorter."""
    selected_files = state["selected_files"]
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
                "You are a careful software engineer. Return small exact "
                "search-and-replace edits that follow the plan. Each old_text "
                "must be copied exactly from the supplied code context and "
                "must identify one unique location. Change only paths in the "
                "selected-files list. Keep replacement text under 40 lines "
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
                f"Code context:\n{state['code_context']}\n\n"
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
    updated: dict[str, str] = {}

    for edit in proposal.edits:
        if edit.path not in allowed_files:
            raise ValueError("An edit targets a file outside the selection.")
        if snippets.get(edit.path, "").count(edit.old_text) != 1:
            raise ValueError("old_text must appear exactly once in supplied context.")
        if edit.old_text == edit.new_text:
            raise ValueError("An edit does not change anything.")

        if edit.path not in originals:
            path = (repository / edit.path).resolve()
            if repository not in path.parents:
                raise ValueError("An edit path escapes the repository.")
            originals[edit.path] = path.read_text(encoding="utf-8")
            updated[edit.path] = originals[edit.path]

        if updated[edit.path].count(edit.old_text) != 1:
            raise ValueError("old_text must identify one current file location.")
        updated[edit.path] = updated[edit.path].replace(
            edit.old_text, edit.new_text, 1
        )

    changed_files = list(originals)
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
                len(edit.new_text) > MAX_REPLACEMENT_CHARS
                or len(edit.new_text.splitlines()) > 40
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
