"""Lesson 16: inspect the real PR command without executing it."""

from multi_agent_system.github_pr_opener import build_pr_command


def main() -> None:
    """Print a safe preview of the command produced from workflow state."""
    state = {
        "issue": "Fix checkout",
        "issue_title": "Fix checkout after currency change",
        "issue_number": 7,
        "branch_name": "agent/issue-7-fix-checkout",
        "patch_summary": "Repair currency conversion during checkout.",
        "changed_files": ["checkout.py"],
        "test_files": ["tests/test_checkout.py"],
        "test_status": "passed",
        "test_command": "python3 -m pytest",
    }

    command = build_pr_command(state, "OWNER", "REPOSITORY")
    print("Command preview only; nothing was pushed or created:\n")
    for argument in command:
        print(repr(argument))


if __name__ == "__main__":
    main()
