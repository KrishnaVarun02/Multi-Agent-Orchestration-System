# Multi-Agent Orchestration System

A learning project that builds a GitHub-issue-to-pull-request workflow one safe step at a time.

## Our learning path

1. Python functions and shared workflow state
2. Conditional routing
3. LangGraph orchestration
4. LLM-powered planning and code changes
5. Read-only GitHub integration
6. Docker test sandbox
7. Human-approved pull request creation

## Lessons

Run either completed lesson:

```bash
python3 lessons/01_shared_state.py
python3 lessons/02_conditional_routing.py
python3 lessons/03_typed_agent_state.py
python3 lessons/04_deterministic_agents.py
python3 -m lessons.05_langgraph_stategraph
python3 -m lessons.06_llm_planner
python3 -m lessons.07_local_repository_reader
python3 -m lessons.08_llm_code_reader
python3 -m lessons.09_llm_code_writer
python3 -m lessons.10_llm_test_writer
python3 -m lessons.11_temporary_test_sandbox
python3 -m lessons.12_docker_test_sandbox
python3 -m lessons.13_github_issue_reader ISSUE_URL
python3 -m lessons.14_human_approval
python3 -m lessons.15_git_branch_preparer
```

Before Lesson 6, copy `.env.example` to `.env` and replace the placeholder with
your OpenRouter API key. `.env` is ignored by Git and must never be committed.

`lessons/` contains small, self-contained exercises. We will explain each new line before adding it.

## Run the automated tests

```bash
source .venv/bin/activate
python3 -m pytest
```

## Run the application package

From the repository root, run:

```bash
python3 -m multi_agent_system
```

`multi_agent_system/__init__.py` defines the package; it is not the program's entry point.

Run the compiled LangGraph with its real OpenRouter Code Reader, Planner, Code
Writer, and Test Writer:

```bash
python3 -m multi_agent_system.llm_langgraph_workflow
```

The complete LLM command validates generated patches but does not execute them
by default. Local execution must be explicitly enabled with
`run_llm_workflow(..., execute_tests=True)`. Lesson 11 runs only a trusted,
deterministic example in a temporary copy.

## Build the Docker test sandbox

Start Docker Desktop (or another Docker daemon), then build the reusable image:

```bash
docker build -f docker/Dockerfile.sandbox -t multi-agent-test-sandbox:latest .
python3 -m lessons.12_docker_test_sandbox
```

The full LLM graph uses this Docker runner when `execute_tests=True`. The
container has no network, mounts the patched copy read-only, drops Linux
capabilities, and limits memory, CPU, processes, and execution time.

## Read a GitHub issue

Public issues can be read without a token:

```bash
python3 -m lessons.13_github_issue_reader \
  https://github.com/OWNER/REPOSITORY/issues/NUMBER
```

For private repositories, add a fine-grained `GITHUB_TOKEN` with read-only
Issues permission to `.env`. The token is never printed or sent to LLM prompts.
