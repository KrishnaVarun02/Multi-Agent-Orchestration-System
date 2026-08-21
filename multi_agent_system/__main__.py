"""Command-line entry point for running the package as a program."""

from multi_agent_system.langgraph_workflow import run_langgraph_workflow


def main() -> None:
    """Run one example issue through the deterministic workflow."""
    issue = "Users cannot complete checkout after changing currency"
    result = run_langgraph_workflow(issue)

    print("LangGraph execution order:")
    for agent_name in result["execution_log"]:
        print(f"- {agent_name}")

    print("\nFinal state:")
    print(result)


if __name__ == "__main__":
    main()
