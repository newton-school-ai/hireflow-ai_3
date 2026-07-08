import pytest

from src.config.settings import Settings
from src.utils.llm_client import (
    GeminiLLMClient,
    GroqLLMClient,
    LLMClientError,
    OllamaLLMClient,
    OpenAILLMClient,
    get_llm_client,
)


def test_get_llm_client_selects_groq():
    settings = Settings(llm_provider="groq", groq_api_key="test-key")

    client = get_llm_client(settings)

    assert isinstance(client, GroqLLMClient)


def test_get_llm_client_selects_gemini():
    settings = Settings(llm_provider="gemini", google_api_key="test-key")

    client = get_llm_client(settings)

    assert isinstance(client, GeminiLLMClient)


def test_get_llm_client_selects_openai():
    settings = Settings(llm_provider="openai", openai_api_key="test-key")

    client = get_llm_client(settings)

    assert isinstance(client, OpenAILLMClient)


def test_get_llm_client_selects_ollama_without_key():
    settings = Settings(llm_provider="ollama")

    client = get_llm_client(settings)

    assert isinstance(client, OllamaLLMClient)


def test_get_llm_client_requires_groq_key():
    settings = Settings(llm_provider="groq", groq_api_key=None)

    with pytest.raises(LLMClientError, match="GROQ_API_KEY"):
        get_llm_client(settings)
