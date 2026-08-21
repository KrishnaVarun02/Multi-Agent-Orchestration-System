"""Create the shared OpenRouter client used by LLM-powered agents."""

import os

from dotenv import load_dotenv
from openai import OpenAI


def get_openrouter_client_and_model() -> tuple[OpenAI, str]:
    """Load configuration and return a client plus model name."""
    load_dotenv()

    api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
    model = (
        os.getenv("OPENROUTER_MODEL")
        or os.getenv("OPENAI_MODEL")
        or "openai/gpt-5.6-luna"
    )

    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is missing from .env.")

    if "/" not in model:
        model = f"openai/{model}"

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )
    return client, model
