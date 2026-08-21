# Multi-Agent Orchestration System

A LangGraph-based system that takes a software issue from repository inspection through code and test generation, optional sandbox execution, human approval, and (when explicitly enabled) pull-request creation. It also includes a deterministic workflow useful for examples and tests.

## Prerequisites

- Python with a virtual-environment module
- Docker, when using sandboxed test execution
- Credentials and access required by the configured GitHub and OpenAI integrations

The repository does not define packaging metadata, so run commands from its root.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate       # Windows: .venv\\Scripts\\activate
python -m pip install -r requirements.txt
```

Configure the environment variables and credentials required by the integration modules before using GitHub or LLM-backed steps. Keep tokens out of source control. Docker must be running for `--execute-tests`; without it, use the workflow without sandbox execution or expect the test-runner step to fail.

## Quick start

The package entry point runs a small LangGraph example:

```bash
python -m multi_agent_system
```

For the complete issue-to-PR workflow, provide a full GitHub issue URL:

```bash
python lessons/17_complete_workflow_cli.py https://github.com/OWNER/REPO/issues/1
```

Useful options:

- `--repo-path PATH` selects the local repository (default: `.`).
- `--execute-tests` runs generated changes in the Docker sandbox.
- `--review` enables interactive human review and revision.
- `--create-pr` permits an approved run to push a branch and create a pull request.

Do not use `--create-pr` unless credentials, repository permissions, and the generated patch have been reviewed. An interrupted approval run can be resumed through the workflow's `resume_workflow` API; checkpoint configuration must be supplied by the caller.

## Workflow modes

The deterministic workflow (`multi_agent_system.workflow`) produces simulated context, patches, tests, and PR URLs. It does not edit a repository or create a real pull request. It classifies an issue, optionally researches complex issues, plans a change, and records each agent in `execution_log`.

The LangGraph workflow coordinates issue loading, repository indexing, code reading, classification, research, planning, code and test generation, sandbox testing, human approval, branch preparation, and optional GitHub PR creation. LLM nodes and integration nodes are replaceable in tests. Repository changes, test execution, branch pushes, and PR creation are real operations only when the corresponding workflow options and credentials permit them.

## Testing

Run the test suite from the repository root:

```bash
python -m pytest
```

The tests currently focus on CLI review-payload behavior. Workflow tests commonly replace LLM and external-service nodes, so passing tests does not validate live GitHub, OpenAI, Docker, branch, or pull-request integrations.

## Repository layout

- `multi_agent_system/workflow.py` — deterministic workflow
- `multi_agent_system/llm_langgraph_workflow.py` — configurable LangGraph orchestration
- `lessons/17_complete_workflow_cli.py` — complete command-line interface
- `tests/` — automated tests
- `requirements.txt` — pinned runtime dependencies

## Contributing

Keep workflow transitions, safety checks, CLI behavior, and documentation synchronized. Add tests for changes to routing or state fields, prefer injectable external-service nodes, and document any new credentials or mutating operations.
