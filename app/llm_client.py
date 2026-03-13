import os
from typing import Optional

from dotenv import load_dotenv
from groq import Groq


# Load variables from a local .env file if present.
load_dotenv()

_client: Optional[Groq] = None


def get_groq_client() -> Groq:
    """Configure and return a singleton Groq client using environment vars."""

    global _client

    if _client is not None:
        return _client

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY environment variable is not set")

    _client = Groq(api_key=api_key)
    return _client


def call_llm(system_prompt: str, user_message: str, model: Optional[str] = None) -> str:
    """Call the LLM with a system prompt and user message and return text."""

    client = get_groq_client()

    model_name = model or os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        temperature=0.0,
    )

    # The SDK returns a list of choices; we take the first one.
    content = response.choices[0].message.content
    return content or ""