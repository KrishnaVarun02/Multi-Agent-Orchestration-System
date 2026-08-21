"""Lesson 7: safely read real source files from a local repository."""

from multi_agent_system.langgraph_workflow import AgentState
from multi_agent_system.repository_reader import read_repository


if __name__ == "__main__":
    initial_state: AgentState = {
        "issue": "Understand this repository",
        "repo_path": ".",
        "execution_log": [],
    }
    result = read_repository(initial_state)

    print("Files selected:")
    for file_path in result["repository_files"]:
        print(f"- {file_path}")

    print(f"\nCharacters collected: {len(result['code_context'])}")
