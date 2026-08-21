"""Lesson 4: assemble all agents before connecting AI or external tools."""

from typing import TypedDict


class AgentState(TypedDict, total=False):
    """Shared data produced and consumed by the workflow's agents."""

    issue: str
    code_context: str
    complexity: str
    research: str
    plan: str
    patch: str
    tests: str
    pr_url: str
    execution_log: list[str]


def code_reader(state: AgentState) -> AgentState:
    """Simulate finding code related to the issue."""
    state["code_context"] = f"Relevant module for: {state['issue']}"
    state["execution_log"].append("code_reader")
    return state


def classify_issue(state: AgentState) -> AgentState:
    """Classify issues with more than eight words as complex."""
    word_count = len(state["issue"].split())
    state["complexity"] = "complex" if word_count > 8 else "simple"
    state["execution_log"].append("classifier")
    return state


def researcher(state: AgentState) -> AgentState:
    """Simulate deeper repository research for a complex issue."""
    state["research"] = "Inspect dependencies and recent changes."
    state["execution_log"].append("researcher")
    return state


def planner(state: AgentState) -> AgentState:
    """Create a deterministic implementation plan."""
    if "research" in state:
        state["plan"] = "Update related modules, handle edge cases, and add tests."
    else:
        state["plan"] = "Update the relevant module and add one regression test."

    state["execution_log"].append("planner")
    return state


def code_writer(state: AgentState) -> AgentState:
    """Simulate a patch produced from the plan."""
    state["patch"] = f"Simulated code change based on plan: {state['plan']}"
    state["execution_log"].append("code_writer")
    return state


def test_writer(state: AgentState) -> AgentState:
    """Simulate a regression test for the proposed patch."""
    state["tests"] = f"Simulated test for patch: {state['patch']}"
    state["execution_log"].append("test_writer")
    return state


def pr_opener(state: AgentState) -> AgentState:
    """Return a fake PR URL; this lesson never contacts GitHub."""
    state["pr_url"] = "https://github.com/example/project/pull/123 (simulated)"
    state["execution_log"].append("pr_opener")
    return state


def run_workflow(issue: str) -> AgentState:
    """Run the complete deterministic workflow in dependency order."""
    state: AgentState = {"issue": issue, "execution_log": []}
    state = code_reader(state)
    state = classify_issue(state)

    if state["complexity"] == "complex":
        state = researcher(state)

    state = planner(state)
    state = code_writer(state)
    state = test_writer(state)
    state = pr_opener(state)
    return state


if __name__ == "__main__":
    result = run_workflow(
        "Users cannot complete checkout after changing currency when a discount code is active"
    )

    print("Execution order:")
    for agent_name in result["execution_log"]:
        print(f"- {agent_name}")

    print("\nFinal state:")
    print(result)
