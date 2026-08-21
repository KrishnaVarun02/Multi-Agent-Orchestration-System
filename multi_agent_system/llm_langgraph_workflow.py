"""LangGraph workflow whose LLM nodes can be replaced for testing."""

from collections.abc import Callable
import uuid

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from multi_agent_system.docker_runner import run_patch_in_docker
from multi_agent_system.git_branch_preparer import (
    prepare_local_branch,
    route_after_branch,
)
from multi_agent_system.github_issue_reader import load_issue_input
from multi_agent_system.github_pr_opener import open_github_pull_request
from multi_agent_system.human_approval import human_approval, route_after_approval
from multi_agent_system.langgraph_workflow import (
    AgentState,
    classifier,
    researcher,
    route_by_complexity,
)
from multi_agent_system.llm_code_reader import llm_code_reader
from multi_agent_system.llm_code_writer import llm_code_writer, route_after_code_writer
from multi_agent_system.llm_planner import llm_planner
from multi_agent_system.llm_test_writer import llm_test_writer
from multi_agent_system.repository_reader import index_repository
from multi_agent_system.sandbox_runner import route_after_tests

PlannerNode = Callable[[AgentState], AgentState]
CodeReaderNode = Callable[[AgentState], AgentState]
CodeWriterNode = Callable[[AgentState], AgentState]
TestWriterNode = Callable[[AgentState], AgentState]
TestRunnerNode = Callable[[AgentState], AgentState]
IssueReaderNode = Callable[[AgentState], AgentState]
ApprovalNode = Callable[[AgentState], AgentState]
BranchPreparerNode = Callable[[AgentState], AgentState]
PrOpenerNode = Callable[[AgentState], AgentState]


def build_llm_graph(
    planner_node: PlannerNode = llm_planner,
    code_reader_node: CodeReaderNode = llm_code_reader,
    code_writer_node: CodeWriterNode = llm_code_writer,
    test_writer_node: TestWriterNode = llm_test_writer,
    test_runner_node: TestRunnerNode = run_patch_in_docker,
    issue_reader_node: IssueReaderNode = load_issue_input,
    approval_node: ApprovalNode = human_approval,
    branch_preparer_node: BranchPreparerNode = prepare_local_branch,
    pr_opener_node: PrOpenerNode = open_github_pull_request,
    checkpointer=None,
):
    """Build a graph whose LLM nodes can be replaced during tests."""
    builder = StateGraph(AgentState)

    builder.add_node("issue_reader", issue_reader_node)
    builder.add_node("repository_indexer", index_repository)
    builder.add_node("code_reader", code_reader_node)
    builder.add_node("classifier", classifier)
    builder.add_node("researcher", researcher)
    builder.add_node("planner", planner_node)
    builder.add_node("code_writer", code_writer_node)
    builder.add_node("test_writer", test_writer_node)
    builder.add_node("test_runner", test_runner_node)
    builder.add_node("human_approval", approval_node)
    builder.add_node("branch_preparer", branch_preparer_node)
    builder.add_node("pr_opener", pr_opener_node)

    builder.add_edge(START, "issue_reader")
    builder.add_edge("issue_reader", "repository_indexer")
    builder.add_edge("repository_indexer", "code_reader")
    builder.add_edge("code_reader", "classifier")
    builder.add_conditional_edges(
        "classifier",
        route_by_complexity,
        {"researcher": "researcher", "planner": "planner"},
    )
    builder.add_edge("researcher", "planner")
    builder.add_edge("planner", "code_writer")
    builder.add_conditional_edges(
        "code_writer",
        route_after_code_writer,
        {"test_writer": "test_writer", "end": END},
    )
    builder.add_edge("test_writer", "test_runner")
    builder.add_conditional_edges(
        "test_runner",
        route_after_tests,
        {"human_approval": "human_approval", "end": END},
    )
    builder.add_conditional_edges(
        "human_approval",
        route_after_approval,
        {
            "branch_preparer": "branch_preparer",
            "revise": "code_writer",
            "end": END,
        },
    )
    builder.add_conditional_edges(
        "branch_preparer",
        route_after_branch,
        {"pr_opener": "pr_opener", "end": END},
    )
    builder.add_edge("pr_opener", END)

    return builder.compile(checkpointer=checkpointer)


graph = build_llm_graph(checkpointer=InMemorySaver())


def run_llm_workflow(
    issue: str,
    repo_path: str = ".",
    execute_tests: bool = False,
    thread_id: str | None = None,
) -> AgentState:
    """Run the graph with the real OpenRouter-powered nodes."""
    workflow_thread_id = thread_id or uuid.uuid4().hex
    return graph.invoke(
        {
            "issue": issue,
            "repo_path": repo_path,
            "execute_tests": execute_tests,
            "workflow_thread_id": workflow_thread_id,
            "execution_log": [],
        },
        config={"configurable": {"thread_id": workflow_thread_id}},
    )


def run_github_issue_workflow(
    issue_url: str,
    repo_path: str = ".",
    execute_tests: bool = False,
    thread_id: str | None = None,
) -> AgentState:
    """Run the complete graph starting from a GitHub issue URL."""
    workflow_thread_id = thread_id or uuid.uuid4().hex
    return graph.invoke(
        {
            "issue_url": issue_url,
            "repo_path": repo_path,
            "execute_tests": execute_tests,
            "workflow_thread_id": workflow_thread_id,
            "execution_log": [],
        },
        config={"configurable": {"thread_id": workflow_thread_id}},
    )


def resume_workflow(
    thread_id: str, decision: str, feedback: str = ""
) -> AgentState:
    """Resume a paused workflow using the same checkpoint thread ID."""
    return graph.invoke(
        Command(resume={"decision": decision, "feedback": feedback}),
        config={"configurable": {"thread_id": thread_id}},
    )


def main() -> None:
    """Run the compiled LLM graph from the command line."""
    issue = (
        "Users cannot complete checkout after changing currency "
        "when a discount is active"
    )
    result = run_llm_workflow(issue, repo_path=".")

    print("Execution order:")
    for agent_name in result["execution_log"]:
        print(f"- {agent_name}")

    print("\nLLM-selected files:")
    for file_path in result["selected_files"]:
        print(f"- {file_path}")

    print("\nWhy these files were selected:")
    print(result["file_selection_reasoning"])

    print("\nLLM-generated plan:")
    print(result["plan"])

    print("\nSteps:")
    for number, step in enumerate(result["plan_steps"], start=1):
        print(f"{number}. {step}")

    print("\nRisks:")
    for risk in result["plan_risks"]:
        print(f"- {risk}")

    print("\nLLM-generated patch summary:")
    print(result["patch_summary"])

    print("\nProposed patch (not applied):")
    print(result["patch"])

    print("\nLLM-generated test summary:")
    print(result["test_summary"])

    print("\nProposed test patch (not applied):")
    print(result["test_patch"])

    print("\nSuggested test command (not executed):")
    print(result["test_command"])

    print("\nSandbox status:")
    print(result["test_status"])
    print(result["test_output"])

    if result.get("pr_url"):
        print("\nPull request URL:")
        print(result["pr_url"])
    else:
        print("\nPR creation status:")
        print(result.get("pr_status", "not reached"))


if __name__ == "__main__":
    main()
