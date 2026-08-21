"""Test Code Writer retries without making real OpenRouter requests."""

import json
from types import SimpleNamespace

from multi_agent_system import llm_code_writer as writer_module


class FakeCompletions:
    """Return predefined model messages and count requests."""

    def __init__(self, contents: list[str]):
        self.contents = contents
        self.calls = 0
        self.requests: list[dict] = []

    def create(self, **kwargs):
        self.requests.append(kwargs)
        content = self.contents[self.calls]
        self.calls += 1
        message = SimpleNamespace(content=content)
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def writer_state() -> dict:
    """Return the minimum shared state needed by the Code Writer."""
    return {
        "issue": "Update the greeting",
        "repo_path": "",
        "selected_files": ["app.py"],
        "selected_file_contents": {"app.py": "print('hello')\n"},
        "code_context": "### app.py\nprint('hello')",
        "plan": "Change hello to hi.",
        "plan_steps": ["Edit app.py"],
        "plan_risks": ["Output regression"],
    }


def valid_patch_json() -> str:
    """Return a complete structured response."""
    return json.dumps(
        {
            "summary": "Update greeting",
            "edits": [
                {
                    "path": "app.py",
                    "old_text": "print('hello')",
                    "new_text": "print('hi')",
                }
            ],
        }
    )


def test_code_writer_retries_truncated_json(monkeypatch, tmp_path) -> None:
    completions = FakeCompletions(['{"summary":"cut off', valid_patch_json()])
    client = SimpleNamespace(
        chat=SimpleNamespace(completions=completions)
    )
    monkeypatch.setattr(
        writer_module,
        "get_openrouter_client_and_model",
        lambda: (client, "test-model"),
    )

    (tmp_path / "app.py").write_text("print('hello')\n", encoding="utf-8")
    state = writer_state()
    state["repo_path"] = str(tmp_path)
    result = writer_module.llm_code_writer(state)

    assert completions.calls == 2
    assert result["code_generation_status"] == "generated"
    assert result["changed_files"] == ["app.py"]
    retry_prompt = completions.requests[1]["messages"][0]["content"]
    assert "did not match the schema" in retry_prompt


def test_code_writer_stops_cleanly_after_two_invalid_responses(
    monkeypatch, tmp_path
) -> None:
    completions = FakeCompletions(["not json", "still not json"])
    client = SimpleNamespace(
        chat=SimpleNamespace(completions=completions)
    )
    monkeypatch.setattr(
        writer_module,
        "get_openrouter_client_and_model",
        lambda: (client, "test-model"),
    )

    (tmp_path / "app.py").write_text("print('hello')\n", encoding="utf-8")
    state = writer_state()
    state["repo_path"] = str(tmp_path)
    result = writer_module.llm_code_writer(state)

    assert completions.calls == 2
    assert result["code_generation_status"] == "failed"
    assert result["patch"] == ""
    assert writer_module.route_after_code_writer(result) == "end"
