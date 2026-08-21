"""Lesson 15: commit approved changes on an isolated local Git branch."""

import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

from multi_agent_system.git_branch_preparer import prepare_local_branch


def run_git(repository: Path, *arguments: str) -> str:
    """Run a trusted Git command for this deterministic lesson."""
    result = subprocess.run(
        ["git", "-C", str(repository), *arguments],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def main() -> None:
    """Show that a branch is created without changing the current worktree."""
    with TemporaryDirectory(prefix="lesson-15-git-") as temp_dir:
        repository = Path(temp_dir)
        run_git(repository, "init", "--quiet")
        original = 'def greeting():\n    return "hello"\n'
        (repository / "app.py").write_text(original, encoding="utf-8")
        run_git(repository, "add", "app.py")
        run_git(
            repository,
            "-c",
            "user.name=Lesson User",
            "-c",
            "user.email=lesson@example.com",
            "commit",
            "--quiet",
            "-m",
            "Initial commit",
        )

        result = prepare_local_branch(
            {
                "repo_path": str(repository),
                "issue": "Update greeting",
                "issue_number": 3,
                "issue_title": "Update greeting",
                "pull_request_approved": True,
                "tests_passed": True,
                "changed_files": ["app.py"],
                "patch": (
                    "--- a/app.py\n+++ b/app.py\n@@ -1,2 +1,2 @@\n"
                    " def greeting():\n-    return \"hello\"\n+    return \"hi\"\n"
                ),
                "test_files": ["tests/test_app.py"],
                "test_patch": (
                    "--- /dev/null\n+++ b/tests/test_app.py\n@@ -0,0 +1 @@\n"
                    "+assert True\n"
                ),
                "execution_log": [],
            }
        )

        branch_code = run_git(
            repository, "show", f"{result['branch_name']}:app.py"
        )
        print(f"Status: {result['branch_status']}")
        print(f"Branch: {result['branch_name']}")
        print(f"Commit: {result['commit_sha']}")
        print(f"Current file unchanged: {(repository / 'app.py').read_text() == original}")
        print(f"Branch contains updated code: {'return \"hi\"' in branch_code}")


if __name__ == "__main__":
    main()
