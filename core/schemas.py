from pydantic import BaseModel, Field
from typing import List, Optional

class LLMConfig(BaseModel):
    provider: str = "gemini" # gemini or openai
    api_key: str

class TelegramConfig(BaseModel):
    bot_token: str
    allowed_user_ids: List[int]

class DatabaseConfig(BaseModel):
    url: str = "postgresql+asyncpg://user:pass@localhost:5432/simmi"
    redis_url: str = "redis://localhost:6379/0"

class PersonalityConfig(BaseModel):
    name: str = "Simmi"
    owner: str = "Sunny"
    tone: str = "playful but intelligent"
    role: str = "personal AI assistant and executor"
    description: str = "A highly capable autonomous agent."

class WhatsAppConfig(BaseModel):
    enabled: bool = False
    mode: str = "none" # meta or baileys

class VoiceConfig(BaseModel):
    enabled: bool = False
    elevenlabs_api_key: Optional[str] = None
    elevenlabs_voice_id: Optional[str] = None
    response_mode: str = "text" # text or voice

class SimmiConfig(BaseModel):
    personality: PersonalityConfig
    llm: LLMConfig
    telegram: TelegramConfig
    database: DatabaseConfig
    whatsapp: WhatsAppConfig
    voice: VoiceConfig = VoiceConfig()
    storage_path: str = "./storage"
