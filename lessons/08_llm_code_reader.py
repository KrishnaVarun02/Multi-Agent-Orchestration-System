"""Lesson 8: let an LLM select relevant files from a safe index."""

from multi_agent_system.llm_code_reader import llm_code_reader
from multi_agent_system.repository_reader import index_repository


def main() -> None:
    """Index this repository and ask OpenRouter which files matter."""
    state = {
        "issue": "Understand how the LangGraph LLM workflow is assembled",
        "repo_path": ".",
        "execution_log": [],
    }
    indexed_state = {**state, **index_repository(state)}
    result = llm_code_reader(indexed_state)

    print("Selected files:")
    for path in result["selected_files"]:
        print(f"- {path}")

    print("\nReasoning:")
    print(result["file_selection_reasoning"])
    print(f"\nLoaded context characters: {len(result['code_context'])}")


if __name__ == "__main__":
    main()
