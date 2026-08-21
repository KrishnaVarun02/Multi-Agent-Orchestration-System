"""Lesson 10: ask an LLM for pytest tests without applying them."""

from multi_agent_system.llm_test_writer import llm_test_writer


def main() -> None:
    """Generate a test proposal for a small code-change example."""
    state = {
        "issue": "Prevent division by zero in the divide function",
        "repository_files": ["calculator.py"],
        "code_context": (
            "### calculator.py\n"
            "def divide(first, second):\n"
            "    return first / second\n"
        ),
        "plan": "Validate the denominator before division.",
        "patch": (
            "--- a/calculator.py\n+++ b/calculator.py\n"
            "@@ -1,2 +1,4 @@\n def divide(first, second):\n"
            "+    if second == 0:\n"
            "+        raise ValueError('second cannot be zero')\n"
            "     return first / second\n"
        ),
        "execution_log": [],
    }

    result = llm_test_writer(state)

    print("Test summary:")
    print(result["test_summary"])
    print("\nTest files:")
    for path in result["test_files"]:
        print(f"- {path}")
    print("\nProposed test patch (not applied):")
    print(result["test_patch"])
    print("\nSuggested command (not executed):")
    print(result["test_command"])


if __name__ == "__main__":
    main()
