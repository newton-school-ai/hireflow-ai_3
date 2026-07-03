"""
Unified LLM client supporting Groq, Gemini, OpenAI, and Ollama.

Usage:
    from src.utils.llm_client import get_llm_client
    client = get_llm_client()
    profile_data = await client.extract_profile_from_resume(resume_text)
"""

import json
import logging
import re

import httpx

from src.config.settings import get_settings

logger = logging.getLogger(__name__)

# Prompt template for structured resume extraction
RESUME_EXTRACTION_PROMPT = """You are a structured data extraction engine. Extract the following fields from the resume text below.
Return ONLY a valid JSON object with these keys (use null for missing fields, [] for empty lists):

{
  "name": "full name",
  "email": "email address",
  "skills": ["list", "of", "technical", "skills"],
  "experience": [
    {
      "title": "job title",
      "company": "company name",
      "duration": "time period",
      "description": "brief description"
    }
  ],
  "education": [
    {
      "degree": "degree name",
      "institution": "school name",
      "year": "graduation year"
    }
  ],
  "projects": [
    {
      "name": "project name",
      "description": "brief description",
      "technologies": ["tech1", "tech2"]
    }
  ],
  "target_roles": ["roles the candidate seems suited for based on their experience"],
  "preferred_locations": ["locations mentioned or inferred"]
}

Resume text:
---
{resume_text}
---

Return ONLY the JSON object. No markdown, no explanation."""


class LLMClient:
    """
    Unified LLM client that routes requests to the configured provider.
    Supports: groq, gemini, openai, ollama.
    """

    def __init__(self):
        self.settings = get_settings()
        self.provider = self.settings.llm_provider.lower()

    async def _call_groq(self, prompt: str) -> str:
        """Call Groq API (OpenAI-compatible endpoint)."""
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.settings.groq_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.settings.groq_model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
            "max_tokens": 2048,
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]

    async def _call_gemini(self, prompt: str) -> str:
        """Call Google Gemini API."""
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.settings.gemini_model}:generateContent"
            f"?key={self.settings.google_api_key}"
        )
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.1, "maxOutputTokens": 2048},
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]

    async def _call_openai(self, prompt: str) -> str:
        """Call OpenAI API."""
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.settings.openai_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": "gpt-3.5-turbo",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
            "max_tokens": 2048,
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]

    async def _call_ollama(self, prompt: str) -> str:
        """Call local Ollama API."""
        url = f"{self.settings.ollama_base_url}/api/generate"
        payload = {
            "model": self.settings.ollama_model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.1},
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["response"]

    async def generate(self, prompt: str) -> str:
        """
        Route a prompt to the configured LLM provider and return the raw response.
        """
        provider_map = {
            "groq": self._call_groq,
            "gemini": self._call_gemini,
            "openai": self._call_openai,
            "ollama": self._call_ollama,
        }

        handler = provider_map.get(self.provider)
        if handler is None:
            raise ValueError(
                f"Unsupported LLM provider: '{self.provider}'. "
                f"Supported: {list(provider_map.keys())}"
            )

        logger.info("Calling LLM provider: %s", self.provider)
        return await handler(prompt)

    async def extract_profile_from_resume(self, resume_text: str) -> dict:
        """
        Send resume text to the LLM and extract structured profile data.
        Returns a dict with extracted fields.
        Raises ValueError if the LLM response cannot be parsed as JSON.
        """
        prompt = RESUME_EXTRACTION_PROMPT.replace("{resume_text}", resume_text)
        raw_response = await self.generate(prompt)

        # Try to parse JSON from the response (LLMs sometimes wrap in markdown)
        try:
            return json.loads(raw_response)
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code block
            json_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw_response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(1))
            # Last resort: find first { to last }
            start = raw_response.find("{")
            end = raw_response.rfind("}")
            if start != -1 and end != -1:
                return json.loads(raw_response[start : end + 1])
            raise ValueError(
                f"Could not parse LLM response as JSON. Raw response: {raw_response[:500]}"
            )


def get_llm_client() -> LLMClient:
    """Factory function to create an LLMClient instance."""
    return LLMClient()
