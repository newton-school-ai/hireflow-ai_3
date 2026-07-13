import json
from abc import ABC, abstractmethod
from typing import Any

import httpx

from src.config.settings import Settings, get_settings


class LLMClientError(RuntimeError):
    pass


class BaseLLMClient(ABC):
    @abstractmethod
    def chat(self, prompt: str) -> str:
        raise NotImplementedError

    def extract(self, prompt: str) -> Any:
        enhanced_prompt = prompt
        if "json" not in prompt.lower():
            enhanced_prompt += "\n\nReturn the response as a valid JSON list or JSON object. Return ONLY raw JSON, with no explanation or conversational text."
        response = self.chat(enhanced_prompt)
        return _parse_json_response(response)

    def extract_profile(self, resume_text: str) -> dict[str, Any]:
        response = self.chat(_profile_extraction_prompt(resume_text))
        result = _parse_json_response(response)
        if not isinstance(result, dict):
            raise LLMClientError("Extracted profile must be a JSON object")
        return result


class GroqLLMClient(BaseLLMClient):
    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model

    def chat(self, prompt: str) -> str:
        from groq import Groq
        try:
            client = Groq(api_key=self.api_key)
            response = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
            )
            return response.choices[0].message.content or ""
        except Exception as exc:
            raise LLMClientError(f"Groq API error: {exc}") from exc


class GeminiLLMClient(BaseLLMClient):
    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model

    def chat(self, prompt: str) -> str:
        import google.generativeai as genai
        try:
            genai.configure(api_key=self.api_key)
            model = genai.GenerativeModel(self.model)
            response = model.generate_content(prompt)
            return response.text or ""
        except Exception as exc:
            raise LLMClientError(f"Gemini API error: {exc}") from exc


class OpenAILLMClient(BaseLLMClient):
    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model

    def chat(self, prompt: str) -> str:
        from openai import OpenAI
        try:
            client = OpenAI(api_key=self.api_key)
            response = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
            )
            return response.choices[0].message.content or ""
        except Exception as exc:
            raise LLMClientError(f"OpenAI API error: {exc}") from exc


class AnthropicLLMClient(BaseLLMClient):
    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model

    def chat(self, prompt: str) -> str:
        import anthropic
        try:
            client = anthropic.Anthropic(api_key=self.api_key)
            response = client.messages.create(
                model=self.model,
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}],
            )
            if not response.content:
                return ""
            return response.content[0].text
        except Exception as exc:
            raise LLMClientError(f"Anthropic API error: {exc}") from exc


class OllamaLLMClient(BaseLLMClient):
    def __init__(self, base_url: str, model: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model

    def chat(self, prompt: str) -> str:
        try:
            response = httpx.post(
                f"{self.base_url}/api/generate",
                json={"model": self.model, "prompt": prompt, "stream": False},
                timeout=60,
            )
            response.raise_for_status()
            return str(response.json().get("response", ""))
        except Exception as exc:
            raise LLMClientError(f"Ollama API error: {exc}") from exc


def _is_placeholder_or_empty(key: str | None) -> bool:
    if not key:
        return True
    key_strip = key.strip()
    return key_strip == "" or "your_" in key_strip.lower() or key_strip.lower() == "none"


def get_llm_client(settings: Settings | None = None) -> BaseLLMClient:
    settings = settings or get_settings()
    provider = settings.llm_provider.lower().strip()

    if provider == "groq":
        if _is_placeholder_or_empty(settings.groq_api_key):
            raise LLMClientError("GROQ_API_KEY is required when LLM_PROVIDER=groq")
        return GroqLLMClient(settings.groq_api_key, settings.groq_model)

    if provider == "gemini":
        if _is_placeholder_or_empty(settings.google_api_key):
            raise LLMClientError("GOOGLE_API_KEY is required when LLM_PROVIDER=gemini")
        return GeminiLLMClient(settings.google_api_key, settings.gemini_model)

    if provider == "openai":
        if _is_placeholder_or_empty(settings.openai_api_key):
            raise LLMClientError("OPENAI_API_KEY is required when LLM_PROVIDER=openai")
        return OpenAILLMClient(settings.openai_api_key, settings.openai_model)

    if provider == "anthropic":
        if _is_placeholder_or_empty(settings.anthropic_api_key):
            raise LLMClientError("ANTHROPIC_API_KEY is required when LLM_PROVIDER=anthropic")
        return AnthropicLLMClient(settings.anthropic_api_key, settings.anthropic_model)

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


def _parse_json_response(raw_response: str) -> Any:
    text = raw_response.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].strip()

    # Find the first occurrence of '{' or '[' to locate the JSON body
    first_dict = text.find("{")
    first_list = text.find("[")
    
    if first_dict == -1 and first_list == -1:
        raise LLMClientError("LLM response did not contain a JSON object or list")
        
    if first_dict != -1 and (first_list == -1 or first_dict < first_list):
        start = first_dict
        end = text.rfind("}")
    else:
        start = first_list
        end = text.rfind("]")

    if start == -1 or end == -1:
        raise LLMClientError("LLM response did not contain a matching JSON boundary")

    try:
        parsed = json.loads(text[start : end + 1])
    except json.JSONDecodeError as exc:
        raise LLMClientError("LLM response was not valid JSON") from exc

    return parsed
