"""LLM provider abstraction — supports Groq (free) and OpenAI."""

from __future__ import annotations

from langchain_core.language_models import BaseChatModel
from loguru import logger

from src.core.config import settings


def get_llm(temperature: float = 0.3, max_tokens: int = 4096) -> BaseChatModel:
    """
    Get the configured LLM instance.
    
    Supports:
        - Groq (free tier, very fast, uses Llama 3)
        - OpenAI (paid, GPT-4o-mini or GPT-4o)
    """
    provider = settings.LLM_PROVIDER.lower()

    if provider == "groq":
        from langchain_groq import ChatGroq

        if not settings.GROQ_API_KEY or settings.GROQ_API_KEY.startswith("gsk_your"):
            raise ValueError(
                "Groq API key not set! Get a free key at https://console.groq.com "
                "and add it to your .env file."
            )

        logger.info(f"Using Groq LLM: {settings.GROQ_MODEL}")
        return ChatGroq(
            api_key=settings.GROQ_API_KEY,
            model=settings.GROQ_MODEL,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    elif provider == "openai":
        from langchain_openai import ChatOpenAI

        if not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY.startswith("sk-your"):
            raise ValueError(
                "OpenAI API key not set! Get one at https://platform.openai.com "
                "and add it to your .env file."
            )

        logger.info(f"Using OpenAI LLM: {settings.OPENAI_MODEL}")
        return ChatOpenAI(
            api_key=settings.OPENAI_API_KEY,
            model=settings.OPENAI_MODEL,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    elif provider == "nvidia":
        from langchain_openai import ChatOpenAI

        if not settings.NVIDIA_API_KEY or settings.NVIDIA_API_KEY.startswith("nvapi-your"):
            raise ValueError(
                "NVIDIA API key not set! Get one at https://build.nvidia.com "
                "and add it to your .env file."
            )

        logger.info(f"Using NVIDIA LLM: {settings.NVIDIA_MODEL}")
        return ChatOpenAI(
            api_key=settings.NVIDIA_API_KEY,
            base_url="https://integrate.api.nvidia.com/v1",
            model=settings.NVIDIA_MODEL,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    else:
        raise ValueError(f"Unknown LLM provider: {provider}. Use 'groq' or 'openai'.")
