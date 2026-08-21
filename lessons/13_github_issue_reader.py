"""Lesson 13: fetch a real GitHub issue through the read-only API."""

import argparse

from multi_agent_system.github_issue_reader import github_issue_reader


def main() -> None:
    """Read an issue URL supplied on the command line and print its fields."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "issue_url",
        help="A URL like https://github.com/OWNER/REPO/issues/NUMBER",
    )
    arguments = parser.parse_args()

    result = github_issue_reader(
        {"issue_url": arguments.issue_url, "execution_log": []}
    )

    print(f"Repository: {result['repository_owner']}/{result['repository_name']}")
    print(f"Issue number: {result['issue_number']}")
    print(f"Title: {result['issue_title']}")
    print(f"Labels: {', '.join(result['issue_labels']) or 'none'}")
    print(f"GitHub authentication: {result['github_authentication']}")
    print("\nBody:")
    print(result["issue_body"])


if __name__ == "__main__":
    main()
