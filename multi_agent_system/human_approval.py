"""Pause LangGraph so a person can approve or reject PR creation."""

from typing import Literal

from langgraph.types import interrupt

from multi_agent_system.langgraph_workflow import AgentState

MAX_FEEDBACK_CHARS = 2_000


def human_approval(state: AgentState) -> AgentState:
    """Interrupt execution and convert the resume value into state updates."""
    decision = interrupt(
        {
            "type": "pull_request_approval",
            "message": "Review the tested changes before creating a pull request.",
            "issue": state.get("issue_title", state["issue"]),
            "patch_summary": state["patch_summary"],
            "changed_files": state["changed_files"],
            "patch": state["patch"],
            "test_summary": state["test_summary"],
            "test_files": state["test_files"],
            "test_patch": state["test_patch"],
            "test_status": state["test_status"],
        }
    )

    if not isinstance(decision, dict):
        choice = "reject"
        feedback = "Invalid approval response."
    else:
        choice = str(decision.get("decision", "reject")).strip().lower()
        feedback = str(decision.get("feedback", ""))[:MAX_FEEDBACK_CHARS]

    approved = choice == "approve"
    return {
        "pull_request_approved": approved,
        "approval_status": "approved" if approved else "rejected",
        "approval_feedback": feedback,
        "execution_log": ["human_approval"],
    }


def route_after_approval(
    state: AgentState,
) -> Literal["branch_preparer", "end"]:
    """Prepare a branch only after an explicit human approval."""
    return "branch_preparer" if state["pull_request_approved"] else "end"
