"""OpenRouter-powered Code Writer that proposes, but does not apply, a patch."""

from pydantic import BaseModel, ConfigDict, Field

from multi_agent_system.langgraph_workflow import AgentState
from multi_agent_system.openrouter_client import get_openrouter_client_and_model
from multi_agent_system.repository_reader import MAX_SELECTED_FILES


class PatchOutput(BaseModel):
    """The exact patch structure required from the model."""

    model_config = ConfigDict(extra="forbid")

    summary: str = Field(description="A concise summary of the proposed change")
    changed_files: list[str] = Field(
        description="Exact selected repository paths changed by the patch",
        max_length=MAX_SELECTED_FILES,
    )
    unified_diff: str = Field(
        description="A unified diff without Markdown code fences"
    )


def llm_code_writer(state: AgentState) -> AgentState:
    """Generate a validated patch proposal without changing files on disk."""
    client, model = get_openrouter_client_and_model()
    selected_files = state["selected_files"]

    completion = client.chat.completions.create(
        model=model,
        max_tokens=2500,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a careful software engineer. Create a minimal "
                    "unified diff that follows the plan. Change only paths in "
                    "the supplied selected-files list. Do not use Markdown "
                    "code fences and do not invent file contents you cannot see."
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
        ],
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
    if not content:
        raise RuntimeError("OpenRouter did not return a patch proposal.")

    proposal = PatchOutput.model_validate_json(content)
    allowed_files = set(selected_files)
    invalid_files = [
        path for path in proposal.changed_files if path not in allowed_files
    ]
    if invalid_files:
        raise RuntimeError(
            "OpenRouter proposed changes to unapproved files: "
            + ", ".join(invalid_files)
        )

    if not proposal.changed_files or not proposal.unified_diff.strip():
        raise RuntimeError("OpenRouter returned an empty patch proposal.")

    return {
        "patch_summary": proposal.summary,
        "changed_files": proposal.changed_files,
        "patch": proposal.unified_diff,
        "execution_log": ["llm_code_writer"],
    }
