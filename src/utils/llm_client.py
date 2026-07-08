import json
from abc import ABC, abstractmethod
from typing import Any

import httpx

from src.config.settings import Settings, get_settings


class LLMClientError(RuntimeError):
    pass


class BaseLLMClient(ABC):
    @abstractmethod
    def generate(self, prompt: str) -> str:
        raise NotImplementedError

    def extract_profile(self, resume_text: str) -> dict[str, Any]:
        response = self.generate(_profile_extraction_prompt(resume_text))
        return _parse_json_response(response)


class GroqLLMClient(BaseLLMClient):
    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model

    def generate(self, prompt: str) -> str:
        from groq import Groq

        client = Groq(api_key=self.api_key)
        response = client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        return response.choices[0].message.content or ""


class GeminiLLMClient(BaseLLMClient):
    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model

    def generate(self, prompt: str) -> str:
        import google.generativeai as genai

        genai.configure(api_key=self.api_key)
        model = genai.GenerativeModel(self.model)
        response = model.generate_content(prompt)
        return response.text or ""


class OpenAILLMClient(BaseLLMClient):
    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model

    def generate(self, prompt: str) -> str:
        from openai import OpenAI

        client = OpenAI(api_key=self.api_key)
        response = client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        return response.choices[0].message.content or ""


class OllamaLLMClient(BaseLLMClient):
    def __init__(self, base_url: str, model: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model

    def generate(self, prompt: str) -> str:
        response = httpx.post(
            f"{self.base_url}/api/generate",
            json={"model": self.model, "prompt": prompt, "stream": False},
            timeout=60,
        )
        response.raise_for_status()
        return str(response.json().get("response", ""))


def get_llm_client(settings: Settings | None = None) -> BaseLLMClient:
    settings = settings or get_settings()
    provider = settings.llm_provider.lower().strip()

    if provider == "groq":
        if not settings.groq_api_key:
            raise LLMClientError("GROQ_API_KEY is required when LLM_PROVIDER=groq")
        return GroqLLMClient(settings.groq_api_key, settings.groq_model)

    if provider == "gemini":
        if not settings.google_api_key:
            raise LLMClientError("GOOGLE_API_KEY is required when LLM_PROVIDER=gemini")
        return GeminiLLMClient(settings.google_api_key, settings.gemini_model)

    if provider == "openai":
        if not settings.openai_api_key:
            raise LLMClientError("OPENAI_API_KEY is required when LLM_PROVIDER=openai")
        return OpenAILLMClient(settings.openai_api_key, settings.openai_model)

    if provider == "ollama":
        return OllamaLLMClient(settings.ollama_base_url, settings.ollama_model)

    raise LLMClientError(f"Unsupported LLM provider: {settings.llm_provider}")


def _profile_extraction_prompt(resume_text: str) -> str:
    return f"""
Extract a HireFlow user profile from this resume text.

Return only valid JSON with these fields:
name string, email string, skills array of strings, mode "internship" or "job",
weekly_quota integer, target_roles array of strings, preferred_locations array of
strings, min_stipend integer or null, experience array, education array,
projects array.

Use "job" for mode unless the resume clearly targets internships. Use 10 for
weekly_quota when it is not present.

Resume text:
{resume_text}
""".strip()


def _parse_json_response(raw_response: str) -> dict[str, Any]:
    text = raw_response.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].strip()

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise LLMClientError("LLM response did not contain a JSON object")

    try:
        parsed = json.loads(text[start : end + 1])
    except json.JSONDecodeError as exc:
        raise LLMClientError("LLM response was not valid JSON") from exc

    if not isinstance(parsed, dict):
        raise LLMClientError("LLM response JSON must be an object")
    return parsed
