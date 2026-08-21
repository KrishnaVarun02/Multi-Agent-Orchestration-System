"""Tests for the repository's user-facing README documentation."""

from pathlib import Path


README = Path(__file__).parents[1] / "README.md"


def readme_text() -> str:
    """Return the repository README as plain text."""
    return README.read_text(encoding="utf-8")


def test_readme_is_a_practical_workflow_guide() -> None:
    content = readme_text()

    assert "# Multi-Agent Orchestration System" in content
    assert "## Prerequisites" in content
    assert "## Setup" in content
    assert "## Quick start" in content
    assert "## Testing" in content


def test_readme_documents_installation_and_configuration() -> None:
    content = readme_text()

    assert "python -m venv .venv" in content
    assert "python -m pip install -r requirements.txt" in content
    assert "environment variables" in content
    assert "credentials" in content
    assert "Docker" in content
    assert "tokens out of source control" in content


def test_readme_documents_both_command_line_entry_points() -> None:
    content = readme_text()

    assert "python -m multi_agent_system" in content
    assert "lessons/17_complete_workflow_cli.py" in content
    assert "https://github.com/OWNER/REPO/issues/1" in content
    assert "--repo-path" in content
    assert "--execute-tests" in content
    assert "--review" in content
    assert "--create-pr" in content


def test_readme_explains_workflow_modes_and_mutating_operations() -> None:
    content = readme_text()

    assert "deterministic workflow" in content
    assert "LangGraph workflow" in content
    assert "execution_log" in content
    assert "does not edit a repository or create a real pull request" in content
    assert "Do not use `--create-pr`" in content
    assert "human approval" in content


def test_readme_documents_tests_and_repository_layout() -> None:
    content = readme_text()

    assert "python -m pytest" in content
    assert "multi_agent_system/workflow.py" in content
    assert "multi_agent_system/llm_langgraph_workflow.py" in content
    assert "lessons/17_complete_workflow_cli.py" in content
    assert "tests/" in content
    assert "requirements.txt" in content
