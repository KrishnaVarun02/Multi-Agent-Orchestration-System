"""An OpenRouter-powered Planner node with structured output."""

from pydantic import BaseModel, ConfigDict, Field

from multi_agent_system.langgraph_workflow import AgentState
from multi_agent_system.openrouter_client import get_openrouter_client_and_model


class PlanOutput(BaseModel):
    """The exact response structure required from the model."""

    model_config = ConfigDict(extra="forbid")

    summary: str = Field(description="A concise implementation-plan summary")
    steps: list[str] = Field(description="Ordered implementation steps")
    risks: list[str] = Field(description="Risks and edge cases to verify")


def llm_planner(state: AgentState) -> AgentState:
    """Ask OpenRouter for a structured plan and return state updates."""
    client, model = get_openrouter_client_and_model()

    issue = state["issue"]
    code_context = state["code_context"]
    research = state.get("research", "No extra research was required.")

    completion = client.chat.completions.create(
        model=model,
        max_tokens=1000,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a software-engineering planner. Produce a concise, "
                    "actionable implementation plan. Do not write code."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Issue:\n{issue}\n\n"
                    f"Code context:\n{code_context}\n\n"
                    f"Research:\n{research}"
                ),
            },
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "implementation_plan",
                "strict": True,
                "schema": PlanOutput.model_json_schema(),
            },
        },
        extra_body={"provider": {"require_parameters": True}},
    )

    content = completion.choices[0].message.content
    if not content:
        raise RuntimeError("OpenRouter did not return a plan.")

    plan = PlanOutput.model_validate_json(content)

    return {
        "plan": plan.summary,
        "plan_steps": plan.steps,
        "plan_risks": plan.risks,
        "execution_log": ["llm_planner"],
    }
