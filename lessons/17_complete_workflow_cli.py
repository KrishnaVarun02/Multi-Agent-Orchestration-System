"""Lesson 17: run the complete issue-to-PR graph from one command."""

import argparse
from pathlib import Path
from typing import Any

from multi_agent_system.langgraph_workflow import AgentState
from multi_agent_system.llm_langgraph_workflow import (
    resume_workflow,
    run_github_issue_workflow,
)


def parse_arguments() -> argparse.Namespace:
    """Convert terminal arguments into a Python namespace object."""
    parser = argparse.ArgumentParser(
        description="Run the complete GitHub issue-to-pull-request workflow."
    )
    parser.add_argument("issue_url", help="Full GitHub issue URL")
    parser.add_argument(
        "--repo-path",
        default=".",
        help="Local repository root (default: current directory)",
    )
    parser.add_argument(
        "--execute-tests",
        action="store_true",
        help="Run generated changes in the Docker sandbox",
    )
    parser.add_argument(
        "--review",
        action="store_true",
        help="Interactively reject and revise without enabling PR creation",
    )
    parser.add_argument(
        "--create-pr",
        action="store_true",
        help="Allow an approved run to push its branch and create a PR",
    )
    return parser.parse_args()


def get_review_payload(state: AgentState) -> dict[str, Any] | None:
    """Return the human-review data when LangGraph has paused."""
    interrupts = state.get("__interrupt__", [])
    if not interrupts:
        return None
    return interrupts[0].value


def print_review(review: dict[str, Any]) -> None:
    """Display the important generated artifacts before approval."""
    print("\n=== HUMAN REVIEW REQUIRED ===")
    print(f"Issue: {review['issue']}")
    print(f"Test status: {review['test_status']}")
    print(
        "Revision: "
        f"{review.get('revision_count', 0)} of "
        f"{review.get('max_revision_attempts', 2)}"
    )
    print(f"\nPatch summary:\n{review['patch_summary']}")
    print(f"\nChanged files: {', '.join(review['changed_files'])}")
    print(f"\nCode patch:\n{review['patch']}")
    print(f"\nTest summary:\n{review['test_summary']}")
    print(f"\nTest files: {', '.join(review['test_files'])}")
    print(f"\nTest patch:\n{review['test_patch']}")


def print_final_status(state: AgentState) -> None:
    """Explain where the graph stopped and whether it created a PR."""
    print("\nExecution order:")
    for node_name in state.get("execution_log", []):
        print(f"- {node_name}")

    if state.get("pr_url"):
        print(f"\nPull request: {state['pr_url']}")
    elif state.get("pr_status"):
        print(f"\nPR status: {state['pr_status']}")
    elif state.get("test_status") != "passed":
        if state.get("code_generation_status") == "failed":
            print("\nWorkflow stopped at code generation:")
            print(state.get("code_generation_error", "Unknown generation error"))
        elif state.get("test_generation_status") == "failed":
            print("\nWorkflow stopped at test generation:")
            print(state.get("test_generation_error", "Unknown generation error"))
        else:
            print(f"\nWorkflow stopped at tests: {state.get('test_status')}")
            print(state.get("test_output", ""))
            print("\nGenerated change that was tested:")
            print(f"Summary: {state.get('patch_summary', 'Not available')}")
            print(f"Files: {', '.join(state.get('changed_files', []))}")
            print(state.get("patch", ""))
            print("\nGenerated tests:")
            print(f"Summary: {state.get('test_summary', 'Not available')}")
            print(f"Files: {', '.join(state.get('test_files', []))}")
            print(state.get("test_patch", ""))
    elif state.get("approval_status"):
        print(f"\nApproval status: {state['approval_status']}")


def main() -> None:
    """Start, review, and optionally resume the complete workflow."""
    arguments = parse_arguments()
    repository = Path(arguments.repo_path).resolve()

    state = run_github_issue_workflow(
        arguments.issue_url,
        repo_path=str(repository),
        execute_tests=arguments.execute_tests,
    )
    while True:
        review = get_review_payload(state)
        if review is None:
            print_final_status(state)
            return

        print_review(review)
        if not arguments.review and not arguments.create_pr:
            print(
                "\nPreview complete. Nothing was pushed. Add --review to "
                "request revisions or --create-pr to enable PR approval."
            )
            return

        decision = input(
            "\nType approve, reject, or stop: "
        ).strip().lower()
        if decision == "approve" and not arguments.create_pr:
            print("\nPreview approved. Nothing was pushed because --create-pr is off.")
            return
        if decision == "stop":
            print("\nReview stopped. Nothing was pushed.")
            return

        feedback = ""
        if decision == "approve":
            repository_name = (
                f"{state['repository_owner']}/{state['repository_name']}"
            )
            confirmed_repository = input(
                f"Type {repository_name} to confirm the target repository: "
            )
            if confirmed_repository.strip() != repository_name:
                decision = "reject"
                feedback = "Repository confirmation failed."
        else:
            decision = "reject"
            feedback = input(
                "Describe the required revision, or leave blank to reject: "
            ).strip()

        state = resume_workflow(
            state["workflow_thread_id"], decision, feedback
        )


if __name__ == "__main__":
    main()
