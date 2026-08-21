"""Lesson 6: use an OpenRouter-hosted model for the Planner node."""

import os

from dotenv import load_dotenv

from multi_agent_system.llm_langgraph_workflow import run_llm_workflow


if __name__ == "__main__":
    load_dotenv()

    api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit(
            "OPENROUTER_API_KEY is missing. Copy .env.example to .env and add your key."
        )

    result = run_llm_workflow(
        "Users cannot complete checkout after changing currency when a discount is active"
    )

    print("LLM-generated plan:")
    print(result["plan"])

    print("\nSteps:")
    for number, step in enumerate(result["plan_steps"], start=1):
        print(f"{number}. {step}")

    print("\nRisks:")
    for risk in result["plan_risks"]:
        print(f"- {risk}")
