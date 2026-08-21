"""Lesson 1: specialized functions share one workflow state."""


def code_reader(state: dict) -> dict:
    """A tiny agent that adds codebase findings to the shared state."""
    issue = state["issue"]
    state["code_context"] = f"Likely files related to: {issue}"
    return state


def planner(state: dict) -> dict:
    """A tiny agent that adds a proposed implementation plan."""
    state["plan"] = "1. Update the code. 2. Add a regression test."
    return state


def run_workflow(issue: str) -> dict:
    """The orchestrator: it decides the current order of agents."""
    state = {"issue": issue}
    state = code_reader(state)
    state = planner(state)
    return state


if __name__ == "__main__":
    result = run_workflow("Login fails when an email contains uppercase letters")
    print(result)
