"""Lesson 11: apply trusted patches and run pytest in a temporary copy."""

from pathlib import Path
from tempfile import TemporaryDirectory

from multi_agent_system.sandbox_runner import run_patch_in_sandbox


def main() -> None:
    """Demonstrate that sandbox changes never touch the original project."""
    with TemporaryDirectory(prefix="lesson-11-original-") as temp_dir:
        repository = Path(temp_dir)
        source_file = repository / "app.py"
        original = 'def greeting():\n    return "hello"\n'
        source_file.write_text(original, encoding="utf-8")

        state = {
            "repo_path": str(repository),
            "changed_files": ["app.py"],
            "patch": (
                "--- a/app.py\n+++ b/app.py\n@@ -1,2 +1,2 @@\n"
                " def greeting():\n-    return \"hello\"\n+    return \"hi\"\n"
            ),
            "test_files": ["tests/test_app.py"],
            "test_patch": (
                "--- /dev/null\n+++ b/tests/test_app.py\n@@ -0,0 +1,5 @@\n"
                "+from app import greeting\n+\n+\n"
                "+def test_greeting():\n+    assert greeting() == \"hi\"\n"
            ),
            "execute_tests": True,
            "execution_log": [],
        }

        result = run_patch_in_sandbox(state)

        print(f"Sandbox status: {result['test_status']}")
        print(result["test_output"])
        print(f"Original file unchanged: {source_file.read_text() == original}")
        print(f"Test file created in original: {(repository / 'tests').exists()}")


if __name__ == "__main__":
    main()
