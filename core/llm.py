from google import genai
from google.genai import types
from openai import OpenAI
from typing import List, Dict, Any, Optional
from core.security import SecurityManager
from core.logger import get_logger

logger = get_logger("llm_client")

class LLMClient:
    def __init__(self, provider: str, encrypted_api_key: str):
        self.provider = provider
        sm = SecurityManager()
        self.api_key = sm.decrypt(encrypted_api_key)
        
        if provider == "gemini":
            self.client = genai.Client(api_key=self.api_key)
            self.model_name = 'gemini-2.0-flash'
        elif provider == "openai":
            self.client = OpenAI(api_key=self.api_key)
            self.model_name = "gpt-4-turbo-preview"
        else:
            raise ValueError(f"Unsupported provider: {provider}")

    async def generate(self, prompt: str, history: List[Dict[str, str]] = None, system_instruction: str = "") -> str:
        """Unified generate interface as requested."""
        try:
            if self.provider == "gemini":
                # The new SDK uses a different approach for system instructions and history
                config = types.GenerateContentConfig(
                    system_instruction=system_instruction if system_instruction else None,
                    temperature=0.7
                )
                
                # Simulating chat history with the new SDK
                contents = []
                if history:
                    for msg in history:
                        role = "user" if msg['role'] == "user" else "model"
                        contents.append(types.Content(role=role, parts=[types.Part(text=msg['content'])]))
                
                contents.append(types.Content(role="user", parts=[types.Part(text=prompt)]))
                
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=contents,
                    config=config
                )
                return response.text
                
            elif self.provider == "openai":
                messages = []
                if system_instruction:
                    messages.append({"role": "system", "content": system_instruction})
                if history:
                    messages.extend(history)
                messages.append({"role": "user", "content": prompt})
                
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages
                )
                return response.choices[0].message.content
        except Exception as e:
            logger.error("llm_generation_failed", provider=self.provider, error=str(e))
            raise

    async def generate_response(self, prompt: str, history: List[Dict[str, str]] = None, system_instruction: str = "") -> str:
        """Wrapper for backward compatibility."""
        return await self.generate(prompt, history, system_instruction)

    async def get_embedding(self, text: str) -> List[float]:
        try:
            if self.provider == "gemini":
                response = self.client.models.embed_content(
                    model="models/gemini-embedding-001",
                    contents=[text]
                )
                return response.embeddings[0].values
            elif self.provider == "openai":
                response = self.client.embeddings.create(
                    input=text,
                    model="text-embedding-3-small"
                )
                return response.data[0].embedding
        except Exception as e:
            logger.error("llm_embedding_failed", provider=self.provider, error=str(e))
            raise
