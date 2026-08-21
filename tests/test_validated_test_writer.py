"""Tests for deterministic Test Writer validation."""

import json
from types import SimpleNamespace

from multi_agent_system import validated_test_writer as writer_module


class FakeCompletions:
    def __init__(self, contents: list[str]):
        self.contents = contents
        self.calls = 0
        self.requests: list[dict] = []

    def create(self, **kwargs):
        self.requests.append(kwargs)
        content = self.contents[self.calls]
        self.calls += 1
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
        )


def test_writer_retries_invalid_python_syntax(monkeypatch, tmp_path) -> None:
    invalid = json.dumps(
        {
            "summary": "Broken test",
            "files": [
                {
                    "path": "tests/test_readme.py",
                    "content": "def test invalid():\n    assert True\n",
                }
            ],
            "suggested_command": "python3 -m pytest",
        }
    )
    valid = json.dumps(
        {
            "summary": "Valid test",
            "files": [
                {
                    "path": "tests/test_readme.py",
                    "content": "def test_readme():\n    assert True\n",
                }
            ],
            "suggested_command": "python3 -m pytest",
        }
    )
    completions = FakeCompletions([invalid, valid])
    client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    monkeypatch.setattr(
        writer_module,
        "get_openrouter_client_and_model",
        lambda: (client, "test-model"),
    )
    state = {
        "issue": "Document setup",
        "repo_path": str(tmp_path),
        "code_context": "# Project",
        "plan": "Add setup documentation.",
        "patch": "--- a/README.md\n+++ b/README.md\n",
        "repository_files": ["README.md"],
    }

    result = writer_module.validated_test_writer(state)

    assert completions.calls == 2
    assert result["test_generation_status"] == "generated"
    assert "def test_readme" in result["test_patch"]
    retry_prompt = completions.requests[1]["messages"][0]["content"]
    assert "syntax is invalid" in retry_prompt
