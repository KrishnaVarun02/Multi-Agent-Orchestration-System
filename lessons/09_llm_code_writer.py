"""Lesson 9: ask an LLM for a patch without applying it."""

from multi_agent_system.llm_code_writer import llm_code_writer


def main() -> None:
    """Generate a safe patch proposal for a small example module."""
    state = {
        "issue": "Prevent division by zero in the divide function",
        "selected_files": ["calculator.py"],
        "code_context": (
            "### calculator.py\n"
            "def divide(first, second):\n"
            "    return first / second\n"
        ),
        "plan": "Validate the denominator before division.",
        "plan_steps": [
            "Check whether second is zero",
            "Raise ValueError with a clear message",
        ],
        "plan_risks": ["Existing callers may expect ZeroDivisionError"],
        "execution_log": [],
    }

    result = llm_code_writer(state)

    print("Patch summary:")
    print(result["patch_summary"])
    print("\nChanged files:")
    for path in result["changed_files"]:
        print(f"- {path}")
    print("\nProposed patch (not applied):")
    print(result["patch"])


if __name__ == "__main__":
    main()
