"""Lesson 2: route issues through different agents using conditions."""


def classify_issue(state: dict) -> dict:
    """Classify an issue using a small, predictable rule."""
    issue = state["issue"]
    word_count = len(issue.split())

    if word_count <= 8:
        state["complexity"] = "simple"
    else:
        state["complexity"] = "complex"

    return state


def route_by_complexity(state: dict) -> str:
    """Return the name of the agent that should run next."""
    if state["complexity"] == "complex":
        return "researcher"

    return "planner"


def researcher(state: dict) -> dict:
    """Add extra investigation for a complex issue."""
    state["research"] = "Inspect related modules and recent code changes."
    return state


def planner(state: dict) -> dict:
    """Create a plan using everything currently stored in state."""
    if "research" in state:
        state["plan"] = "Use the research, update related modules, and add tests."
    else:
        state["plan"] = "Update the affected code and add one regression test."

    return state


def run_workflow(issue: str) -> dict:
    """Orchestrate classification, conditional research, and planning."""
    state = {"issue": issue}
    state = classify_issue(state)
    next_agent = route_by_complexity(state)

    if next_agent == "researcher":
        state = researcher(state)

    state = planner(state)
    return state


if __name__ == "__main__":
    issues = [
        "Fix the login button color",
        "Users cannot complete checkout after changing currency when a discount code is active",
    ]

    for issue in issues:
        result = run_workflow(issue)
        print(result)
