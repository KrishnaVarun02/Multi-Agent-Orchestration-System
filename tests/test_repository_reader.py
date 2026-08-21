"""Tests for safe, bounded local repository reading."""

from pathlib import Path

from multi_agent_system.repository_reader import (
    index_repository,
    read_repository,
    read_selected_files,
)


def test_reader_includes_source_and_ignores_secrets(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text("print('hello')", encoding="utf-8")
    (tmp_path / "README.md").write_text("# Example", encoding="utf-8")
    (tmp_path / ".env").write_text("SECRET=do-not-read", encoding="utf-8")

    virtual_environment = tmp_path / ".venv"
    virtual_environment.mkdir()
    (virtual_environment / "ignored.py").write_text("secret", encoding="utf-8")
    (tmp_path / "tempCodeRunnerFile.py").write_text(
        "incomplete scratch code", encoding="utf-8"
    )

    result = read_repository(
        {
            "issue": "Inspect the example",
            "repo_path": str(tmp_path),
            "execution_log": [],
        }
    )

    assert result["repository_files"] == ["README.md", "app.py"]
    assert "print('hello')" in result["code_context"]
    assert "do-not-read" not in result["code_context"]
    assert "ignored.py" not in result["code_context"]
    assert "tempCodeRunnerFile.py" not in result["repository_files"]


def test_loader_reads_only_valid_indexed_paths(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text("SAFE_CONTENT", encoding="utf-8")
    (tmp_path / ".env").write_text("SECRET_CONTENT", encoding="utf-8")

    state = {
        "issue": "Inspect app.py",
        "repo_path": str(tmp_path),
        "execution_log": [],
    }
    indexed = index_repository(state)
    updates = read_selected_files(
        {**state, **indexed}, ["../outside.py", ".env", "app.py"]
    )

    assert indexed["repository_files"] == ["app.py"]
    assert updates["selected_files"] == ["app.py"]
    assert "SAFE_CONTENT" in updates["code_context"]
    assert "SECRET_CONTENT" not in updates["code_context"]
