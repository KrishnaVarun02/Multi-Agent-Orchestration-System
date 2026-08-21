"""Test the LLM workflow without spending money or calling an API."""

from pathlib import Path

from multi_agent_system.langgraph_workflow import AgentState
from multi_agent_system.llm_langgraph_workflow import build_llm_graph


def fake_planner(state: AgentState) -> AgentState:
    """Return the same shape as the real LLM Planner."""
    return {
        "plan": f"Fake plan for: {state['issue']}",
        "plan_steps": ["Change the code", "Add tests"],
        "plan_risks": ["Regression risk"],
        "execution_log": ["llm_planner"],
    }


def fake_code_reader(state: AgentState) -> AgentState:
    """Select and load one known file without calling an API."""
    from multi_agent_system.repository_reader import read_selected_files

    updates = read_selected_files(state, ["app.py"])
    return {
        **updates,
        "file_selection_reasoning": "app.py contains the example code",
        "execution_log": ["llm_code_reader"],
    }


def fake_code_writer(state: AgentState) -> AgentState:
    """Return a proposed patch without calling an API or changing a file."""
    return {
        "patch_summary": "Update the greeting",
        "changed_files": ["app.py"],
        "patch": "--- a/app.py\n+++ b/app.py\n@@ -1 +1 @@\n-print('hello')\n+print('hi')",
        "execution_log": ["llm_code_writer"],
    }


def fake_test_writer(state: AgentState) -> AgentState:
    """Return a test proposal without calling an API or writing a file."""
    test_patch = (
        "--- /dev/null\n+++ b/tests/test_app.py\n"
        "@@ -0,0 +1 @@\n+assert True"
    )
    return {
        "test_summary": "Test the greeting",
        "test_files": ["tests/test_app.py"],
        "test_patch": test_patch,
        "test_command": "python3 -m pytest",
        "tests": test_patch,
        "execution_log": ["llm_test_writer"],
    }


def fake_test_runner(state: AgentState) -> AgentState:
    """Pretend the sandbox tests passed."""
    return {
        "tests_passed": True,
        "test_status": "passed",
        "test_output": "1 passed",
        "execution_log": ["sandbox_test_runner"],
    }


def fake_human_approval(state: AgentState) -> AgentState:
    """Approve without interrupting this graph-integration test."""
    return {
        "pull_request_approved": True,
        "approval_status": "approved",
        "approval_feedback": "",
        "execution_log": ["human_approval"],
    }


def fake_branch_preparer(state: AgentState) -> AgentState:
    """Pretend an approved local branch and commit were created."""
    return {
        "branch_prepared": True,
        "branch_name": "agent/issue-manual-fix-login-button",
        "branch_status": "prepared",
        "commit_sha": "abc123",
        "execution_log": ["git_branch_preparer"],
    }


def test_llm_graph_accepts_fake_llm_nodes(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text("print('hello')", encoding="utf-8")
    graph = build_llm_graph(
        planner_node=fake_planner,
        code_reader_node=fake_code_reader,
        code_writer_node=fake_code_writer,
        test_writer_node=fake_test_writer,
        test_runner_node=fake_test_runner,
        approval_node=fake_human_approval,
        branch_preparer_node=fake_branch_preparer,
    )
    result = graph.invoke(
        {
            "issue": "Fix the login button",
            "repo_path": str(tmp_path),
            "execution_log": [],
        }
    )

    assert result["repository_files"] == ["app.py"]
    assert result["selected_files"] == ["app.py"]
    assert "print('hello')" in result["code_context"]
    assert result["plan_steps"] == ["Change the code", "Add tests"]
    assert result["plan_risks"] == ["Regression risk"]
    assert result["changed_files"] == ["app.py"]
    assert result["patch"].startswith("--- a/app.py")
    assert result["test_files"] == ["tests/test_app.py"]
    assert result["test_command"] == "python3 -m pytest"
    assert (tmp_path / "app.py").read_text(encoding="utf-8") == "print('hello')"
    assert not (tmp_path / "tests" / "test_app.py").exists()
    assert "llm_planner" in result["execution_log"]
    assert "llm_code_writer" in result["execution_log"]
    assert "llm_test_writer" in result["execution_log"]
    assert "sandbox_test_runner" in result["execution_log"]
    assert result["approval_status"] == "approved"
    assert result["branch_status"] == "prepared"
    assert result["tests_passed"] is True
    assert result["execution_log"][:2] == [
        "manual_issue_input",
        "repository_indexer",
    ]
    assert result["execution_log"][2] == "llm_code_reader"
    assert result["pr_url"].endswith("(simulated)")
