"""Lesson 5: run the workflow through a compiled LangGraph StateGraph."""

from multi_agent_system.langgraph_workflow import run_langgraph_workflow


if __name__ == "__main__":
    result = run_langgraph_workflow(
        "Users cannot complete checkout after changing currency when a discount is active"
    )

    print("LangGraph execution order:")
    for agent_name in result["execution_log"]:
        print(f"- {agent_name}")

    print("\nFinal state:")
    print(result)
