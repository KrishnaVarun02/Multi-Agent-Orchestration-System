"""OpenRouter-powered selection of issue-relevant repository files."""

from pydantic import BaseModel, ConfigDict, Field

from multi_agent_system.langgraph_workflow import AgentState
from multi_agent_system.openrouter_client import get_openrouter_client_and_model
from multi_agent_system.repository_reader import (
    MAX_SELECTED_FILES,
    read_selected_files,
)


class FileSelection(BaseModel):
    """The exact file-selection response required from the model."""

    model_config = ConfigDict(extra="forbid")

    files: list[str] = Field(
        description="Exact repository paths most relevant to the issue",
        max_length=MAX_SELECTED_FILES,
    )
    reasoning: str = Field(description="A concise reason for this selection")


def llm_code_reader(state: AgentState) -> AgentState:
    """Ask OpenRouter to choose files, then load only validated paths."""
    client, model = get_openrouter_client_and_model()
    repository_files = state["repository_files"]

    completion = client.chat.completions.create(
        model=model,
        max_tokens=800,
        messages=[
            {
                "role": "system",
                "content": (
                    "You select repository files for investigating a GitHub "
                    "issue. Return at most 8 exact paths from the supplied "
                    "list. Prefer implementation, tests, and relevant config."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Issue:\n{state['issue']}\n\n"
                    "Available repository files:\n"
                    + "\n".join(repository_files)
                ),
            },
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "file_selection",
                "strict": True,
                "schema": FileSelection.model_json_schema(),
            },
        },
        extra_body={"provider": {"require_parameters": True}},
    )

    content = completion.choices[0].message.content
    if not content:
        raise RuntimeError("OpenRouter did not return a file selection.")

    selection = FileSelection.model_validate_json(content)
    allowed_files = set(repository_files)
    validated_files = [
        path for path in selection.files if path in allowed_files
    ]
    if not validated_files:
        raise RuntimeError("OpenRouter did not select any valid repository files.")

    read_updates = read_selected_files(state, validated_files)
    return {
        **read_updates,
        "file_selection_reasoning": selection.reasoning,
        "execution_log": ["llm_code_reader"],
    }
