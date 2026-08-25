"""
Model client for N.O.V.A.

Two free API tiers, two independent rate-limit pools:
  - Gemini (Google AI Studio free tier) is the default.
  - Groq (free tier, fast open-weight models) is the automatic fallback.

If the primary provider errors or gets rate-limited mid-conversation,
LangChain's `.with_fallbacks()` transparently retries the same call on the
fallback provider instead of the whole agent loop crashing.
"""

import os

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq


def _build_gemini() -> ChatGoogleGenerativeAI:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Get a free key at "
            "https://aistudio.google.com/apikey and add it to .env"
        )
    return ChatGoogleGenerativeAI(
        model=os.getenv("GEMINI_MODEL", "gemini-flash-latest"),
        google_api_key=api_key,
        temperature=0.3,
        timeout=30,
        max_retries=2,
    )


def _build_groq() -> ChatGroq:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GROQ_API_KEY is not set. Get a free key at "
            "https://console.groq.com/keys and add it to .env"
        )
    return ChatGroq(
        model=os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"),
        api_key=api_key,
        temperature=0.3,
    )


def get_llm():
    """Return the primary LLM wired with an automatic fallback provider."""
    primary_name = os.getenv("PRIMARY_PROVIDER", "gemini").lower()

    if primary_name == "groq":
        primary, fallback = _build_groq(), _build_gemini
    else:
        primary, fallback = _build_gemini(), _build_groq

    # Fallback is built lazily so a missing fallback key doesn't crash
    # startup if you're only using one provider for now.
    try:
        fallback_llm = fallback()
        return primary.with_fallbacks([fallback_llm])
    except RuntimeError:
        return primary
