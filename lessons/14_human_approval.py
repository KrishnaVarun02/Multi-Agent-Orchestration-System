"""Lesson 14: pause and resume LangGraph for human approval."""

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from multi_agent_system.human_approval import human_approval
from multi_agent_system.langgraph_workflow import AgentState


def build_lesson_graph():
    """Build a one-node graph with in-memory checkpointing."""
    builder = StateGraph(AgentState)
    builder.add_node("human_approval", human_approval)
    builder.add_edge(START, "human_approval")
    builder.add_edge("human_approval", END)
    return builder.compile(checkpointer=InMemorySaver())


def main() -> None:
    """Pause, display the review payload, and resume from terminal input."""
    graph = build_lesson_graph()
    config = {"configurable": {"thread_id": "lesson-14-review"}}
    state: AgentState = {
        "issue": "Prevent division by zero",
        "patch_summary": "Raise ValueError when the denominator is zero",
        "changed_files": ["calculator.py"],
        "patch": "--- a/calculator.py\n+++ b/calculator.py\n...",
        "test_summary": "Add a zero-denominator regression test",
        "test_files": ["tests/test_calculator.py"],
        "test_patch": "--- /dev/null\n+++ b/tests/test_calculator.py\n...",
        "test_status": "passed",
        "execution_log": [],
    }

    paused = graph.invoke(state, config=config)
    review = paused["__interrupt__"][0].value
    print("Graph paused for review:\n")
    for key, value in review.items():
        print(f"{key}: {value}")

    answer = input("\nType approve or reject: ").strip().lower()
    feedback = input("Optional feedback: ").strip()
    result = graph.invoke(
        Command(resume={"decision": answer, "feedback": feedback}),
        config=config,
    )

    print(f"\nApproval status: {result['approval_status']}")
    print(f"Approved: {result['pull_request_approved']}")


if __name__ == "__main__":
    main()
