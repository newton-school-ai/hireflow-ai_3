import json
import httpx
import re
from typing import Optional, Dict, Any
from src.config.settings import settings

class LLMClient:
    """
    A unified client for calling various LLM providers (Groq, Gemini, OpenAI, Ollama)
    with a consistent interface.
    """
    
    def __init__(self):
        self.provider = settings.LLM_PROVIDER.lower()
        
    def generate_text(self, system_prompt: str, user_prompt: str) -> str:
        """
        Generic method to generate text based on system and user prompts.
        """
        if self.provider == "groq":
            return self._call_groq(system_prompt, user_prompt)
        elif self.provider == "gemini":
            return self._call_gemini(system_prompt, user_prompt)
        elif self.provider == "openai":
            return self._call_openai(system_prompt, user_prompt)
        elif self.provider == "ollama":
            return self._call_ollama(system_prompt, user_prompt)
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")
            
    def extract_profile(self, resume_text: str) -> Dict[str, Any]:
        """
        Extracts structured profile information from resume text using the LLM.
        """
        system_prompt = (
            "You are an expert recruitment assistant. Extract structured candidate profile "
            "information from the provided resume text. Respond ONLY with a valid, clean JSON object. "
            "Do not include any preambles, explanations, or markdown code blocks (like ```json). "
            "The JSON must have the following schema:\n"
            "{\n"
            "  \"name\": \"string\",\n"
            "  \"email\": \"string\",\n"
            "  \"skills\": [\"string\"],\n"
            "  \"experience\": [\n"
            "    {\n"
            "      \"job_title\": \"string\",\n"
            "      \"company\": \"string\",\n"
            "      \"duration\": \"string\",\n"
            "      \"description\": \"string\"\n"
            "    }\n"
            "  ],\n"
            "  \"education\": [\n"
            "    {\n"
            "      \"degree\": \"string\",\n"
            "      \"institution\": \"string\",\n"
            "      \"year\": \"string\"\n"
            "    }\n"
            "  ]\n"
            "}"
        )
        
        user_prompt = f"Resume text:\n{resume_text}"
        
        response_text = self.generate_text(system_prompt, user_prompt)
        
        # Clean response text in case the LLM returned markdown blocks
        clean_json = response_text.strip()
        if clean_json.startswith("```"):
            # Strip first line (e.g. ```json) and last line (```)
            lines = clean_json.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            clean_json = "\n".join(lines).strip()
            
        try:
            return json.loads(clean_json)
        except json.JSONDecodeError:
            # Fallback regex extraction if JSON is wrapped in some other way
            match = re.search(r"\{.*\}", clean_json, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except json.JSONDecodeError:
                    pass
            # Default fallback structure if parsing failed completely
            return {
                "name": "",
                "email": "",
                "skills": [],
                "experience": [],
                "education": [],
                "raw_extraction_error": True,
                "raw_text": response_text
            }

    def _call_groq(self, system_prompt: str, user_prompt: str) -> str:
        if not settings.GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY is not set in environment settings.")
        
        # Use httpx for a direct HTTP post or import groq SDK
        # Imports groq SDK directly since we have it in requirements
        from groq import Groq
        client = Groq(api_key=settings.GROQ_API_KEY)
        completion = client.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1
        )
        return completion.choices[0].message.content

    def _call_gemini(self, system_prompt: str, user_prompt: str) -> str:
        if not settings.GOOGLE_API_KEY:
            raise ValueError("GOOGLE_API_KEY is not set in environment settings.")
        import google.generativeai as genai
        genai.configure(api_key=settings.GOOGLE_API_KEY)
        model = genai.GenerativeModel(
            model_name=settings.GEMINI_MODEL,
            system_instruction=system_prompt
        )
        response = model.generate_content(
            user_prompt,
            generation_config=genai.GenerationConfig(temperature=0.1)
        )
        return response.text

    def _call_openai(self, system_prompt: str, user_prompt: str) -> str:
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is not set in environment settings.")
        from openai import OpenAI
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        completion = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1
        )
        return completion.choices[0].message.content

    def _call_ollama(self, system_prompt: str, user_prompt: str) -> str:
        # Use httpx to call local Ollama service
        url = f"{settings.OLLAMA_BASE_URL}/api/chat"
        payload = {
            "model": settings.OLLAMA_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "stream": False,
            "options": {
                "temperature": 0.1
            }
        }
        with httpx.Client() as client:
            response = client.post(url, json=payload, timeout=60.0)
            response.raise_for_status()
            data = response.json()
            return data["message"]["content"]
