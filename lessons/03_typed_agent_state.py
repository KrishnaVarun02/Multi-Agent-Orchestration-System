"""Lesson 3: describe the shared workflow state with TypedDict."""

from typing import TypedDict


class AgentState(TypedDict, total=False):
    """Values that agents can read from or add to the workflow."""

    issue: str
    code_context: str
    complexity: str
    research: str
    plan: str


def code_reader(state: AgentState) -> AgentState:
    """Add simulated codebase context for the issue."""
    issue = state["issue"]
    state["code_context"] = f"Likely files related to: {issue}"
    return state


def classify_issue(state: AgentState) -> AgentState:
    """Classify the issue using its word count."""
    word_count = len(state["issue"].split())

    if word_count <= 8:
        state["complexity"] = "simple"
    else:
        state["complexity"] = "complex"

    return state


def route_by_complexity(state: AgentState) -> str:
    """Choose whether the Researcher is needed before planning."""
    if state["complexity"] == "complex":
        return "researcher"

    return "planner"


def researcher(state: AgentState) -> AgentState:
    """Add extra investigation for complex issues."""
    state["research"] = "Inspect related modules and recent code changes."
    return state


def planner(state: AgentState) -> AgentState:
    """Create a plan from the context collected by earlier agents."""
    if "research" in state:
        state["plan"] = "Use the research, update related modules, and add tests."
    else:
        state["plan"] = "Update the affected code and add one regression test."

    return state


def run_workflow(issue: str) -> AgentState:
    """Run the agents in order, including the conditional branch."""
    state: AgentState = {"issue": issue}
    state = code_reader(state)
    state = classify_issue(state)
    next_agent = route_by_complexity(state)

    if next_agent == "researcher":
        state = researcher(state)

    state = planner(state)
    return state


if __name__ == "__main__":
    result = run_workflow(
        "Users cannot complete checkout after changing currency when a discount code is active"
    )
    print(result)
