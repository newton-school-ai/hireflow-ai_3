import pytest

from src.config.settings import Settings, get_settings
from src.utils.llm_client import (
    AnthropicLLMClient,
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


def test_get_llm_client_selects_anthropic():
    settings = Settings(llm_provider="anthropic", anthropic_api_key="test-key")
    client = get_llm_client(settings)
    assert isinstance(client, AnthropicLLMClient)


def test_get_llm_client_selects_ollama_without_key():
    settings = Settings(llm_provider="ollama")
    client = get_llm_client(settings)
    assert isinstance(client, OllamaLLMClient)


def test_get_llm_client_requires_groq_key():
    settings = Settings(llm_provider="groq", groq_api_key=None)
    with pytest.raises(LLMClientError, match="GROQ_API_KEY"):
        get_llm_client(settings)

    settings_placeholder = Settings(llm_provider="groq", groq_api_key="your_groq_api_key_here")
    with pytest.raises(LLMClientError, match="GROQ_API_KEY"):
        get_llm_client(settings_placeholder)


def test_get_llm_client_requires_gemini_key():
    settings = Settings(llm_provider="gemini", google_api_key=None)
    with pytest.raises(LLMClientError, match="GOOGLE_API_KEY"):
        get_llm_client(settings)

    settings_placeholder = Settings(llm_provider="gemini", google_api_key="your_google_api_key_here")
    with pytest.raises(LLMClientError, match="GOOGLE_API_KEY"):
        get_llm_client(settings_placeholder)


def test_get_llm_client_requires_openai_key():
    settings = Settings(llm_provider="openai", openai_api_key=None)
    with pytest.raises(LLMClientError, match="OPENAI_API_KEY"):
        get_llm_client(settings)

    settings_placeholder = Settings(llm_provider="openai", openai_api_key="your_openai_api_key_here")
    with pytest.raises(LLMClientError, match="OPENAI_API_KEY"):
        get_llm_client(settings_placeholder)


def test_get_llm_client_requires_anthropic_key():
    settings = Settings(llm_provider="anthropic", anthropic_api_key=None)
    with pytest.raises(LLMClientError, match="ANTHROPIC_API_KEY"):
        get_llm_client(settings)

    settings_placeholder = Settings(llm_provider="anthropic", anthropic_api_key="your_anthropic_api_key_here")
    with pytest.raises(LLMClientError, match="ANTHROPIC_API_KEY"):
        get_llm_client(settings_placeholder)


def test_get_llm_client_invalid_provider():
    settings = Settings(llm_provider="invalid")
    with pytest.raises(LLMClientError, match="Unsupported LLM provider"):
        get_llm_client(settings)


def test_live_llm_client():
    settings = get_settings()
    provider = settings.llm_provider.lower().strip()
    
    # Check if we have active credentials
    has_credentials = False
    if provider == "groq" and settings.groq_api_key and "your_" not in settings.groq_api_key:
        has_credentials = True
    elif provider == "gemini" and settings.google_api_key and "your_" not in settings.google_api_key:
        has_credentials = True
    elif provider == "openai" and settings.openai_api_key and "your_" not in settings.openai_api_key:
        has_credentials = True
    elif provider == "anthropic" and settings.anthropic_api_key and "your_" not in settings.anthropic_api_key:
        has_credentials = True
    elif provider == "ollama":
        # Check if Ollama is running
        import httpx
        try:
            httpx.get(settings.ollama_base_url, timeout=1.0)
            has_credentials = True
        except Exception:
            has_credentials = False

    if not has_credentials:
        pytest.skip(f"Live provider '{provider}' API key/endpoint not configured. Skipping live test.")

    client = get_llm_client(settings)
    
    # Test chat response
    chat_response = client.chat("Respond with only the word 'Hello'.")
    assert chat_response is not None
    assert "hello" in chat_response.lower()

    # Test extract response
    prompt = "Extract skills as a JSON list from this text: 'Senior developer with Python, FastAPI, and Kubernetes experience.'"
    result = client.extract(prompt)
    assert isinstance(result, (list, dict))
    
    if isinstance(result, list):
        skills = [s.lower() for s in result]
    else:
        # Check dictionary keys / values
        skills_val = result.get("skills", result)
        if isinstance(skills_val, list):
            skills = [s.lower() for s in skills_val]
        else:
            skills = [str(skills_val).lower()]

    assert any("python" in s for s in skills)
