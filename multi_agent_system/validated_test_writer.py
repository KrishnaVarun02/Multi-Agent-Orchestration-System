"""OpenRouter Test Writer with deterministic Python and diff validation."""

import ast
from difflib import unified_diff
from pathlib import Path, PurePosixPath
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from multi_agent_system.langgraph_workflow import AgentState
from multi_agent_system.openrouter_client import get_openrouter_client_and_model
from multi_agent_system.repository_reader import MAX_SELECTED_FILES

MAX_TEST_ATTEMPTS = 2
MAX_TEST_CHARS = 6_000
MAX_TEST_LINES = 120


class TestFileProposal(BaseModel):
    """One new pytest file proposed by the model."""

    model_config = ConfigDict(extra="forbid")

    path: str = Field(description="Safe relative path for a new pytest file")
    content: str = Field(
        description="Complete syntactically valid Python test-file content",
        min_length=1,
        max_length=MAX_TEST_CHARS,
    )


class TestOutput(BaseModel):
    """The exact structured test proposal required from the model."""

    model_config = ConfigDict(extra="forbid")

    summary: str = Field(description="A concise summary of the proposed tests")
    files: list[TestFileProposal] = Field(
        description="New focused pytest files",
        min_length=1,
        max_length=MAX_SELECTED_FILES,
    )
    suggested_command: str = Field(description="A suggested pytest command")


def is_safe_test_path(path: str) -> bool:
    """Accept only relative Python test paths without traversal."""
    candidate = PurePosixPath(path)
    if not path or "\\" in path or candidate.is_absolute():
        return False
    if ".." in candidate.parts or candidate.suffix != ".py":
        return False
    return "tests" in candidate.parts or candidate.name.startswith("test_")


def _test_messages(
    state: AgentState, retry: bool, failure_reason: str
) -> list[dict[str, str]]:
    """Build the test prompt and include safe feedback on retry."""
    retry_instruction = ""
    if retry:
        retry_instruction = (
            " Your previous response failed validation. Return a smaller, "
            f"corrected test. Validation feedback: {failure_reason}"
        )

    return [
        {
            "role": "system",
            "content": (
                "You are a Python test engineer. Return complete content for "
                "new focused pytest files. Python will generate the diff. "
                "Every function name must be a valid Python identifier and "
                "pytest test functions must start with test_. Keep each file "
                "under 120 lines. Do not return diff syntax or Markdown fences."
                + retry_instruction
            ),
        },
        {
            "role": "user",
            "content": (
                f"Issue:\n{state['issue']}\n\n"
                f"Code context:\n{state['code_context']}\n\n"
                f"Implementation plan:\n{state['plan']}\n\n"
                f"Proposed code patch:\n{state['patch']}\n\n"
                "Known repository files:\n"
                + "\n".join(state.get("repository_files", []))
            ),
        },
    ]


def _build_test_patch(
    content: str, state: AgentState
) -> tuple[TestOutput, list[str], str]:
    """Validate test files with Python's parser and generate their diff."""
    proposal = TestOutput.model_validate_json(content)
    repository = Path(state["repo_path"]).resolve()
    test_paths: list[str] = []
    diff_sections: list[str] = []

    for test_file in proposal.files:
        if not is_safe_test_path(test_file.path):
            raise ValueError("A proposed test path is unsafe.")
        if test_file.path in test_paths:
            raise ValueError("A test path was proposed more than once.")
        if len(test_file.content.splitlines()) > MAX_TEST_LINES:
            raise ValueError("A proposed test file exceeds 120 lines.")
        if (repository / test_file.path).exists():
            raise ValueError("Test Writer may not overwrite an existing file.")

        try:
            tree = ast.parse(test_file.content, filename=test_file.path)
        except SyntaxError as error:
            raise ValueError(
                f"Python syntax is invalid near line {error.lineno}."
            ) from error
        if not any(
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name.startswith("test_")
            for node in ast.walk(tree)
        ):
            raise ValueError("A proposed file contains no pytest test function.")

        normalized_content = test_file.content.rstrip() + "\n"
        diff_sections.append(
            "".join(
                unified_diff(
                    [],
                    normalized_content.splitlines(keepends=True),
                    fromfile="/dev/null",
                    tofile=f"b/{test_file.path}",
                )
            )
        )
        test_paths.append(test_file.path)

    return proposal, test_paths, "".join(diff_sections)


def validated_test_writer(state: AgentState) -> AgentState:
    """Generate validated pytest files without writing or running them."""
    client, model = get_openrouter_client_and_model()
    last_failure = "No valid structured test was returned."

    for attempt in range(MAX_TEST_ATTEMPTS):
        completion = client.chat.completions.create(
            model=model,
            max_tokens=3_500,
            messages=_test_messages(state, attempt > 0, last_failure),
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "test_proposal",
                    "strict": True,
                    "schema": TestOutput.model_json_schema(),
                },
            },
            extra_body={"provider": {"require_parameters": True}},
        )
        content = completion.choices[0].message.content

        try:
            if not content:
                raise ValueError("The model returned no content.")
            proposal, test_files, test_patch = _build_test_patch(content, state)
        except ValidationError:
            last_failure = "The response was incomplete or did not match the schema."
            continue
        except ValueError as error:
            last_failure = str(error)
            continue

        return {
            "test_summary": proposal.summary,
            "test_files": test_files,
            "test_patch": test_patch,
            "test_command": proposal.suggested_command,
            "tests": test_patch,
            "test_generation_status": "generated",
            "test_generation_error": "",
            "execution_log": ["llm_test_writer"],
        }

    return {
        "test_summary": "Test generation failed.",
        "test_files": [],
        "test_patch": "",
        "test_command": "",
        "tests": "",
        "test_generation_status": "failed",
        "test_generation_error": (
            "OpenRouter did not produce valid tests after two attempts. "
            f"Last validation result: {last_failure}"
        ),
        "execution_log": ["llm_test_writer"],
    }


def route_after_test_writer(
    state: AgentState,
) -> Literal["test_runner", "end"]:
    """Run Docker only when syntactically valid tests were generated."""
    if state.get("test_generation_status") == "failed":
        return "end"
    return "test_runner" if state.get("test_patch") else "end"
